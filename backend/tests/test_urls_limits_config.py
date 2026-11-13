"""Small guarantees: the public address, the rate limiter's memory, secret-free logs, start-up checks."""
from __future__ import annotations

import logging

import pytest
from starlette.requests import Request

from vexen import config, deps, logs, mailer, security, urls

SITE = "https://vexen.example.test"


def _request(headers):
    scope = {
        "type": "http", "method": "POST", "path": "/api/v1/authorize", "scheme": "http",
        "server": ("internal-host", 8000), "client": ("198.51.100.1", 5000), "query_string": b"",
        "headers": [(name.lower().encode(), value.encode()) for name, value in headers.items()],
    }
    return Request(scope)


# --------------------------------------------------------------------------- #
# The address used in emails, invitations and the developer page
# --------------------------------------------------------------------------- #
def test_the_public_address_comes_from_configuration(monkeypatch):
    assert urls.configured_public_url() == ""
    monkeypatch.setenv("RAILWAY_PUBLIC_DOMAIN", "vexen.up.railway.app")
    assert urls.configured_public_url() == "https://vexen.up.railway.app"
    monkeypatch.setenv("RENDER_EXTERNAL_URL", "https://vexen.onrender.com/")
    assert urls.configured_public_url() == "https://vexen.onrender.com"
    monkeypatch.setenv("PUBLIC_APP_URL", SITE + "/")
    assert urls.configured_public_url() == SITE  # the operator's word wins


@pytest.mark.parametrize("value", ["", "   ", "vexen.example.test", "ftp://vexen.example.test"])
def test_a_malformed_address_is_ignored(monkeypatch, value):
    monkeypatch.setenv("PUBLIC_APP_URL", value)
    assert urls.configured_public_url() == ""


def test_request_headers_cannot_change_a_configured_address(monkeypatch):
    monkeypatch.setenv("PUBLIC_APP_URL", SITE)
    spoofed = _request({"host": "evil.example", "x-forwarded-host": "evil.example",
                        "x-forwarded-proto": "http"})
    assert deps.public_base_url(spoofed) == SITE
    assert mailer.public_app_url("https://evil.example") == SITE


def test_without_configuration_the_forwarded_headers_are_used():
    request = _request({"host": "internal-host:8000", "x-forwarded-host": "site.example",
                        "x-forwarded-proto": "https"})
    assert deps.public_base_url(request) == "https://site.example"
    assert mailer.public_app_url("https://site.example") == "https://site.example"


# --------------------------------------------------------------------------- #
# The rate limiter
# --------------------------------------------------------------------------- #
@pytest.fixture
def clock(monkeypatch):
    now = {"t": 10_000.0}
    monkeypatch.setattr(deps.time, "monotonic", lambda: now["t"])
    deps._BUCKETS.clear()
    monkeypatch.setattr(deps, "_last_sweep", 0.0)
    yield now
    deps._BUCKETS.clear()


def test_the_limiter_blocks_and_then_recovers(clock):
    from fastapi import HTTPException

    for _ in range(3):
        deps.rate_limit("k", limit=3, window_seconds=60)
    with pytest.raises(HTTPException) as blocked:
        deps.rate_limit("k", limit=3, window_seconds=60)
    assert blocked.value.status_code == 429
    clock["t"] += 61
    deps.rate_limit("k", limit=3, window_seconds=60)


def test_the_limiter_forgets_callers_nobody_has_seen_for_hours(clock):
    for i in range(deps._MAX_BUCKETS + 5000):
        deps._BUCKETS[f"stale-{i}"].append(1.0)
    deps.rate_limit("fresh", limit=5, window_seconds=60)
    assert list(deps._BUCKETS) == ["fresh"]


def test_the_limiter_cannot_be_grown_without_bound(clock):
    for i in range(deps._MAX_BUCKETS + 5000):
        deps._BUCKETS[f"recent-{i}"].append(clock["t"] - 5)
    deps.rate_limit("fresh", limit=5, window_seconds=60)
    assert len(deps._BUCKETS) <= deps._MAX_BUCKETS


