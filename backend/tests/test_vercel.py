"""Running on Vercel: the function entry, vercel.json, start-up, email, addresses and downloads.

Nothing here needs Vercel, a database or the network. The routing rules in vercel.json are read the
way Vercel compiles them (each "source" is a regular expression over the whole path).
"""
from __future__ import annotations

import ast
import asyncio
import importlib.util
import inspect
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import types
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from vexen import config, db, deps, mailer, serverless, site, startup, urls

BACKEND = Path(__file__).resolve().parent.parent
REPO = BACKEND.parent
VERCEL_JSON = json.loads((REPO / "vercel.json").read_text(encoding="utf-8"))
SITE = "https://vexen.example.test"
GOOD = {
    "MONGO_URL": "mongodb+srv://app:secret123@cluster0.abcde.mongodb.net/?retryWrites=true&w=majority",
    "JWT_SECRET": "x" * 40,
    "API_KEY_PEPPER": "pepper",
    "PUBLIC_APP_URL": SITE,
}


def _good(monkeypatch, **changes):
    for name, value in {**GOOD, **changes}.items():
        if value is None:
            monkeypatch.delenv(name, raising=False)
        else:
            monkeypatch.setenv(name, value)


# --------------------------------------------------------------------------- #
# The function Vercel runs
# --------------------------------------------------------------------------- #
def test_the_vercel_entry_hands_over_the_servers_app():
    """Loaded the way Vercel loads it (by file path, in a fresh interpreter, from the project root)."""
    code = (
        "import importlib.util, os, sys\n"
        "spec = importlib.util.spec_from_file_location('api.index', sys.argv[1])\n"
        "module = importlib.util.module_from_spec(spec)\n"
        "spec.loader.exec_module(module)\n"
        "import server\n"
        "print(type(module.app).__name__, module.app is server.app, os.environ.get('VEXEN_PLATFORM'))\n"
    )
    env = {k: v for k, v in os.environ.items() if not k.startswith(("VERCEL", "VEXEN_", "PYTHONPATH"))}
    result = subprocess.run([sys.executable, "-c", code, str(REPO / "api" / "index.py")],
                            cwd=REPO, env=env, capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stderr[-3000:]
    assert result.stdout.split()[-3:] == ["FastAPI", "True", "vercel"]


def test_the_entry_names_its_app_at_the_top_level():
    tree = ast.parse((REPO / "api" / "index.py").read_text(encoding="utf-8"))
    assigned = {target.id for node in tree.body if isinstance(node, ast.Assign)
                for target in node.targets if isinstance(target, ast.Name)}
    assert "app" in assigned  # Vercel looks for a top-level ASGI app called `app`


def _requirements(path: Path) -> list:
    lines = (raw.split("#", 1)[0].strip() for raw in path.read_text(encoding="utf-8").splitlines())
    return sorted(line.lower() for line in lines if line)


def test_the_function_installs_exactly_the_servers_pinned_packages():
    function = _requirements(REPO / "api" / "requirements.txt")
    assert function == _requirements(BACKEND / "requirements.txt"), "change api/ and backend/ requirements together"
    assert all("==" in line for line in function)
    assert not any(line.startswith("-") for line in function)  # Vercel's builder cannot follow -r includes


def test_the_function_runs_python_3_12():
    assert (REPO / "api" / ".python-version").read_text(encoding="utf-8").strip() == "3.12"


# --------------------------------------------------------------------------- #
# vercel.json: building, the function's limits, routing and headers
# --------------------------------------------------------------------------- #
def test_vercel_builds_the_website_from_the_lockfile():
    assert VERCEL_JSON["framework"] is None  # "Other": no preset adds a catch-all of its own
    install = VERCEL_JSON["installCommand"]
    assert install.startswith("cd frontend && yarn install") and "--frozen-lockfile" in install
    assert VERCEL_JSON["buildCommand"] == "sh frontend/vercel-build.sh"
    assert VERCEL_JSON["outputDirectory"] == "frontend/build"
    # One region (all Hobby allows), next to the database: pdx1 (Portland) for an Atlas cluster in AWS
    # Oregon. DEPLOY.md (step 1.2) has owners of a cluster elsewhere change it, so any region code passes.
    (region,) = VERCEL_JSON["regions"]
    assert re.fullmatch(r"[a-z]{3}\d", region), region


def test_the_function_outlasts_the_websites_longest_wait_and_carries_nothing_private():
    function = VERCEL_JSON["functions"]["api/index.py"]
    # The website's longest wait is the rule writer's (two AI attempts of up to 45 seconds each).
    waits = [int(ms) for path in (REPO / "frontend" / "src").rglob("*.js")
             for ms in re.findall(r"timeout:\s*(\d{4,})", path.read_text(encoding="utf-8"))]
    assert waits and max(waits) / 1000 < function["maxDuration"] <= 300  # 300 s is the Hobby plan's most
    assert VERCEL_JSON["fluid"] is True  # ...with Fluid compute; without it Hobby stops at 60 s
    excluded = function["excludeFiles"].strip("{}").split(",")
    for folder in ("frontend/**", "deck/**", "memory/**", ".demovideo/**", "test_reports/**", "tests/**",
                   "backend/tests/**", "**/.env", "**/.env.*", ".gitconfig", "**/*.pem", "**/*.key"):
        assert folder in excluded, folder
    # includeFiles is added after excludeFiles is applied, so it names only the server's own modules:
    # a pattern such as vexen/** would bring back a stray .env or cache file that excludeFiles removed.
    assert function["includeFiles"] == "backend/{server.py,vexen/*.py}"
    shipped = [p for p in (BACKEND / "vexen").rglob("*") if p.is_file() and "__pycache__" not in p.parts]
    assert shipped and all(p.parent.name == "vexen" and p.suffix == ".py" for p in shipped), \
        "a file under vexen/ that is not a top-level .py module would be left out of the function"


def _rewrite(path: str):
    """Where a request goes after the files on disk: the first rewrite whose source matches."""
    for rule in VERCEL_JSON["rewrites"]:
        if re.fullmatch(rule["source"], path):
            return rule["destination"]
    return None


@pytest.mark.parametrize("path", [
    "/api", "/api/health", "/api/v1/authorize", "/api/does-not-exist.json",
    "/api/public/approvals/eyJhIjoxfQ.c2lnbmF0dXJlMTIz",
])
def test_every_api_address_goes_to_the_function(path):
    assert _rewrite(path) == "/api/index"


@pytest.mark.parametrize("path", [
    "/app", "/app/agents", "/login", "/signup", "/contact", "/app/agents/",
    "/approve/eyJhIjoxfQ.c2lnbmF0dXJlMTIz",   # signed links contain a dot
    "/join/eyJhIjoxfQ.c2lnbmF0dXJlMTIz",
    "/join/looks-like-a-file.js",             # even one that ends like a file name
])
def test_every_page_address_opens_the_app(path):
    assert _rewrite(path) == "/index.html"


@pytest.mark.parametrize("path", [
    "/static/js/main.deadbeef.js", "/static/css/gone.css", "/static/media/logo", "/icons/nope.png",
    "/favicon.ico", "/nothing.map", "/other-robots.txt", "/docs/vexen-cap-table.pdf", "/demo/missing.mp4",
])
def test_a_missing_file_is_a_404_never_a_page_of_html(path):
    assert _rewrite(path) is None


def test_only_api_and_the_addresses_under_it_belong_to_the_function():
    for path in ("/apiary", "/apis", "/app/api"):
        assert _rewrite(path) == "/index.html", path


def test_vercel_and_the_container_agree_on_what_looks_like_a_file():
    for suffix in site._FILE_SUFFIXES:
        assert _rewrite(f"/some/missing{suffix}") is None, suffix
        assert _rewrite(f"/approve/body{suffix}") == "/index.html", suffix


def _headers(path: str, query=()) -> dict:
    found: dict = {}
    for rule in VERCEL_JSON["headers"]:
        if not re.fullmatch(rule["source"], path):
            continue
        if any(cond["type"] == "query" and cond["key"] not in query for cond in rule.get("has", [])):
            continue
        for header in rule["headers"]:
            key = header["key"].lower()
            assert found.get(key, header["value"]) == header["value"], f"two rules disagree on {key} for {path}"
            found[key] = header["value"]
    return found


def test_the_browser_protections_are_the_servers_own():
    for path in ("/", "/app/agents", "/static/js/main.abc123.js", "/demo/vexen-demo.mp4", "/approve/a.b"):
        headers = _headers(path)
        for name, value in site._SECURITY_HEADERS:
            assert headers[name] == value, (path, name)
    # The function adds them itself (site.SecurityHeaders); vercel.json must not add a second copy.
    assert _headers("/api/health") == {} and _headers("/api") == {}


def test_files_are_cached_to_match_how_they_change():
    assert _headers("/static/js/main.abc123.js")["cache-control"] == "public, max-age=31536000, immutable"
    for path in ("/", "/index.html", "/sw.js", "/manifest.json", "/asset-manifest.json", "/robots.txt",
                 "/app/agents", "/approve/eyJhIjoxfQ.c2lnbmF0dXJlMTIz"):
        assert _headers(path)["cache-control"] == "no-cache", path


def test_a_file_asked_for_with_download_is_saved_not_opened():
    assert _headers("/demo/vexen-demo.mp4", query={"download"})["content-disposition"] == "attachment"
    assert "content-disposition" not in _headers("/demo/vexen-demo.mp4")


_CRON_FIELD = re.compile(r"(\*|\d+(-\d+)?)(/\d+)?(,(\*|\d+(-\d+)?)(/\d+)?)*")


def _is_cron(schedule: str) -> bool:
    """Five fields of numbers, ranges, steps and lists: the cron expressions Vercel takes."""
    fields = schedule.split()
    return len(fields) == 5 and all(_CRON_FIELD.fullmatch(field) for field in fields)


def test_the_email_schedule_calls_the_scheduled_run():
    (cron,) = VERCEL_JSON["crons"]
    assert cron["path"] == "/api/internal/outbox"
    assert cron["path"] in {route.path for route in serverless.router.routes}
    # Daily by default, which every plan accepts. DEPLOY.md (section 6) has Pro owners make it every
    # 5 minutes; that change must not fail these tests (Vercel itself refuses it on Hobby).
    assert _is_cron(cron["schedule"]), cron["schedule"]
    assert _is_cron("0 9 * * *") and _is_cron("*/5 * * * *") and not _is_cron("0 9 * *")


def _ignore_rules(path: Path) -> list:
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("#")]


