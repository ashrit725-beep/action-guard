"""Signed, single-purpose links so somebody can act straight from an email.

A link token is a compact HMAC-signed blob. It carries ids only — never a
password, never a session token — and it is only ever accepted for the one
purpose it names. Verification never raises and never explains why it failed.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from typing import Any, Dict, Optional

PURPOSE_APPROVAL = "approval"
PURPOSE_INVITE = "invite"

DEFAULT_TTL_SECONDS = 24 * 3600
INVITE_TTL_SECONDS = 7 * 24 * 3600
MAX_TOKEN_LENGTH = 1024


def _secret() -> bytes:
    secret = os.environ.get("JWT_SECRET")
    if not secret:
        raise RuntimeError("JWT_SECRET is not configured")
    # Domain separation: a link token must never be usable as a session token.
    return ("vexen-link-v1:" + secret).encode("utf-8")


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _unb64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _mac(body: str) -> str:
    return _b64(hmac.new(_secret(), body.encode("ascii"), hashlib.sha256).digest()[:24])


def sign(purpose: str, data: Dict[str, Any], *, ttl_seconds: int = DEFAULT_TTL_SECONDS) -> str:
    payload = {**data, "p": purpose, "exp": int(time.time()) + int(ttl_seconds)}
    body = _b64(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    return f"{body}.{_mac(body)}"


def verify(token: str, purpose: str) -> Optional[Dict[str, Any]]:
    """Return the payload if the token is genuine, unexpired and for `purpose`."""
    if not token or "." not in token or len(token) > MAX_TOKEN_LENGTH:
        return None
    body, _, mac = token.rpartition(".")
    try:
        if not hmac.compare_digest(mac, _mac(body)):
            return None
        payload = json.loads(_unb64(body))
    except Exception:  # noqa: BLE001 - a malformed token is simply invalid
        return None
    if not isinstance(payload, dict) or payload.get("p") != purpose:
        return None
    expires = payload.get("exp")
    if not isinstance(expires, int) or expires < int(time.time()):
        return None
    return payload


# ---------------------------------------------------------------------------
# Approval links ("decide this from your phone")
# ---------------------------------------------------------------------------
def approval_token(*, org_id: str, approval_id: str, user_id: Optional[str] = None,
                   ttl_seconds: int = DEFAULT_TTL_SECONDS) -> str:
    """A link for one person, one approval.

    The recipient's id travels inside the token, so the audit trail can name
    exactly who decided even though nobody signed in.
    """
    data: Dict[str, Any] = {"o": org_id, "a": approval_id}
    if user_id:
        data["u"] = user_id
    return sign(PURPOSE_APPROVAL, data, ttl_seconds=ttl_seconds)


def read_approval_token(token: str) -> Optional[Dict[str, Optional[str]]]:
    payload = verify(token, PURPOSE_APPROVAL)
    if not payload:
        return None
    org_id, approval_id = payload.get("o"), payload.get("a")
    if not org_id or not approval_id:
        return None
    user_id = payload.get("u")
    return {
        "org_id": str(org_id),
        "approval_id": str(approval_id),
        "user_id": str(user_id) if user_id else None,
    }


# ---------------------------------------------------------------------------
# Invite links ("join this workspace")
# ---------------------------------------------------------------------------
def invite_token(*, org_id: str, invite_id: str,
                 ttl_seconds: int = INVITE_TTL_SECONDS) -> str:
    return sign(PURPOSE_INVITE, {"o": org_id, "i": invite_id}, ttl_seconds=ttl_seconds)


def read_invite_token(token: str) -> Optional[Dict[str, str]]:
    payload = verify(token, PURPOSE_INVITE)
    if not payload:
        return None
    org_id, invite_id = payload.get("o"), payload.get("i")
    if not org_id or not invite_id:
        return None
    return {"org_id": str(org_id), "invite_id": str(invite_id)}