# --------------------------------------------------------------------------- #
# Signed links stay out of the server's own log
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("path", [
    "/api/public/approvals/eyJhIjoxfQ.c2lnbmF0dXJlMTIz",
    "/api/public/approvals/eyJhIjoxfQ.c2lnbmF0dXJlMTIz/decision",
    "/api/public/invites/eyJhIjoxfQ.c2lnbmF0dXJlMTIz",
    "/approve/eyJhIjoxfQ.c2lnbmF0dXJlMTIz",
    "/join/eyJhIjoxfQ.c2lnbmF0dXJlMTIz",
])
def test_tokens_are_hidden(path):
    hidden = logs.hide_tokens(path)
    assert "eyJhIjoxfQ" not in hidden and "[hidden]" in hidden


def test_ordinary_addresses_are_left_alone():
    for path in ("/api/agents", "/app/approvals", "/static/js/main.abc123.js", "/approve/x"):
        assert logs.hide_tokens(path) == path


def test_the_access_log_filter_rewrites_the_path_argument():
    record = logging.LogRecord(
        "uvicorn.access", logging.INFO, "", 0, '%s - "%s %s HTTP/%s" %d',
        ("203.0.113.9:5000", "GET", "/approve/AAAAAAAAAAAA.BBBBBBBB", "1.1", 200), None)
    assert logs.HideTokens().filter(record) is True
    assert "AAAAAAAAAAAA" not in record.getMessage() and "[hidden]" in record.getMessage()


# --------------------------------------------------------------------------- #
# Start-up checks
# --------------------------------------------------------------------------- #
GOOD = {
    "MONGO_URL": "mongodb+srv://app:secret123@cluster0.abcde.mongodb.net/?retryWrites=true&w=majority",
    "JWT_SECRET": "x" * 40,
    "API_KEY_PEPPER": "pepper",
    "PUBLIC_APP_URL": SITE,
}


def _env(monkeypatch, **values):
    for name, value in values.items():
        monkeypatch.setenv(name, value)


def test_a_complete_setup_starts_cleanly(monkeypatch, anthropic_key):
    _env(monkeypatch, **GOOD)
    assert config.check() == ([], [])


def test_an_empty_setup_says_what_is_missing():
    problems, notes = config.check()
    text = " ".join(problems)
    assert "MONGO_URL" in text and "JWT_SECRET" in text
    assert any("AI features are switched off" in n for n in notes)
    assert any("PUBLIC_APP_URL" in n for n in notes)


@pytest.mark.parametrize("mongo, fragment", [
    ("https://not-a-database.example.test", "not a MongoDB connection string"),
    ("mongodb+srv://app:<db_password>@cluster0.abcde.mongodb.net/", "placeholder"),
])
def test_a_bad_database_address_is_caught(monkeypatch, mongo, fragment):
    _env(monkeypatch, **{**GOOD, "MONGO_URL": mongo})
    problems, _ = config.check()
    assert any(fragment in p for p in problems)


def test_stray_spaces_around_the_database_address_are_harmless(monkeypatch):
    from vexen import db

    _env(monkeypatch, **{**GOOD, "MONGO_URL": "  " + GOOD["MONGO_URL"] + " \r\n"})
    assert config.check()[0] == []  # what the start-up check accepts...
    seen = {}
    monkeypatch.setattr(db, "AsyncIOMotorClient", lambda url, **kwargs: seen.setdefault("url", url))
    monkeypatch.setattr(db, "_client", None)
    db.get_client()
    assert seen["url"] == GOOD["MONGO_URL"]  # ...is exactly what the client is given
    monkeypatch.setattr(db, "_client", None)


def test_a_guessable_signing_secret_is_refused(monkeypatch):
    _env(monkeypatch, **{**GOOD, "JWT_SECRET": "short"})
    problems, _ = config.check()
    assert any("JWT_SECRET" in p for p in problems)