def test_private_material_and_secrets_are_never_uploaded():
    rules = _ignore_rules(REPO / ".vercelignore")
    for rule in ("/deck", "/memory", "/.demovideo", "/test_reports", "/.emergent", "**/.env", "**/.env.*",
                 "frontend/build", "**/node_modules", ".vercel"):
        assert rule in rules, rule
    # The investor documents stay out of the upload until the owner publishes them, which deletes all
    # three lines (DEPLOY.md, section 8). Without SERVE_INVESTOR_DOCS the build leaves them out anyway.
    investor = [f"frontend/public/{name}" in rules for name in site.INVESTOR_FILES]
    assert all(investor) or not any(investor), "list all three investor documents in .vercelignore, or none"
    assert "/sdk" in rules and "sdk" not in rules  # frontend/public/sdk is part of the website


def test_what_a_local_vercel_build_leaves_in_api_is_never_committed_or_uploaded():
    """`vercel build` writes these next to api/requirements.txt, and later builds install from them."""
    for ignore_file in (".gitignore", ".vercelignore"):
        rules = _ignore_rules(REPO / ignore_file)
        for name in ("api/pyproject.toml", "api/uv.lock"):
            assert name in rules, f"{name} is missing from {ignore_file}"


# --------------------------------------------------------------------------- #
# The website build script
# --------------------------------------------------------------------------- #
@pytest.fixture
def frontend_copy(tmp_path):
    """frontend/ with the real build script and a stand-in for `yarn build`."""
    shutil.copy(REPO / "frontend" / "vercel-build.sh", tmp_path / "vercel-build.sh")
    tools = tmp_path / "tools"
    tools.mkdir()
    yarn = tools / "yarn"
    yarn.write_text(
        "#!/bin/sh\n"
        "mkdir -p build/docs build/elsewhere\n"
        'echo "CI=$CI GENERATE_SOURCEMAP=$GENERATE_SOURCEMAP" > build/settings.txt\n'
        "for name in vexen-pitch-deck vexen-cap-table vexen-idea-one-pager vexen-supporting-document; do\n"
        "  echo '%PDF' > build/docs/$name.pdf\n"
        "done\n"
        "echo '%PDF' > build/elsewhere/Vexen-Cap-Table.PDF\n"
        "ln -s ../docs/vexen-pitch-deck.pdf build/elsewhere/vexen-idea-one-pager.pdf\n",
        encoding="utf-8",
    )
    yarn.chmod(0o755)
    return tmp_path


