"""What changes when Vexen runs as a Vercel Function instead of one long-running container.

On Vercel the API is a function (api/index.py hands it this same app) and the website comes from
Vercel's CDN. A function instance is paused between requests and can be stopped at any moment, so
nothing may be left running once a request's invocation ends:

* Work a request starts in the background (a push to the approvers' phones) is finished after the
  response has been sent, inside the same invocation, instead of being left to run "later".
* Email a request queued is sent the same way, right after the response: nobody waits on the mail
  server, and nothing depends on a worker that may be paused. Any request also looks at the queue
  at most once a minute, which picks up retries and messages a stopped instance left behind.
* A scheduled call (vercel.json "crons") to /api/internal/outbox sends whatever is still waiting,
  for example after a quiet night. It needs CRON_SECRET; without it that address does not exist.

In the container none of this applies: the email worker runs all the time (server.py).
"""
from __future__ import annotations

import asyncio
import hmac
import logging
import os
import time
from contextvars import ContextVar
from typing import Any, Coroutine, List, Optional, Set

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

logger = logging.getLogger("vexen.serverless")

# api/index.py sets this, so the app knows it is a Vercel Function even when the project does not
# expose Vercel's own system variables (VERCEL=1).
PLATFORM_ENV = "VEXEN_PLATFORM"


def on_vercel() -> bool:
    """True inside a Vercel Function, or wherever Vercel's VERCEL=1 is set."""
    if (os.environ.get(PLATFORM_ENV) or "").strip().lower() == "vercel":
        return True
    return (os.environ.get("VERCEL") or "").strip() == "1"


# --------------------------------------------------------------------------- #
# Work that belongs to one request
# --------------------------------------------------------------------------- #
class _RequestWork:
    __slots__ = ("tasks", "mail_queued")

    def __init__(self) -> None:
        self.tasks: List[asyncio.Task] = []
        self.mail_queued = False


_work: ContextVar[Optional[_RequestWork]] = ContextVar("vexen_request_work", default=None)
_running: Set[asyncio.Task] = set()  # the event loop itself only keeps weak references to tasks


def in_background(coro: Coroutine[Any, Any, Any], *, name: Optional[str] = None) -> asyncio.Task:
    """Start `coro` without making the request wait for it.

    In the container it simply runs on. On Vercel the request's invocation finishes it after the
    response has gone out (see AfterResponse), because a paused instance would leave it half done.
    """
    task = asyncio.create_task(coro, name=name)
    _running.add(task)
    task.add_done_callback(_running.discard)
    work = _work.get()
    if work is not None:
        work.tasks.append(task)
    return task


def note_mail_queued() -> None:
    """Called by mailer.queue_email: this request put a message in the outbox."""
    work = _work.get()
    if work is not None:
        work.mail_queued = True


BACKGROUND_WAIT_SECONDS = 60  # the longest a request's background work may keep its invocation open
OUTBOX_LOOK_EVERY_SECONDS = 60  # how often an instance looks at the email queue when nothing was queued
_last_outbox_look = float("-inf")  # never; a new instance's clock (time.monotonic) can be under a minute old


