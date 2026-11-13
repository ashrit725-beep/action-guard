"""Serve the website (the built React app) from the same address as the API.

One container, one address: everything under /api is the API and every other
address is the website. That is also why the browser needs no CORS: the page and
the API it talks to share an origin.

The rules this module keeps:

* Real files (hashed JS and CSS under /static, icons, the service worker, the
  demo video, the SDK) are served as files, with cache headers that match how
  they change: hashed files for a year, ``index.html`` and ``sw.js`` never stale.
* Any other page address (``/app/agents``, ``/approve/<token>``) gets
  ``index.html`` so the React router can take over. Signed links end in
  ``<body>.<mac>``, so a dot alone never means "this is a file".
* A request that is clearly for a file that does not exist (a ``/static/js/x.js``
  from before a redeploy) is a real 404, never a page of HTML.
* Unknown ``/api/...`` addresses stay a JSON 404.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

import anyio
from starlette.datastructures import MutableHeaders
from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse, Response
from starlette.staticfiles import StaticFiles
from starlette.types import ASGIApp, Message, Receive, Scope, Send

logger = logging.getLogger("vexen.site")

# backend/vexen/site.py -> the repository root, or /app inside the container
ROOT = Path(__file__).resolve().parent.parent.parent

# Things that are clearly files: asking for one that does not exist is a 404.
_FILE_SUFFIXES = frozenset({
    ".js", ".mjs", ".css", ".map", ".json", ".txt", ".xml", ".webmanifest",
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".webp", ".avif",
    ".woff", ".woff2", ".ttf", ".otf",
    ".mp4", ".webm", ".pdf", ".py",
})
# Signed links are written /approve/<body>.<mac>, so their last part contains a dot.
_LINK_PREFIXES = ("approve/", "join/")

# Investor material ships inside the build but is not part of the product site.
# It is only served when SERVE_INVESTOR_DOCS is switched on.
INVESTOR_FILES = frozenset({
    "docs/vexen-pitch-deck.pdf",
    "docs/vexen-cap-table.pdf",
    "docs/vexen-idea-one-pager.pdf",
})
INVESTOR_DOWNLOADS = frozenset({"pitch-deck", "cap-table", "one-pager"})

_NEVER_STALE = frozenset({"", "index.html", "sw.js", "manifest.json", "asset-manifest.json", "robots.txt"})


def investor_docs_enabled() -> bool:
    return (os.environ.get("SERVE_INVESTOR_DOCS") or "").strip().lower() in {"1", "true", "yes", "on"}


def build_dir() -> Optional[Path]:
    """The built website, if there is one (FRONTEND_BUILD_DIR, else frontend/build)."""
    for candidate in (os.environ.get("FRONTEND_BUILD_DIR"), ROOT / "frontend" / "build"):
        if candidate and (Path(candidate) / "index.html").is_file():
            return Path(candidate)
    return None


def files_dir() -> Optional[Path]:
    """Where the public files (demo video, PDFs, SDK) can be read from."""
    built = build_dir()
    if built is not None:
        return built
    source = ROOT / "frontend" / "public"
    return source if source.is_dir() else None


def _is_api_path(path: str) -> bool:
    return path == "api" or path.startswith("api/")


def _looks_like_file(path: str) -> bool:
    if path.startswith(_LINK_PREFIXES):
        return False
    return Path(path).suffix.lower() in _FILE_SUFFIXES


def _cache_control(path: str) -> str:
    if path.startswith("static/"):
        return "public, max-age=31536000, immutable"  # the file name changes when the file does
    if path in _NEVER_STALE:
        return "no-cache"  # always ask, so a redeploy shows up at once (the ETag keeps it cheap)
    return "public, max-age=86400"


class SiteFiles(StaticFiles):
    """StaticFiles that also knows the website's addresses (see the module notes)."""

    def _is_investor_file(self, path: str) -> bool:
        """True when `path` reaches one of the investor documents, however it is spelled.

        Comparing names is not enough: macOS and Windows file systems ignore upper and
        lower case, Windows also ignores a trailing dot or space, and a symbolic or hard
        link is another name for the same file. Asking the file system whether it is the
        same file closes all of those at once.
        """
        try:
            full_path, stat_result = self.lookup_path(path)
        except (ValueError, OSError):  # an address no file system accepts is not a file
            return False
        if stat_result is None:
            return False
        for relative in INVESTOR_FILES:
            try:
                if os.path.samefile(full_path, os.path.join(str(self.directory), relative)):
                    return True
            except OSError:
                continue
        return False

    async def get_response(self, path: str, scope: Scope) -> Response:
        if "\x00" in path:  # never a real file; the operating system would answer with an error
            raise HTTPException(status_code=404)
        clean = path.strip("/")
        if _is_api_path(clean):
            raise HTTPException(status_code=404)
        if not investor_docs_enabled():
            lowered = clean.replace("\\", "/").lower()
            if lowered in INVESTOR_FILES or (
                lowered.startswith("docs") and await anyio.to_thread.run_sync(self._is_investor_file, path)
            ):
                raise HTTPException(status_code=404)
        try:
            response = await super().get_response(path, scope)
        except HTTPException as exc:
            if exc.status_code != 404:
                raise
        else:
            response.headers["Cache-Control"] = _cache_control(clean)
            return response
        if clean.startswith("static/") or _looks_like_file(clean):
            raise HTTPException(status_code=404)
        page = await super().get_response("index.html", scope)
        page.headers["Cache-Control"] = "no-cache"
        return page