def _build(frontend: Path, **env) -> subprocess.CompletedProcess:
    full = {**os.environ, "PATH": f"{frontend / 'tools'}{os.pathsep}{os.environ['PATH']}", **env}
    return subprocess.run(["sh", str(frontend / "vercel-build.sh")], env=full, capture_output=True,
                          text=True, timeout=60)


def _shipped(frontend: Path) -> set:
    build = frontend / "build"
    return {str(p.relative_to(build)) for p in build.rglob("*") if p.is_file() or p.is_symlink()}


@pytest.mark.skipif(shutil.which("sh") is None, reason="needs a POSIX shell")
def test_the_build_leaves_the_investor_documents_out(frontend_copy):
    result = _build(frontend_copy)
    assert result.returncode == 0, result.stderr
    assert _shipped(frontend_copy) == {"settings.txt", "docs/vexen-supporting-document.pdf"}
    # Vercel sets CI=1; a lint warning must not fail the deploy. No source maps are published.
    assert (frontend_copy / "build" / "settings.txt").read_text().split() == ["CI=false", "GENERATE_SOURCEMAP=false"]


@pytest.mark.skipif(shutil.which("sh") is None, reason="needs a POSIX shell")
@pytest.mark.parametrize("setting", ["true", " TRUE ", "1", "yes", "on"])
def test_the_investor_documents_ship_only_when_switched_on(frontend_copy, setting):
    assert _build(frontend_copy, SERVE_INVESTOR_DOCS=setting).returncode == 0
    assert "docs/vexen-cap-table.pdf" in _shipped(frontend_copy)
    assert "elsewhere/Vexen-Cap-Table.PDF" in _shipped(frontend_copy)


@pytest.mark.skipif(shutil.which("sh") is None, reason="needs a POSIX shell")
@pytest.mark.parametrize("setting", ["", "false", "0", "no", "nope"])
def test_anything_else_keeps_them_out(frontend_copy, setting):
    assert _build(frontend_copy, SERVE_INVESTOR_DOCS=setting).returncode == 0
    assert _shipped(frontend_copy) == {"settings.txt", "docs/vexen-supporting-document.pdf"}


# --------------------------------------------------------------------------- #
# Knowing it is on Vercel, and the addresses it puts in emails
# --------------------------------------------------------------------------- #
def test_vercel_is_recognised_by_its_own_variable_or_by_the_entry(monkeypatch):
    assert serverless.on_vercel() is False
    monkeypatch.setenv("VERCEL", "1")
    assert serverless.on_vercel() is True
    monkeypatch.delenv("VERCEL")
    monkeypatch.setenv("VEXEN_PLATFORM", "vercel")
    assert serverless.on_vercel() is True


def test_in_production_links_use_the_production_domain(monkeypatch):
    monkeypatch.setenv("VERCEL_ENV", "production")
    monkeypatch.setenv("VERCEL_PROJECT_PRODUCTION_URL", "vexen.example.test")
    monkeypatch.setenv("VERCEL_URL", "vexen-abc123-team.vercel.app")
    assert urls.configured_public_url() == "https://vexen.example.test"
    monkeypatch.setenv("PUBLIC_APP_URL", "https://app.example.test/")
    assert urls.configured_public_url() == "https://app.example.test"  # the operator's word still wins


