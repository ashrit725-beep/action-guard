"""Browser push notifications.

A push message is a courtesy, never a source of truth: if it fails, the email and
the console still tell the whole story. So every function here is written to fail
quietly, prune dead subscriptions, and stay off the event loop (pywebpush is
blocking, so it runs in a threadpool).
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger("vexen.push")

SEND_TIMEOUT_SECONDS = 12
# A browser tells us a subscription is dead with one of these.
DEAD_STATUSES = (404, 410)


def vapid_public_key() -> str:
    return (os.environ.get("VAPID_PUBLIC_KEY") or "").strip()


def push_configured() -> bool:
    return bool(vapid_public_key() and (os.environ.get("VAPID_PRIVATE_KEY") or "").strip())


def _claims() -> Dict[str, str]:
    return {"sub": (os.environ.get("VAPID_SUBJECT") or "mailto:admin@vexen.app").strip()}


def _send_blocking(subscription: Dict[str, Any], payload: Dict[str, Any]) -> Optional[int]:
    """Deliver one push. Returns an HTTP status to act on, or None on success."""
    from pywebpush import WebPushException, webpush

    try:
        webpush(
            subscription_info={
                "endpoint": subscription["endpoint"],
                "keys": {"p256dh": subscription["p256dh"], "auth": subscription["auth"]},
            },
            data=json.dumps(payload),
            vapid_private_key=(os.environ.get("VAPID_PRIVATE_KEY") or "").strip(),
            vapid_claims=dict(_claims()),
            timeout=SEND_TIMEOUT_SECONDS,
        )
        return None
    except WebPushException as exc:
        status = getattr(getattr(exc, "response", None), "status_code", None)
        if status not in DEAD_STATUSES:
            logger.info("Push rejected (%s): %s", status, str(exc)[:160])
        return status or 0
    except Exception as exc:  # noqa: BLE001 - never let a courtesy message escalate
        logger.info("Push failed: %s", str(exc)[:160])
        return 0


async def send_to_user(db, *, org_id: str, user_id: str,
                       payload: Dict[str, Any]) -> Dict[str, int]:
    """Push to every device this person has switched on."""
    if not push_configured():
        return {"sent": 0, "removed": 0}
    subs = await db.push_subscriptions.find(
        {"org_id": org_id, "user_id": user_id}).to_list(20)
    sent = removed = 0
    for sub in subs:
        status = await asyncio.to_thread(_send_blocking, sub, payload)
        if status is None:
            sent += 1
            continue
        if status in DEAD_STATUSES:
            # The browser threw this subscription away; so do we.
            await db.push_subscriptions.delete_one({"id": sub["id"]})
            removed += 1
    return {"sent": sent, "removed": removed}


async def broadcast(db, *, org_id: str, user_ids: List[str],
                    payload: Dict[str, Any]) -> Dict[str, int]:
    totals = {"sent": 0, "removed": 0}
    for user_id in user_ids:
        result = await send_to_user(db, org_id=org_id, user_id=user_id, payload=payload)
        totals["sent"] += result["sent"]
        totals["removed"] += result["removed"]
    return totals


# ---------------------------------------------------------------------------
# Message bodies
# ---------------------------------------------------------------------------
def approval_payload(*, agent_name: str, what: str, amount_display: Optional[str],
                     decide_url: str) -> Dict[str, Any]:
    body = f"Wants to {what.lower()}" + (f" for {amount_display}" if amount_display else "")
    return {
        "title": f"{agent_name} needs your OK",
        "body": f"{body}. Nothing happens until you decide.",
        "tag": "vexen-approval",
        "url": decide_url,
        "requireInteraction": True,
    }


def test_payload(*, workspace: str, url: str) -> Dict[str, Any]:
    return {
        "title": "Vexen notifications are on",
        "body": f"You will get alerts like this for {workspace}.",
        "tag": "vexen-test",
        "url": url,
    }
