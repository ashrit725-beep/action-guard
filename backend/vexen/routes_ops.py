"""Dashboard, simulator, developer API, public authorization API, org settings, contact."""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Request

from . import llm, mailer
from .catalog import permission_meta
from .db import clean, clean_many, get_db
from .deps import (
    AgentPrincipal,
    Principal,
    approver_principal,
    client_ip,
    current_principal,
    editor_principal,
    public_base_url,
    rate_limit,
)
from .engine import ALLOW, APPROVAL_REQUIRED, BLOCK
from .models import AssistantChatIn, AuthorizeRequest, ContactMessageIn, OrganizationUpdate, SimulatorStart
from .scenarios import SCENARIO_BY_ID, SCENARIOS
from .service import (
    APPROVAL_TTL_MINUTES,
    approval_state,
    credential_status,
    dashboard_payload,
    ensure_scenario_agent,
    evaluate_and_record,
    now_utc,
    uid,
)

router = APIRouter(prefix="/api", tags=["ops"])
# strict_content_type=False: agents authenticate with a header, not a cookie, so there is nothing for a
# browser to be tricked into sending, and a client that forgets "Content-Type: application/json" still works.
public_router = APIRouter(prefix="/api/v1", tags=["public-api"], strict_content_type=False)


def _iso(value: Any) -> Optional[str]:
    """ISO-8601 or nothing — agents parse these, so never guess a value."""
    if not value:
        return None
    return value.isoformat() if hasattr(value, "isoformat") else str(value)


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
@router.get("/dashboard")
async def dashboard(principal: Principal = Depends(current_principal)) -> Dict[str, Any]:
    db = get_db()
    payload = await dashboard_payload(db, org_id=principal.org_id)
    payload["organization"] = clean(principal.org)
    payload["user"] = {"name": principal.user.get("name"), "email": principal.email}
    return payload


# ---------------------------------------------------------------------------
# Organization settings
# ---------------------------------------------------------------------------
@router.get("/organization")
async def get_organization(principal: Principal = Depends(current_principal)) -> Dict[str, Any]:
    db = get_db()
    members = await db.memberships.find({"org_id": principal.org_id}).to_list(200)
    users = await db.users.find({"org_id": principal.org_id}).to_list(200)
    user_by_id = {u["id"]: u for u in users}
    member_rows = []
    for m in members:
        u = user_by_id.get(m["user_id"])
        if not u:
            continue
        member_rows.append({
            "user_id": u["id"], "name": u.get("name"), "email": u.get("email"),
            "role": m.get("role"), "joined_at": m.get("created_at"),
        })
    counts = {
        "agents": await db.agents.count_documents({"org_id": principal.org_id}),
        "policies": await db.policies.count_documents({"org_id": principal.org_id}),
        "audit_events": await db.audit_events.count_documents({"org_id": principal.org_id}),
        "credentials": await db.credentials.count_documents(
            {"org_id": principal.org_id, "status": "active"}),
    }
    return {"organization": clean(principal.org), "members": clean_many(member_rows), "counts": counts}


@router.patch("/organization")
async def update_organization(payload: OrganizationUpdate,
                              principal: Principal = Depends(editor_principal)) -> Dict[str, Any]:
    db = get_db()
    membership = await db.memberships.find_one(
        {"org_id": principal.org_id, "user_id": principal.user_id})
    if (membership or {}).get("role") not in ("owner", "admin"):
        raise HTTPException(status_code=403, detail="Only organization owners can change these settings.")
    updates: Dict[str, Any] = {}
    if payload.name:
        updates["name"] = payload.name.strip()
    if payload.industry is not None:
        updates["industry"] = payload.industry.strip() or None
    if payload.agent_defaults is not None:
        updates["agent_defaults"] = payload.agent_defaults.model_dump()
    if not updates:
        raise HTTPException(status_code=422, detail="Nothing to update.")
    updates["updated_at"] = now_utc()
    await db.organizations.update_one({"id": principal.org_id}, {"$set": updates})
    org = await db.organizations.find_one({"id": principal.org_id})
    return {"organization": clean(org)}


# ---------------------------------------------------------------------------
# Simulator
# ---------------------------------------------------------------------------
def _scenario_public(scenario: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": scenario["id"],
        "name": scenario["name"],
        "summary": scenario["summary"],
        "expected": scenario["expected"],
        "template_id": scenario["template_id"],
        "agent_name": scenario["agent_name"],
        "featured": scenario.get("featured", False),
        "step_count": len(scenario["steps"]),
        "steps": [
            {"label": s["label"], "detail": s["detail"], "amount": s.get("amount"),
             "resource_id": s.get("resource_id")}
            for s in scenario["steps"]
        ],
    }


