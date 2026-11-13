"""Password hashing, JWT sessions and agent API-key credentials for Vexen."""
from __future__ import annotations

import hashlib
import hmac
import os
import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

import asyncio

import bcrypt
import jwt

def _env_int(name: str, default: int) -> int:
    """A blank or malformed value in a hosting dashboard falls back instead of crashing at import."""
    try:
        value = int((os.environ.get(name) or "").strip() or default)
    except ValueError:
        return default
    return value if value > 0 else default


JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_MINUTES = _env_int("ACCESS_TOKEN_MINUTES", 60)
REFRESH_TOKEN_DAYS = _env_int("REFRESH_TOKEN_DAYS", 30)

KEY_PREFIX = "vex_sk_live_"


def jwt_secret() -> str:
    secret = os.environ.get("JWT_SECRET")
    if not secret:
        raise RuntimeError("JWT_SECRET is not configured")
    return secret


# ---------------------------------------------------------------------------
# Passwords
# ---------------------------------------------------------------------------
PASSWORD_RULES = [
    ("At least 10 characters", lambda p: len(p) >= 10),
    ("An uppercase letter", lambda p: bool(re.search(r"[A-Z]", p))),
    ("A lowercase letter", lambda p: bool(re.search(r"[a-z]", p))),
    ("A number", lambda p: bool(re.search(r"\d", p))),
]

COMMON_PASSWORDS = {
    "password123", "password1234", "qwerty12345", "letmein123", "welcome123",
    "admin12345", "iloveyou123", "1234567890", "passw0rd12",
}


def password_problems(password: str) -> list[str]:
    problems = [label for label, check in PASSWORD_RULES if not check(password or "")]
    if (password or "").lower() in COMMON_PASSWORDS:
        problems.append("Not a commonly used password")
    return problems


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8")[:72], bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    if not password or not hashed:
        return False
    try:
        return bcrypt.checkpw(password.encode("utf-8")[:72], hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


# Hashing a password on purpose takes ~300ms of CPU. Doing that on the event
# loop freezes every other person's request (and every agent's decision) while
# it runs, so signups and logins hand the work to a worker thread.
async def hash_password_async(password: str) -> str:
    return await asyncio.to_thread(hash_password, password)


async def verify_password_async(password: str, hashed: str) -> bool:
    return await asyncio.to_thread(verify_password, password, hashed)


# ---------------------------------------------------------------------------
# JWT sessions
# ---------------------------------------------------------------------------
def create_token(*, user_id: str, org_id: str, session_id: str, token_type: str = "access",
                 minutes: Optional[int] = None) -> Tuple[str, datetime]:
    now = datetime.now(timezone.utc)
    if token_type == "refresh":
        expires = now + timedelta(days=REFRESH_TOKEN_DAYS)
    else:
        expires = now + timedelta(minutes=minutes or ACCESS_TOKEN_MINUTES)
    payload = {
        "sub": user_id,
        "org": org_id,
        "sid": session_id,
        "typ": token_type,
        "iat": int(now.timestamp()),
        "exp": int(expires.timestamp()),
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(payload, jwt_secret(), algorithm=JWT_ALGORITHM), expires


def decode_token(token: str, *, expected_type: str = "access") -> Optional[Dict[str, Any]]:
    try:
        payload = jwt.decode(token, jwt_secret(), algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None
    if payload.get("typ") != expected_type:
        return None
    if not payload.get("sub") or not payload.get("org") or not payload.get("sid"):
        return None
    return payload


# ---------------------------------------------------------------------------
# Agent API keys
# ---------------------------------------------------------------------------
def generate_agent_key() -> Tuple[str, str, str]:
    """Return (plaintext_secret, sha256_hash, display_prefix).

    The plaintext secret is shown exactly once at creation time and never stored.
    """
    body = secrets.token_urlsafe(32).replace("-", "").replace("_", "")[:36]
    plaintext = f"{KEY_PREFIX}{body}"
    return plaintext, hash_api_key(plaintext), plaintext[: len(KEY_PREFIX) + 6]


def hash_api_key(plaintext: str) -> str:
    pepper = os.environ.get("API_KEY_PEPPER", "")
    return hashlib.sha256((pepper + (plaintext or "")).encode("utf-8")).hexdigest()


def verify_api_key(plaintext: str, stored_hash: str) -> bool:
    if not plaintext or not stored_hash:
        return False
    return hmac.compare_digest(hash_api_key(plaintext), stored_hash)


def looks_like_agent_key(value: str) -> bool:
    return bool(value) and value.startswith(KEY_PREFIX) and len(value) >= len(KEY_PREFIX) + 20


def new_session_id() -> str:
    return "VEX-SES-" + uuid.uuid4().hex[:12].upper()


def fingerprint(value: str) -> str:
    return hashlib.sha256((value or "").encode("utf-8")).hexdigest()[:16]