def test_a_preview_links_to_itself_never_to_production(monkeypatch):
    monkeypatch.setenv("VERCEL_ENV", "preview")
    monkeypatch.setenv("VERCEL_PROJECT_PRODUCTION_URL", "vexen.example.test")  # Vercel sets it in previews too
    assert urls.configured_public_url() == ""
    monkeypatch.setenv("VERCEL_URL", "vexen-abc123-team.vercel.app")
    assert urls.configured_public_url() == "https://vexen-abc123-team.vercel.app"
    monkeypatch.setenv("VERCEL_BRANCH_URL", "vexen-git-feature-team.vercel.app")
    assert urls.configured_public_url() == "https://vexen-git-feature-team.vercel.app"


def test_an_address_on_this_machine_still_loses_to_a_real_one(monkeypatch):
    monkeypatch.setenv("VERCEL_ENV", "development")
    monkeypatch.setenv("VERCEL_URL", "localhost:3000")
    assert urls.configured_public_url() == "https://localhost:3000"  # alone, it is what there is
    monkeypatch.setenv("RAILWAY_PUBLIC_DOMAIN", "vexen.up.railway.app")
    assert urls.configured_public_url() == "https://vexen.up.railway.app"


def test_a_vercel_production_deployment_needs_an_address(monkeypatch, anthropic_key):
    _good(monkeypatch, PUBLIC_APP_URL=None, VERCEL_ENV="production")
    assert any("PUBLIC_APP_URL is not set" in p for p in config.check()[0])
    monkeypatch.setenv("VERCEL_PROJECT_PRODUCTION_URL", "vexen.example.test")
    assert config.check() == ([], [])


def test_a_short_cron_secret_is_ignored_and_said_so(monkeypatch, anthropic_key):
    _good(monkeypatch, CRON_SECRET="short")
    assert serverless.cron_secret() == ""
    assert any("CRON_SECRET is shorter" in note for note in config.check()[1])
    monkeypatch.setenv("CRON_SECRET", "  " + "c" * 16 + " ")
    assert serverless.cron_secret() == "c" * 16 and config.check() == ([], [])


def test_on_vercel_a_missing_cron_secret_is_noticed_once_email_is_set_up(monkeypatch, anthropic_key):
    _good(monkeypatch, VERCEL="1")
    assert config.check() == ([], [])
    _good(monkeypatch, SMTP_HOST="smtp.example.test", SMTP_USERNAME="me", SMTP_PASSWORD="pw")
    assert any("CRON_SECRET is not set" in note for note in config.check()[1])


def test_on_vercel_each_instance_keeps_a_small_database_pool(monkeypatch):
    seen: dict = {}
    monkeypatch.setattr(db, "AsyncIOMotorClient", lambda url, **kwargs: seen.update(kwargs) or object())
    monkeypatch.setattr(db, "_client", None)
    monkeypatch.setenv("MONGO_URL", "mongodb://127.0.0.1:27017")
    db.get_client()
    assert (seen["maxPoolSize"], seen["minPoolSize"]) == (200, 5)  # the container: as before
    monkeypatch.setattr(db, "_client", None)
    monkeypatch.setenv("VERCEL", "1")
    db.get_client()
    assert (seen["maxPoolSize"], seen["minPoolSize"], seen["maxIdleTimeMS"]) == (10, 0, 60_000)


# --------------------------------------------------------------------------- #
# Start-up work: once per process, from the lifespan or the first request
# --------------------------------------------------------------------------- #
@pytest.fixture
def indexes(monkeypatch):
    """A stand-in for the database's index setup, and no call to Anthropic."""
    calls = {"n": 0, "fail": False}

    async def ensure_indexes():
        calls["n"] += 1
        await asyncio.sleep(0.01)  # long enough for simultaneous first requests to pile up
        if calls["fail"]:
            raise RuntimeError("no route to host")

    monkeypatch.setattr(db, "ensure_indexes", ensure_indexes)
    monkeypatch.setattr(startup.llm, "verify", lambda: {})
    return calls


def test_the_setup_runs_once_however_many_requests_arrive_together(monkeypatch, anthropic_key, indexes):
    _good(monkeypatch)
    checks = []
    real_check = config.check
    monkeypatch.setattr(startup.config, "check", lambda: checks.append(1) or real_check())
    setup = startup.Setup()

    async def scenario():
        first = await asyncio.gather(*(setup.ensure() for _ in range(10)))
        later = await setup.ensure()
        await setup.stop()
        return first, later

    first, later = asyncio.run(scenario())
    assert first == [None] * 10 and later is None
    assert indexes["n"] == 1 and len(checks) == 1


def test_a_setup_problem_is_answered_plainly_and_the_database_is_left_alone(indexes):
    status, detail = asyncio.run(startup.Setup().ensure())  # nothing is configured
    assert status == 500
    assert "MONGO_URL is not set" in detail and "JWT_SECRET must be at least 32 characters" in detail
    assert indexes["n"] == 0


def test_a_database_that_does_not_answer_is_tried_again_later(monkeypatch, anthropic_key, indexes):
    _good(monkeypatch)
    indexes["fail"] = True
    setup = startup.Setup()

    async def scenario():
        first = await setup.ensure()
        second = await setup.ensure()  # inside the waiting time: the database is not asked again
        setup._db_failed_at -= startup.DB_RETRY_SECONDS + 1  # the waiting time has passed
        indexes["fail"] = False
        third = await setup.ensure()
        await setup.stop()
        return first, second, third

    first, second, third = asyncio.run(scenario())
    assert first[0] == second[0] == 503 and "Network Access" in first[1]
    assert third is None and indexes["n"] == 2