def test_settings_that_could_redirect_the_ai_are_reported_as_ignored(monkeypatch, anthropic_key):
    _env(monkeypatch, **GOOD, ANTHROPIC_BASE_URL="https://proxy.example.test",
         ANTHROPIC_CUSTOM_HEADERS="X-Api-Key: other", ANTHROPIC_AUTH_TOKEN="other-token",
         ANTHROPIC_WORKSPACE_ID="not-a-workspace")
    problems, notes = config.check()
    assert problems == []
    text = " ".join(notes)
    for name in ("ANTHROPIC_BASE_URL", "ANTHROPIC_CUSTOM_HEADERS", "ANTHROPIC_AUTH_TOKEN"):
        assert f"{name} is set but ignored" in text
    assert "ANTHROPIC_WORKSPACE_ID is not a workspace ID" in text


def test_a_half_finished_email_or_push_setup_is_noticed(monkeypatch, anthropic_key):
    _env(monkeypatch, **GOOD, SMTP_HOST="smtp.example.test", VAPID_PUBLIC_KEY="abc")
    problems, notes = config.check()
    assert problems == []
    assert any("Email is half set up" in n for n in notes)
    assert any("Phone notifications are half set up" in n for n in notes)


def test_an_unusable_token_lifetime_falls_back_instead_of_crashing(monkeypatch):
    for value, expected in (("", 60), ("abc", 60), ("0", 60), ("-5", 60), ("15", 15)):
        monkeypatch.setenv("SOME_MINUTES", value)
        assert security._env_int("SOME_MINUTES", 60) == expected


# --------------------------------------------------------------------------- #
# Found in review
# --------------------------------------------------------------------------- #
def test_a_leftover_local_address_loses_to_the_hosts_real_one(monkeypatch):
    monkeypatch.setenv("PUBLIC_APP_URL", "http://localhost:8000")
    assert urls.configured_public_url() == "http://localhost:8000"  # alone, it is what was asked for
    monkeypatch.setenv("RENDER_EXTERNAL_URL", "https://vexen.onrender.com")
    assert urls.configured_public_url() == "https://vexen.onrender.com"
    assert any("points at this machine" in note for note in config.check()[1])


def test_a_production_container_will_not_start_without_a_public_address(monkeypatch, anthropic_key):
    _env(monkeypatch, **{**GOOD, "PUBLIC_APP_URL": ""}, VEXEN_ENV="production")
    assert any("PUBLIC_APP_URL is not set" in p for p in config.check()[0])
    monkeypatch.setenv("RENDER_EXTERNAL_URL", "https://vexen.onrender.com")
    assert config.check()[0] == []  # the host's own address is enough
    monkeypatch.delenv("RENDER_EXTERNAL_URL")
    monkeypatch.setenv("PUBLIC_APP_URL", "vexen.example.com")  # forgot https://
    assert any("must start with https://" in p for p in config.check()[0])


def test_a_locked_out_caller_stays_locked_out_during_a_flood(clock):
    from fastapi import HTTPException

    for _ in range(3):
        deps.rate_limit("login:victim", limit=3, window_seconds=300)
    for i in range(deps._MAX_BUCKETS + 5000):
        deps._BUCKETS[f"made-up-{i}"].append(clock["t"] - 1)
    deps.rate_limit("fresh", limit=5, window_seconds=60)  # triggers the sweep
    with pytest.raises(HTTPException) as blocked:
        deps.rate_limit("login:victim", limit=3, window_seconds=300)
    assert blocked.value.status_code == 429


def test_keys_built_from_text_a_stranger_chose_stay_small(clock):
    deps.rate_limit("link-read:" + "x" * 50_000, limit=5, window_seconds=60)
    assert max(len(key) for key in deps._BUCKETS) < 100


def test_the_client_address_is_always_a_real_address():
    assert deps.client_ip(_request({"x-forwarded-for": "203.0.113.9, 10.0.0.1"})) == "203.0.113.9"
    assert deps.client_ip(_request({"x-forwarded-for": "2001:db8::1"})) == "2001:db8::1"
    for junk in ("x" * 5000, "not-an-address", "<script>"):
        assert deps.client_ip(_request({"x-forwarded-for": junk})) == "198.51.100.1"
