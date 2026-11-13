"""Policies, approvals, audit log and security center routes."""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from . import ai, llm
from .catalog import PERMISSION_CATALOG, POLICY_EFFECTS
from .db import clean, clean_many, get_db
from .deps import (
    Principal,
    approver_principal,
    current_principal,
    editor_principal,
    public_base_url,
    rate_limit,
)
from .engine import ALLOW, APPROVAL_REQUIRED, BLOCK
from .models import (
    ApprovalDecision,
    PolicyCreate,
    PolicyGenerateRequest,
    PolicyPatch,
    PolicyTestRequest,
)
from .service import (
    decide_approval as svc_decide_approval,
    evaluate_and_record,
    integrity_hash,
    now_utc,
    security_findings,
    slugify,
    uid,
)

router = APIRouter(prefix="/api", tags=["governance"])

EFFECT_COPY = {
    "DENY": "Never allow this. The action is blocked even if an agent has the permission.",
    "REQUIRE_APPROVAL": "Escalate to a human. Nothing happens until someone approves.",
    "LIMIT": "Cap the amount. Anything above the cap needs approval.",
    "MAX_TTL": "Force temporary access to expire within a maximum lifetime.",
    "REQUIRE_SCOPE": "Refuse the action unless the grant names the exact resources allowed.",
}


# ---------------------------------------------------------------------------
# Policies
# ---------------------------------------------------------------------------
@router.get("/policies")
async def list_policies(principal: Principal = Depends(current_principal)) -> Dict[str, Any]:
    db = get_db()
    rows = await db.policies.find({"org_id": principal.org_id}).sort("priority", 1).to_list(300)
    items = []
    for row in rows:
        item = clean(row)
        item["effect_copy"] = EFFECT_COPY.get(row.get("effect", ""), "")
        items.append(item)
    return {
        "items": items,
        "total": len(items),
        "effects": [{"value": e, "label": e.replace("_", " ").title(), "copy": EFFECT_COPY[e]}
                    for e in POLICY_EFFECTS],
        "permission_keys": [p["key"] for p in PERMISSION_CATALOG],
        "generator_available": ai.generator_available(),
    }


@router.post("/policies", status_code=201)
async def create_policy(payload: PolicyCreate,
                        principal: Principal = Depends(editor_principal)) -> Dict[str, Any]:
    db = get_db()
    if payload.effect == "LIMIT" and payload.params.max_amount is None:
        raise HTTPException(status_code=422, detail="A Limit policy needs a maximum amount.")
    if payload.effect == "MAX_TTL" and payload.params.max_ttl_minutes is None:
        raise HTTPException(status_code=422, detail="A Max TTL policy needs a lifetime in minutes.")
    count = await db.policies.count_documents({"org_id": principal.org_id})
    if count >= 200:
        raise HTTPException(status_code=409, detail="Policy limit reached for this organization.")

    base_slug = slugify(payload.name)[:60] or "policy"
    slug = base_slug
    n = 1
    while await db.policies.find_one({"org_id": principal.org_id, "slug": slug}):
        n += 1
        slug = f"{base_slug}-{n}"

    doc = {
        "id": uid("pol"),
        "org_id": principal.org_id,
        "slug": slug,
        "name": payload.name.strip(),
        "description": (payload.description or "").strip() or None,
        "effect": payload.effect,
        "priority": payload.priority,
        "match": payload.match.model_dump(exclude_none=True),
        "params": payload.params.model_dump(exclude_none=True),
        "system": False,
        "enabled": payload.enabled,
        "source": payload.source or "manual",
        "rationale": payload.rationale,
        "created_at": now_utc(),
        "created_by_email": principal.email,
    }
    await db.policies.insert_one(dict(doc))
    return clean(doc)


