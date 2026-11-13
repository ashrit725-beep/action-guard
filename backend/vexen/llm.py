"""The one door to the AI provider: Anthropic, and only Anthropic.

Vexen's two AI features (the plain-English rule writer and the in-app helper)
run on Anthropic's Claude. This module is the only place that reads the provider
key or builds a client, and it is strict on purpose so nothing else can be
slotted in:

* There is exactly one AI credential: ``ANTHROPIC_API_KEY``.
* It must be shaped like an Anthropic API key (``sk-ant-...``). A key from any
  other provider is refused before a single request leaves the server.
* Requests go to ``https://api.anthropic.com`` and nowhere else. The client is
  built with an explicit key and an explicit address, so ``ANTHROPIC_BASE_URL``
  and ``ANTHROPIC_AUTH_TOKEN`` in the environment cannot redirect traffic to a
  proxy or a "compatible" endpoint.
* The final judge is Anthropic itself: ``verify()`` asks the API whether it
  accepts the key (a free metadata call, no text is generated).

The key is never logged, returned or included in an error message.
"""
from __future__ import annotations

import collections
import hashlib
import logging
import os
import re
import threading
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

logger = logging.getLogger("vexen.llm")

PROVIDER = "anthropic"
KEY_ENV = "ANTHROPIC_API_KEY"
API_URL = "https://api.anthropic.com"
MODEL = "claude-opus-5-5"
KEY_PREFIX = "sk-ant-"

# sk-ant-<kind>-<secret>: letters, digits, dash and underscore only.
_KEY_SHAPE = re.compile(r"^sk-ant-[A-Za-z0-9_-]{24,}$")

# What a pasted key most likely is when it is not an Anthropic API key, so the
# message can say so. Longer, more specific prefixes come first.
_NOT_AN_API_KEY = (
    ("sk-ant-admin", "an Anthropic Admin key, which manages an organization and cannot run models"),
    ("sk-ant-oat", "an Anthropic sign-in token, not an API key"),
)
_OTHER_PROVIDERS = (
    ("sk-proj-", "an OpenAI key"),
    ("sk-svcacct-", "an OpenAI key"),
    ("sk-emergent-", "an Emergent universal key"),
    ("sk-or-", "an OpenRouter key"),
    ("vex_sk_live_", "a Vexen agent key"),
    ("AIza", "a Google key"),
    ("gsk_", "a Groq key"),
    ("xai-", "an xAI key"),
    ("pplx-", "a Perplexity key"),
    ("hf_", "a Hugging Face token"),
    ("r8_", "a Replicate token"),
    ("sk-", "an OpenAI-style key"),
)

# A key Anthropic has just refused is not retried for this long, so a broken
# setup does not send a doomed request for every click.
REJECTED_COOLDOWN_SECONDS = 300


