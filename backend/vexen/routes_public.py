"""Signed-link endpoints (decide an approval from a phone) and email plumbing.

These routes accept a signed link instead of a session, so a person can act
straight from an email on a phone without signing in. The link only ever grants
the one thing it names, expires, and stops working the moment the request is
decided.

Deliberate design note: the GET never changes anything. Mail clients and
security scanners routinely fetch every link in a message, so a link that
approved on GET would approve by itself. The link opens a page; the person taps.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request

from . import links, mailer, push
from .catalog import permission_meta
from .db import get_db
from .deps import Principal, client_ip, current_principal, public_base_url, rate_limit
from .models import LinkApprovalDecision, PushSubscriptionIn
from .service import (
    APPROVAL_TTL_MINUTES,
    APPROVER_ROLES,
    approval_state,
    decide_approval as svc_decide_approval,
    evaluate_and_record,
)

public_router = APIRouter(prefix="/api/public", tags=["public-links"])
router = APIRouter(prefix="/api", tags=["email"])

INVALID_LINK = HTTPException(
    status_code=404,
    detail="This link is no longer valid. It may have expired — open Vexen and "
           "decide from the Waiting for you page instead.",
)


def _iso(value: Any) -> Optional[str]:
    if not value:
        return None
    return value.isoformat() if hasattr(value, "isoformat") else str(value)


def _amount_display(amount: Optional[float], currency: Optional[str]) -> Optional[str]:
    if amount is None:
        return None
    symbol = {"USD": "$", "EUR": "\u20ac", "GBP": "\u00a3"}.get((currency or "USD").upper(), "")
    try:
        return f"{symbol}{float(amount):,.2f}"
    except (TypeError, ValueError):
        return None


async def _resolve(token: str) -> Dict[str, Any]:
    """Turn a signed link into (approval, org, user). Raises a friendly 404."""
    claims = links.read_approval_token(token or "")
    if not claims:
        raise INVALID_LINK
    db = get_db()
    approval = await db.approvals.find_one(
        {"org_id": claims["org_id"], "id": claims["approval_id"]})
    if not approval:
        raise INVALID_LINK
    org = await db.organizations.find_one({"id": claims["org_id"]})
    if not org:
        raise INVALID_LINK
    user = None
    if claims.get("user_id"):
        user = await db.users.find_one({"id": claims["user_id"], "org_id": claims["org_id"]})
    return {"db": db, "approval": approval, "org": org, "user": user}


@public_router.get("/approvals/{token}")
async def read_approval_link(token: str, request: Request) -> Dict[str, Any]:
    """Show what an agent is waiting for. Reading never decides anything."""
    rate_limit(f"link-read:{client_ip(request)}", limit=240, window_seconds=300)
    context = await _resolve(token)
    approval, org, user = context["approval"], context["org"], context["user"]
    state = approval_state(approval)
    meta = permission_meta(approval.get("permission_key") or "")
    app_url = mailer.public_app_url(public_base_url(request))
    return {
        "state": state,
        "can_decide": state == "pending",
        "workspace": org.get("name"),
        "agent_name": approval.get("agent_name"),
        "agent_id": approval.get("agent_id"),
        "what": meta.get("label") or approval.get("permission_key"),
        "what_detail": meta.get("description"),
        "permission_key": approval.get("permission_key"),
        "sensitive": bool(meta.get("sensitive")),
        "amount": approval.get("amount"),
        "currency": approval.get("currency") or "USD",
        "amount_display": _amount_display(approval.get("amount"), approval.get("currency")),
        "resource_id": approval.get("resource_id"),
        "reason": approval.get("reason"),
        "risk": approval.get("risk"),
        "policy": approval.get("policy"),
        "requested_at": _iso(approval.get("created_at")),
        "decided_at": _iso(approval.get("decided_at")),
        "decided_by": approval.get("decided_by_email"),
        "note": approval.get("note"),
        "used_at": _iso(approval.get("consumed_at")),
        "expires_at": _iso(approval.get("expires_at")),
        "recipient_name": (user or {}).get("name"),
        "valid_for_minutes": APPROVAL_TTL_MINUTES,
        "console_url": f"{app_url}/app/approvals",
    }


@public_router.post("/approvals/{token}/decision")
async def decide_approval_link(token: str, payload: LinkApprovalDecision,
                               request: Request) -> Dict[str, Any]:
    """Approve or refuse from the emailed link. One tap, recorded like any other."""
    ip = client_ip(request)
    rate_limit(f"link-decide-ip:{ip}", limit=60, window_seconds=300)
    context = await _resolve(token)
    db, approval, org, user = context["db"], context["approval"], context["org"], context["user"]

    if not user:
        raise INVALID_LINK
    membership = await db.memberships.find_one({"org_id": org["id"], "user_id": user["id"]})
    if not membership or membership.get("role") not in APPROVER_ROLES:
        raise HTTPException(
            status_code=403,
            detail="Your role in this workspace cannot decide approvals.",
        )
    if approval.get("status") != "pending":
        raise HTTPException(
            status_code=409,
            detail=f"This request was already {approval.get('status')} "
                   f"by {approval.get('decided_by_email') or 'someone in your workspace'}.",
        )

    updated = await svc_decide_approval(
        db, org=org, approval_id=approval["id"], decision=payload.decision,
        actor=user, note=payload.note,
    )
    if not updated:
        raise HTTPException(status_code=409, detail="This request was already decided.")

    # Re-run the original request through the engine so the recorded outcome is
    # real — exactly what the console does when somebody clicks Approve.
    agent = await db.agents.find_one({"org_id": org["id"], "agent_id": updated["agent_id"]})
    outcome = None
    if agent and not updated.get("simulation_run_id"):
        outcome = await evaluate_and_record(
            db, org=org, agent=agent,
            payload={
                "resource": updated.get("resource"),
                "action": updated.get("action"),
                "resource_id": updated.get("resource_id"),
                "amount": updated.get("amount"),
                "currency": updated.get("currency"),
            },
            source=updated.get("source") or "email-link",
            actor_email=user.get("email"),
            approval_id=approval["id"],
            base_url=public_base_url(request),
        )
    approved = payload.decision == "approved"
    return {
        "ok": True,
        "state": payload.decision,
        "decided_by": user.get("email"),
        "agent_name": updated.get("agent_name"),
        "valid_for_minutes": APPROVAL_TTL_MINUTES if approved else None,
        "message": (
            f"Approved. {updated.get('agent_name')} may go ahead once, "
            f"within the next {APPROVAL_TTL_MINUTES} minutes."
            if approved else
            f"Refused. {updated.get('agent_name')} will not be allowed to do this."
        ),
        "outcome": (outcome or {}).get("decision") if outcome else None,
    }


# ---------------------------------------------------------------------------
# Email plumbing for the signed-in user
# ---------------------------------------------------------------------------
@router.get("/notifications/email")
async def email_status(principal: Principal = Depends(current_principal)) -> Dict[str, Any]:
    """Is email actually working, and what has Vexen tried to send lately?"""
    db = get_db()
    stats = await mailer.outbox_stats(db, org_id=principal.org_id)
    prefs = principal.user.get("notification_prefs") or {}
    return {
        **stats,
        "from_address": mailer.smtp_settings().get("from_email") or None,
        "your_email": principal.email,
        "you_receive_approval_emails": prefs.get("email_approval_requests", True),
    }


@router.post("/notifications/email/test", status_code=202)
async def send_test_email(request: Request,
                          principal: Principal = Depends(current_principal)) -> Dict[str, Any]:
    """Queue a test message to the signed-in person's own address."""
    rate_limit(f"email-test:{principal.user_id}", limit=5, window_seconds=600)
    db = get_db()
    app_url = mailer.public_app_url(public_base_url(request))
    subject, text, html = mailer.test_email(
        workspace=principal.org.get("name") or "your workspace",
        console_url=f"{app_url}/app",
    )
    queued = await mailer.queue_email(
        db, to=principal.email, subject=subject, text=text, html=html,
        kind="test", org_id=principal.org_id, user_id=principal.user_id,
    )
    return {
        "ok": bool(queued),
        "configured": mailer.smtp_configured(),
        "to": principal.email,
        "message": (
            f"Test message queued for {principal.email}. It usually arrives within a minute."
            if mailer.smtp_configured() else
            "Email is not set up on this server yet, so the message is waiting in the queue."
        ),
    }


