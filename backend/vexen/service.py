"""Vexen application services: seeding, agents, authorization persistence, insights."""
from __future__ import annotations

import hashlib
import json
import re
import uuid
from datetime import datetime, timedelta, timezone
from fnmatch import fnmatch
from typing import Any, Dict, List, Optional, Tuple

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo.errors import DuplicateKeyError

from .catalog import (
    AGENT_TEMPLATES,
    GRANT_ALLOW,
    GRANT_BLOCK,
    SENSITIVE_PERMISSIONS,
    STARTER_TEMPLATE_IDS,
    SYSTEM_POLICIES,
    permission_meta,
)
from .engine import (
    ALLOW,
    APPROVAL_REQUIRED,
    BLOCK,
    authorize,
    compute_agent_risk,
    new_agent_id,
)
from .library import resolve_template
from .serverless import in_background

UTC = timezone.utc

# Who is allowed to decide an approval, and therefore who is worth emailing.
APPROVER_ROLES = ("owner", "admin", "approver")

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

# How long a human "yes" stays usable. Real approvals are short-lived: the agent
# has to come back and use it promptly, once.
APPROVAL_TTL_MINUTES = 30


def now_utc() -> datetime:
    return datetime.now(UTC)


def uid(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:20]}"


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (value or "").lower()).strip("-")
    return slug or "org"


def day_start(dt: Optional[datetime] = None) -> datetime:
    dt = dt or now_utc()
    return dt.replace(hour=0, minute=0, second=0, microsecond=0)