class ProviderKeyError(RuntimeError):
    """ANTHROPIC_API_KEY is missing, is not an Anthropic API key, or was refused."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class ProviderBusy(RuntimeError):
    """Too many model calls are already running; the caller should try again shortly."""


@dataclass(frozen=True)
class KeyCheck:
    ok: bool
    code: str  # "ok" | "missing" | "not_an_anthropic_key"
    message: str  # plain words for whoever runs the server; never contains the key
    key: str = ""  # the cleaned key when ok, otherwise empty


# Whitespace, plus the invisible characters (byte-order mark, zero-width space, direction
# marks, soft hyphen) that ride along when a key is copied out of a web page.
_EDGE = " \t\r\n\x0b\x0c   ﻿​‌‍⁠‎‏" \
        "‪‫‬‭‮⁦⁧⁨⁩­"


def _clean(raw: Optional[str]) -> str:
    value = (raw or "").strip(_EDGE)
    # A value pasted with its quotes ("sk-ant-...") is a common dashboard slip.
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        value = value[1:-1].strip(_EDGE)
    return value


def check_key(raw: Optional[str]) -> KeyCheck:
    """Decide from its shape alone whether a value can be an Anthropic API key."""
    value = _clean(raw)
    if not value:
        return KeyCheck(False, "missing",
                        f"{KEY_ENV} is not set. Add an Anthropic API key (it starts with {KEY_PREFIX}).")
    for prefix, what in _NOT_AN_API_KEY:
        if value.startswith(prefix):
            return KeyCheck(False, "not_an_anthropic_key",
                            f"{KEY_ENV} holds {what}. Create a regular API key in the "
                            "Anthropic Console and use that.")
    if not value.startswith(KEY_PREFIX):
        guess = next((what for prefix, what in _OTHER_PROVIDERS if value.startswith(prefix)), "")
        looks_like = f" It looks like {guess}." if guess else ""
        return KeyCheck(False, "not_an_anthropic_key",
                        f"{KEY_ENV} is not an Anthropic API key.{looks_like} "
                        f"Only Anthropic keys fit here; they start with {KEY_PREFIX}.")
    if not _KEY_SHAPE.match(value):
        return KeyCheck(False, "not_an_anthropic_key",
                        f"{KEY_ENV} starts like an Anthropic key but is cut short or has "
                        "extra characters. Copy the whole key again.")
    return KeyCheck(True, "ok", "The key has the shape of an Anthropic API key.", value)


def _current() -> KeyCheck:
    return check_key(os.environ.get(KEY_ENV))


# An Anthropic API key that is not tied to one workspace must say which workspace a request
# runs in. Most keys are tied to one and need nothing; see docs/DEPLOY.md.
WORKSPACE_ENV = "ANTHROPIC_WORKSPACE_ID"
_WORKSPACE_SHAPE = re.compile(r"^wrkspc_[A-Za-z0-9]{10,}\Z")

# SDK settings that would otherwise be read from the environment and could change where a
# request goes or which credential it carries. They are ignored (see _new_client).
IGNORED_ENV = ("ANTHROPIC_BASE_URL", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_CUSTOM_HEADERS")


def workspace_id() -> str:
    """The workspace ID from ANTHROPIC_WORKSPACE_ID, or "" when unset or not shaped like one."""
    value = _clean(os.environ.get(WORKSPACE_ENV))
    return value if _WORKSPACE_SHAPE.match(value) else ""


def _fingerprint(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------- #
# What Anthropic has said about the key (process-wide, never the key itself)
# --------------------------------------------------------------------------- #
_lock = threading.Lock()
_verdict: Dict[str, Any] = {"fingerprint": "", "state": "unverified", "detail": "", "at": 0.0}


def _remember(key: str, state: str, detail: str) -> None:
    with _lock:
        _verdict.update(fingerprint=_fingerprint(key), state=state, detail=detail, at=time.monotonic())


def _verdict_for(key: str) -> Dict[str, Any]:
    with _lock:
        if _verdict["fingerprint"] != _fingerprint(key):
            return {"state": "unverified", "detail": "", "at": 0.0}
        return dict(_verdict)


def mark_working() -> None:
    """A real request just succeeded with the current key."""
    check = _current()
    if check.ok:
        _remember(check.key, "ready", "Anthropic accepted the key.")


def mark_rejected(detail: str = "") -> None:
    """Anthropic refused the current key (HTTP 401 or 403)."""
    check = _current()
    if check.ok:
        _remember(check.key, "rejected",
                  detail or "Anthropic refused this key. It may be revoked, mistyped or disabled.")
        logger.error("Anthropic refused %s. AI features are off until it is replaced.", KEY_ENV)


def mark_model_unavailable() -> None:
    """The key is Anthropic's, but its workspace cannot use the model (HTTP 404)."""
    check = _current()
    if check.ok:
        _remember(check.key, "model_unavailable",
                  f"The key is a valid Anthropic key, but it cannot use {MODEL}. "
                  "Check the model access of its workspace in the Anthropic Console.")
        logger.error("The Anthropic key works but has no access to %s.", MODEL)


def _reset_for_tests() -> None:
    with _lock:
        _verdict.update(fingerprint="", state="unverified", detail="", at=0.0)
    _calls_today.clear()
    _in_flight.clear()


# Verdicts that switch the AI features off until the cooldown has passed.
_BLOCKING = ("rejected", "model_unavailable")


def _blocked(verdict: Dict[str, Any]) -> bool:
    return (verdict["state"] in _BLOCKING
            and (time.monotonic() - verdict["at"]) <= REJECTED_COOLDOWN_SECONDS)


# --------------------------------------------------------------------------- #
# Public surface
# --------------------------------------------------------------------------- #
def available() -> bool:
    """True when an Anthropic key is in place and Anthropic has not just refused it."""
    check = _current()
    return check.ok and not _blocked(_verdict_for(check.key))


def require_key() -> str:
    """Return the Anthropic key or raise ProviderKeyError. Nothing else can pass."""
    check = _current()
    if not check.ok:
        raise ProviderKeyError(check.code, check.message)
    verdict = _verdict_for(check.key)
    if _blocked(verdict):
        raise ProviderKeyError(verdict["state"], verdict["detail"])
    return check.key


_construct_lock = threading.Lock()


def _new_client(*, api_key: str, timeout: float, max_retries: int):
    """The only place an Anthropic client is constructed.

    Passing the key and the address explicitly makes the SDK ignore ANTHROPIC_BASE_URL and
    ANTHROPIC_AUTH_TOKEN. It would still read ANTHROPIC_CUSTOM_HEADERS, which can replace the
    credential, add another one, or change the Host header. So that variable is hidden while the
    client is built: the only credential is the validated key, and the only extra header is the
    workspace ID.
    """
    import anthropic

    workspace = workspace_id()
    headers = {"anthropic-workspace-id": workspace} if workspace else None
    with _construct_lock:
        hidden = {name: os.environ.pop(name) for name in IGNORED_ENV if name in os.environ}
        try:
            return anthropic.Anthropic(
                api_key=api_key,
                base_url=API_URL,
                max_retries=max_retries,
                timeout=timeout,
                default_headers=headers,
            )
        finally:
            os.environ.update(hidden)


def client(*, timeout: float, max_retries: int = 1):
    """Build the Anthropic client for a real request (see _new_client)."""
    return _new_client(api_key=require_key(), timeout=timeout, max_retries=max_retries)