@router.patch("/policies/{policy_id}")
async def patch_policy(policy_id: str, payload: PolicyPatch,
                       principal: Principal = Depends(editor_principal)) -> Dict[str, Any]:
    db = get_db()
    existing = await db.policies.find_one({"org_id": principal.org_id, "id": policy_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Policy not found.")

    updates: Dict[str, Any] = {}
    data = payload.model_dump(exclude_none=True)
    if existing.get("system"):
        # Baseline protections may be toggled but not rewritten.
        if set(data.keys()) - {"enabled"}:
            raise HTTPException(
                status_code=403,
                detail="Vexen baseline policies cannot be edited. You may disable them instead.",
            )
    for field in ("name", "description", "effect", "priority", "enabled"):
        if field in data:
            updates[field] = data[field]
    if payload.match is not None:
        updates["match"] = payload.match.model_dump(exclude_none=True)
    if payload.params is not None:
        updates["params"] = payload.params.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=422, detail="Nothing to update.")
    updates["updated_at"] = now_utc()
    updates["updated_by_email"] = principal.email
    await db.policies.update_one({"org_id": principal.org_id, "id": policy_id}, {"$set": updates})
    row = await db.policies.find_one({"org_id": principal.org_id, "id": policy_id})
    return clean(row)


@router.delete("/policies/{policy_id}")
async def delete_policy(policy_id: str,
                        principal: Principal = Depends(editor_principal)) -> Dict[str, Any]:
    db = get_db()
    existing = await db.policies.find_one({"org_id": principal.org_id, "id": policy_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Policy not found.")
    if existing.get("system"):
        raise HTTPException(status_code=403,
                            detail="Baseline policies cannot be deleted. Disable it instead.")
    await db.policies.delete_one({"org_id": principal.org_id, "id": policy_id})
    return {"ok": True}


@router.post("/policies/generate")
async def generate_policy(payload: PolicyGenerateRequest,
                          principal: Principal = Depends(editor_principal)) -> Dict[str, Any]:
    rate_limit(f"policy-gen:{principal.user_id}", limit=20, window_seconds=300)
    if not ai.generator_available():
        raise HTTPException(
            status_code=503,
            detail="The rule writer is switched off on this server right now. "
                   "You can still add rules by hand.",
        )
    try:
        rule = await _run_generator(payload.prompt, principal.user_id)
    except llm.ProviderBusy as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except ai.PolicyGeneratorUnavailable as exc:
        # The generator could not run at all: our side, not the request.
        raise HTTPException(status_code=503, detail=str(exc))
    except ai.PolicyGenerationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    rule["effect_copy"] = EFFECT_COPY.get(rule["effect"], "")
    return {"rule": rule}


async def _run_generator(prompt: str, owner: str = "") -> Dict[str, Any]:
    return await llm.run_blocking(ai.generate_policy, prompt, owner=owner)


@router.post("/policies/test")
async def test_policies(payload: PolicyTestRequest,
                        principal: Principal = Depends(current_principal)) -> Dict[str, Any]:
    """Dry-run a request through the live engine WITHOUT writing audit history."""
    from .engine import authorize

    db = get_db()
    agent = await db.agents.find_one({"org_id": principal.org_id, "agent_id": payload.agent_id})
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found.")
    permissions = await db.permissions.find(
        {"org_id": principal.org_id, "agent_id": payload.agent_id}).to_list(500)
    policies = await db.policies.find(
        {"org_id": principal.org_id, "enabled": True}).sort("priority", 1).to_list(300)
    agent_for_engine = dict(agent)
    agent_for_engine["credential_status"] = "active"
    result = authorize(
        agent_for_engine, permissions, policies,
        {"resource": payload.resource, "action": payload.action,
         "resource_id": payload.resource_id, "amount": payload.amount},
        authenticated=True,
    )
    result["dry_run"] = True
    result["audit_id"] = None
    return {"result": result}


# ---------------------------------------------------------------------------
# Approvals
# ---------------------------------------------------------------------------
@router.get("/approvals")
async def list_approvals(principal: Principal = Depends(current_principal),
                         status: str = Query(default="pending", max_length=20),
                         page: int = Query(default=1, ge=1, le=10000),
                         limit: int = Query(default=50, ge=1, le=200)) -> Dict[str, Any]:
    db = get_db()
    query: Dict[str, Any] = {"org_id": principal.org_id}
    if status and status != "all":
        query["status"] = status
    total = await db.approvals.count_documents(query)
    rows = await (db.approvals.find(query).sort("created_at", -1)
                  .skip((page - 1) * limit).limit(limit).to_list(limit))
    counts = {
        "pending": await db.approvals.count_documents({"org_id": principal.org_id, "status": "pending"}),
        "approved": await db.approvals.count_documents({"org_id": principal.org_id, "status": "approved"}),
        "denied": await db.approvals.count_documents({"org_id": principal.org_id, "status": "denied"}),
    }
    return {"items": clean_many(rows), "total": total, "page": page, "limit": limit, "counts": counts}


@router.post("/approvals/{approval_id}/decision")
async def approve_or_deny(approval_id: str, payload: ApprovalDecision, request: Request,
                          principal: Principal = Depends(approver_principal)) -> Dict[str, Any]:
    db = get_db()
    approval = await db.approvals.find_one({"org_id": principal.org_id, "id": approval_id})
    if not approval:
        raise HTTPException(status_code=404, detail="Approval request not found.")
    if approval.get("status") != "pending":
        raise HTTPException(status_code=409,
                            detail=f"This request was already {approval.get('status')}.")
    updated = await svc_decide_approval(
        db, org=principal.org, approval_id=approval_id,
        decision=payload.decision, actor=principal.user, note=payload.note,
    )
    if not updated:
        raise HTTPException(status_code=409, detail="This request was already decided.")

    # Re-run the original request through the engine so the recorded outcome is real.
    # Simulator runs re-execute the step themselves, so we don't double-record here.
    agent = await db.agents.find_one({"org_id": principal.org_id, "agent_id": updated["agent_id"]})
    outcome = None
    if agent and not updated.get("simulation_run_id"):
        outcome = await evaluate_and_record(
            db, org=principal.org, agent=agent,
            payload={
                "resource": updated.get("resource"),
                "action": updated.get("action"),
                "resource_id": updated.get("resource_id"),
                "amount": updated.get("amount"),
                "currency": updated.get("currency"),
            },
            source=updated.get("source") or "console",
            actor_email=principal.email,
            approval_id=approval_id,
            simulation_run_id=updated.get("simulation_run_id"),
            base_url=public_base_url(request),
        )
    return {"approval": clean(updated), "outcome": outcome}


# ---------------------------------------------------------------------------
# Audit log
# ---------------------------------------------------------------------------
FILTERS = {
    "all": {},
    "allowed": {"decision": ALLOW},
    "blocked": {"decision": BLOCK},
    "approval": {"decision": APPROVAL_REQUIRED},
    "high_risk": {"risk": {"$in": ["HIGH", "CRITICAL"]}},
    "simulated": {"simulated": True},
    "api": {"source": "api"},
}


@router.get("/audit")
async def list_audit(principal: Principal = Depends(current_principal),
                     filter: str = Query(default="all", max_length=20),
                     search: Optional[str] = Query(default=None, max_length=100),
                     agent_id: Optional[str] = Query(default=None, max_length=40),
                     page: int = Query(default=1, ge=1, le=10000),
                     limit: int = Query(default=50, ge=1, le=200)) -> Dict[str, Any]:
    db = get_db()
    query: Dict[str, Any] = {"org_id": principal.org_id}
    query.update(FILTERS.get(filter, {}))
    if agent_id:
        query["agent_id"] = agent_id
    if search:
        safe = re.escape(search.strip()[:80])
        query["$or"] = [
            {"agent_name": {"$regex": safe, "$options": "i"}},
            {"agent_id": {"$regex": safe, "$options": "i"}},
            {"permission_key": {"$regex": safe, "$options": "i"}},
            {"resource_id": {"$regex": safe, "$options": "i"}},
            {"reason": {"$regex": safe, "$options": "i"}},
            {"audit_id": {"$regex": safe, "$options": "i"}},
            {"policy": {"$regex": safe, "$options": "i"}},
        ]
    total = await db.audit_events.count_documents(query)
    rows = await (db.audit_events.find(query).sort("created_at", -1)
                  .skip((page - 1) * limit).limit(limit).to_list(limit))
    base = {"org_id": principal.org_id}
    counts = {
        "all": await db.audit_events.count_documents(base),
        "allowed": await db.audit_events.count_documents({**base, "decision": ALLOW}),
        "blocked": await db.audit_events.count_documents({**base, "decision": BLOCK}),
        "approval": await db.audit_events.count_documents({**base, "decision": APPROVAL_REQUIRED}),
        "high_risk": await db.audit_events.count_documents(
            {**base, "risk": {"$in": ["HIGH", "CRITICAL"]}}),
    }
    return {"items": clean_many(rows), "total": total, "page": page, "limit": limit, "counts": counts}


@router.get("/audit/verify")
async def verify_audit(principal: Principal = Depends(current_principal),
                       limit: int = Query(default=500, ge=1, le=5000)) -> Dict[str, Any]:
    """Recompute the tamper-evident hash of recent audit events."""
    db = get_db()
    rows = await (db.audit_events.find({"org_id": principal.org_id})
                  .sort("created_at", -1).limit(limit).to_list(limit))
    tampered: List[str] = []
    for row in rows:
        expected = integrity_hash(row)
        if row.get("integrity_hash") and row["integrity_hash"] != expected:
            tampered.append(row["audit_id"])
    return {
        "checked": len(rows),
        "verified": len(rows) - len(tampered),
        "tampered": tampered,
        "intact": not tampered,
    }


@router.get("/audit/{audit_id}")
async def get_audit_event(audit_id: str,
                          principal: Principal = Depends(current_principal)) -> Dict[str, Any]:
    db = get_db()
    row = await db.audit_events.find_one({"org_id": principal.org_id, "audit_id": audit_id})
    if not row:
        raise HTTPException(status_code=404, detail="Audit event not found.")
    event = clean(row)
    event["integrity_verified"] = (not row.get("integrity_hash")) or \
        row["integrity_hash"] == integrity_hash(row)
    approval = None
    if row.get("approval_id"):
        approval = clean(await db.approvals.find_one(
            {"org_id": principal.org_id, "id": row["approval_id"]}))
    return {"event": event, "approval": approval}


# ---------------------------------------------------------------------------
# Security center
# ---------------------------------------------------------------------------
@router.get("/security")
async def security_center(principal: Principal = Depends(current_principal)) -> Dict[str, Any]:
    db = get_db()
    org_id = principal.org_id
    findings = await security_findings(db, org_id=org_id)

    by_severity = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    by_category: Dict[str, int] = {}
    for f in findings:
        by_severity[f["severity"]] = by_severity.get(f["severity"], 0) + 1
        by_category[f["category"]] = by_category.get(f["category"], 0) + 1

    posture = "Protected"
    if by_severity["critical"]:
        posture = "At risk"
    elif by_severity["high"]:
        posture = "Needs attention"

    high_risk_agents = await db.agents.find(
        {"org_id": org_id, "risk": {"$in": ["HIGH", "CRITICAL"]}}
    ).sort("risk_score", -1).to_list(50)

    events = await db.security_events.find({"org_id": org_id}).sort("created_at", -1).to_list(40)
    blocked_recent = await db.audit_events.find(
        {"org_id": org_id, "decision": BLOCK, "event_type": "authorization"}
    ).sort("created_at", -1).to_list(15)

    total_agents = await db.agents.count_documents({"org_id": org_id})
    score = 100
    score -= by_severity["critical"] * 22
    score -= by_severity["high"] * 10
    score -= by_severity["medium"] * 4
    score -= by_severity["low"] * 1
    score = max(5, min(100, score))

    return {
        "posture": posture,
        "score": score,
        "findings": findings,
        "counts": {"by_severity": by_severity, "by_category": by_category,
                   "total": len(findings), "agents": total_agents},
        "high_risk_agents": clean_many(high_risk_agents),
        "security_events": clean_many(events),
        "recent_blocked": clean_many(blocked_recent),
    }


@router.get("/notifications")
async def list_notifications(principal: Principal = Depends(current_principal),
                             limit: int = Query(default=30, ge=1, le=100)) -> Dict[str, Any]:
    db = get_db()
    rows = await (db.notifications.find({"org_id": principal.org_id})
                  .sort("created_at", -1).limit(limit).to_list(limit))
    unread = await db.notifications.count_documents({"org_id": principal.org_id, "read": False})
    return {"items": clean_many(rows), "unread": unread}


@router.post("/notifications/read")
async def mark_notifications_read(principal: Principal = Depends(current_principal)) -> Dict[str, Any]:
    db = get_db()
    result = await db.notifications.update_many(
        {"org_id": principal.org_id, "read": False}, {"$set": {"read": True}})
    return {"ok": True, "updated": result.modified_count}
