"""Agent, permission, credential and template-catalog routes."""
from __future__ import annotations

import re
from datetime import timedelta
from fnmatch import fnmatch
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from .catalog import (
    PERMISSION_CATALOG,
    PERMISSION_CATEGORIES,
    permission_meta,
)
from .db import clean, clean_many, get_db
from .deps import Principal, current_principal, editor_principal
from .library import resolve_template, search_templates, template_detail
from .models import AgentCreate, AgentUpdate, CredentialCreate, PermissionPatch, PermissionUpsert
from .service import (
    credential_status,
    deploy_agent,
    issue_credential,
    now_utc,
    refresh_agent_risk,
    upsert_permission,
)

router = APIRouter(prefix="/api", tags=["agents"])

VALID_PERMISSION_KEYS = {p["key"] for p in PERMISSION_CATALOG}


# ---------------------------------------------------------------------------
# Catalog
# ---------------------------------------------------------------------------
@router.get("/catalog/permissions")
async def catalog_permissions() -> Dict[str, Any]:
    return {
        "items": PERMISSION_CATALOG,
        "categories": PERMISSION_CATEGORIES,
        "total": len(PERMISSION_CATALOG),
    }


@router.get("/catalog/templates")
async def catalog_templates(
    search: Optional[str] = Query(default=None, max_length=80),
    category: Optional[str] = Query(default=None, max_length=60),
    industry: Optional[str] = Query(default=None, max_length=40),
    tier: Optional[str] = Query(default=None, max_length=40),
    only_base: bool = Query(default=False),
    page: int = Query(default=1, ge=1, le=2000),
    limit: int = Query(default=24, ge=1, le=60),
) -> Dict[str, Any]:
    """Browse the agent library (10,000+ ready-made agents), paginated."""
    return search_templates(
        search=search,
        category=category,
        industry=industry,
        tier=tier,
        only_base=only_base,
        page=page,
        limit=limit,
    )


@router.get("/catalog/templates/{template_id}")
async def catalog_template_detail(template_id: str) -> Dict[str, Any]:
    detail = template_detail(template_id)
    if not detail:
        raise HTTPException(status_code=404, detail="That agent template does not exist.")
    return detail


# ---------------------------------------------------------------------------
# Agents
# ---------------------------------------------------------------------------
async def _load_agent(db, org_id: str, agent_id: str) -> Dict[str, Any]:
    agent = await db.agents.find_one({"org_id": org_id, "agent_id": agent_id})
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found.")
    return agent


async def _enrich(db, org_id: str, agent: Dict[str, Any]) -> Dict[str, Any]:
    out = clean(agent)
    out["credential_status"] = await credential_status(db, org_id=org_id, agent_id=agent["agent_id"])
    return out


@router.get("/agents")
async def list_agents(
    principal: Principal = Depends(current_principal),
    search: Optional[str] = Query(default=None, max_length=80),
    status: Optional[str] = Query(default=None, max_length=20),
    risk: Optional[str] = Query(default=None, max_length=20),
    page: int = Query(default=1, ge=1, le=10000),
    limit: int = Query(default=50, ge=1, le=200),
) -> Dict[str, Any]:
    db = get_db()
    query: Dict[str, Any] = {"org_id": principal.org_id}
    if status and status != "all":
        query["status"] = status
    if risk and risk != "all":
        query["risk"] = risk.upper()
    if search:
        safe = re.escape(search.strip()[:60])
        query["$or"] = [
            {"name": {"$regex": safe, "$options": "i"}},
            {"agent_id": {"$regex": safe, "$options": "i"}},
            {"category": {"$regex": safe, "$options": "i"}},
        ]
    total = await db.agents.count_documents(query)
    rows = await (db.agents.find(query).sort("created_at", -1)
                  .skip((page - 1) * limit).limit(limit).to_list(limit))
    items = [await _enrich(db, principal.org_id, row) for row in rows]
    return {"items": items, "total": total, "page": page, "limit": limit}


