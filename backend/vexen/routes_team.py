"""Team seats: who is in a workspace, what they may do, and how they join.

One account belongs to one workspace, so an invitation creates the teammate's
account inside the workspace they were invited to. That keeps tenancy simple and
means a person can never accidentally act in the wrong workspace.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from . import links, mailer
from .db import clean, clean_many, get_db
from .deps import (
    ROLE_LABELS,
    ROLE_SUMMARIES,
    Principal,
    client_ip,
    current_principal,
    editor_principal,
    owner_principal,
    public_base_url,
    rate_limit,
)
from .models import InviteAccept, InviteCreate, MemberRoleUpdate
from .security import create_token, hash_password_async, new_session_id, password_problems
from .service import add_notification, alert_recipients, now_utc, uid

router = APIRouter(prefix="/api/team", tags=["team"])
public_router = APIRouter(prefix="/api/public", tags=["public-invites"])

INVITE_DAYS = 7

# An admin may bring people in, but never someone who could out-rank them.
INVITABLE_BY = {
    "owner": ("admin", "approver", "viewer"),
    "admin": ("approver", "viewer"),
}


def _role_card(role: str) -> Dict[str, str]:
    return {
        "value": role,
        "label": ROLE_LABELS.get(role, role.title()),
        "summary": ROLE_SUMMARIES.get(role, ""),
    }


def _invite_expired(invite: Dict[str, Any]) -> bool:
    expires = invite.get("expires_at")
    if not expires:
        return False
    if not expires.tzinfo:
        expires = expires.replace(tzinfo=timezone.utc)
    return expires <= datetime.now(timezone.utc)


async def _queue_invite_email(db, *, org: Dict[str, Any], invite: Dict[str, Any],
                              inviter: Dict[str, Any], base_url: Optional[str]) -> str:
    app_url = mailer.public_app_url(base_url)
    token = links.invite_token(org_id=org["id"], invite_id=invite["id"])
    join_url = f"{app_url}/join/{token}"
    subject, text, html = mailer.invite_email(
        workspace=org.get("name") or "a Vexen workspace",
        role_label=ROLE_LABELS.get(invite["role"], invite["role"]),
        inviter=inviter.get("name") or inviter.get("email") or "A teammate",
        join_url=join_url,
        role_summary=ROLE_SUMMARIES.get(invite["role"], ""),
    )
    await mailer.queue_email(
        db, to=invite["email"], subject=subject, text=text, html=html,
        kind="invite", org_id=org["id"],
        dedupe_key=f"invite:{invite['id']}:{invite.get('send_count', 0)}",
    )
    return join_url


async def _tell_the_team_somebody_joined(db, *, org: Dict[str, Any], joiner: Dict[str, Any],
                                         role: str, base_url: Optional[str] = None) -> None:
    """Let the people who asked to hear about teammates know, by email."""
    try:
        team_url = f"{mailer.public_app_url(base_url)}/app/team"
        for person in await alert_recipients(db, org_id=org["id"],
                                             pref_key="email_team_activity"):
            if person["id"] == joiner["id"]:
                continue
            subject, text, html = mailer.team_joined_email(
                workspace=org.get("name") or "your workspace",
                joiner_name=joiner.get("name") or joiner.get("email"),
                joiner_email=joiner.get("email"),
                role_label=ROLE_LABELS.get(role, role),
                team_url=team_url,
            )
            await mailer.queue_email(
                db, to=person["email"], subject=subject, text=text, html=html,
                kind="team_activity", org_id=org["id"], user_id=person["id"],
                dedupe_key=f"joined:{joiner['id']}:{person['id']}",
            )
    except Exception:  # noqa: BLE001 - a courtesy email must never block joining
        return


# ---------------------------------------------------------------------------
# Reading the team
# ---------------------------------------------------------------------------
@router.get("")
async def list_team(principal: Principal = Depends(current_principal)) -> Dict[str, Any]:
    """Everyone in this workspace, plus anyone who has been invited."""
    db = get_db()
    memberships = await db.memberships.find({"org_id": principal.org_id}).to_list(500)
    users = await db.users.find(
        {"id": {"$in": [m["user_id"] for m in memberships]}}).to_list(500)
    user_by_id = {u["id"]: u for u in users}

    members: List[Dict[str, Any]] = []
    for membership in memberships:
        user = user_by_id.get(membership["user_id"])
        if not user:
            continue
        members.append({
            "user_id": user["id"],
            "name": user.get("name"),
            "email": user.get("email"),
            "role": membership.get("role"),
            "role_label": ROLE_LABELS.get(membership.get("role"), membership.get("role")),
            "joined_at": membership.get("created_at"),
            "last_login_at": user.get("last_login_at"),
            "is_you": user["id"] == principal.user_id,
        })
    members.sort(key=lambda m: (
        {"owner": 0, "admin": 1, "approver": 2, "viewer": 3}.get(m["role"], 9),
        (m.get("name") or "").lower(),
    ))

    invites = await db.invites.find(
        {"org_id": principal.org_id, "status": "pending"}).sort("created_at", -1).to_list(100)
    pending = [{
        "id": inv["id"],
        "email": inv["email"],
        "role": inv["role"],
        "role_label": ROLE_LABELS.get(inv["role"], inv["role"]),
        "invited_by": inv.get("invited_by_email"),
        "created_at": inv.get("created_at"),
        "expires_at": inv.get("expires_at"),
        "expired": _invite_expired(inv),
    } for inv in invites]

    return {
        "members": clean_many(members),
        "invites": clean_many(pending),
        "workspace_name": principal.org.get("name"),
        "your_role": principal.role,
        "roles": [_role_card(r) for r in ("owner", "admin", "approver", "viewer")],
        "can_invite": [_role_card(r) for r in INVITABLE_BY.get(principal.role, ())],
        "can_manage_people": principal.role == "owner",
        "seats_used": len(members),
    }


# ---------------------------------------------------------------------------
# Inviting
# ---------------------------------------------------------------------------
@router.post("/invites", status_code=201)
async def create_invite(payload: InviteCreate, request: Request,
                        principal: Principal = Depends(editor_principal)) -> Dict[str, Any]:
    rate_limit(f"invite:{principal.org_id}", limit=40, window_seconds=3600)
    db = get_db()
    email = payload.email.lower().strip()
    allowed = INVITABLE_BY.get(principal.role, ())
    if payload.role not in allowed:
        wanted = ROLE_LABELS.get(payload.role, payload.role).lower()
        article = "an" if wanted[:1] in "aeiou" else "a"
        can = ", ".join(ROLE_LABELS.get(r, r).lower() for r in allowed) or "nobody"
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Your role can invite {can} — not {article} {wanted}.",
        )

    existing_user = await db.users.find_one({"email": email})
    if existing_user:
        if existing_user.get("org_id") == principal.org_id:
            raise HTTPException(status_code=409, detail=f"{email} is already in this workspace.")
        # Being honest beats a silent failure: one account, one workspace.
        raise HTTPException(
            status_code=409,
            detail=f"{email} already has a Vexen account in another workspace. "
                   "Ask them to use a different address for this one.",
        )
    if await db.invites.find_one({"org_id": principal.org_id, "email": email,
                                  "status": "pending"}):
        raise HTTPException(status_code=409,
                            detail=f"{email} has already been invited and has not joined yet.")

    invite = {
        "id": uid("inv"),
        "org_id": principal.org_id,
        "email": email,
        "role": payload.role,
        "status": "pending",
        "invited_by": principal.user_id,
        "invited_by_email": principal.email,
        "created_at": now_utc(),
        "expires_at": now_utc() + timedelta(days=INVITE_DAYS),
        "send_count": 0,
    }
    await db.invites.insert_one(dict(invite))
    join_url = await _queue_invite_email(
        db, org=principal.org, invite=invite, inviter=principal.user,
        base_url=public_base_url(request))
    await add_notification(
        db, org_id=principal.org_id, kind="team",
        title=f"{email} was invited",
        body=f"{principal.email} invited them as "
             f"{ROLE_LABELS.get(payload.role, payload.role)}.",
        severity="info", link="/app/team")
    return {
        "ok": True,
        "invite": clean({**invite, "role_label": ROLE_LABELS.get(payload.role)}),
        "join_url": join_url,
        "emailed": mailer.smtp_configured(),
        "message": (
            f"Invitation emailed to {email}."
            if mailer.smtp_configured() else
            f"Invitation created for {email}. Email is not set up on this server, "
            "so share the link yourself."
        ),
    }


@router.post("/invites/{invite_id}/resend")
async def resend_invite(invite_id: str, request: Request,
                        principal: Principal = Depends(editor_principal)) -> Dict[str, Any]:
    rate_limit(f"invite-resend:{principal.org_id}", limit=30, window_seconds=3600)
    db = get_db()
    invite = await db.invites.find_one({"org_id": principal.org_id, "id": invite_id})
    if not invite or invite.get("status") != "pending":
        raise HTTPException(status_code=404, detail="That invitation is no longer waiting.")
    await db.invites.update_one(
        {"id": invite_id},
        {"$set": {"expires_at": now_utc() + timedelta(days=INVITE_DAYS)},
         "$inc": {"send_count": 1}},
    )
    invite["send_count"] = int(invite.get("send_count") or 0) + 1
    join_url = await _queue_invite_email(
        db, org=principal.org, invite=invite, inviter=principal.user,
        base_url=public_base_url(request))
    return {"ok": True, "join_url": join_url,
            "message": f"Invitation sent to {invite['email']} again."}


@router.delete("/invites/{invite_id}")
async def revoke_invite(invite_id: str,
                        principal: Principal = Depends(editor_principal)) -> Dict[str, Any]:
    db = get_db()
    result = await db.invites.update_one(
        {"org_id": principal.org_id, "id": invite_id, "status": "pending"},
        {"$set": {"status": "revoked", "revoked_at": now_utc()}},
    )
    if not result.matched_count:
        raise HTTPException(status_code=404, detail="That invitation is no longer waiting.")
    await add_notification(
        db, org_id=principal.org_id, kind="team", title="Invitation cancelled",
        body=f"{principal.email} cancelled an invitation.", severity="info",
        link="/app/team")
    return {"ok": True, "message": "Invitation cancelled. That link no longer works."}


# ---------------------------------------------------------------------------
# Managing people
# ---------------------------------------------------------------------------
@router.patch("/members/{user_id}")
async def change_member_role(user_id: str, payload: MemberRoleUpdate,
                             principal: Principal = Depends(owner_principal)) -> Dict[str, Any]:
    db = get_db()
    if user_id == principal.user_id:
        raise HTTPException(status_code=400,
                            detail="You cannot change your own role. Ask another owner.")
    membership = await db.memberships.find_one({"org_id": principal.org_id, "user_id": user_id})
    if not membership:
        raise HTTPException(status_code=404, detail="That person is not in this workspace.")
    await db.memberships.update_one(
        {"org_id": principal.org_id, "user_id": user_id},
        {"$set": {"role": payload.role, "updated_at": now_utc()}},
    )
    person = await db.users.find_one({"id": user_id})
    label = ROLE_LABELS.get(payload.role, payload.role)
    await add_notification(
        db, org_id=principal.org_id, kind="team", title="Role changed",
        body=f"{(person or {}).get('email') or 'A teammate'} is now {label}.",
        severity="info", link="/app/team")
    name = (person or {}).get("name")
    return {"ok": True,
            "message": (f"{name} is now {label}." if name else f"Their role is now {label}.")}


@router.delete("/members/{user_id}")
async def remove_member(user_id: str,
                        principal: Principal = Depends(owner_principal)) -> Dict[str, Any]:
    db = get_db()
    if user_id == principal.user_id:
        raise HTTPException(status_code=400,
                            detail="You cannot remove yourself from your own workspace.")
    membership = await db.memberships.find_one({"org_id": principal.org_id, "user_id": user_id})
    if not membership:
        raise HTTPException(status_code=404, detail="That person is not in this workspace.")
    person = await db.users.find_one({"id": user_id})
    # Take away access first, then the record — never leave a live session behind.
    await db.sessions.update_many({"user_id": user_id}, {"$set": {"revoked": True}})
    await db.memberships.delete_one({"org_id": principal.org_id, "user_id": user_id})
    await db.users.delete_one({"id": user_id})
    await add_notification(
        db, org_id=principal.org_id, kind="team", title="Someone was removed",
        body=f"{(person or {}).get('email') or 'A teammate'} no longer has access.",
        severity="warning", link="/app/team")
    return {"ok": True,
            "message": f"{(person or {}).get('name') or 'That person'} no longer has access."}


# ---------------------------------------------------------------------------
# Accepting an invitation (no session yet)
# ---------------------------------------------------------------------------
@public_router.get("/invites/{token}")
async def read_invite(token: str, request: Request) -> Dict[str, Any]:
    rate_limit(f"invite-read:{client_ip(request)}", limit=120, window_seconds=300)
    claims = links.read_invite_token(token or "")
    if not claims:
        raise HTTPException(status_code=404,
                            detail="This invitation link has expired. Ask for a new one.")
    db = get_db()
    invite = await db.invites.find_one(
        {"org_id": claims["org_id"], "id": claims["invite_id"]})
    if not invite:
        raise HTTPException(status_code=404, detail="This invitation no longer exists.")
    org = await db.organizations.find_one({"id": claims["org_id"]})
    state = invite.get("status")
    if state == "pending" and _invite_expired(invite):
        state = "expired"
    return {
        "state": state,
        "email": invite["email"],
        "role": invite["role"],
        "role_label": ROLE_LABELS.get(invite["role"], invite["role"]),
        "role_summary": ROLE_SUMMARIES.get(invite["role"], ""),
        "workspace": (org or {}).get("name"),
        "invited_by": invite.get("invited_by_email"),
        "expires_at": invite.get("expires_at"),
    }


@public_router.post("/invites/{token}/accept", status_code=201)
async def accept_invite(token: str, payload: InviteAccept, request: Request) -> Dict[str, Any]:
    """Create the teammate's account directly inside the workspace."""
    ip = client_ip(request)
    rate_limit(f"invite-accept:{ip}", limit=15, window_seconds=900)
    claims = links.read_invite_token(token or "")
    if not claims:
        raise HTTPException(status_code=404,
                            detail="This invitation link has expired. Ask for a new one.")
    db = get_db()
    invite = await db.invites.find_one(
        {"org_id": claims["org_id"], "id": claims["invite_id"]})
    if not invite:
        raise HTTPException(status_code=404, detail="This invitation no longer exists.")
    if invite.get("status") != "pending":
        raise HTTPException(status_code=409,
                            detail=f"This invitation was already {invite.get('status')}.")
    if _invite_expired(invite):
        raise HTTPException(status_code=410,
                            detail="This invitation has expired. Ask for a new one.")

    org = await db.organizations.find_one({"id": claims["org_id"]})
    if not org:
        raise HTTPException(status_code=404, detail="That workspace no longer exists.")
    if await db.users.find_one({"email": invite["email"]}):
        raise HTTPException(status_code=409,
                            detail="An account already exists for this address. Sign in instead.")

    # Hold invited teammates to exactly the same password bar as everybody else.
    problems = password_problems(payload.password)
    if problems:
        raise HTTPException(status_code=422, detail="Password needs: " + ", ".join(problems))

    # Hashing is deliberately slow, so keep it off the event loop.
    hashed = await hash_password_async(payload.password)
    user = {
        "id": uid("usr"),
        "org_id": org["id"],
        "name": payload.name.strip(),
        "email": invite["email"],
        "password_hash": hashed,
        "job_title": None,
        "timezone": "UTC",
        "notification_prefs": {
            "approval_requests": True,
            "blocked_actions": True,
            "high_risk_agents": True,
            "weekly_digest": False,
            "email_approval_requests": True,
            "email_blocked_actions": False,
            "email_team_activity": True,
        },
        "created_at": now_utc(),
        "last_login_at": now_utc(),
        "onboarded": False,
    }
    await db.users.insert_one(dict(user))
    await db.memberships.insert_one({
        "id": uid("mem"), "org_id": org["id"], "user_id": user["id"],
        "role": invite["role"], "created_at": now_utc(),
    })
    await db.invites.update_one(
        {"id": invite["id"]},
        {"$set": {"status": "accepted", "accepted_at": now_utc(), "accepted_by": user["id"]}},
    )

    session_id = new_session_id()
    await db.sessions.insert_one({
        "id": session_id, "user_id": user["id"], "org_id": org["id"],
        "user_agent": (request.headers.get("user-agent") or "")[:200],
        "ip": ip, "created_at": now_utc(), "last_seen_at": now_utc(), "revoked": False,
    })
    await add_notification(
        db, org_id=org["id"], kind="team", title=f"{user['name']} joined",
        body=f"{user['email']} accepted their invitation as "
             f"{ROLE_LABELS.get(invite['role'], invite['role'])}.",
        severity="info", link="/app/team")
    await _tell_the_team_somebody_joined(db, org=org, joiner=user, role=invite["role"],
                                         base_url=public_base_url(request))

    access, access_exp = create_token(user_id=user["id"], org_id=org["id"],
                                      session_id=session_id)
    refresh, _ = create_token(user_id=user["id"], org_id=org["id"],
                              session_id=session_id, token_type="refresh")
    return {
        "access_token": access,
        "refresh_token": refresh,
        "token_type": "bearer",
        "expires_at": access_exp.isoformat(),
        "user": {"id": user["id"], "name": user["name"], "email": user["email"],
                 "role": invite["role"]},
        "organization": {"id": org["id"], "name": org.get("name"), "slug": org.get("slug")},
        "message": f"Welcome to {org.get('name')}.",
    }
