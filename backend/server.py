"""
Vexen server: the API and the website, from one address.

Vexen sits between an AI agent and the systems it wants to touch.
Every authorization decision in this service is made server-side, defaults to
deny, and produces a tamper-evident audit event.

Everything under /api is the API. Every other address is the website (the built
React app in frontend/build), so a single container serves both.
"""
from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

ROOT = Path(__file__).parent
load_dotenv(ROOT / ".env")

from vexen import config, llm, logs, site  # noqa: E402
from vexen.catalog import AGENT_TEMPLATES, PERMISSION_CATALOG  # noqa: E402
from vexen.db import close_db, ensure_indexes, get_db  # noqa: E402
from vexen.mailer import outbox_worker, smtp_configured  # noqa: E402
from vexen.routes_agents import router as agents_router  # noqa: E402
from vexen.routes_auth import router as auth_router  # noqa: E402
from vexen.routes_governance import router as governance_router  # noqa: E402
from vexen.routes_ops import public_router, router as ops_router  # noqa: E402
from vexen.routes_public import public_router as links_router, router as email_router  # noqa: E402
from vexen.routes_team import public_router as invites_router, router as team_router  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("vexen")
logs.install()  # signed links never reach the access log


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Say plainly what is wrong with the setup, instead of starting half-broken.
    problems, notes = config.check()
    for note in notes:
        logger.warning("Setup note: %s", note)
    if problems:
        for problem in problems:
            logger.error("Setup problem: %s", problem)
        raise RuntimeError("Vexen cannot start. " + " ".join(problems))

    try:
        await ensure_indexes()
    except Exception as exc:  # noqa: BLE001
        logger.error("Could not set up the database: %s", exc)
        raise RuntimeError(
            "Vexen cannot start: the database did not answer. Check MONGO_URL, the database "
            "user's password and, on MongoDB Atlas, Network Access."
        ) from exc
    logger.info("Vexen indexes ready")

    # Ask Anthropic whether the AI key works, without delaying startup or failing it.
    ai_check = asyncio.create_task(asyncio.to_thread(llm.verify), name="vexen-ai-check")

    # Outbound email is drained by one background task so that no request —
    # least of all an agent's authorization call — ever waits on a mail server.
    stop_mail = asyncio.Event()
    mail_task = asyncio.create_task(outbox_worker(stop_mail), name="vexen-outbox")
    logger.info("Email worker started (smtp configured: %s)", smtp_configured())

    yield

    stop_mail.set()
    mail_task.cancel()
    ai_check.cancel()
    for task in (mail_task, ai_check):
        try:
            await task
        except (asyncio.CancelledError, Exception):  # noqa: BLE001
            pass
    await close_db()


app = FastAPI(
    title="Vexen API",
    description="AI agent security and permissions platform. Default deny.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url=None,
    openapi_url="/api/openapi.json",
    swagger_ui_oauth2_redirect_url="/api/docs/oauth2-redirect",
)

# The website and the API share one address, so browsers need no CORS. It is only
# switched on for a front end hosted somewhere else:
#   CORS_ORIGINS=https://app.example.com,https://www.example.com
origins = [o.strip() for o in (os.environ.get("CORS_ORIGINS") or "").split(",") if o.strip()]
if origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.add_middleware(site.BodyLimit)
app.add_middleware(site.SecurityHeaders)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail},
                        headers=getattr(exc, "headers", None))


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    first = (exc.errors() or [{}])[0]
    field = ".".join(str(p) for p in (first.get("loc") or [])[1:]) or "request"
    message = first.get("msg", "Invalid request.")
    message = message.replace("Value error, ", "")
    return JSONResponse(status_code=422, content={"detail": f"{field}: {message}"})


@app.exception_handler(Exception)
async def unhandled_handler(request: Request, exc: Exception):
    # Never leak internals through errors.
    logger.exception("Unhandled error on %s %s", request.method, logs.hide_tokens(request.url.path))
    return JSONResponse(
        status_code=500,
        content={"detail": "Something went wrong on our side. The request was not authorized."},
    )


@app.get("/api/health")
async def health():
    """The host's liveness check. Deliberately trivial: it must answer in milliseconds."""
    return {
        "status": "ok",
        "service": "vexen",
        "default_decision": "BLOCK",
        "permissions": len(PERMISSION_CATALOG),
        "agent_templates": len(AGENT_TEMPLATES),
    }


@app.get("/api/ready")
async def ready():
    """Like /api/health, but it also asks the database. For people and monitors."""
    ai = llm.status()
    try:
        await asyncio.wait_for(get_db().command("ping"), timeout=5)
    except Exception:  # noqa: BLE001
        return JSONResponse(
            status_code=503,
            content={"status": "degraded", "database": "unreachable", "ai": ai["state"]},
        )
    return {"status": "ok", "database": "ok", "ai": ai["state"], "ai_provider": ai["provider"]}


# --------------------------------------------------------------------------- #
# Downloads. The same files are served statically for in-page playback; these
# routes force a save-to-disk instead of opening in the browser.
# The pitch deck, cap table and one-pager are investor material: they are only
# served when SERVE_INVESTOR_DOCS is switched on.
# --------------------------------------------------------------------------- #
DOWNLOADS = {
    "demo-video": ("demo/vexen-demo.mp4", "vexen-demo.mp4", "video/mp4"),
    "demo-video-webm": ("demo/vexen-demo.webm", "vexen-demo.webm", "video/webm"),
    "supporting-document": (
        "docs/vexen-supporting-document.pdf",
        "Vexen-Supporting-Document.pdf",
        "application/pdf",
    ),
    "pitch-deck": (
        "docs/vexen-pitch-deck.pdf",
        "Vexen-Pitch-Deck.pdf",
        "application/pdf",
    ),
    "cap-table": (
        "docs/vexen-cap-table.pdf",
        "Vexen-Cap-Table.pdf",
        "application/pdf",
    ),
    "one-pager": (
        "docs/vexen-idea-one-pager.pdf",
        "Vexen-Idea-One-Pager.pdf",
        "application/pdf",
    ),
}


@app.get("/api/download/{item}")
async def download(item: str):
    entry = DOWNLOADS.get(item)
    if item in site.INVESTOR_DOWNLOADS and not site.investor_docs_enabled():
        entry = None
    if not entry:
        return JSONResponse(status_code=404, content={"detail": "Nothing to download here."})
    relative, filename, media_type = entry
    base = site.files_dir()
    path = base / relative if base else None
    if path is None or not path.is_file():
        return JSONResponse(status_code=404, content={"detail": "That file is not available."})
    return FileResponse(
        path,
        media_type=media_type,
        filename=filename,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "public, max-age=3600",
        },
    )


app.include_router(auth_router)
app.include_router(agents_router)
app.include_router(governance_router)
app.include_router(ops_router)
app.include_router(email_router)
app.include_router(team_router)
app.include_router(public_router)
app.include_router(links_router)
app.include_router(invites_router)

# The website answers every address the API does not. A no-op when there is no build.
site.mount(app)
