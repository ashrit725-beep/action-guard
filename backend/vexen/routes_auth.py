"""Authentication, session and account routes."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Request, status

from .db import clean, clean_many, get_db
from .deps import Principal, client_ip, current_principal, rate_limit
from .models import (
    LoginRequest,
    NotificationPrefs,
    PasswordChange,
    ProfileUpdate,
    RefreshRequest,
    SignupRequest,
)
from .security import (
    create_token,
    decode_token,
    hash_password_async,
    new_session_id,
    password_problems,
    verify_password_async,
)
from .service import create_organization, now_utc, uid

router = APIRouter(prefix="/api/auth", tags=["auth"])


async def _new_session(db, *, user: Dict[str, Any], request: Request) -> Dict[str, Any]:
    session = {
        "id": new_session_id(),
        "user_id": user["id"],
        "org_id": user["org_id"],
        "created_at": now_utc(),
        "last_seen_at": now_utc(),
        "user_agent": (request.headers.get("user-agent") or "Unknown")[:220],
        "ip": client_ip(request),
        "revoked": False,
    }
    await db.sessions.insert_one(dict(session))
    return session


def _tokens(user: Dict[str, Any], session_id: str) -> Dict[str, Any]:
    access, access_exp = create_token(user_id=user["id"], org_id=user["org_id"], session_id=session_id)
    refresh, _ = create_token(user_id=user["id"], org_id=user["org_id"],
                              session_id=session_id, token_type="refresh")
    return {
        "access_token": access,
        "refresh_token": refresh,
        "token_type": "bearer",
        "expires_at": access_exp.isoformat(),
    }


async def _public_user(db, user: Dict[str, Any]) -> Dict[str, Any]:
    org = await db.organizations.find_one({"id": user["org_id"]})
    membership = await db.memberships.find_one({"org_id": user["org_id"], "user_id": user["id"]})
    return {
        "user": clean(user),
        "organization": clean(org),
        "role": (membership or {}).get("role", "owner"),
    }


@router.post("/signup", status_code=status.HTTP_201_CREATED)
async def signup(payload: SignupRequest, request: Request) -> Dict[str, Any]:
    # Thousands of real people share one apparent IP (mobile carriers, offices,
    # school networks, this cluster's own ingress), so the per-IP number is only
    # a crude flood guard. The meaningful limit is per email address.
    email = payload.email.lower().strip()
    rate_limit(f"signup-ip:{client_ip(request)}", limit=300, window_seconds=600)
    rate_limit(f"signup-email:{email}", limit=6, window_seconds=600)
    db = get_db()

    problems = password_problems(payload.password)
    if problems:
        raise HTTPException(status_code=422, detail="Password needs: " + ", ".join(problems))

    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=409, detail="An account with this email already exists.")

    user_id = uid("usr")
    org_name = (payload.organization or f"{payload.name.split(' ')[0]}'s Workspace").strip()[:80]
    org = await create_organization(db, name=org_name, owner_id=user_id)

    user = {
        "id": user_id,
        "email": email,
        "name": payload.name.strip()[:80],
        "password_hash": await hash_password_async(payload.password),
        "org_id": org["id"],
        "job_title": None,
        "timezone": "UTC",
        "created_at": now_utc(),
        "notification_prefs": NotificationPrefs().model_dump(),
        "onboarded": False,
    }
    try:
        await db.users.insert_one(dict(user))
    except Exception:  # noqa: BLE001
        raise HTTPException(status_code=409, detail="An account with this email already exists.")

    await db.memberships.insert_one({
        "id": uid("mem"), "org_id": org["id"], "user_id": user_id,
        "role": "owner", "created_at": now_utc(),
    })
    # New workspaces start completely empty on purpose: zero agents means zero
    # capability. The user picks what they want from the library themselves.
    # (Baseline safety rules are still installed by create_organization.)

    session = await _new_session(db, user=user, request=request)
    return {**_tokens(user, session["id"]), **await _public_user(db, user)}


@router.post("/login")
async def login(payload: LoginRequest, request: Request) -> Dict[str, Any]:
    ip = client_ip(request)
    # Per-email is what actually stops password guessing; the per-IP ceiling is
    # deliberately high so a whole office is not locked out by one bad actor.
    rate_limit(f"login-ip:{ip}", limit=600, window_seconds=300)
    rate_limit(f"login-email:{payload.email.lower()}", limit=12, window_seconds=300)
    db = get_db()
    user = await db.users.find_one({"email": payload.email.lower().strip()})
    if not user or not await verify_password_async(payload.password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Incorrect email or password.")
    session = await _new_session(db, user=user, request=request)
    return {**_tokens(user, session["id"]), **await _public_user(db, user)}


@router.post("/refresh")
async def refresh(payload: RefreshRequest) -> Dict[str, Any]:
    db = get_db()
    claims = decode_token(payload.refresh_token, expected_type="refresh")
    if not claims:
        raise HTTPException(status_code=401, detail="Session expired. Please sign in again.")
    session = await db.sessions.find_one({"id": claims["sid"]})
    if not session or session.get("revoked"):
        raise HTTPException(status_code=401, detail="Session expired. Please sign in again.")
    user = await db.users.find_one({"id": claims["sub"]})
    if not user:
        raise HTTPException(status_code=401, detail="Session expired. Please sign in again.")
    return {**_tokens(user, session["id"]), **await _public_user(db, user)}


@router.post("/logout")
async def logout(principal: Principal = Depends(current_principal)) -> Dict[str, Any]:
    db = get_db()
    await db.sessions.update_one({"id": principal.session_id},
                                 {"$set": {"revoked": True, "revoked_at": now_utc()}})
    return {"ok": True}


@router.get("/me")
async def me(principal: Principal = Depends(current_principal)) -> Dict[str, Any]:
    db = get_db()
    return await _public_user(db, principal.user)


@router.patch("/profile")
async def update_profile(payload: ProfileUpdate,
                         principal: Principal = Depends(current_principal)) -> Dict[str, Any]:
    db = get_db()
    updates = {k: v for k, v in payload.model_dump(exclude_none=True).items()}
    if updates:
        await db.users.update_one({"id": principal.user_id}, {"$set": updates})
    user = await db.users.find_one({"id": principal.user_id})
    return await _public_user(db, user)


@router.patch("/notifications")
async def update_notifications(payload: NotificationPrefs,
                               principal: Principal = Depends(current_principal)) -> Dict[str, Any]:
    db = get_db()
    await db.users.update_one({"id": principal.user_id},
                              {"$set": {"notification_prefs": payload.model_dump()}})
    return {"notification_prefs": payload.model_dump()}


@router.post("/password")
async def change_password(payload: PasswordChange,
                          principal: Principal = Depends(current_principal)) -> Dict[str, Any]:
    db = get_db()
    if not await verify_password_async(payload.current_password, principal.user.get("password_hash", "")):
        raise HTTPException(status_code=400, detail="Your current password is incorrect.")
    problems = password_problems(payload.new_password)
    if problems:
        raise HTTPException(status_code=422, detail="Password needs: " + ", ".join(problems))
    await db.users.update_one({"id": principal.user_id},
                              {"$set": {"password_hash": await hash_password_async(payload.new_password),
                                        "password_changed_at": now_utc()}})
    # Every other session is invalidated when the password changes.
    await db.sessions.update_many(
        {"user_id": principal.user_id, "id": {"$ne": principal.session_id}},
        {"$set": {"revoked": True, "revoked_at": now_utc(), "revoked_reason": "password_change"}},
    )
    return {"ok": True, "message": "Password updated. Other sessions were signed out."}


@router.get("/sessions")
async def list_sessions(principal: Principal = Depends(current_principal)) -> Dict[str, Any]:
    db = get_db()
    rows = await db.sessions.find({"user_id": principal.user_id}).sort("created_at", -1).to_list(60)
    items = []
    for row in rows:
        item = clean(row)
        item["current"] = row["id"] == principal.session_id
        items.append(item)
    return {"items": items, "total": len(items)}


@router.delete("/sessions/{session_id}")
async def revoke_session(session_id: str,
                         principal: Principal = Depends(current_principal)) -> Dict[str, Any]:
    db = get_db()
    result = await db.sessions.update_one(
        {"id": session_id, "user_id": principal.user_id},
        {"$set": {"revoked": True, "revoked_at": now_utc(), "revoked_reason": "user"}},
    )
    if not result.matched_count:
        raise HTTPException(status_code=404, detail="Session not found.")
    return {"ok": True, "current": session_id == principal.session_id}


@router.post("/sessions/revoke-others")
async def revoke_other_sessions(principal: Principal = Depends(current_principal)) -> Dict[str, Any]:
    db = get_db()
    result = await db.sessions.update_many(
        {"user_id": principal.user_id, "id": {"$ne": principal.session_id}, "revoked": False},
        {"$set": {"revoked": True, "revoked_at": now_utc(), "revoked_reason": "user"}},
    )
    return {"ok": True, "revoked": result.modified_count}