def test_in_the_container_a_setup_problem_still_stops_the_start(monkeypatch, anthropic_key, indexes):
    with pytest.raises(RuntimeError, match=r"^Vexen cannot start\. MONGO_URL is not set"):
        asyncio.run(startup.Setup().run(fatal=True))
    asyncio.run(startup.Setup().run(fatal=False))  # on Vercel the start goes on

    _good(monkeypatch)
    indexes["fail"] = True
    with pytest.raises(RuntimeError, match="Vexen cannot start: the database did not answer") as stopped:
        asyncio.run(startup.Setup().run(fatal=True))
    assert str(stopped.value.__cause__) == "no route to host"


def _gated(setup: startup.Setup) -> FastAPI:
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    @app.get("/api/health")
    async def health():
        return {"status": "ok"}

    @app.get("/api/agents")
    async def agents():
        return {"agents": []}

    @app.get("/elsewhere")
    async def elsewhere():
        return {"page": True}

    app.add_middleware(startup.SetupGate, setup=setup)
    return app


def test_the_gate_answers_api_requests_with_the_setup_problem(indexes):
    with TestClient(_gated(startup.Setup())) as client:
        refused = client.get("/api/agents")
        assert refused.status_code == 500 and "MONGO_URL is not set" in refused.json()["detail"]
        assert client.get("/api/health").json() == {"status": "ok"}  # liveness answers whatever happens
        assert client.get("/elsewhere").json() == {"page": True}  # only the API waits for the setup
    assert indexes["n"] == 0


def test_the_gate_opens_once_the_setup_is_done(monkeypatch, anthropic_key, indexes):
    _good(monkeypatch)
    with TestClient(_gated(startup.Setup())) as client:
        assert client.get("/api/agents").json() == {"agents": []}
        assert client.get("/api/agents").json() == {"agents": []}
    assert indexes["n"] == 1


def test_on_vercel_the_ai_key_check_finishes_inside_the_request_that_started_it(
        monkeypatch, anthropic_key, indexes):
    # A Vercel instance is paused once a request ends, so a check left running "in the background"
    # would never finish and the AI would stay "unverified". The first request now waits for it,
    # after its response has gone out.
    _good(monkeypatch)
    monkeypatch.setenv("VERCEL", "1")
    checked: list = []

    def verify():
        import time

        time.sleep(0.2)  # Anthropic takes a moment to answer
        checked.append(True)
        return {}

    monkeypatch.setattr(startup.llm, "verify", verify)
    with TestClient(serverless.AfterResponse(_gated(startup.Setup()))) as client:
        assert client.get("/api/agents").json() == {"agents": []}
        assert checked == [True]


@pytest.fixture
def server_app(monkeypatch, indexes):
    """The real app with its real lifespan, with the email worker replaced by a recorder."""
    import server

    started = []

    async def outbox_worker(stop):
        started.append(True)
        await stop.wait()

    monkeypatch.setattr(server, "outbox_worker", outbox_worker)
    server.setup.__init__()  # forget an earlier test's setup: it runs once per process
    yield server.app, started
    server.setup.__init__()


def test_on_vercel_the_lifespan_starts_no_worker_and_answers_a_bad_setup(monkeypatch, server_app):
    app, started = server_app
    monkeypatch.setenv("VERCEL", "1")
    with TestClient(app) as client:  # starts although nothing is configured
        assert client.get("/api/health").status_code == 200
        refused = client.get("/api/ready")
        assert refused.status_code == 500 and "MONGO_URL is not set" in refused.json()["detail"]
    assert started == []


def test_on_vercel_a_new_instance_never_waits_for_the_database_to_start(
        monkeypatch, anthropic_key, indexes, server_app):
    # Vercel holds every request to a new instance until the start-up is over, so the start-up must
    # not wait on the database: the liveness check answers at once, and the first API request sets up.
    app, started = server_app
    _good(monkeypatch)
    monkeypatch.setenv("VERCEL", "1")
    with TestClient(app) as client:
        assert indexes["n"] == 0
        assert client.get("/api/health").status_code == 200
        assert indexes["n"] == 0
        assert client.get("/api/does-not-exist").status_code == 404
        assert indexes["n"] == 1
    assert started == []


def test_in_the_container_the_lifespan_starts_the_email_worker(monkeypatch, anthropic_key, server_app):
    app, started = server_app
    _good(monkeypatch)
    with TestClient(app) as client:
        assert client.get("/api/health").status_code == 200
    assert started == [True]


def test_in_the_container_a_bad_setup_still_stops_the_server(server_app):
    app, started = server_app
    with pytest.raises(RuntimeError, match="Vexen cannot start"):
        with TestClient(app):
            pass
    assert started == []


# --------------------------------------------------------------------------- #
# Work left after the response, and the email it queued
# --------------------------------------------------------------------------- #
def _request_that_leaves_work(events):
    async def push():
        await asyncio.sleep(0.05)
        events.append("push sent")

    async def app(scope, receive, send):
        serverless.in_background(push(), name="test-push")
        serverless.note_mail_queued()
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})
        events.append("handler returned")

    async def send(message):
        events.append(message["type"])

    async def send_queued_email(*, queued):
        events.append(("email", queued))

    return app, send, send_queued_email