@router.get("/simulator/scenarios")
async def list_scenarios(principal: Principal = Depends(current_principal)) -> Dict[str, Any]:
    db = get_db()
    items = []
    for scenario in SCENARIOS:
        agent = await db.agents.find_one({"org_id": principal.org_id,
                                          "template_id": scenario["template_id"]})
        row = _scenario_public(scenario)
        row["agent"] = clean(agent) if agent else None
        items.append(row)
    recent = await (db.simulator_runs.find({"org_id": principal.org_id})
                    .sort("created_at", -1).limit(8).to_list(8))
    return {"items": items, "recent_runs": clean_many(recent), "simulated": True}


def _run_summary(steps: List[Dict[str, Any]]) -> Dict[str, Any]:
    allowed = len([s for s in steps if s.get("decision") == ALLOW])
    escalated = len([s for s in steps if s.get("escalated")])
    blocked = len([s for s in steps if s.get("decision") == BLOCK and not s.get("escalated")])
    prevented = sum(float(s.get("amount") or 0) for s in steps
                    if s.get("decision") in (BLOCK, APPROVAL_REQUIRED) or s.get("escalated"))
    authorized = sum(float(s.get("amount") or 0) for s in steps if s.get("decision") == ALLOW)
    return {
        "allowed": allowed,
        "approval_required": escalated,
        "blocked": blocked,
        "unauthorized_spend": 0.0,
        "spend_prevented": round(prevented, 2),
        "authorized_spend": round(authorized, 2),
        "total_steps": len(steps),
    }