class AfterResponse:
    """On Vercel, finish a request's background work and send its email once the response is out.

    The response reaches the caller as soon as the app sends it; this middleware then keeps the
    invocation open for the work that is left, so a paused or stopped instance never cuts it short.
    An agent waiting on /api/v1/authorize is therefore never slowed down by a mail server or a push
    service. Off Vercel it does nothing.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not on_vercel():
            await self.app(scope, receive, send)
            return
        work = _RequestWork()
        token = _work.set(work)
        try:
            await self.app(scope, receive, send)
        finally:
            _work.reset(token)
        # Only reached when the app answered normally. After an unexpected error the background work
        # keeps running as best it can, and the error answer is not held up by it.
        await finish(work)


async def finish(work: _RequestWork) -> None:
    # The email goes out while the background work finishes, so the approvers' email never waits
    # for a slow push service. Mail the background work queues meanwhile is sent once it is done.
    queued, work.mail_queued = work.mail_queued, False
    await asyncio.gather(_wait_for(work.tasks), send_queued_email(queued=queued))
    if work.mail_queued:
        await send_queued_email(queued=True)


async def _wait_for(tasks: List[asyncio.Task]) -> None:
    if not tasks:
        return
    done, pending = await asyncio.wait(tasks, timeout=BACKGROUND_WAIT_SECONDS)
    for task in done:
        if not task.cancelled() and task.exception() is not None:
            logger.warning("Background work failed: %s", str(task.exception())[:200])
    if pending:
        logger.warning("%s background task(s) still running after %s seconds.",
                       len(pending), BACKGROUND_WAIT_SECONDS)


AFTER_RESPONSE_SEND_SECONDS = 45  # with the background wait above, well inside vercel.json's maxDuration


async def send_queued_email(*, queued: bool) -> None:
    """Send what the outbox holds: always after a request queued mail, otherwise at most once a minute.

    Everything that is due goes out, not just one batch: a request can queue more mail than a batch
    holds (an approval alert to a large team), and on Vercel no worker comes back for the rest.
    """
    global _last_outbox_look
    from . import mailer

    if not mailer.smtp_configured():
        return  # mail waits in the queue until email is set up, exactly as in the container
    now = time.monotonic()
    if not queued and now - _last_outbox_look < OUTBOX_LOOK_EVERY_SECONDS:
        return
    _last_outbox_look = now
    try:
        from .db import get_db

        await mailer.drain_for(get_db(), seconds=AFTER_RESPONSE_SEND_SECONDS)
    except Exception as exc:  # noqa: BLE001 - the response is already out; the next look retries
        logger.error("Could not send queued email after a request: %s", str(exc)[:200])


# --------------------------------------------------------------------------- #
# The scheduled email run (vercel.json "crons")
# --------------------------------------------------------------------------- #
CRON_SECRET_ENV = "CRON_SECRET"
MIN_CRON_SECRET_LENGTH = 16
CRON_SEND_SECONDS = 50  # well inside the function's time limit (vercel.json maxDuration)

router = APIRouter()


def cron_secret() -> str:
    """CRON_SECRET when it is long enough to be a secret, otherwise "" (the run is switched off)."""
    value = (os.environ.get(CRON_SECRET_ENV) or "").strip()
    return value if len(value) >= MIN_CRON_SECRET_LENGTH else ""


def bearer_matches(header: str, secret: str) -> bool:
    """Compare an Authorization header with "Bearer <secret>" in constant time."""
    supplied = (header or "").encode("latin-1", "replace")  # how the server decoded the header's bytes
    return hmac.compare_digest(supplied, f"Bearer {secret}".encode("utf-8"))


@router.api_route("/api/internal/outbox", methods=["GET", "POST"], include_in_schema=False)
async def run_outbox(request: Request):
    """Send the queued email. Vercel calls this on the schedule in vercel.json, with
    "Authorization: Bearer <CRON_SECRET>". Any scheduler that sends the same header can call it."""
    secret = cron_secret()
    if not secret:  # switched off: answer as if the address did not exist
        return JSONResponse(status_code=404, content={"detail": "Not Found"})
    from .deps import client_ip, rate_limit

    # Counted before the secret is compared, so a caller over the limit is refused even with the
    # right secret: guessing really slows down. The schedule itself makes one call at a time.
    rate_limit(f"outbox-run:{client_ip(request)}", limit=20, window_seconds=60)
    if not bearer_matches(request.headers.get("authorization") or "", secret):
        return JSONResponse(status_code=401, content={"detail": "Not allowed."},
                            headers={"WWW-Authenticate": "Bearer"})

    from . import mailer
    from .db import get_db

    if not mailer.smtp_configured():
        return {"email": "not configured", "recovered": 0, "sent": 0, "failed": 0}
    totals = await mailer.drain_for(get_db(), seconds=CRON_SEND_SECONDS)
    return {"email": "configured", **totals}
