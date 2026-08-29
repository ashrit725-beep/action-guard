"""Authentication dependencies, tenancy guards and lightweight rate limiting."""
from __future__ import annotations

import time
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Deque, Dict, Optional, Tuple

from fastapi import Depends, HTTPException, Request, status

from .db import get_db
from .security import decode_token, hash_api_key, looks_like_agent_key

# ---------------------------------------------------------------------------
# Rate limiting (per-process token buckets; safe defaults, fails closed on abuse)
# ---------------------------------------------------------------------------
_BUCKETS: Dict[str, Deque[float]] = defaultdict(deque)


def rate_limit(key: str, *, limit: int, window_seconds: int) -> None:
    now = time.monotonic()
    bucket = _BUCKETS[key]
    cutoff = now - window_seconds
    while bucket and bucket[0] < cutoff:
        bucket.popleft()
    if len(bucket) >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please slow down and try again shortly.",
        )
    bucket.append(now)
    if len(_BUCKETS) > 20000:  # keep memory bounded
        for stale_key in list(_BUCKETS.keys())[:5000]:
            if not _BUCKETS[stale_key]:
                _BUCKETS.pop(stale_key, None)


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def public_base_url(request: Request) -> str:
    """The address somebody outside this cluster can actually reach.

    Behind the ingress, `request.base_url` is an internal cluster hostname, so
    the developer docs (and the URLs we hand to agents) must be built from the
    forwarded headers instead — otherwise every copied curl command fails on
    someone else's machine.
    """
    proto = (request.headers.get("x-forwarded-proto") or "").split(",")[0].strip()
    host = (request.headers.get("x-forwarded-host") or "").split(",")[0].strip()
    if not host:
        host = (request.headers.get("host") or "").split(",")[0].strip()
    if not host:
        return str(request.base_url).rstrip("/")
    if not proto:
        local = host.startswith("localhost") or host.startswith("127.0.0.1")
        proto = request.url.scheme if local else "https"
    return f"{proto}://{host}"


@dataclass
class Principal:
    user: Dict[str, Any]
    org: Dict[str, Any]
    session_id: str
    role: str = "owner"

    @property
    def org_id(self) -> str:
        return str(self.org["id"])

    @property
    def user_id(self) -> str:
        return str(self.user["id"])

    @property
    def email(self) -> str:
        return str(self.user.get("email", ""))

    @property
    def can_edit(self) -> bool:
        """May change agents, rules, keys and workspace settings."""
        return self.role in ("owner", "admin")

    @property
    def can_approve(self) -> bool:
        """May approve or refuse what an agent is waiting on."""
        return self.role in ("owner", "admin", "approver")


def _bearer(request: Request) -> Optional[str]:
    header = request.headers.get("authorization") or ""
    if header.lower().startswith("bearer "):
        return header[7:].strip()
    return None


UNAUTHORIZED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Your session has expired. Please sign in again.",
    headers={"WWW-Authenticate": "Bearer"},
)


async def current_principal(request: Request) -> Principal:
    token = _bearer(request)
    if not token:
        raise UNAUTHORIZED
    payload = decode_token(token, expected_type="access")
    if not payload:
        raise UNAUTHORIZED
    db = get_db()
    session = await db.sessions.find_one({"id": payload["sid"]})
    if not session or session.get("revoked"):
        raise UNAUTHORIZED
    user = await db.users.find_one({"id": payload["sub"]})
    if not user or user.get("org_id") != payload["org"]:
        raise UNAUTHORIZED
    org = await db.organizations.find_one({"id": payload["org"]})
    if not org:
        raise UNAUTHORIZED
    membership = await db.memberships.find_one({"org_id": org["id"], "user_id": user["id"]})
    if not membership:
        raise UNAUTHORIZED
    await db.sessions.update_one(
        {"id": session["id"]},
        {"$set": {"last_seen_at": datetime.now(timezone.utc), "ip": client_ip(request)}},
    )
    return Principal(user=user, org=org, session_id=session["id"],
                     role=str(membership.get("role") or "viewer"))


CurrentPrincipal = Depends(current_principal)


# ---------------------------------------------------------------------------
# Roles: who is allowed to change things, and who may only look
# ---------------------------------------------------------------------------
ROLES = ("owner", "admin", "approver", "viewer")

ROLE_LABELS = {
    "owner": "Owner",
    "admin": "Admin",
    "approver": "Approver",
    "viewer": "Viewer",
}

ROLE_SUMMARIES = {
    "owner": "Can do everything, including billing and removing people.",
    "admin": "Can add agents and change rules, but cannot remove people.",
    "approver": "Can approve or refuse what is waiting, and see everything.",
    "viewer": "Can look at everything but cannot change or decide anything.",
}

_ROLE_MESSAGES = {
    "edit": "Your role can look but not change things. Ask an owner or admin in "
            "your workspace to make this change.",
    "approve": "Your role cannot approve or refuse agent actions. Ask an owner, "
               "admin or approver in your workspace.",
    "own": "Only the workspace owner can do this.",
}


def require_roles(*allowed: str, kind: str = "edit"):
    """Build a dependency that only lets certain roles through."""

    async def guard(principal: Principal = Depends(current_principal)) -> Principal:
        if principal.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=_ROLE_MESSAGES.get(kind, _ROLE_MESSAGES["edit"]),
            )
        return principal

    return guard


# Ready-made guards, so every route reads plainly.
editor_principal = require_roles("owner", "admin", kind="edit")
approver_principal = require_roles("owner", "admin", "approver", kind="approve")
owner_principal = require_roles("owner", kind="own")


async def agent_principal(request: Request) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Resolve an agent API key into (credential, agent). Never leaks why it failed."""
    raw = request.headers.get("x-vexen-key") or request.headers.get("x-api-key") or _bearer(request) or ""
    raw = raw.strip()
    generic = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing Vexen agent key.",
    )
    if not looks_like_agent_key(raw):
        rate_limit(f"authz-anon:{client_ip(request)}", limit=300, window_seconds=60)
        raise generic
    db = get_db()
    cred = await db.credentials.find_one({"key_hash": hash_api_key(raw)})
    if not cred or cred.get("status") != "active":
        rate_limit(f"authz-anon:{client_ip(request)}", limit=300, window_seconds=60)
        raise generic
    expires_at = cred.get("expires_at")
    if expires_at:
        exp = expires_at if expires_at.tzinfo else expires_at.replace(tzinfo=timezone.utc)
        if exp <= datetime.now(timezone.utc):
            raise generic
    rate_limit(f"authz-key:{cred['id']}", limit=600, window_seconds=60)
    agent = await db.agents.find_one({"org_id": cred["org_id"], "agent_id": cred["agent_id"]})
    if not agent:
        raise generic
    await db.credentials.update_one(
        {"id": cred["id"]},
        {"$set": {"last_used_at": datetime.now(timezone.utc)}, "$inc": {"use_count": 1}},
    )
    return cred, agent


AgentPrincipal = Depends(agent_principal)