def as_utc(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    if isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        return dt if dt.tzinfo else dt.replace(tzinfo=UTC)
    return None


# ---------------------------------------------------------------------------
# Organization seeding
# ---------------------------------------------------------------------------
async def create_organization(db: AsyncIOMotorDatabase, *, name: str, owner_id: str) -> Dict[str, Any]:
    """Create a workspace whose slug is unique, even in a rush.

    Two strangers called "John Smith" signing up in the same second used to
    collide on the unique slug index and one of them got a 500. We now let the
    database be the referee: try the readable slug, and on a clash fall back to
    a short random suffix (and finally the workspace id, which cannot clash).
    """
    base = slugify(name)
    org_id = uid("org")
    org = {
        "id": org_id,
        "name": name,
        "slug": base,
        "owner_id": owner_id,
        "industry": None,
        "created_at": now_utc(),
        "agent_defaults": {
            "default_status": "active",
            "default_purchase_limit": 100.0,
            "default_temp_access_minutes": 60,
            "require_approval_for_sensitive": True,
            "block_payment_credentials": True,
        },
    }
    for attempt in range(6):
        if attempt == 1:
            existing = await db.organizations.count_documents({"slug": {"$regex": f"^{re.escape(base)}"}})
            org["slug"] = f"{base}-{existing + 1}"
        elif attempt > 1:
            org["slug"] = f"{base}-{uuid.uuid4().hex[:6]}"
        try:
            await db.organizations.insert_one(dict(org))
            break
        except DuplicateKeyError:
            continue
    else:
        org["slug"] = org_id
        await db.organizations.insert_one(dict(org))
    await seed_system_policies(db, org["id"])
    return org


async def seed_system_policies(db: AsyncIOMotorDatabase, org_id: str) -> None:
    docs = []
    for tpl in SYSTEM_POLICIES:
        docs.append({
            "id": uid("pol"),
            "org_id": org_id,
            "slug": tpl["slug"],
            "name": tpl["name"],
            "description": tpl["description"],
            "effect": tpl["effect"],
            "priority": tpl["priority"],
            "match": tpl["match"],
            "params": tpl["params"],
            "system": True,
            "enabled": True,
            "source": "vexen-baseline",
            "created_at": now_utc(),
            "created_by_email": "Vexen baseline",
        })
    if docs:
        try:
            await db.policies.insert_many(docs, ordered=False)
        except Exception:  # noqa: BLE001 - duplicate slug on retry is harmless
            for doc in docs:
                await db.policies.update_one(
                    {"org_id": org_id, "slug": doc["slug"]},
                    {"$setOnInsert": doc}, upsert=True,
                )


async def seed_starter_agents(db: AsyncIOMotorDatabase, *, org_id: str, actor: Dict[str, Any]) -> None:
    for template_id in STARTER_TEMPLATE_IDS:
        await deploy_agent(db, org_id=org_id, actor=actor, template_id=template_id, issue_key=False)


# ---------------------------------------------------------------------------
# Agents & permissions
# ---------------------------------------------------------------------------
async def deploy_agent(
    db: AsyncIOMotorDatabase,
    *,
    org_id: str,
    actor: Dict[str, Any],
    template_id: Optional[str] = None,
    name: Optional[str] = None,
    description: Optional[str] = None,
    issue_key: bool = False,
) -> Dict[str, Any]:
    template = resolve_template(template_id or "") if template_id else None
    agent_id = new_agent_id()
    agent = {
        "id": agent_id,
        "agent_id": agent_id,
        "org_id": org_id,
        "name": (name or (template["name"] if template else "New Agent"))[:60],
        "description": description or (template["description"] if template else None),
        "template_id": template["id"] if template else None,
        "template_name": template["name"] if template else None,
        "category": template["category"] if template else "Custom",
        "icon": template["icon"] if template else "Bot",
        "status": "active",
        "owner_id": actor.get("id"),
        "owner_email": actor.get("email"),
        "owner_name": actor.get("name"),
        "created_at": now_utc(),
        "updated_at": now_utc(),
        "last_activity_at": None,
        "risk": "LOW",
        "risk_score": 0,
        "risk_factors": [],
        "permission_count": 0,
        "actions_count": 0,
        "blocked_count": 0,
    }
    await db.agents.insert_one(dict(agent))

    if template:
        for grant in template["permissions"]:
            await upsert_permission(
                db, org_id=org_id, agent_id=agent_id, actor=actor,
                key=grant["key"], decision=grant["decision"],
                constraints=dict(grant.get("constraints") or {}),
                expires_in_minutes=grant.get("expires_in_minutes"),
            )
    await refresh_agent_risk(db, org_id=org_id, agent_id=agent_id)
    if issue_key:
        await issue_credential(db, org_id=org_id, agent_id=agent_id, actor=actor, name="Primary key")
    return await db.agents.find_one({"org_id": org_id, "agent_id": agent_id})


async def upsert_permission(
    db: AsyncIOMotorDatabase,
    *,
    org_id: str,
    agent_id: str,
    actor: Dict[str, Any],
    key: str,
    decision: str,
    constraints: Dict[str, Any],
    expires_in_minutes: Optional[int] = None,
) -> Dict[str, Any]:
    constraints = {k: v for k, v in (constraints or {}).items() if v is not None}
    meta = permission_meta(key)

    # A LIMITED grant must carry a limit, otherwise the engine fails closed.
    if decision == "LIMITED":
        if constraints.get("max_amount") is None:
            constraints["max_amount"] = 100.0
        constraints.setdefault("approval_required_above", constraints["max_amount"])
    if decision == "APPROVAL_REQUIRED":
        constraints["require_approval"] = True
    if decision == "BLOCK":
        constraints = {}

    expires_at = None
    if expires_in_minutes:
        minutes = int(expires_in_minutes)
        minutes = await clamp_ttl(db, org_id=org_id, key=key, minutes=minutes)
        expires_at = now_utc() + timedelta(minutes=minutes)
        constraints["temporary"] = True

    doc = {
        "org_id": org_id,
        "agent_id": agent_id,
        "key": key,
        "resource": meta["resource"],
        "action": meta["action"],
        "label": meta["label"],
        "category": meta["category"],
        "sensitive": meta["sensitive"],
        "supports_amount": meta["supports_amount"],
        "decision": decision,
        "constraints": constraints,
        "expires_at": expires_at,
        "updated_at": now_utc(),
        "updated_by_email": actor.get("email"),
    }
    existing = await db.permissions.find_one({"org_id": org_id, "agent_id": agent_id, "key": key})
    if existing:
        await db.permissions.update_one({"_id": existing["_id"]}, {"$set": doc})
    else:
        doc["id"] = uid("perm")
        doc["created_at"] = now_utc()
        await db.permissions.insert_one(dict(doc))
    await refresh_agent_risk(db, org_id=org_id, agent_id=agent_id)
    return await db.permissions.find_one({"org_id": org_id, "agent_id": agent_id, "key": key})


async def clamp_ttl(db: AsyncIOMotorDatabase, *, org_id: str, key: str, minutes: int) -> int:
    """Honour MAX_TTL policies at grant time so we never store an illegal grant."""
    cursor = db.policies.find({"org_id": org_id, "enabled": True, "effect": "MAX_TTL"})
    async for policy in cursor:
        patterns = (policy.get("match") or {}).get("permissions") or ["*"]
        if any(fnmatch(key, p) for p in patterns):
            cap = (policy.get("params") or {}).get("max_ttl_minutes")
            if cap:
                minutes = min(minutes, int(cap))
    return max(1, minutes)


async def refresh_agent_risk(db: AsyncIOMotorDatabase, *, org_id: str, agent_id: str) -> Dict[str, Any]:
    perms = await db.permissions.find({"org_id": org_id, "agent_id": agent_id}).to_list(500)
    since = now_utc() - timedelta(hours=24)
    blocked = await db.audit_events.count_documents({
        "org_id": org_id, "agent_id": agent_id, "decision": BLOCK, "created_at": {"$gte": since},
    })
    risk = compute_agent_risk(perms, recent_blocked=blocked)
    active = len([p for p in perms if p.get("decision") != GRANT_BLOCK])
    await db.agents.update_one(
        {"org_id": org_id, "agent_id": agent_id},
        {"$set": {
            "risk": risk["risk"], "risk_score": risk["risk_score"],
            "risk_factors": risk["risk_factors"],
            "permission_count": active,
            "grant_count": len(perms),
            "blocked_24h": blocked,
            "updated_at": now_utc(),
        }},
    )
    return risk


async def credential_status(db: AsyncIOMotorDatabase, *, org_id: str, agent_id: str) -> str:
    active = await db.credentials.count_documents(
        {"org_id": org_id, "agent_id": agent_id, "status": "active"})
    if active:
        return "active"
    any_cred = await db.credentials.count_documents({"org_id": org_id, "agent_id": agent_id})
    return "revoked" if any_cred else "none"


async def issue_credential(
    db: AsyncIOMotorDatabase, *, org_id: str, agent_id: str, actor: Dict[str, Any],
    name: str = "Primary key", expires_in_days: Optional[int] = None,
) -> Tuple[Dict[str, Any], str]:
    from .security import generate_agent_key

    plaintext, key_hash, prefix = generate_agent_key()
    doc = {
        "id": uid("cred"),
        "org_id": org_id,
        "agent_id": agent_id,
        "name": name[:60],
        "key_hash": key_hash,
        "prefix": prefix,
        "status": "active",
        "created_at": now_utc(),
        "created_by_email": actor.get("email"),
        "last_used_at": None,
        "use_count": 0,
        "expires_at": (now_utc() + timedelta(days=int(expires_in_days))) if expires_in_days else None,
    }
    await db.credentials.insert_one(dict(doc))
    await db.agents.update_one({"org_id": org_id, "agent_id": agent_id},
                               {"$set": {"credential_status": "active", "updated_at": now_utc()}})
    return doc, plaintext


# ---------------------------------------------------------------------------
# Authorization + persistence
# ---------------------------------------------------------------------------
def integrity_hash(event: Dict[str, Any]) -> str:
    created = as_utc(event.get("created_at")) or now_utc()
    payload = {
        "audit_id": event.get("audit_id"),
        "org_id": event.get("org_id"),
        "agent_id": event.get("agent_id"),
        "permission_key": event.get("permission_key"),
        "decision": event.get("decision"),
        "reason_code": event.get("reason_code"),
        "amount": None if event.get("amount") is None else round(float(event["amount"]), 2),
        # Mongo stores millisecond precision, so hash at that resolution.
        "created_ms": int(created.timestamp() * 1000),
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()


def _approval_matches(approval: Dict[str, Any], *, permission_key: str,
                      amount: Optional[float], resource_id: Optional[str]) -> bool:
    """Does this approval cover exactly the action being asked about?

    Scope is deliberately strict: same permission, same resource, same amount.
    A human approving "$250 at sku-8842" must never authorise anything else.
    """
    if approval.get("permission_key") != permission_key:
        return False
    if (approval.get("resource_id") or None) != (resource_id or None):
        return False
    a, b = approval.get("amount"), amount
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    return round(float(a), 2) == round(float(b), 2)


def _iso_or_none(value: Any) -> Optional[str]:
    dt = as_utc(value)
    return dt.isoformat() if dt else None


def approval_expired(approval: Dict[str, Any], at: Optional[datetime] = None) -> bool:
    expires_at = as_utc(approval.get("expires_at"))
    if not expires_at:
        return False
    return expires_at <= (at or now_utc())


def approval_state(approval: Dict[str, Any]) -> str:
    """One word an agent (or a person) can act on."""
    status = str(approval.get("status") or "pending")
    if status != "approved":
        return status
    if approval.get("consumed_at"):
        return "used"
    if approval_expired(approval):
        return "expired"
    return "approved"


async def _claim_approval(db: AsyncIOMotorDatabase, *, org_id: str, agent_id: str,
                          approval_id: str, permission_key: str, amount: Optional[float],
                          resource_id: Optional[str], consume: bool) -> Optional[Dict[str, Any]]:
    """Load an approval for reuse — and, for real agent traffic, spend it.

    An approval is single use. The claim is a single atomic update so two agent
    calls racing with the same approval id cannot both be allowed: whoever wins
    the update gets the approval, the other is told to ask a human again.
    """
    record = await db.approvals.find_one({"org_id": org_id, "id": approval_id, "agent_id": agent_id})
    if not record:
        return None
    if not _approval_matches(record, permission_key=permission_key, amount=amount,
                             resource_id=resource_id):
        return None
    if str(record.get("status")) != "approved":
        # pending or denied: hand it back so the engine can report the real state
        return record
    if record.get("consumed_at") or approval_expired(record):
        return None
    if not consume:
        return record
    claimed = await db.approvals.find_one_and_update(
        {"org_id": org_id, "id": approval_id, "agent_id": agent_id,
         "status": "approved", "consumed_at": None},
        {"$set": {"consumed_at": now_utc(), "consumed_by": "agent-api"}},
        return_document=True,
    )
    return claimed or None


async def evaluate_and_record(
    db: AsyncIOMotorDatabase,
    *,
    org: Dict[str, Any],
    agent: Dict[str, Any],
    payload: Dict[str, Any],
    source: str,
    actor_email: Optional[str] = None,
    approval_id: Optional[str] = None,
    simulation_run_id: Optional[str] = None,
    consume_approval: bool = False,
    base_url: Optional[str] = None,
) -> Dict[str, Any]:
    org_id = org["id"]
    agent_id = agent["agent_id"]

    permissions = await db.permissions.find({"org_id": org_id, "agent_id": agent_id}).to_list(500)
    policies = await db.policies.find({"org_id": org_id, "enabled": True}).sort("priority", 1).to_list(300)

    permission_key = f"{payload.get('resource')}.{payload.get('action')}"
    resource_id = payload.get("resource_id")
    amount = payload.get("amount")

    approval = None
    if approval_id:
        # Only the agent's own call through the public API spends the approval.
        # The console re-run that happens the moment a human clicks "Approve"
        # just reads it, so the waiting agent can still claim it once.
        approval = await _claim_approval(
            db, org_id=org_id, agent_id=agent_id, approval_id=approval_id,
            permission_key=permission_key, amount=amount, resource_id=resource_id,
            consume=consume_approval,
        )

    calls_today = await db.audit_events.count_documents({
        "org_id": org_id, "agent_id": agent_id, "permission_key": permission_key,
        "decision": ALLOW, "event_type": "authorization",
        "created_at": {"$gte": day_start()},
    })
    recent_blocked = await db.audit_events.count_documents({
        "org_id": org_id, "agent_id": agent_id, "decision": BLOCK,
        "created_at": {"$gte": now_utc() - timedelta(hours=24)},
    })

    agent_for_engine = dict(agent)
    agent_for_engine["credential_status"] = await credential_status(
        db, org_id=org_id, agent_id=agent_id)

    request = {
        "resource": payload.get("resource"),
        "action": payload.get("action"),
        "resource_id": resource_id,
        "amount": amount,
        "currency": payload.get("currency") or "USD",
        "_calls_today": calls_today,
    }
    result = authorize(
        agent_for_engine, permissions, policies, request,
        authenticated=True, approval=approval, recent_blocked=recent_blocked,
    )

    created = now_utc()
    event = {
        **result,
        "org_id": org_id,
        "agent_name": agent.get("name"),
        "agent_template": agent.get("template_name"),
        "event_type": "authorization",
        "source": source,
        "actor_email": actor_email,
        "simulation_run_id": simulation_run_id,
        "simulated": source == "simulator",
        "created_at": created,
        "sealed": True,
    }
    event["integrity_hash"] = integrity_hash(event)
    await db.audit_events.insert_one(dict(event))

    await db.authorization_requests.insert_one({
        "id": result["request_id"],
        "org_id": org_id,
        "agent_id": agent_id,
        "agent_name": agent.get("name"),
        "permission_key": result["permission_key"],
        "resource_id": resource_id,
        "amount": amount,
        "currency": request["currency"],
        "decision": result["decision"],
        "reason_code": result["reason_code"],
        "audit_id": result["audit_id"],
        "source": source,
        "created_at": created,
    })

    # Book-keeping for the one-time approval that may have been spent above.
    if approval is not None:
        claimed_here = consume_approval and bool(approval.get("consumed_at"))
        if result["decision"] == ALLOW and claimed_here:
            await db.approvals.update_one(
                {"org_id": org_id, "id": approval["id"]},
                {"$set": {"consumed_audit_id": result["audit_id"]}},
            )
        elif claimed_here:
            # The action was not allowed after all (agent paused, policy change,
            # limit dropped...), so hand the approval back instead of burning it.
            await db.approvals.update_one(
                {"org_id": org_id, "id": approval["id"]},
                {"$set": {"consumed_at": None, "consumed_by": None}},
            )
        if result["decision"] == APPROVAL_REQUIRED:
            # Let a waiting agent keep polling the same request id.
            result["approval_id"] = approval["id"]
        result["approval_expires_at"] = _iso_or_none(approval.get("expires_at"))

    if result["decision"] == APPROVAL_REQUIRED and approval is None:
        approval_doc = {
            "id": uid("appr"),
            "org_id": org_id,
            "agent_id": agent_id,
            "agent_name": agent.get("name"),
            "status": "pending",
            "permission_key": result["permission_key"],
            "resource": payload.get("resource"),
            "action": payload.get("action"),
            "resource_id": resource_id,
            "amount": amount,
            "currency": request["currency"],
            "reason": result["reason"],
            "policy": result["policy"],
            "risk": result["risk"],
            "risk_score": result["risk_score"],
            "effective_limit": result.get("effective_limit"),
            "audit_id": result["audit_id"],
            "request_id": result["request_id"],
            "source": source,
            "simulation_run_id": simulation_run_id,
            "created_at": created,
            "decided_at": None,
            "decided_by_email": None,
            "note": None,
        }
        await db.approvals.insert_one(dict(approval_doc))
        result["approval_id"] = approval_doc["id"]
        await add_notification(
            db, org_id=org_id, kind="approval",
            title=f"{agent.get('name')} needs approval",
            body=result["reason"][:220],
            severity="warning",
            link="/app/approvals",
        )
        # Email the people who can actually decide this. Queued, never sent here.
        await queue_approval_alerts(
            db, org=org, approval=approval_doc, agent=agent, base_url=base_url)
        # Nudge their phones too, in the background so the agent is not kept waiting.
        in_background(push_approval_alerts(
            db, org=org, approval=approval_doc, agent=agent, base_url=base_url), name="vexen-push")
        await add_security_event(
            db, org_id=org_id, kind="approval_required", severity="medium",
            title=f"{agent.get('name')} escalated {result['permission_key']}",
            description=result["reason"], agent=agent, audit_id=result["audit_id"],
            amount=amount,
        )
    elif result["decision"] == BLOCK:
        severity = "high" if result["risk"] in ("HIGH", "CRITICAL") else "medium"
        await add_security_event(
            db, org_id=org_id, kind="blocked_action", severity=severity,
            title=f"{agent.get('name')} blocked on {result['permission_key']}",
            description=result["reason"], agent=agent, audit_id=result["audit_id"],
            amount=amount,
        )
        if result["risk"] in ("HIGH", "CRITICAL"):
            await add_notification(
                db, org_id=org_id, kind="blocked",
                title=f"Blocked: {agent.get('name')} \u2192 {result['permission_key']}",
                body=result["reason"][:220], severity="danger", link="/app/audit",
            )

    inc: Dict[str, int] = {"actions_count": 1}
    if result["decision"] == BLOCK:
        inc["blocked_count"] = 1
    await db.agents.update_one(
        {"org_id": org_id, "agent_id": agent_id},
        {"$set": {"last_activity_at": created}, "$inc": inc},
    )
    await refresh_agent_risk(db, org_id=org_id, agent_id=agent_id)
    return result


async def add_notification(db: AsyncIOMotorDatabase, *, org_id: str, kind: str, title: str,
                           body: str, severity: str = "info", link: Optional[str] = None) -> None:
    await db.notifications.insert_one({
        "id": uid("ntf"), "org_id": org_id, "kind": kind, "title": title[:160],
        "body": body[:400], "severity": severity, "link": link,
        "read": False, "created_at": now_utc(),
    })


# ---------------------------------------------------------------------------
# Email alerts (queued only — sending happens in a background worker)
# ---------------------------------------------------------------------------
async def alert_recipients(db: AsyncIOMotorDatabase, *, org_id: str,
                           pref_key: str) -> List[Dict[str, Any]]:
    """People who may decide approvals AND asked to be emailed about them."""
    memberships = await db.memberships.find(
        {"org_id": org_id, "role": {"$in": list(APPROVER_ROLES)}}).to_list(200)
    if not memberships:
        return []
    users = await db.users.find(
        {"id": {"$in": [m["user_id"] for m in memberships]}}).to_list(200)
    role_by_user = {m["user_id"]: m.get("role") for m in memberships}
    wanted = []
    for user in users:
        prefs = user.get("notification_prefs") or {}
        # Missing key means "not yet chosen" — default to on for the important one.
        if prefs.get(pref_key, pref_key == "email_approval_requests") is False:
            continue
        if not (user.get("email") or "").strip():
            continue
        wanted.append({**user, "role": role_by_user.get(user["id"])})
    return wanted


async def queue_approval_alerts(db: AsyncIOMotorDatabase, *, org: Dict[str, Any],
                                approval: Dict[str, Any], agent: Dict[str, Any],
                                base_url: Optional[str] = None) -> int:
    """Email everyone who can decide this, with a link that works on a phone.

    This only writes rows into the outbox, so an agent waiting on
    /api/v1/authorize is never slowed down by a mail server.
    """
    from . import links, mailer

    try:
        recipients = await alert_recipients(
            db, org_id=org["id"], pref_key="email_approval_requests")
        if not recipients:
            return 0
        app_url = mailer.public_app_url(base_url)
        console_url = f"{app_url}/app/approvals"
        label = permission_meta(approval.get("permission_key") or "").get("label") \
            or approval.get("permission_key")
        queued = 0
        for user in recipients:
            # One link per person, so the audit trail can name who decided.
            token = links.approval_token(
                org_id=org["id"], approval_id=approval["id"], user_id=user["id"])
            subject, text, html = mailer.approval_alert_email(
                approval=approval,
                agent_name=agent.get("name") or "An agent",
                workspace=org.get("name") or "your workspace",
                permission_label=label,
                decide_url=f"{app_url}/approve/{token}",
                console_url=console_url,
                recipient_name=user.get("name") or "",
            )
            sent = await mailer.queue_email(
                db, to=user["email"], subject=subject, text=text, html=html,
                kind="approval_alert", org_id=org["id"], user_id=user["id"],
                dedupe_key=f"approval:{approval['id']}:{user['id']}",
            )
            if sent:
                queued += 1
        return queued
    except Exception:  # noqa: BLE001 - an alert must never break a decision
        return 0


async def push_approval_alerts(db: AsyncIOMotorDatabase, *, org: Dict[str, Any],
                               approval: Dict[str, Any], agent: Dict[str, Any],
                               base_url: Optional[str] = None) -> None:
    """Nudge the phones of anyone who turned this device on.

    Fire-and-forget on purpose: a push service being slow must never hold up an
    agent's authorization call, and email remains the reliable channel.
    """
    from . import links, mailer, push

    try:
        if not push.push_configured():
            return
        recipients = await alert_recipients(
            db, org_id=org["id"], pref_key="email_approval_requests")
        if not recipients:
            return
        app_url = mailer.public_app_url(base_url)
        label = permission_meta(approval.get("permission_key") or "").get("label") \
            or approval.get("permission_key") or "do something"
        amount = approval.get("amount")
        amount_display = None
        if amount is not None:
            symbol = {"USD": "$", "EUR": "\u20ac", "GBP": "\u00a3"}.get(
                (approval.get("currency") or "USD").upper(), "")
            amount_display = f"{symbol}{float(amount):,.2f}"
        for user in recipients:
            token = links.approval_token(
                org_id=org["id"], approval_id=approval["id"], user_id=user["id"])
            await push.send_to_user(
                db, org_id=org["id"], user_id=user["id"],
                payload=push.approval_payload(
                    agent_name=agent.get("name") or "An agent",
                    what=str(label),
                    amount_display=amount_display,
                    decide_url=f"{app_url}/approve/{token}",
                ),
            )
    except Exception:  # noqa: BLE001 - a nudge must never break a decision
        return


async def add_security_event(db: AsyncIOMotorDatabase, *, org_id: str, kind: str, severity: str,
                             title: str, description: str, agent: Optional[Dict[str, Any]] = None,
                             audit_id: Optional[str] = None,
                             amount: Optional[float] = None) -> None:
    await db.security_events.insert_one({
        "id": uid("sec"), "org_id": org_id, "kind": kind, "severity": severity,
        "title": title[:180], "description": description[:600],
        "agent_id": (agent or {}).get("agent_id"),
        "agent_name": (agent or {}).get("name"),
        "audit_id": audit_id, "amount": amount, "created_at": now_utc(),
    })


# ---------------------------------------------------------------------------
# Approvals
# ---------------------------------------------------------------------------
async def decide_approval(
    db: AsyncIOMotorDatabase, *, org: Dict[str, Any], approval_id: str,
    decision: str, actor: Dict[str, Any], note: Optional[str] = None,
) -> Dict[str, Any]:
    org_id = org["id"]
    decided = now_utc()
    changes: Dict[str, Any] = {
        "status": decision, "decided_at": decided,
        "decided_by_email": actor.get("email"), "decided_by": actor.get("id"),
        "note": (note or None),
    }
    if decision == "approved":
        # A yes is a short-lived, single-use pass — not a standing permission.
        changes["expires_at"] = decided + timedelta(minutes=APPROVAL_TTL_MINUTES)
        changes["consumed_at"] = None
        changes["consumed_by"] = None
    updated = await db.approvals.find_one_and_update(
        {"org_id": org_id, "id": approval_id, "status": "pending"},
        {"$set": changes},
        return_document=True,
    )
    if not updated:
        return {}

    event = {
        "audit_id": "VEX-EVT-" + uuid.uuid4().hex[:12].upper(),
        "request_id": updated.get("request_id"),
        "org_id": org_id,
        "agent_id": updated["agent_id"],
        "agent_name": updated.get("agent_name"),
        "event_type": "approval",
        "decision": ALLOW if decision == "approved" else BLOCK,
        "reason": f"Human approval {decision} by {actor.get('email')}"
                  + (f" \u2014 \u201c{note}\u201d" if note else ""),
        "reason_code": "APPROVAL_GRANTED" if decision == "approved" else "APPROVAL_DENIED",
        "permission_key": updated.get("permission_key"),
        "resource": updated.get("resource"),
        "action": updated.get("action"),
        "resource_id": updated.get("resource_id"),
        "amount": updated.get("amount"),
        "currency": updated.get("currency") or "USD",
        "risk": updated.get("risk") or "MEDIUM",
        "risk_score": updated.get("risk_score") or 40,
        "policy": updated.get("policy"),
        "approval_id": approval_id,
        "approval_status": decision,
        "source": "console",
        "actor_email": actor.get("email"),
        "simulation_run_id": updated.get("simulation_run_id"),
        "simulated": updated.get("source") == "simulator",
        "trace": [],
        "created_at": now_utc(),
        "sealed": True,
    }
    event["integrity_hash"] = integrity_hash(event)
    await db.audit_events.insert_one(dict(event))
    await add_security_event(
        db, org_id=org_id, kind="approval_decision",
        severity="low" if decision == "approved" else "medium",
        title=f"Approval {decision}: {updated.get('agent_name')} \u2192 {updated.get('permission_key')}",
        description=event["reason"],
        agent={"agent_id": updated["agent_id"], "name": updated.get("agent_name")},
        audit_id=event["audit_id"], amount=updated.get("amount"),
    )
    return updated


# ---------------------------------------------------------------------------
# Dashboard & security center
# ---------------------------------------------------------------------------
async def dashboard_payload(db: AsyncIOMotorDatabase, *, org_id: str) -> Dict[str, Any]:
    from .db import clean_many

    start = day_start()
    base = {"org_id": org_id, "event_type": "authorization"}

    total_agents = await db.agents.count_documents({"org_id": org_id})
    active_agents = await db.agents.count_documents({"org_id": org_id, "status": "active"})
    actions_today = await db.audit_events.count_documents({**base, "created_at": {"$gte": start}})
    allowed_today = await db.audit_events.count_documents(
        {**base, "decision": ALLOW, "created_at": {"$gte": start}})
    blocked_today = await db.audit_events.count_documents(
        {**base, "decision": BLOCK, "created_at": {"$gte": start}})
    approval_today = await db.audit_events.count_documents(
        {**base, "decision": APPROVAL_REQUIRED, "created_at": {"$gte": start}})
    pending_approvals = await db.approvals.count_documents({"org_id": org_id, "status": "pending"})
    total_actions = await db.audit_events.count_documents(base)
    total_blocked = await db.audit_events.count_documents({**base, "decision": BLOCK})

    risk_counts = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}
    async for row in db.agents.aggregate([
        {"$match": {"org_id": org_id}},
        {"$group": {"_id": "$risk", "n": {"$sum": 1}}},
    ]):
        if row["_id"] in risk_counts:
            risk_counts[row["_id"]] = row["n"]

    prevented = 0.0
    async for row in db.audit_events.aggregate([
        {"$match": {"org_id": org_id, "event_type": "authorization",
                    "decision": {"$in": [BLOCK, APPROVAL_REQUIRED]},
                    "amount": {"$gt": 0}}},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}}},
    ]):
        prevented = float(row.get("total") or 0)

    approved_spend = 0.0
    async for row in db.audit_events.aggregate([
        {"$match": {"org_id": org_id, "event_type": "authorization",
                    "decision": ALLOW, "amount": {"$gt": 0}}},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}}},
    ]):
        approved_spend = float(row.get("total") or 0)

    recent = await db.audit_events.find({"org_id": org_id}).sort("created_at", -1).to_list(14)
    events = await db.security_events.find(
        {"org_id": org_id, "severity": {"$in": ["medium", "high", "critical"]}}
    ).sort("created_at", -1).to_list(8)

    findings = await security_findings(db, org_id=org_id)
    critical = [f for f in findings if f["severity"] in ("high", "critical")]
    status = "Protected"
    if critical:
        status = "Needs attention"
    if any(f["severity"] == "critical" for f in findings):
        status = "At risk"

    return {
        "security_status": status,
        "status_detail": (
            (
                "Nothing can act on your behalf yet. Add an agent and Vexen will start checking "
                "everything it tries to do."
                if total_agents == 0
                else "Every single thing your agents try is being checked before it happens."
            )
            if status == "Protected"
            else (
                f"{len(critical)} thing{'' if len(critical) == 1 else 's'} worth looking at on your "
                "Safety check page."
            )
        ),
        "metrics": {
            "active_agents": active_agents,
            "total_agents": total_agents,
            "actions_today": actions_today,
            "allowed_today": allowed_today,
            "blocked_today": blocked_today,
            "approval_today": approval_today,
            "pending_approvals": pending_approvals,
            "total_actions": total_actions,
            "total_blocked": total_blocked,
            "unauthorized_spend_prevented": round(prevented, 2),
            "approved_spend": round(approved_spend, 2),
            "open_findings": len(findings),
        },
        "risk_overview": risk_counts,
        "recent_activity": clean_many(recent),
        "security_events": clean_many(events),
        "findings": findings[:5],
    }


