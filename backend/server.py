"""
Vexen API server.

Vexen sits between an AI agent and the systems it wants to touch.
Every authorization decision in this service is made server-side, defaults to
deny, and produces a tamper-evident audit event.
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

from vexen.catalog import AGENT_TEMPLATES, PERMISSION_CATALOG  # noqa: E402
from vexen.db import close_db, ensure_indexes  # noqa: E402
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await ensure_indexes()
        logger.info("Vexen indexes ready")
    except Exception as exc:  # noqa: BLE001
        logger.error("Index setup failed: %s", exc)

    # Outbound email is drained by one background task so that no request —
    # least of all an agent's authorization call — ever waits on a mail server.
    stop_mail = asyncio.Event()
    mail_task = asyncio.create_task(outbox_worker(stop_mail), name="vexen-outbox")
    logger.info("Email worker started (smtp configured: %s)", smtp_configured())

    yield

    stop_mail.set()
    mail_task.cancel()
    try:
        await mail_task
    except (asyncio.CancelledError, Exception):  # noqa: BLE001
        pass
    await close_db()


app = FastAPI(
    title="Vexen API",
    description="AI agent security and permissions platform. Default deny.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

origins = os.environ.get("CORS_ORIGINS", "*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in origins.split(",")] if origins != "*" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Something went wrong on our side. The request was not authorized."},
    )


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "service": "vexen",
        "default_decision": "BLOCK",
        "permissions": len(PERMISSION_CATALOG),
        "agent_templates": len(AGENT_TEMPLATES),
    }


# --------------------------------------------------------------------------- #
# Downloads. The same files are served statically for in-page playback; these
# routes force a save-to-disk instead of opening in the browser.
# --------------------------------------------------------------------------- #
PUBLIC_DIR = Path(__file__).resolve().parent.parent / "frontend" / "public"

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
    if not entry:
        return JSONResponse(status_code=404, content={"detail": "Nothing to download here."})
    relative, filename, media_type = entry
    path = PUBLIC_DIR / relative
    if not path.is_file():
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