def test_on_vercel_a_requests_work_is_finished_after_its_response_is_sent(monkeypatch):
    monkeypatch.setenv("VERCEL", "1")
    events: list = []
    app, send, email = _request_that_leaves_work(events)
    monkeypatch.setattr(serverless, "send_queued_email", email)
    asyncio.run(serverless.AfterResponse(app)({"type": "http", "path": "/api/v1/authorize"}, None, send))
    # The email goes out at once, not after the push (a slow push service must not delay it), and the
    # invocation still lasts until the push is done.
    assert events == ["http.response.start", "http.response.body", "handler returned",
                      ("email", True), "push sent"]


def test_mail_queued_by_background_work_is_sent_once_that_work_is_done(monkeypatch):
    monkeypatch.setenv("VERCEL", "1")
    sends: list = []

    async def send_queued_email(*, queued):
        sends.append(queued)

    async def queues_mail():
        await asyncio.sleep(0.01)
        serverless.note_mail_queued()

    async def app(scope, receive, send):
        serverless.in_background(queues_mail())
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    async def sink(message):
        pass

    monkeypatch.setattr(serverless, "send_queued_email", send_queued_email)
    asyncio.run(serverless.AfterResponse(app)({"type": "http", "path": "/api/x"}, None, sink))
    assert sends == [False, True]  # the regular look, then the mail the background work queued


def test_in_the_container_nothing_waits_and_the_worker_sends_the_email(monkeypatch):
    events: list = []
    app, send, email = _request_that_leaves_work(events)
    monkeypatch.setattr(serverless, "send_queued_email", email)

    async def scenario():
        await serverless.AfterResponse(app)({"type": "http", "path": "/api/v1/authorize"}, None, send)
        events.append("request over")
        await asyncio.sleep(0.1)  # the push carries on by itself, as it always has

    asyncio.run(scenario())
    assert events == ["http.response.start", "http.response.body", "handler returned",
                      "request over", "push sent"]


def test_an_error_answer_is_not_held_up_by_background_work(monkeypatch):
    monkeypatch.setenv("VERCEL", "1")
    events: list = []
    monkeypatch.setattr(serverless, "send_queued_email", lambda **_: events.append("email"))

    async def slow():
        await asyncio.sleep(5)

    async def app(scope, receive, send):
        serverless.in_background(slow())
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        asyncio.run(serverless.AfterResponse(app)({"type": "http", "path": "/api/x"}, None, None))
    assert events == []


def test_queued_email_is_sent_at_once_and_otherwise_looked_for_once_a_minute(monkeypatch):
    calls: list = []

    async def recover_stuck(database):
        calls.append("recover")
        return 0

    async def drain_once(database, **_):
        calls.append("drain")
        return {"sent": 0, "failed": 0}

    monkeypatch.setattr(mailer, "smtp_configured", lambda: True)
    monkeypatch.setattr(mailer, "recover_stuck", recover_stuck)
    monkeypatch.setattr(mailer, "drain_once", drain_once)
    monkeypatch.setattr(db, "get_db", lambda: object())
    monkeypatch.setattr(serverless, "_last_outbox_look", float("-inf"))

    asyncio.run(serverless.send_queued_email(queued=False))  # nobody has looked yet
    assert calls == ["recover", "drain"]
    asyncio.run(serverless.send_queued_email(queued=False))  # looked a moment ago: leave it
    assert calls == ["recover", "drain"]
    asyncio.run(serverless.send_queued_email(queued=True))  # this request queued mail: send it now
    assert calls == ["recover", "drain"] * 2

    monkeypatch.setattr(mailer, "smtp_configured", lambda: False)
    asyncio.run(serverless.send_queued_email(queued=True))  # no email set up: the mail waits, as before
    assert len(calls) == 4

    async def broken(database):
        raise RuntimeError("mail server down")

    monkeypatch.setattr(mailer, "smtp_configured", lambda: True)
    monkeypatch.setattr(mailer, "recover_stuck", broken)
    asyncio.run(serverless.send_queued_email(queued=True))  # logged, never raised: the response is out


def test_a_new_instance_looks_and_logs_at_once_even_when_its_clock_is_young(monkeypatch, caplog):
    """time.monotonic() counts from boot, so on a freshly started instance it can be under a minute."""
    young = types.SimpleNamespace(monotonic=lambda: 30.0)
    calls: list = []

    async def recover_stuck(database):
        calls.append("recover")
        return 0

    async def drain_once(database, **_):
        calls.append("drain")
        return {"sent": 0, "failed": 0}

    monkeypatch.setattr(mailer, "smtp_configured", lambda: True)
    monkeypatch.setattr(mailer, "recover_stuck", recover_stuck)
    monkeypatch.setattr(mailer, "drain_once", drain_once)
    monkeypatch.setattr(db, "get_db", lambda: object())
    # A fresh copy of the module, as a new instance has it (the shared copy has looked already).
    spec = importlib.util.find_spec("vexen.serverless")
    fresh = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fresh)
    fresh.time = young
    asyncio.run(fresh.send_queued_email(queued=False))
    assert calls == ["recover", "drain"]

    monkeypatch.setattr(startup, "time", young)
    with caplog.at_level(logging.ERROR, logger="vexen"), TestClient(_gated(startup.Setup())) as client:
        assert client.get("/api/agents").status_code == 500
    assert any(r.getMessage().startswith("Answering API requests with 500") for r in caplog.records)