@router.post("/simulator/runs", status_code=201)
async def start_run(payload: SimulatorStart,
                    principal: Principal = Depends(approver_principal)) -> Dict[str, Any]:
    rate_limit(f"sim:{principal.user_id}", limit=60, window_seconds=300)
    db = get_db()
    scenario = SCENARIO_BY_ID.get(payload.scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found.")
    agent = await ensure_scenario_agent(
        db, org_id=principal.org_id, actor=principal.user, scenario=scenario)
    run = {
        "id": uid("sim"),
        "org_id": principal.org_id,
        "scenario_id": scenario["id"],
        "scenario_name": scenario["name"],
        "agent_id": agent["agent_id"],
        "agent_name": agent["name"],
        "status": "running",
        "cursor": 0,
        "paused_approval_id": None,
        "started_by_email": principal.email,
        "created_at": now_utc(),
        "updated_at": now_utc(),
        "simulated": True,
        "steps": [
            {
                "index": i,
                "label": s["label"],
                "detail": s["detail"],
                "resource": s["resource"],
                "action": s["action"],
                "resource_id": s.get("resource_id"),
                "amount": s.get("amount"),
                "status": "pending",
                "decision": None,
                "escalated": False,
                "reason": None,
                "risk": None,
                "policy": None,
                "audit_id": None,
                "approval_id": None,
                "trace": [],
            }
            for i, s in enumerate(scenario["steps"])
        ],
    }
    run["summary"] = _run_summary(run["steps"])
    await db.simulator_runs.insert_one(dict(run))
    return {"run": clean(run), "agent": clean(agent)}


@router.get("/simulator/runs/{run_id}")
async def get_run(run_id: str, principal: Principal = Depends(current_principal)) -> Dict[str, Any]:
    db = get_db()
    run = await db.simulator_runs.find_one({"org_id": principal.org_id, "id": run_id})
    if not run:
        raise HTTPException(status_code=404, detail="Simulation run not found.")
    approval = None
    if run.get("paused_approval_id"):
        approval = clean(await db.approvals.find_one(
            {"org_id": principal.org_id, "id": run["paused_approval_id"]}))
    return {"run": clean(run), "pending_approval": approval}


@router.post("/simulator/runs/{run_id}/step")
async def run_step(run_id: str, request: Request,
                   principal: Principal = Depends(approver_principal)) -> Dict[str, Any]:
    db = get_db()
    run = await db.simulator_runs.find_one({"org_id": principal.org_id, "id": run_id})
    if not run:
        raise HTTPException(status_code=404, detail="Simulation run not found.")
    if run.get("status") == "completed":
        return {"run": clean(run), "finished": True, "pending_approval": None}

    steps: List[Dict[str, Any]] = run["steps"]
    cursor = int(run.get("cursor") or 0)
    if cursor >= len(steps):
        await db.simulator_runs.update_one(
            {"_id": run["_id"]},
            {"$set": {"status": "completed", "summary": _run_summary(steps),
                      "updated_at": now_utc()}})
        run = await db.simulator_runs.find_one({"_id": run["_id"]})
        return {"run": clean(run), "finished": True, "pending_approval": None}

    approval_id: Optional[str] = None
    if run.get("paused_approval_id"):
        approval = await db.approvals.find_one(
            {"org_id": principal.org_id, "id": run["paused_approval_id"]})
        if approval and approval.get("status") == "pending":
            return {"run": clean(run), "finished": False,
                    "waiting_for_approval": True,
                    "pending_approval": clean(approval)}
        approval_id = run["paused_approval_id"]

    agent = await db.agents.find_one(
        {"org_id": principal.org_id, "agent_id": run["agent_id"]})
    if not agent:
        raise HTTPException(status_code=409,
                            detail="The agent for this simulation no longer exists.")

    step = steps[cursor]
    result = await evaluate_and_record(
        db, org=principal.org, agent=agent,
        payload={
            "resource": step["resource"], "action": step["action"],
            "resource_id": step.get("resource_id"), "amount": step.get("amount"),
            "currency": "USD",
        },
        source="simulator", actor_email=principal.email,
        approval_id=approval_id, simulation_run_id=run_id,
        base_url=public_base_url(request),
    )

    step["decision"] = result["decision"]
    step["reason"] = result["reason"]
    step["reason_code"] = result["reason_code"]
    step["risk"] = result["risk"]
    step["risk_score"] = result["risk_score"]
    step["policy"] = result["policy"]
    step["audit_id"] = result["audit_id"]
    step["trace"] = result["trace"]
    step["effective_limit"] = result.get("effective_limit")
    step["evaluated_at"] = result["evaluated_at"]

    paused_approval: Optional[Dict[str, Any]] = None
    if result["decision"] == APPROVAL_REQUIRED and not approval_id:
        step["status"] = APPROVAL_REQUIRED
        step["escalated"] = True
        step["approval_id"] = result.get("approval_id")
        new_cursor = cursor
        paused_id = result.get("approval_id")
        paused_approval = clean(await db.approvals.find_one(
            {"org_id": principal.org_id, "id": paused_id}))
    else:
        step["status"] = result["decision"]
        if approval_id:
            step["escalated"] = True
            step["approval_id"] = approval_id
        new_cursor = cursor + 1
        paused_id = None

    finished = new_cursor >= len(steps)
    summary = _run_summary(steps)
    await db.simulator_runs.update_one(
        {"_id": run["_id"]},
        {"$set": {
            "steps": steps, "cursor": new_cursor, "paused_approval_id": paused_id,
            "status": "completed" if finished else "running",
            "summary": summary, "updated_at": now_utc(),
        }},
    )
    run = await db.simulator_runs.find_one({"_id": run["_id"]})
    return {
        "run": clean(run),
        "step": step,
        "result": result,
        "finished": finished,
        "waiting_for_approval": bool(paused_id),
        "pending_approval": paused_approval,
    }


@router.post("/simulator/runs/{run_id}/reset")
async def reset_run(run_id: str,
                    principal: Principal = Depends(approver_principal)) -> Dict[str, Any]:
    db = get_db()
    run = await db.simulator_runs.find_one({"org_id": principal.org_id, "id": run_id})
    if not run:
        raise HTTPException(status_code=404, detail="Simulation run not found.")
    await db.simulator_runs.update_one({"_id": run["_id"]},
                                      {"$set": {"status": "abandoned", "updated_at": now_utc()}})
    return {"ok": True}


# ---------------------------------------------------------------------------
# Developer API surface
# ---------------------------------------------------------------------------
@router.get("/developers")
async def developer_overview(request: Request,
                             principal: Principal = Depends(current_principal)) -> Dict[str, Any]:
    db = get_db()
    agents = await db.agents.find({"org_id": principal.org_id}).sort("created_at", -1).to_list(300)
    rows = []
    for agent in agents:
        creds = await db.credentials.find(
            {"org_id": principal.org_id, "agent_id": agent["agent_id"]}
        ).sort("created_at", -1).to_list(10)
        rows.append({
            "agent_id": agent["agent_id"],
            "name": agent["name"],
            "status": agent["status"],
            "risk": agent.get("risk"),
            "permission_count": agent.get("permission_count", 0),
            "credentials": clean_many(creds),
            "credential_status": await credential_status(
                db, org_id=principal.org_id, agent_id=agent["agent_id"]),
        })
    api_calls = await db.audit_events.count_documents(
        {"org_id": principal.org_id, "source": "api"})
    base = public_base_url(request)
    return {
        "base_url": base,
        "authorize_endpoint": f"{base}/api/v1/authorize",
        "introspect_endpoint": f"{base}/api/v1/agent",
        "approval_endpoint": f"{base}/api/v1/approvals/{{approval_id}}",
        "approval_valid_minutes": APPROVAL_TTL_MINUTES,
        "approval_single_use": True,
        "agents": rows,
        "api_calls": api_calls,
        "decisions": ["ALLOW", "BLOCK", "APPROVAL_REQUIRED"],
        "auth_header": "X-Vexen-Key",
    }


# ---------------------------------------------------------------------------
# Public authorization API (real: agent API keys)
# ---------------------------------------------------------------------------
@public_router.post("/authorize")
async def authorize_endpoint(payload: AuthorizeRequest, request: Request,
                             principal: Tuple[Dict[str, Any], Dict[str, Any]] = AgentPrincipal
                             ) -> Dict[str, Any]:
    cred, agent = principal
    db = get_db()
    org = await db.organizations.find_one({"id": cred["org_id"]})
    if not org:
        raise HTTPException(status_code=401, detail="Invalid or missing Vexen agent key.")
    result = await evaluate_and_record(
        db, org=org, agent=agent,
        payload={
            "resource": payload.resource, "action": payload.action,
            "resource_id": payload.resource_id, "amount": payload.amount,
            "currency": payload.currency or "USD",
        },
        source="api", actor_email=None, approval_id=payload.approval_id,
        # This is the real enforcement point, so this is where a human's
        # one-time approval actually gets spent.
        consume_approval=True,
        base_url=public_base_url(request),
    )
    return {
        "decision": result["decision"],
        "reason": result["reason"],
        "reason_code": result["reason_code"],
        "policy": result["policy"],
        "risk": result["risk"],
        "risk_score": result["risk_score"],
        "expiration": result["expiration"],
        "audit_id": result["audit_id"],
        "request_id": result["request_id"],
        "permission": result["permission_key"],
        "approval_id": result.get("approval_id"),
        "approval_status": result.get("approval_status"),
        "approval_expires_at": result.get("approval_expires_at"),
        "approval_check_url": (
            f"{public_base_url(request)}/api/v1/approvals/{result['approval_id']}"
            if result.get("approval_id") else None
        ),
        "effective_limit": result.get("effective_limit"),
        "agent": {"id": agent["agent_id"], "name": agent["name"]},
        "evaluated_at": result["evaluated_at"],
        "evaluation": result["trace"],
    }


@public_router.get("/approvals/{approval_id}")
async def approval_status(approval_id: str, request: Request,
                          principal: Tuple[Dict[str, Any], Dict[str, Any]] = AgentPrincipal
                          ) -> Dict[str, Any]:
    """Let a waiting agent ask "has a human decided yet?" without spending it.

    Agents poll this while a person makes up their mind, then repeat the original
    /authorize call with `approval_id` once the answer is yes. Reading the status
    never authorises anything on its own.
    """
    cred, agent = principal
    db = get_db()
    record = await db.approvals.find_one(
        {"org_id": cred["org_id"], "id": approval_id, "agent_id": agent["agent_id"]})
    if not record:
        raise HTTPException(status_code=404, detail="No such approval request for this agent.")
    state = approval_state(record)
    return {
        "approval_id": record["id"],
        "state": state,
        "status": record.get("status"),
        "may_proceed": state == "approved",
        "permission": record.get("permission_key"),
        "resource_id": record.get("resource_id"),
        "amount": record.get("amount"),
        "currency": record.get("currency") or "USD",
        "reason": record.get("reason"),
        "requested_at": _iso(record.get("created_at")),
        "decided_at": _iso(record.get("decided_at")),
        "decided_by": record.get("decided_by_email"),
        "note": record.get("note"),
        "expires_at": _iso(record.get("expires_at")),
        "used_at": _iso(record.get("consumed_at")),
        "valid_for_minutes": APPROVAL_TTL_MINUTES,
        "single_use": True,
        "retry_with": {
            "url": f"{public_base_url(request)}/api/v1/authorize",
            "approval_id": record["id"],
        } if state == "approved" else None,
        "poll_after_seconds": 3 if state == "pending" else None,
    }


@public_router.get("/agent")
async def agent_introspect(principal: Tuple[Dict[str, Any], Dict[str, Any]] = AgentPrincipal
                           ) -> Dict[str, Any]:
    cred, agent = principal
    db = get_db()
    perms = await db.permissions.find(
        {"org_id": cred["org_id"], "agent_id": agent["agent_id"]}).sort("key", 1).to_list(500)
    return {
        "agent": {
            "agent_id": agent["agent_id"],
            "name": agent["name"],
            "status": agent["status"],
            "risk": agent.get("risk"),
            "created_at": (agent.get("created_at") or now_utc()).isoformat(),
        },
        "key": {"prefix": cred.get("prefix"), "name": cred.get("name")},
        "permissions": [
            {
                "permission": p["key"],
                "decision": p["decision"],
                "constraints": p.get("constraints") or {},
                "expires_at": p["expires_at"].isoformat() if p.get("expires_at") else None,
                "sensitive": permission_meta(p["key"])["sensitive"],
            }
            for p in perms
        ],
    }


# ---------------------------------------------------------------------------
# Public contact form
# ---------------------------------------------------------------------------
@router.post("/public/contact", status_code=201)
async def submit_contact(payload: ContactMessageIn, request: Request) -> Dict[str, Any]:
    rate_limit(f"contact-ip:{client_ip(request)}", limit=60, window_seconds=600)
    rate_limit(f"contact-email:{payload.email.lower()}", limit=3, window_seconds=600)
    db = get_db()
    reference = "VEX-MSG-" + uid("")[1:9].upper()
    await db.contact_messages.insert_one({
        "id": uid("msg"),
        "reference": reference,
        "name": payload.name.strip()[:80],
        "email": payload.email.lower().strip(),
        "company": (payload.company or "").strip()[:100] or None,
        "topic": (payload.topic or "general")[:40],
        "message": payload.message.strip()[:4000],
        "ip": client_ip(request),
        "user_agent": (request.headers.get("user-agent") or "")[:220],
        "created_at": now_utc(),
        "status": "new",
    })
    # Tell whoever runs this site. Optional (CONTACT_NOTIFY_EMAIL, and email must be set up);
    # the message is saved either way, and a mail problem can never fail the visitor's request.
    notify = (os.environ.get("CONTACT_NOTIFY_EMAIL") or "").strip()
    try:
        # A global cap, so a flood of form posts can neither fill the outbox ahead of approval
        # alerts nor use up the mailbox's daily allowance. The message is still saved above.
        rate_limit("contact-notify", limit=20, window_seconds=3600)
    except HTTPException:
        notify = ""
    if notify:
        subject, text, html = mailer.contact_message_email(
            reference=reference, name=payload.name.strip(), email=payload.email.lower().strip(),
            company=(payload.company or "").strip() or None, topic=payload.topic or "general",
            message=payload.message.strip())
        await mailer.queue_email(db, to=notify, subject=subject, text=text, html=html,
                                 kind="contact_message", dedupe_key=f"contact:{reference}")
    return {
        "ok": True,
        "reference": reference,
        "message": "Thanks - your message reached the Vexen founders. "
                   "Keep this reference for follow-up.",
    }


@router.get("/assistant/status")
async def assistant_status(principal: Principal = Depends(current_principal)) -> Dict[str, Any]:
    """Lets the app hide the helper when the server has no working AI key."""
    return {"available": llm.available()}


@router.post("/assistant/chat")
async def assistant_chat(payload: AssistantChatIn,
                         principal: Principal = Depends(current_principal)) -> Dict[str, Any]:
    """Answer a question about this workspace in plain language."""
    from . import assistant

    rate_limit(f"assistant:{principal.user_id}", limit=40, window_seconds=300)
    db = get_db()
    history = [{"role": t.role, "content": t.content} for t in payload.messages]

    snapshot = await assistant.workspace_snapshot(
        db, principal.org_id, principal.user.get("name") or "")
    system = (
        assistant.SYSTEM_PROMPT
        + "\n\nThis person's workspace right now:\n" + snapshot
        + (f"\n\nThey are currently looking at: {payload.page}" if payload.page else "")
    )
    cleaned = assistant._clean_history(history)
    if not cleaned:
        raise HTTPException(status_code=422, detail="Ask a question first.")

    try:
        reply, model = await llm.run_blocking(assistant._anthropic_reply, system, cleaned,
                                              owner=principal.user_id)
    except llm.ProviderBusy as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except assistant.AssistantError as exc:
        raise HTTPException(
            status_code=503,
            detail="The helper is unavailable right now. The Guide page covers the basics.",
        ) from exc
    return {
        "reply": reply,
        "model": model,
        "suggestions": assistant.follow_ups(snapshot),
    }
