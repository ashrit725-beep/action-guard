"""The website is served from the same address as the API."""
from __future__ import annotations

import os

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from vexen import site


@pytest.fixture
def build(tmp_path, monkeypatch):
    """A tiny stand-in for frontend/build."""
    (tmp_path / "static" / "js").mkdir(parents=True)
    (tmp_path / "docs").mkdir()
    (tmp_path / "demo").mkdir()
    (tmp_path / "index.html").write_text('<!doctype html><div id="root"></div>')
    (tmp_path / "static" / "js" / "main.abc123.js").write_text("console.log('app')")
    (tmp_path / "sw.js").write_text("self.addEventListener('push', () => {})")
    (tmp_path / "manifest.json").write_text("{}")
    (tmp_path / "robots.txt").write_text("User-agent: *")
    (tmp_path / "docs" / "vexen-cap-table.pdf").write_bytes(b"%PDF cap table")
    (tmp_path / "docs" / "vexen-pitch-deck.pdf").write_bytes(b"%PDF deck")
    (tmp_path / "docs" / "vexen-idea-one-pager.pdf").write_bytes(b"%PDF one pager")
    (tmp_path / "docs" / "vexen-supporting-document.pdf").write_bytes(b"%PDF supporting")
    (tmp_path / "demo" / "demo.mp4").write_bytes(bytes(range(256)) * 40)
    monkeypatch.setenv("FRONTEND_BUILD_DIR", str(tmp_path))
    return tmp_path


@pytest.fixture
def client(build):
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    @app.get("/api/ping")
    async def ping():
        return {"pong": True}

    app.add_middleware(site.SecurityHeaders)
    assert site.mount(app) is True
    return TestClient(app)


APP_ADDRESSES = [
    "/", "/app", "/app/agents", "/login", "/signup", "/contact",
    "/approve/eyJhIjoxfQ.c2lnbmF0dXJlMTIz",   # signed links contain a dot
    "/join/eyJhIjoxfQ.c2lnbmF0dXJlMTIz",
    "/join/looks-like-a-file.js",             # even one that ends like a file name
]


@pytest.mark.parametrize("path", APP_ADDRESSES)
def test_every_page_address_opens_the_app(client, path):
    response = client.get(path)
    assert response.status_code == 200 and 'id="root"' in response.text
    assert response.headers["cache-control"] == "no-cache"


@pytest.mark.parametrize("path", ["/", "/app/agents"])
def test_head_requests_work(client, path):
    assert client.head(path).status_code == 200


@pytest.mark.parametrize("path", [
    "/static/js/main.deadbeef.js", "/static/css/gone.css", "/icons/nope.png", "/favicon.ico",
    "/nothing.map", "/other-robots.txt",
])
def test_a_missing_file_is_a_404_never_a_page_of_html(client, path):
    response = client.get(path)
    assert response.status_code == 404 and 'id="root"' not in response.text


def test_the_api_is_never_the_website(client):
    assert client.get("/api/ping").json() == {"pong": True}
    for method in ("get", "post", "put", "delete"):
        response = getattr(client, method)("/api/missing")
        assert response.status_code == 404
        assert 'id="root"' not in response.text
    assert client.get("/api/missing").json() == {"detail": "Not Found"}
    assert client.get("/api").status_code == 404


def test_files_are_cached_to_match_how_they_change(client):
    assert client.get("/static/js/main.abc123.js").headers["cache-control"] == \
        "public, max-age=31536000, immutable"
    for path in ("/sw.js", "/manifest.json", "/robots.txt", "/index.html"):
        assert client.get(path).headers["cache-control"] == "no-cache", path
    assert client.get("/demo/demo.mp4").headers["cache-control"] == "public, max-age=86400"


def test_video_can_be_played_from_the_middle(client):
    response = client.get("/demo/demo.mp4", headers={"Range": "bytes=0-99"})
    assert response.status_code == 206
    assert response.headers["content-range"] == "bytes 0-99/10240"
    assert len(response.content) == 100


def test_investor_documents_are_private_unless_switched_on(client, monkeypatch):
    private = ("vexen-cap-table", "vexen-pitch-deck", "vexen-idea-one-pager")
    for name in private:
        assert client.get(f"/docs/{name}.pdf").status_code == 404, name
    assert client.get("/docs/vexen-supporting-document.pdf").status_code == 200

    monkeypatch.setenv("SERVE_INVESTOR_DOCS", "true")
    for name in private:
        assert client.get(f"/docs/{name}.pdf").status_code == 200, name