MAX_PARALLEL_CALLS = 8  # model calls running at once; each holds a worker thread for up to ~90 s
MAX_WAITING_CALLS = 16  # beyond this, answer "busy" instead of queueing without end
_limiter = None

DAILY_LIMIT_ENV = "AI_DAILY_CALL_LIMIT"
DEFAULT_DAILY_CALL_LIMIT = 500
_calls_today = collections.deque()  # start times (monotonic) of the model calls in the last 24 hours


def daily_call_limit() -> int:
    """How many model calls this server allows in a rolling 24 hours; 0 means no limit.

    Anyone can sign up, so this is the server's own ceiling on what the AI features can
    cost. Also set a spending limit in the Anthropic Console: that is the hard stop.
    """
    raw = (os.environ.get(DAILY_LIMIT_ENV) or "").strip()
    try:
        value = int(raw) if raw else DEFAULT_DAILY_CALL_LIMIT
    except ValueError:
        return DEFAULT_DAILY_CALL_LIMIT
    return value if value >= 0 else DEFAULT_DAILY_CALL_LIMIT


def _count_call() -> None:
    limit = daily_call_limit()
    if not limit:
        return
    now = time.monotonic()
    while _calls_today and now - _calls_today[0] > 86400:
        _calls_today.popleft()
    if len(_calls_today) >= limit:
        raise ProviderBusy("The AI helper has reached its limit for today. It comes back within 24 hours.")
    _calls_today.append(now)


MAX_CALLS_PER_PERSON = 2  # model calls one person can have running at the same moment
_in_flight = collections.Counter()


async def run_blocking(func, *args, owner: str = ""):
    """Run a blocking model call in a worker thread without starving the rest of the site.

    The Anthropic client is synchronous and one call can take tens of seconds. The worker
    threads are shared with static files and downloads, so model calls get a small allowance
    of their own, and no one person can use all of it (`owner` identifies the person).
    """
    import anyio

    global _limiter
    if _limiter is None:
        _limiter = anyio.CapacityLimiter(MAX_PARALLEL_CALLS)
    if _limiter.statistics().tasks_waiting >= MAX_WAITING_CALLS:
        raise ProviderBusy("The AI helper is busy right now. Try again in a minute.")
    if owner and _in_flight[owner] >= MAX_CALLS_PER_PERSON:
        raise ProviderBusy("You already have AI requests running. Wait for one to finish, then try again.")
    _count_call()
    if owner:
        _in_flight[owner] += 1
    try:
        return await anyio.to_thread.run_sync(func, *args, limiter=_limiter)
    finally:
        if owner:
            _in_flight[owner] -= 1
            if _in_flight[owner] <= 0:
                del _in_flight[owner]


def verify(*, timeout: float = 10.0) -> Dict[str, Any]:
    """Ask Anthropic whether it accepts the key. Free: reads model details only.

    Safe to call at startup: it never raises and never blocks longer than
    ``timeout``. When Anthropic cannot be reached the key stays "unverified" and
    the first real request settles it.
    """
    check = _current()
    if not check.ok:
        return status()
    import anthropic

    try:
        probe = _new_client(api_key=check.key, timeout=timeout, max_retries=0)
        probe.models.retrieve(MODEL)
    except anthropic.AuthenticationError:
        mark_rejected()
    except anthropic.BadRequestError as exc:
        # Most often a key that is not tied to a workspace and no ANTHROPIC_WORKSPACE_ID to say which.
        logger.error("Anthropic rejected the key check (HTTP 400): %s. If the key is not tied to one "
                     "workspace, set %s.", getattr(exc, "message", "bad request"), WORKSPACE_ENV)
    except anthropic.PermissionDeniedError:
        # This key may simply not be allowed to look up model details. A real request decides.
        logger.warning("Anthropic would not show model details to this key. Will find out on first use.")
    except anthropic.NotFoundError:
        mark_model_unavailable()
    except anthropic.APIError as exc:
        # Rate limit, outage or no network: says nothing about the key itself.
        logger.warning("Could not check the Anthropic key yet (%s). Will try on first use.",
                       type(exc).__name__)
    except Exception as exc:  # noqa: BLE001 - a status check must never take the server down
        logger.warning("Anthropic key check failed unexpectedly (%s).", type(exc).__name__)
    else:
        _remember(check.key, "ready", "Anthropic accepted the key.")
        logger.info("AI ready: Anthropic accepted the key (model %s).", MODEL)
    return status()


def status() -> Dict[str, Any]:
    """What an operator needs to know about the AI setup. Never includes the key."""
    base = {"provider": PROVIDER, "model": MODEL, "endpoint": API_URL, "key_variable": KEY_ENV}
    check = _current()
    if not check.ok:
        state = "missing_key" if check.code == "missing" else "not_an_anthropic_key"
        return {**base, "state": state, "available": False, "detail": check.message}
    verdict = _verdict_for(check.key)
    if verdict["state"] == "unverified":
        detail = "The key has the shape of an Anthropic API key. It is confirmed on first use."
    else:
        detail = verdict["detail"]
    return {**base, "state": verdict["state"], "available": available(), "detail": detail}