# ---------------------------------------------------------------------------
# Browser push notifications (per device)
# ---------------------------------------------------------------------------
@router.get("/push/status")
async def push_status(principal: Principal = Depends(current_principal)) -> Dict[str, Any]:
    db = get_db()
    devices = await db.push_subscriptions.count_documents(
        {"org_id": principal.org_id, "user_id": principal.user_id})
    return {
        "configured": push.push_configured(),
        "public_key": push.vapid_public_key(),
        "devices": devices,
    }


@router.post("/push/subscribe", status_code=201)
async def push_subscribe(payload: PushSubscriptionIn,
                         request: Request,
                         principal: Principal = Depends(current_principal)) -> Dict[str, Any]:
    """Remember this browser so we can nudge it when an agent is waiting."""
    rate_limit(f"push-sub:{principal.user_id}", limit=30, window_seconds=600)
    if not push.push_configured():
        raise HTTPException(
            status_code=503,
            detail="Push notifications are not set up on this server yet.",
        )
    db = get_db()
    now = datetime.now(timezone.utc)
    await db.push_subscriptions.update_one(
        {"endpoint": payload.endpoint},
        {"$set": {
            "org_id": principal.org_id,
            "user_id": principal.user_id,
            "p256dh": payload.keys.p256dh,
            "auth": payload.keys.auth,
            "user_agent": (request.headers.get("user-agent") or "")[:220],
            "updated_at": now,
        },
         "$setOnInsert": {"id": "psub_" + uuid.uuid4().hex[:20], "created_at": now}},
        upsert=True,
    )
    devices = await db.push_subscriptions.count_documents(
        {"org_id": principal.org_id, "user_id": principal.user_id})
    return {"ok": True, "devices": devices,
            "message": "This device will now be notified when an agent needs you."}