@router.post("/agents", status_code=201)
async def create_agent(payload: AgentCreate,
                       principal: Principal = Depends(editor_principal)) -> Dict[str, Any]:
    db = get_db()
    if payload.template_id and not resolve_template(payload.template_id):
        raise HTTPException(status_code=422, detail="Unknown agent template.")
    count = await db.agents.count_documents({"org_id": principal.org_id})
    if count >= 10000:
        raise HTTPException(
            status_code=409,
            detail="You have reached the 10,000 agent limit for this workspace.",
        )
    agent = await deploy_agent(
        db, org_id=principal.org_id, actor=principal.user,
        template_id=payload.template_id, name=payload.name, description=payload.description,
        issue_key=False,
    )
    return await _enrich(db, principal.org_id, agent)


@router.get("/agents/{agent_id}")
async def get_agent(agent_id: str,
                    principal: Principal = Depends(current_principal)) -> Dict[str, Any]:
    db = get_db()
    agent = await _load_agent(db, principal.org_id, agent_id)
    perms = await db.permissions.find(
        {"org_id": principal.org_id, "agent_id": agent_id}).sort("key", 1).to_list(500)
    creds = await db.credentials.find(
        {"org_id": principal.org_id, "agent_id": agent_id}).sort("created_at", -1).to_list(50)
    activity = await db.audit_events.find(
        {"org_id": principal.org_id, "agent_id": agent_id}).sort("created_at", -1).to_list(25)
    policies = await _policies_for_agent(db, principal.org_id, agent, perms)
    pending = await db.approvals.count_documents(
        {"org_id": principal.org_id, "agent_id": agent_id, "status": "pending"})
    return {
        "agent": await _enrich(db, principal.org_id, agent),
        "permissions": clean_many(perms),
        "credentials": clean_many(creds),
        "activity": clean_many(activity),
        "policies": policies,
        "pending_approvals": pending,
    }


async def _policies_for_agent(db, org_id: str, agent: Dict[str, Any],
                              perms: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    all_policies = await db.policies.find({"org_id": org_id}).sort("priority", 1).to_list(300)
    keys = [p["key"] for p in perms]
    matched: List[Dict[str, Any]] = []
    for policy in all_policies:
        match = policy.get("match") or {}
        agents = match.get("agents") or ["*"]
        if "*" not in agents and agent["agent_id"] not in agents \
                and (agent.get("template_id") or "") not in agents:
            continue
        patterns = match.get("permissions") or ["*"]
        hits = [k for k in keys if any(fnmatch(k, pat) for pat in patterns)]
        if hits or patterns == ["*"]:
            row = clean(policy)
            row["affected_permissions"] = hits[:12]
            matched.append(row)
    return matched


@router.patch("/agents/{agent_id}")
async def update_agent(agent_id: str, payload: AgentUpdate,
                       principal: Principal = Depends(editor_principal)) -> Dict[str, Any]:
    db = get_db()
    await _load_agent(db, principal.org_id, agent_id)
    updates = payload.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=422, detail="Nothing to update.")
    updates["updated_at"] = now_utc()
    await db.agents.update_one({"org_id": principal.org_id, "agent_id": agent_id}, {"$set": updates})
    agent = await _load_agent(db, principal.org_id, agent_id)
    return await _enrich(db, principal.org_id, agent)


@router.delete("/agents/{agent_id}")
async def delete_agent(agent_id: str,
                       principal: Principal = Depends(editor_principal)) -> Dict[str, Any]:
    db = get_db()
    await _load_agent(db, principal.org_id, agent_id)
    org_id = principal.org_id
    await db.permissions.delete_many({"org_id": org_id, "agent_id": agent_id})
    await db.credentials.delete_many({"org_id": org_id, "agent_id": agent_id})
    await db.approvals.update_many(
        {"org_id": org_id, "agent_id": agent_id, "status": "pending"},
        {"$set": {"status": "denied", "decided_at": now_utc(),
                  "decided_by_email": principal.email,
                  "note": "Agent deleted \u2014 request auto-denied."}},
    )
    await db.agents.delete_one({"org_id": org_id, "agent_id": agent_id})
    # Audit history is intentionally retained: it is append-only.
    return {"ok": True, "audit_retained": True}


