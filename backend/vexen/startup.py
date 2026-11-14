"""Set up once per process: the start-up checks, the database indexes and the AI key check.

In the container this runs before the server takes its first request, and a problem stops it from
starting, with the reason in the log (the host shows it). A Vercel Function is different: an instance
whose start-up fails is stopped before it can say why, every request then fails with Vercel's own
error page, and the app's start-up may not run at all. So the same work also runs on the first API
request that needs it, at most once per process (a lock keeps simultaneous first requests from
repeating it). On Vercel a problem is answered with a plain JSON error, and logged, instead.
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import List, Optional, Tuple

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from . import config, db, llm, serverless

logger = logging.getLogger("vexen")

DB_MESSAGE = ("the database did not answer. Check MONGO_URL, the database user's password and, "
              "on MongoDB Atlas, Network Access.")
DB_RETRY_SECONDS = 15  # after a failed attempt, answer 503 for this long before asking the database again

Refusal = Tuple[int, str]  # (HTTP status, message)


class Setup:
    """The one-time setup work, safe to start from the lifespan and from any request."""

    def __init__(self) -> None:
        self.checked = False
        self.problems: List[str] = []  # from config.check(): they do not change while the process runs
        self.ready = False
        self.db_error: Optional[BaseException] = None
        self._db_failed_at: Optional[float] = None
        self._lock: Optional[asyncio.Lock] = None
        self._lock_loop: Optional[asyncio.AbstractEventLoop] = None
        self._ai_check: Optional[asyncio.Task] = None

    async def ensure(self) -> Optional[Refusal]:
        """Do whatever has not been done yet. None when the API may answer, else why it may not."""
        if self.ready:
            return None
        loop = asyncio.get_running_loop()
        if self._lock is None or self._lock_loop is not loop:
            self._lock, self._lock_loop = asyncio.Lock(), loop
        async with self._lock:
            return await self._once()

    async def _once(self) -> Optional[Refusal]:
        if self.ready:  # another request finished it while this one waited for the lock
            return None
        if not self.checked:
            # Say plainly what is wrong with the setup, instead of running half-broken.
            problems, notes = config.check()
            for note in notes:
                logger.warning("Setup note: %s", note)
            for problem in problems:
                logger.error("Setup problem: %s", problem)
            self.problems, self.checked = problems, True
        if self.problems:
            return 500, "Vexen is not set up correctly, so it is not answering yet. " + " ".join(self.problems)

        failed_at = self._db_failed_at
        if failed_at is not None and time.monotonic() - failed_at < DB_RETRY_SECONDS:
            return 503, "Vexen cannot work right now: " + DB_MESSAGE
        try:
            await db.ensure_indexes()
        except Exception as exc:  # noqa: BLE001
            logger.error("Could not set up the database: %s", exc)
            self.db_error, self._db_failed_at = exc, time.monotonic()
            return 503, "Vexen cannot work right now: " + DB_MESSAGE
        logger.info("Vexen indexes ready")
        self.ready, self.db_error, self._db_failed_at = True, None, None

        # Ask Anthropic whether the AI key works, without delaying anything or failing on it. On Vercel
        # the request that ran this setup finishes the check after its response (in_background):
        # left to itself, it would sit in an instance that is paused as soon as that request ends.
        self._ai_check = serverless.in_background(asyncio.to_thread(llm.verify), name="vexen-ai-check")
        return None

    async def run(self, *, fatal: bool) -> None:
        """For the lifespan. With `fatal`, a problem stops the server from starting (the container)."""
        refusal = await self.ensure()
        if refusal is None or not fatal:
            return
        if self.problems:
            raise RuntimeError("Vexen cannot start. " + " ".join(self.problems))
        raise RuntimeError("Vexen cannot start: " + DB_MESSAGE) from self.db_error

    async def stop(self) -> None:
        task, self._ai_check = self._ai_check, None
        if task is not None:
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):  # noqa: BLE001
                pass


def needs_setup(path: str) -> bool:
    """Every API address except the liveness check, which must answer at once whatever happens."""
    return (path == "/api" or path.startswith("/api/")) and path != "/api/health"


REFUSAL_LOG_EVERY_SECONDS = 60


class SetupGate:
    """Make sure the one-time setup has run before an API request is answered (see Setup)."""

    def __init__(self, app: ASGIApp, setup: Setup) -> None:
        self.app = app
        self.setup = setup
        self._last_logged = float("-inf")  # never; a new instance's clock can be under a minute old

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not needs_setup(scope.get("path") or ""):
            await self.app(scope, receive, send)
            return
        refusal = await self.setup.ensure()
        if refusal is None:
            await self.app(scope, receive, send)
            return
        status, detail = refusal
        now = time.monotonic()
        if now - self._last_logged >= REFUSAL_LOG_EVERY_SECONDS:
            self._last_logged = now
            logger.error("Answering API requests with %s until this is fixed: %s", status, detail)
        await JSONResponse({"detail": detail}, status_code=status)(scope, receive, send)