@router.delete("/push/subscribe")
async def push_unsubscribe(endpoint: Optional[str] = None,
                           principal: Principal = Depends(current_principal)) -> Dict[str, Any]:
    """Forget one device, or all of them if no endpoint is given."""
    db = get_db()
    query: Dict[str, Any] = {"org_id": principal.org_id, "user_id": principal.user_id}
    if endpoint:
        query["endpoint"] = endpoint
    result = await db.push_subscriptions.delete_many(query)
    return {"ok": True, "removed": result.deleted_count,
            "message": "This device will no longer be notified."}


@router.post("/push/test", status_code=202)
async def push_test(request: Request,
                    principal: Principal = Depends(current_principal)) -> Dict[str, Any]:
    rate_limit(f"push-test:{principal.user_id}", limit=10, window_seconds=600)
    db = get_db()
    app_url = mailer.public_app_url(public_base_url(request))
    devices = await db.push_subscriptions.count_documents(
        {"org_id": principal.org_id, "user_id": principal.user_id})
    result = await push.send_to_user(
        db, org_id=principal.org_id, user_id=principal.user_id,
        payload=push.test_payload(
            workspace=principal.org.get("name") or "your workspace",
            url=f"{app_url}/app/approvals"),
    )
    if result["sent"]:
        return {"ok": True, **result, "message": "Sent. It should appear on this device."}
    if not devices:
        return {
            "ok": False, **result,
            "message": "No device is switched on for notifications yet. Turn it on above, "
                       "then try again.",
        }
    return {
        "ok": False, **result,
        "message": ("We could not reach this device. Switch notifications off and on again, "
                    "or rely on your email alerts."),
    }
