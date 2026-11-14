"""
Vexen server: the API and the website, from one address.

Vexen sits between an AI agent and the systems it wants to touch.
Every authorization decision in this service is made server-side, defaults to
deny, and produces a tamper-evident audit event.

Everything under /api is the API. Every other address is the website (the built
React app in frontend/build), so a single container serves both.

On Vercel the same app runs as a Vercel Function (api/index.py hands it over) and
Vercel's CDN serves the website; vercel.json describes that split.
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
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

ROOT = Path(__file__).parent
load_dotenv(ROOT / ".env")

from vexen import llm, logs, serverless, site, startup  # noqa: E402
from vexen.catalog import AGENT_TEMPLATES, PERMISSION_CATALOG  # noqa: E402
from vexen.db import close_db, get_db  # noqa: E402
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


# The start-up checks, the database indexes and the AI key check: once per process (vexen/startup.py).
setup = startup.Setup()


@asynccontextmanager
async def lifespan(app: FastAPI):
    on_vercel = serverless.on_vercel()
    if not on_vercel:
        # In the container a setup problem stops the server from starting, with the reason in the log.
        await setup.run(fatal=True)
    # On Vercel nothing waits here. Vercel holds every request to a new instance until this start-up
    # is over, so the liveness check would wait on the database too. The first API request runs the
    # setup instead (SetupGate below), and a problem is answered plainly rather than stopping the
    # instance before it could say why.

    # Outbound email is drained by one background task so that no request —
    # least of all an agent's authorization call — ever waits on a mail server.
    # A Vercel instance is paused between requests, so there the mail is sent right
    # after the request that queued it, and by a scheduled call (vexen/serverless.py).
    stop_mail = asyncio.Event()
    mail_task = None
    if on_vercel:
        logger.info("Email is sent after each request that queues it and by the scheduled run "
                    "(smtp configured: %s)", smtp_configured())
    else:
        mail_task = asyncio.create_task(outbox_worker(stop_mail), name="vexen-outbox")
        logger.info("Email worker started (smtp configured: %s)", smtp_configured())

    yield

    stop_mail.set()
    if mail_task is not None:
        mail_task.cancel()
        try:
            await mail_task
        except (asyncio.CancelledError, Exception):  # noqa: BLE001
            pass
    await setup.stop()
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

# Innermost first. An API request waits for the one-time setup (and is told plainly when the setup
# is broken); on Vercel, work a request started is finished after its response has been sent.
app.add_middleware(startup.SetupGate, setup=setup)
app.add_middleware(serverless.AfterResponse)

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
# On Vercel the files are on the CDN, not in the function (whose answers are also
# capped at 4.5 MB; the demo video is 18 MB), so the browser is sent to the file
# itself, and vercel.json marks a file asked for with ?download=1 as a download.
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
    if serverless.on_vercel():
        return RedirectResponse(f"/{relative}?download=1", status_code=307,
                                headers={"Cache-Control": "no-store"})
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
app.include_router(serverless.router)  # /api/internal/outbox: the scheduled email run (CRON_SECRET)

# The website answers every address the API does not. A no-op when there is no build.
site.mount(app)