def test_queueing_an_email_inside_a_request_marks_it_for_sending():
    class Outbox:
        def __init__(self, fail=False):
            self.fail = fail

        async def insert_one(self, doc):
            if self.fail:
                raise RuntimeError("duplicate key")

    def queue(outbox, to="alex@example.com"):
        work = serverless._RequestWork()

        async def scenario():
            token = serverless._work.set(work)
            try:
                return await mailer.queue_email(type("Db", (), {"email_outbox": outbox})(), to=to,
                                                subject="s", text="t", html="h", kind="test")
            finally:
                serverless._work.reset(token)

        return asyncio.run(scenario()), work.mail_queued

    queued, marked = queue(Outbox())
    assert queued and queued.startswith("eml_") and marked is True
    assert queue(Outbox(fail=True)) == (None, False)
    assert queue(Outbox(), to="not-an-address") == (None, False)


def test_request_code_starts_background_work_only_through_in_background():
    for path in sorted((BACKEND / "vexen").glob("*.py")):
        if path.name in ("serverless.py", "startup.py"):
            continue
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Call):
                name = node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, "id", "")
                assert name not in ("create_task", "ensure_future"), f"{path.name}: use serverless.in_background"


# --------------------------------------------------------------------------- #
# The scheduled email run
# --------------------------------------------------------------------------- #
SECRET = "c0ffee" * 6


@pytest.fixture
def cron(monkeypatch):
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    app.include_router(serverless.router)
    runs: list = []

    async def drain_for(database, *, seconds):
        runs.append(seconds)
        return {"recovered": 1, "sent": 2, "failed": 0}

    monkeypatch.setattr(mailer, "drain_for", drain_for)
    monkeypatch.setattr(mailer, "smtp_configured", lambda: True)
    monkeypatch.setattr(db, "get_db", lambda: object())
    deps._BUCKETS.clear()
    yield TestClient(app), runs
    deps._BUCKETS.clear()


def test_without_a_secret_the_scheduled_run_does_not_exist(cron, monkeypatch):
    client, runs = cron
    assert client.get("/api/internal/outbox", headers={"Authorization": "Bearer "}).status_code == 404
    monkeypatch.setenv("CRON_SECRET", "too-short")
    assert client.get("/api/internal/outbox", headers={"Authorization": "Bearer too-short"}).status_code == 404
    assert runs == []


def test_the_scheduled_run_needs_the_exact_secret(cron, monkeypatch):
    client, runs = cron
    monkeypatch.setenv("CRON_SECRET", SECRET)
    for headers in ({}, {"Authorization": SECRET}, {"Authorization": f"Bearer {SECRET}x"},
                    {"Authorization": f"Bearer {SECRET[:-1]}"}, {"Authorization": f"Basic {SECRET}"}):
        refused = client.get("/api/internal/outbox", headers=headers)
        assert refused.status_code == 401 and refused.json() == {"detail": "Not allowed."}, headers
    assert runs == []
    good = {"Authorization": f"Bearer {SECRET}"}
    answer = client.get("/api/internal/outbox", headers=good)  # Vercel's cron jobs send GET
    assert answer.status_code == 200
    assert answer.json() == {"email": "configured", "recovered": 1, "sent": 2, "failed": 0}
    assert client.post("/api/internal/outbox", headers=good).status_code == 200  # other schedulers may POST
    assert runs == [serverless.CRON_SEND_SECONDS] * 2
    assert "compare_digest" in inspect.getsource(serverless.bearer_matches)  # constant-time comparison


def test_guessing_the_secret_is_slowed_down(cron, monkeypatch):
    client, _ = cron
    monkeypatch.setenv("CRON_SECRET", SECRET)
    answers = [client.get("/api/internal/outbox", headers={"Authorization": "Bearer guess"}).status_code
               for _ in range(22)]
    assert answers[:20] == [401] * 20 and answers[20:] == [429, 429]
    # Over the limit even the right secret is refused, so guessing really slows down...
    good = {"Authorization": f"Bearer {SECRET}"}
    assert client.get("/api/internal/outbox", headers=good).status_code == 429
    # ...while any other caller, the schedule included, still gets through.
    assert client.get("/api/internal/outbox", headers={**good, "X-Forwarded-For": "203.0.113.9"}).status_code == 200


def test_without_email_set_up_the_run_sends_nothing(cron, monkeypatch):
    client, runs = cron
    monkeypatch.setenv("CRON_SECRET", SECRET)
    monkeypatch.setattr(mailer, "smtp_configured", lambda: False)
    answer = client.get("/api/internal/outbox", headers={"Authorization": f"Bearer {SECRET}"})
    assert answer.json() == {"email": "not configured", "recovered": 0, "sent": 0, "failed": 0}
    assert runs == []


def test_a_run_sends_batch_after_batch_until_the_queue_is_empty(monkeypatch):
    full = {"sent": mailer.BATCH_SIZE, "failed": 0}
    batches = iter([full, full, {"sent": 3, "failed": 0}])

    async def drain_once(database, **_):
        return next(batches)

    async def recover_stuck(database):
        return 2

    monkeypatch.setattr(mailer, "drain_once", drain_once)
    monkeypatch.setattr(mailer, "recover_stuck", recover_stuck)
    totals = asyncio.run(mailer.drain_for(object(), seconds=60))
    assert totals == {"recovered": 2, "sent": 2 * mailer.BATCH_SIZE + 3, "failed": 0}


def _passes(monkeypatch, results):
    """drain_for over a scripted series of drain_once passes; returns the totals and the passes made."""
    script, made = iter(results), []

    async def drain_once(database, **_):
        made.append(1)
        return next(script)

    async def recover_stuck(database):
        return 0

    monkeypatch.setattr(mailer, "drain_once", drain_once)
    monkeypatch.setattr(mailer, "recover_stuck", recover_stuck)
    return made