# ---------------------------------------------------------------------------
# Permissions
# ---------------------------------------------------------------------------
@router.get("/agents/{agent_id}/permissions")
async def list_permissions(agent_id: str,
                           principal: Principal = Depends(current_principal)) -> Dict[str, Any]:
    db = get_db()
    await _load_agent(db, principal.org_id, agent_id)
    rows = await db.permissions.find(
        {"org_id": principal.org_id, "agent_id": agent_id}).sort("key", 1).to_list(500)
    return {"items": clean_many(rows), "total": len(rows)}


@router.post("/agents/{agent_id}/permissions", status_code=201)
async def create_permission(agent_id: str, payload: PermissionUpsert,
                            principal: Principal = Depends(editor_principal)) -> Dict[str, Any]:
    db = get_db()
    await _load_agent(db, principal.org_id, agent_id)
    if payload.key not in VALID_PERMISSION_KEYS:
        raise HTTPException(status_code=422, detail="Unknown permission key.")
    count = await db.permissions.count_documents({"org_id": principal.org_id, "agent_id": agent_id})
    if count >= 120:
        raise HTTPException(status_code=409, detail="Permission limit reached for this agent.")
    row = await upsert_permission(
        db, org_id=principal.org_id, agent_id=agent_id, actor=principal.user,
        key=payload.key, decision=payload.decision,
        constraints=payload.constraints.model_dump(exclude_none=True),
        expires_in_minutes=payload.expires_in_minutes,
    )
    return clean(row)