async def security_findings(db: AsyncIOMotorDatabase, *, org_id: str) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    now = now_utc()
    agents = await db.agents.find({"org_id": org_id}).to_list(1000)
    agent_by_id = {a["agent_id"]: a for a in agents}

    def add(**kwargs: Any) -> None:
        findings.append({
            "id": kwargs.get("id") or uuid.uuid4().hex[:10],
            "category": kwargs["category"],
            "severity": kwargs["severity"],
            "title": kwargs["title"],
            "description": kwargs["description"],
            "recommendation": kwargs["recommendation"],
            "agent_id": kwargs.get("agent_id"),
            "agent_name": kwargs.get("agent_name"),
            "count": kwargs.get("count"),
        })

    # High risk agents
    for a in agents:
        if a.get("risk") in ("HIGH", "CRITICAL") and a.get("status") == "active":
            add(id=f"risk-{a['agent_id']}", category="Agents with a lot of reach",
                severity="high" if a["risk"] == "HIGH" else "critical",
                title=f"{a['name']} can do more than most agents need to.",
                description="Risk score "
                            f"{a.get('risk_score', 0)} out of 100. "
                            + "; ".join((a.get("risk_factors") or [])[:3]),
                recommendation="Open this agent and switch off anything it does not really need, add a "
                               "spending cap, or set the sensitive items to Ask me first.",
                agent_id=a["agent_id"], agent_name=a["name"])

    # Blocked actions today
    blocked_today = await db.audit_events.count_documents({
        "org_id": org_id, "event_type": "authorization", "decision": BLOCK,
        "created_at": {"$gte": day_start()},
    })
    if blocked_today:
        add(id="blocked-today", category="Things that were stopped", severity="medium" if blocked_today < 5 else "high",
            title=f"Vexen stopped {blocked_today} thing{'s' if blocked_today != 1 else ''} today.",
            description="These requests were refused. Worth a quick look to check your agents are "
                        "behaving the way you expect.",
            recommendation="Open History, filter to Blocked, and check each one was something you would "
                           "have refused too.",
            count=blocked_today)

    # Expired permissions still attached
    expired = await db.permissions.find({
        "org_id": org_id, "expires_at": {"$ne": None, "$lt": now},
    }).to_list(200)
    if expired:
        names = sorted({agent_by_id.get(p["agent_id"], {}).get("name", "Unknown") for p in expired})
        add(id="expired-perms", category="Access that has run out", severity="medium",
            title=f"{len(expired)} permission{'s' if len(expired) != 1 else ''} expired but still listed.",
            description="This temporary access has already run out, so Vexen is refusing it anyway. It "
                        "is only cluttering your list: " + ", ".join(names[:4]),
            recommendation="Remove them, or grant them again with a fresh expiry if they are still needed.",
            count=len(expired))

    # Excessive / sensitive permissions
    for a in agents:
        perms = await db.permissions.find({"org_id": org_id, "agent_id": a["agent_id"]}).to_list(500)
        active = [p for p in perms if p.get("decision") != GRANT_BLOCK]
        sensitive_allowed = [p for p in active
                             if p["key"] in SENSITIVE_PERMISSIONS
                             and p.get("decision") == GRANT_ALLOW
                             and (p.get("constraints") or {}).get("allow_sensitive")]
        if sensitive_allowed:
            add(id=f"sensitive-{a['agent_id']}", category="Too much freedom", severity="critical",
                title=f"{a['name']} can reach something sensitive without asking you.",
                description="Sensitive things it can touch on its own: "
                            + ", ".join(p["key"] for p in sensitive_allowed),
                recommendation="Open this agent and change these to Ask me first, or Never allowed. Your "
                               "built-in rules still block saved cards and secrets regardless.",
                agent_id=a["agent_id"], agent_name=a["name"])
        elif len(active) >= 12:
            add(id=f"broad-{a['agent_id']}", category="Too much freedom", severity="medium",
                title=f"{a['name']} is allowed to do {len(active)} different things.",
                description="The more one agent can do, the more damage a single mistake or a tricked "
                            "agent could cause.",
                recommendation="Consider splitting this into two agents that each do less, or switch "
                               "off the permissions it never actually uses.",
                agent_id=a["agent_id"], agent_name=a["name"], count=len(active))

        uncapped = [p for p in active
                    if p.get("supports_amount") and p.get("decision") == GRANT_ALLOW
                    and not (p.get("constraints") or {}).get("max_amount")]
        if uncapped:
            add(id=f"uncapped-{a['agent_id']}", category="Money", severity="high",
                title=f"{a['name']} can spend with no limit at all.",
                description="No cap is set on: " + ", ".join(p["key"] for p in uncapped),
                recommendation="Open this agent and set a maximum amount. Anything above it will then "
                               "wait for your approval instead of going through.",
                agent_id=a["agent_id"], agent_name=a["name"])

    # Long-lived credentials
    creds = await db.credentials.find({"org_id": org_id, "status": "active"}).to_list(500)
    for c in creds:
        created = as_utc(c.get("created_at")) or now
        age_days = (now - created).days
        if c.get("expires_at") is None and age_days >= 30:
            a = agent_by_id.get(c["agent_id"], {})
            add(id=f"cred-{c['id']}", category="Keys", severity="medium",
                title=f"{a.get('name', 'An agent')} has a key that never expires.",
                description=f"Key {c.get('prefix')}\u2026 was created {age_days} day(s) ago and has no expiry date.",
                recommendation="Replace it with a new key that expires, so a leaked one stops working "
                               "by itself.",
                agent_id=c["agent_id"], agent_name=a.get("name"))

    # Suspicious activity
    async for row in db.audit_events.aggregate([
        {"$match": {"org_id": org_id, "decision": BLOCK, "event_type": "authorization",
                    "created_at": {"$gte": now - timedelta(hours=24)}}},
        {"$group": {"_id": "$agent_id", "n": {"$sum": 1}}},
        {"$match": {"n": {"$gte": 3}}},
        {"$sort": {"n": -1}}, {"$limit": 10},
    ]):
        a = agent_by_id.get(row["_id"], {})
        add(id=f"suspicious-{row['_id']}", category="Odd behaviour", severity="high",
            title=f"{a.get('name', 'An agent')} was stopped {row['n']} times in the last day.",
            description="Repeatedly asking for things it is not allowed to do usually means the agent is "
                        "set up wrong, broken, or being tricked into overreaching.",
            recommendation="Look at what it has been trying. Either give it the right permissions, or "
                           "switch it off until you know why.",
            agent_id=row["_id"], agent_name=a.get("name"), count=row["n"])

    # Disabled baseline policies
    disabled = await db.policies.find({"org_id": org_id, "system": True, "enabled": False}).to_list(50)
    for p in disabled:
        add(id=f"policy-off-{p['id']}", category="Missing protection", severity="critical",
            title=f"A built-in rule is switched off: {p['name']}",
            description="This is one of Vexen's baseline protections, and right now it is not protecting "
                        "your workspace.",
            recommendation="Switch it back on from the Rules page unless you have a very good reason "
                           "not to.")

    # Agents with no credential cannot be used by real integrations
    for a in agents:
        if a.get("status") == "active":
            active_cred = await db.credentials.count_documents(
                {"org_id": org_id, "agent_id": a["agent_id"], "status": "active"})
            if not active_cred:
                add(id=f"nokey-{a['agent_id']}", category="Keys", severity="low",
                    title=f"{a['name']} is not connected to any real software yet.",
                    description="This is completely fine if you are only exploring. A key is only needed "
                                "when you want your own software to ask Vexen for permission.",
                    recommendation="If you build software, create a key on the For developers page. "
                                   "Otherwise you can safely ignore this.",
                    agent_id=a["agent_id"], agent_name=a["name"])

    order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    findings.sort(key=lambda f: order.get(f["severity"], 9))
    return findings