_SECURITY_HEADERS = (
    ("x-content-type-options", "nosniff"),
    ("x-frame-options", "DENY"),
    ("referrer-policy", "strict-origin-when-cross-origin"),
    ("permissions-policy", "camera=(), microphone=(), geolocation=()"),
)


class SecurityHeaders:
    """Add the standard browser protections to every response."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        request_headers = dict(scope.get("headers") or [])
        forwarded_proto = request_headers.get(b"x-forwarded-proto", b"").split(b",")[0].strip()
        secure = scope.get("scheme") == "https" or forwarded_proto == b"https"

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                for name, value in _SECURITY_HEADERS:
                    headers.setdefault(name, value)
                if secure:
                    headers.setdefault("strict-transport-security", "max-age=31536000")
            await send(message)

        await self.app(scope, receive, send_with_headers)


DEFAULT_MAX_BODY_BYTES = 256 * 1024  # the largest real request is a few thousand characters of text


def max_body_bytes() -> int:
    try:
        value = int((os.environ.get("MAX_REQUEST_BYTES") or "").strip() or DEFAULT_MAX_BODY_BYTES)
    except ValueError:
        return DEFAULT_MAX_BODY_BYTES
    return value if value > 0 else DEFAULT_MAX_BODY_BYTES


class _TooLarge(HTTPException):
    """Raised from inside the request when its body turns out to be too big. An HTTPException, so
    that FastAPI passes it on as a 413 instead of turning it into a generic 400."""

    def __init__(self) -> None:
        super().__init__(status_code=413, detail="That request is too large.")


class BodyLimit:
    """Refuse a request body far larger than anything Vexen accepts, before it is held in memory.

    The server reads a whole request body into memory before it can answer, so on a small
    instance one huge upload from a stranger could use up all of it. Bodies that announce their
    size are refused at once; bodies that do not (chunked) are counted as they arrive.
    """

    def __init__(self, app: ASGIApp, max_bytes: Optional[int] = None) -> None:
        self.app = app
        self.max_bytes = max_bytes  # None: read MAX_REQUEST_BYTES on each request

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        limit = self.max_bytes or max_body_bytes()
        declared = dict(scope.get("headers") or []).get(b"content-length", b"").strip()
        if declared.isdigit() and int(declared) > limit:
            await self._refuse(scope, receive, send)
            return

        received = 0
        started = False

        async def counted_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > limit:
                    raise _TooLarge()
            return message

        async def tracked_send(message: Message) -> None:
            nonlocal started
            if message["type"] == "http.response.start":
                started = True
            await send(message)

        try:
            await self.app(scope, counted_receive, tracked_send)
        except _TooLarge:
            if started:  # an answer that has begun cannot be replaced; let the server end the connection
                raise
            await self._refuse(scope, receive, send)

    @staticmethod
    async def _refuse(scope: Scope, receive: Receive, send: Send) -> None:
        response = JSONResponse({"detail": "That request is too large."}, status_code=413,
                                headers={"connection": "close"})
        await response(scope, receive, send)


def mount(app) -> bool:
    """Serve the built website for every address no API route claims. Call after the routers are included."""
    directory = build_dir()
    if directory is None:
        logger.warning("The built website was not found (looked in frontend/build). Serving the API only.")
        return False
    # The router's fallback, not a Mount("/"): a mount at "/" would swallow the router's own
    # "405 Method Not Allowed" and "/path/ redirects to /path" handling for the API's addresses.
    app.router.default = SiteFiles(directory=str(directory))
    logger.info("Serving the website from %s", directory)
    return True