@router.patch("/agents/{agent_id}/permissions/{permission_id}")
async def patch_permission(agent_id: str, permission_id: str, payload: PermissionPatch,
                           principal: Principal = Depends(editor_principal)) -> Dict[str, Any]:
    db = get_db()
    await _load_agent(db, principal.org_id, agent_id)
    existing = await db.permissions.find_one(
        {"org_id": principal.org_id, "agent_id": agent_id, "id": permission_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Permission grant not found.")

    decision = payload.decision or existing["decision"]
    if payload.constraints is not None:
        constraints = payload.constraints.model_dump(exclude_none=True)
    else:
        constraints = dict(existing.get("constraints") or {})

    expires_in_minutes: Optional[int]
    if payload.expires_in_minutes is None:
        remaining = existing.get("expires_at")
        if remaining:
            delta = remaining - now_utc() if remaining.tzinfo else None
            expires_in_minutes = max(1, int(delta.total_seconds() // 60)) if delta and delta > timedelta(0) else None
        else:
            expires_in_minutes = None
    elif payload.expires_in_minutes == 0:
        expires_in_minutes = None
        constraints.pop("temporary", None)
    else:
        expires_in_minutes = payload.expires_in_minutes

    row = await upsert_permission(
        db, org_id=principal.org_id, agent_id=agent_id, actor=principal.user,
        key=existing["key"], decision=decision, constraints=constraints,
        expires_in_minutes=expires_in_minutes,
    )
    if payload.expires_in_minutes == 0:
        await db.permissions.update_one({"_id": row["_id"]}, {"$set": {"expires_at": None}})
        row = await db.permissions.find_one({"_id": row["_id"]})
    return clean(row)


@router.delete("/agents/{agent_id}/permissions/{permission_id}")
async def delete_permission(agent_id: str, permission_id: str,
                            principal: Principal = Depends(editor_principal)) -> Dict[str, Any]:
    db = get_db()
    await _load_agent(db, principal.org_id, agent_id)
    result = await db.permissions.delete_one(
        {"org_id": principal.org_id, "agent_id": agent_id, "id": permission_id})
    if not result.deleted_count:
        raise HTTPException(status_code=404, detail="Permission grant not found.")
    await refresh_agent_risk(db, org_id=principal.org_id, agent_id=agent_id)
    return {"ok": True}


@router.post("/agents/{agent_id}/apply-template/{template_id}")
async def apply_template(agent_id: str, template_id: str,
                         principal: Principal = Depends(editor_principal)) -> Dict[str, Any]:
    """Overlay a template's recommended grants on an existing agent."""
    db = get_db()
    await _load_agent(db, principal.org_id, agent_id)
    template = resolve_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found.")
    for grant in template["permissions"]:
        await upsert_permission(
            db, org_id=principal.org_id, agent_id=agent_id, actor=principal.user,
            key=grant["key"], decision=grant["decision"],
            constraints=dict(grant.get("constraints") or {}),
            expires_in_minutes=grant.get("expires_in_minutes"),
        )
    await db.agents.update_one(
        {"org_id": principal.org_id, "agent_id": agent_id},
        {"$set": {"template_id": template["id"], "template_name": template["name"],
                  "category": template["category"], "icon": template["icon"],
                  "updated_at": now_utc()}},
    )
    rows = await db.permissions.find(
        {"org_id": principal.org_id, "agent_id": agent_id}).sort("key", 1).to_list(500)
    return {"ok": True, "permissions": clean_many(rows), "applied": len(template["permissions"])}


# ---------------------------------------------------------------------------
# Credentials
# ---------------------------------------------------------------------------
@router.get("/agents/{agent_id}/credentials")
async def list_credentials(agent_id: str,
                           principal: Principal = Depends(current_principal)) -> Dict[str, Any]:
    db = get_db()
    await _load_agent(db, principal.org_id, agent_id)
    rows = await db.credentials.find(
        {"org_id": principal.org_id, "agent_id": agent_id}).sort("created_at", -1).to_list(50)
    return {"items": clean_many(rows), "total": len(rows)}


@router.post("/agents/{agent_id}/credentials", status_code=201)
async def create_credential(agent_id: str, payload: CredentialCreate,
                            principal: Principal = Depends(editor_principal)) -> Dict[str, Any]:
    db = get_db()
    await _load_agent(db, principal.org_id, agent_id)
    active = await db.credentials.count_documents(
        {"org_id": principal.org_id, "agent_id": agent_id, "status": "active"})
    if active >= 5:
        raise HTTPException(status_code=409,
                            detail="This agent already has 5 active keys. Revoke one first.")
    cred, plaintext = await issue_credential(
        db, org_id=principal.org_id, agent_id=agent_id, actor=principal.user,
        name=payload.name, expires_in_days=payload.expires_in_days,
    )
    return {
        "credential": clean(cred),
        "secret": plaintext,
        "warning": "This is the only time the full key is shown. Store it in your agent's secret manager.",
    }


@router.delete("/agents/{agent_id}/credentials/{credential_id}")
async def revoke_credential(agent_id: str, credential_id: str,
                            principal: Principal = Depends(editor_principal)) -> Dict[str, Any]:
    db = get_db()
    await _load_agent(db, principal.org_id, agent_id)
    result = await db.credentials.update_one(
        {"org_id": principal.org_id, "agent_id": agent_id, "id": credential_id, "status": "active"},
        {"$set": {"status": "revoked", "revoked_at": now_utc(),
                  "revoked_by_email": principal.email}},
    )
    if not result.matched_count:
        raise HTTPException(status_code=404, detail="Active credential not found.")
    status_now = await credential_status(db, org_id=principal.org_id, agent_id=agent_id)
    await db.agents.update_one({"org_id": principal.org_id, "agent_id": agent_id},
                               {"$set": {"credential_status": status_now}})
    return {"ok": True, "credential_status": status_now}


@router.get("/agents/{agent_id}/activity")
async def agent_activity(agent_id: str,
                         principal: Principal = Depends(current_principal),
                         page: int = Query(default=1, ge=1, le=10000),
                         limit: int = Query(default=50, ge=1, le=200)) -> Dict[str, Any]:
    db = get_db()
    await _load_agent(db, principal.org_id, agent_id)
    query = {"org_id": principal.org_id, "agent_id": agent_id}
    total = await db.audit_events.count_documents(query)
    rows = await (db.audit_events.find(query).sort("created_at", -1)
                  .skip((page - 1) * limit).limit(limit).to_list(limit))
    return {"items": clean_many(rows), "total": total, "page": page, "limit": limit}