# ---------------------------------------------------------------------------
# Simulator support
# ---------------------------------------------------------------------------
async def ensure_scenario_agent(
    db: AsyncIOMotorDatabase, *, org_id: str, actor: Dict[str, Any], scenario: Dict[str, Any],
) -> Dict[str, Any]:
    agent = await db.agents.find_one({
        "org_id": org_id, "template_id": scenario["template_id"], "status": "active",
    })
    if agent:
        return agent
    return await deploy_agent(
        db, org_id=org_id, actor=actor, template_id=scenario["template_id"],
        name=scenario.get("agent_name"),
    )


def template_summary(template: Dict[str, Any]) -> Dict[str, Any]:
    counts = {"ALLOW": 0, "LIMITED": 0, "APPROVAL_REQUIRED": 0, "BLOCK": 0}
    sensitive_blocked = 0
    caps: List[float] = []
    for grant in template["permissions"]:
        counts[grant["decision"]] = counts.get(grant["decision"], 0) + 1
        if grant["decision"] == "BLOCK" and grant["key"] in SENSITIVE_PERMISSIONS:
            sensitive_blocked += 1
        cap = (grant.get("constraints") or {}).get("max_amount")
        if cap:
            caps.append(float(cap))
    return {
        **template,
        "permission_count": len(template["permissions"]),
        "decision_counts": counts,
        "sensitive_blocked": sensitive_blocked,
        "spend_cap": min(caps) if caps else None,
        "permissions": [
            {
                **grant,
                "label": permission_meta(grant["key"])["label"],
                "category": permission_meta(grant["key"])["category"],
                "sensitive": permission_meta(grant["key"])["sensitive"],
            }
            for grant in template["permissions"]
        ],
    }


ALL_TEMPLATE_SUMMARIES = [template_summary(t) for t in AGENT_TEMPLATES]