def test_a_refused_message_does_not_hold_back_the_mail_behind_it(monkeypatch):
    # The refused message waits for its own retry time, so the next pass reaches the others.
    made = _passes(monkeypatch, [{"sent": 0, "failed": 1}, {"sent": 4, "failed": 0}])
    assert asyncio.run(mailer.drain_for(object(), seconds=60)) == {"recovered": 0, "sent": 4, "failed": 1}
    assert len(made) == 2


def test_a_run_stops_when_the_provider_refuses_for_good(monkeypatch):
    # A rejected login: retrying cannot help, so the run stops at once.
    made = _passes(monkeypatch, [{"sent": 0, "failed": 1, "terminal": 1}, {"sent": 4, "failed": 0}])
    assert asyncio.run(mailer.drain_for(object(), seconds=60))["sent"] == 0 and len(made) == 1
    # A provider refusing every message: three refused passes in a row, then stop.
    made = _passes(monkeypatch, [{"sent": 0, "failed": 1}] * 10)
    assert asyncio.run(mailer.drain_for(object(), seconds=60))["failed"] == 3 and len(made) == 3
    # Messages that do go out in between start the count again.
    made = _passes(monkeypatch, [{"sent": 0, "failed": 1}, {"sent": 0, "failed": 1}, {"sent": 2, "failed": 1},
                                 {"sent": 0, "failed": 1}, {"sent": 0, "failed": 1}, {"sent": 9, "failed": 0}])
    assert asyncio.run(mailer.drain_for(object(), seconds=60))["failed"] == 5 and len(made) == 5


def test_a_run_stops_when_its_time_is_up(monkeypatch):
    made = _passes(monkeypatch, [{"sent": mailer.BATCH_SIZE, "failed": 0}] * 10)
    assert asyncio.run(mailer.drain_for(object(), seconds=0))["sent"] == mailer.BATCH_SIZE
    assert len(made) == 1


def test_mail_queued_by_a_request_is_all_sent_not_just_one_batch(monkeypatch):
    runs: list = []

    async def drain_for(database, *, seconds):
        runs.append(seconds)
        return {"recovered": 0, "sent": 30, "failed": 0}

    monkeypatch.setattr(mailer, "smtp_configured", lambda: True)
    monkeypatch.setattr(mailer, "drain_for", drain_for)
    monkeypatch.setattr(db, "get_db", lambda: object())
    asyncio.run(serverless.send_queued_email(queued=True))
    assert runs == [serverless.AFTER_RESPONSE_SEND_SECONDS]
    # The request's background work (60 s at most) and the email run fit well inside the function's limit.
    longest = serverless.BACKGROUND_WAIT_SECONDS + 2 * serverless.AFTER_RESPONSE_SEND_SECONDS
    assert longest < VERCEL_JSON["functions"]["api/index.py"]["maxDuration"]


def test_the_drain_reports_a_refusal_no_retry_can_fix(monkeypatch):
    rows = [{"id": "eml_1", "to": "a@example.test", "subject": "s", "kind": "test"}]
    recorded: list = []

    async def claim(database):
        return rows.pop(0) if rows else None

    async def refuse(**_):
        raise mailer.MailError("535 authentication failed", terminal=True)

    async def record(database, row, error, *, terminal):
        recorded.append(terminal)

    monkeypatch.setattr(mailer, "_claim_next", claim)
    monkeypatch.setattr(mailer, "send_now", refuse)
    monkeypatch.setattr(mailer, "_record_failure", record)
    assert asyncio.run(mailer.drain_once(object())) == {"sent": 0, "failed": 1, "terminal": 1}
    assert recorded == [True]


# --------------------------------------------------------------------------- #
# Downloads
# --------------------------------------------------------------------------- #
def test_on_vercel_a_download_is_sent_to_the_file_on_the_cdn(monkeypatch):
    import server

    monkeypatch.setenv("VERCEL", "1")
    moved = asyncio.run(server.download("demo-video"))
    assert moved.status_code == 307 and moved.headers["location"] == "/demo/vexen-demo.mp4?download=1"
    for item in site.INVESTOR_DOWNLOADS:
        assert asyncio.run(server.download(item)).status_code == 404  # still private
    monkeypatch.setenv("SERVE_INVESTOR_DOCS", "true")
    assert asyncio.run(server.download("cap-table")).headers["location"] == "/docs/vexen-cap-table.pdf?download=1"
    assert asyncio.run(server.download("nothing-here")).status_code == 404


def test_every_download_is_a_file_the_website_ships_and_saves():
    import server

    for item, (relative, _, _) in server.DOWNLOADS.items():
        assert (REPO / "frontend" / "public" / relative).is_file(), item
        assert _headers("/" + relative, query={"download"})["content-disposition"] == "attachment", item


def test_in_the_container_the_server_still_serves_the_download(tmp_path, monkeypatch):
    import server

    (tmp_path / "demo").mkdir()
    (tmp_path / "demo" / "vexen-demo.mp4").write_bytes(b"video")
    (tmp_path / "index.html").write_text('<div id="root"></div>')
    monkeypatch.setenv("FRONTEND_BUILD_DIR", str(tmp_path))
    served = asyncio.run(server.download("demo-video"))
    assert served.status_code == 200
    assert served.headers["content-disposition"] == 'attachment; filename="vexen-demo.mp4"'