@pytest.mark.parametrize("path", [
    "/docs/VEXEN-CAP-TABLE.PDF", "/docs/Vexen-Pitch-Deck.pdf", "/DOCS/vexen-idea-one-pager.pdf",
    "/docs/./vexen-cap-table.pdf", "/docs//vexen-cap-table.pdf", "/docs/x/../vexen-cap-table.pdf",
    "/static/../docs/vexen-cap-table.pdf", "/docs/vexen-cap-table.pdf/",
])
def test_investor_documents_cannot_be_reached_by_another_spelling(client, path):
    assert b"%PDF" not in client.get(path).content
    assert b"%PDF" not in client.get(path, headers={"Range": "bytes=0-3"}).content


@pytest.mark.parametrize("path", [
    "/docs/vexen-cap-table.pdf%00", "/static/js/main.abc123.js%00", "/%00", "/app/%00/agents",
])
def test_a_null_character_in_the_address_is_a_clean_404_not_an_error(client, path):
    assert client.get(path).status_code in (200, 404)  # a page address may still open the app
    assert b"%PDF" not in client.get(path).content


def test_a_link_to_an_investor_document_is_blocked_too(client, build):
    (build / "docs" / "alias.pdf").symlink_to(build / "docs" / "vexen-cap-table.pdf")
    os.link(build / "docs" / "vexen-pitch-deck.pdf", build / "docs" / "second-name.pdf")
    for path in ("/docs/alias.pdf", "/docs/second-name.pdf"):
        response = client.get(path)
        assert response.status_code == 404 and b"%PDF" not in response.content


def test_browser_protections_are_on_every_response(client):
    for path in ("/", "/api/ping", "/static/js/main.abc123.js", "/nope.png"):
        headers = client.get(path).headers
        assert headers["x-content-type-options"] == "nosniff", path
        assert headers["x-frame-options"] == "DENY", path
        assert headers["referrer-policy"] == "strict-origin-when-cross-origin", path
        assert "strict-transport-security" not in headers, path
    secure = client.get("/", headers={"X-Forwarded-Proto": "https"})
    assert secure.headers["strict-transport-security"].startswith("max-age=")


def test_a_path_that_climbs_out_of_the_build_serves_nothing_private(client):
    for path in ("/%2e%2e/%2e%2e/etc/passwd", "/..%2f..%2fetc/passwd", "/static/../../etc/passwd"):
        assert "root:" not in client.get(path).text


def test_the_api_keeps_its_405_and_its_trailing_slash_redirects(client):
    assert client.post("/api/ping").status_code == 405  # a GET-only route
    moved = client.get("/api/ping/", follow_redirects=False)
    assert moved.status_code == 307 and moved.headers["location"].endswith("/api/ping")


def _echo_app(max_bytes):
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    seen = {"calls": 0}

    @app.post("/echo")
    async def echo(request: Request):
        seen["calls"] += 1
        return {"bytes": len(await request.body())}

    app.add_middleware(site.BodyLimit, max_bytes=max_bytes)
    return TestClient(app), seen


def test_a_huge_body_is_refused_before_the_handler_runs():
    client, seen = _echo_app(1000)
    refused = client.post("/echo", content=b"x" * 5000)
    assert refused.status_code == 413 and refused.json() == {"detail": "That request is too large."}
    assert seen["calls"] == 0
    assert client.post("/echo", content=b"x" * 900).json() == {"bytes": 900}


def test_a_body_that_does_not_announce_its_size_is_counted_as_it_arrives():
    client, _ = _echo_app(1000)
    assert client.post("/echo", content=(b"x" * 400 for _ in range(10))).status_code == 413  # chunked
    assert client.post("/echo", content=(b"x" * 100 for _ in range(3))).json() == {"bytes": 300}


def test_the_body_limit_can_be_set_from_the_environment(monkeypatch):
    assert site.max_body_bytes() == site.DEFAULT_MAX_BODY_BYTES
    monkeypatch.setenv("MAX_REQUEST_BYTES", "2000")
    assert site.max_body_bytes() == 2000
    for bad in ("", "abc", "0", "-1"):
        monkeypatch.setenv("MAX_REQUEST_BYTES", bad)
        assert site.max_body_bytes() == site.DEFAULT_MAX_BODY_BYTES


def test_without_a_build_the_server_is_api_only(tmp_path, monkeypatch):
    monkeypatch.delenv("FRONTEND_BUILD_DIR", raising=False)
    monkeypatch.setattr(site, "ROOT", tmp_path)  # a checkout with no frontend/build
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    assert site.mount(app) is False
    assert TestClient(app).get("/").status_code == 404
