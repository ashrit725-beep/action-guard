"""
Vexen authorization engine.

Pure, deterministic, side-effect free.  Given an agent, its permission grants,
the organization's policies and a request, it returns a structured decision.

    ALLOW | BLOCK | APPROVAL_REQUIRED

Design rules
------------
* DEFAULT DENY. If the engine cannot positively prove an action is allowed it
  returns BLOCK.
* The engine never trusts anything supplied by the caller other than the raw
  request shape (action / resource / amount).  Approval state, permissions,
  limits and identity are always passed in by the server from its own store.
* Every evaluation produces a full step-by-step trace which becomes the audit
  event, so a decision can always be explained.
"""
from __future__ import annotations

import re
import uuid
from datetime import datetime, timedelta, timezone
from fnmatch import fnmatch
from typing import Any, Dict, List, Optional, Sequence

from .catalog import (
    ALLOW,
    APPROVAL_REQUIRED,
    BLOCK,
    GRANT_ALLOW,
    GRANT_APPROVAL,
    GRANT_BLOCK,
    GRANT_LIMITED,
    RISK_CRITICAL,
    RISK_HIGH,
    RISK_LOW,
    RISK_MEDIUM,
    SENSITIVE_PERMISSIONS,
    permission_meta,
)

MAX_AMOUNT = 1_000_000_000.0
_TOKEN_RE = re.compile(r"^[a-z0-9]+(?:[._-][a-z0-9]+)*$", re.IGNORECASE)
_RESOURCE_ID_RE = re.compile(r"^[\w\-./:@ +#()'\[\]]{1,256}$")

STEP_LABELS = [
    ("identity", "Verify agent identity"),
    ("agent_status", "Verify agent is active"),
    ("authentication", "Verify request is authenticated"),
    ("request_shape", "Validate request"),
    ("permission_lookup", "Check permission exists"),
    ("expiration", "Check permission expiration"),
    ("resource_scope", "Check resource restrictions"),
    ("action_scope", "Check action restrictions"),
    ("numeric_limits", "Check numerical limits"),
    ("sensitive_resource", "Check sensitive-resource restrictions"),
    ("policy_evaluation", "Evaluate organization policies"),
    ("approval_requirement", "Check human approval requirement"),
    ("risk_assessment", "Calculate risk"),
]


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _as_dt(value: Any) -> Optional[datetime]:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str):
        raw = value.replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(raw)
        except ValueError:
            return None
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    return None


def _iso(value: Any) -> Optional[str]:
    dt = _as_dt(value)
    return dt.isoformat() if dt else None


def new_audit_id() -> str:
    return "VEX-EVT-" + uuid.uuid4().hex[:12].upper()


def new_request_id() -> str:
    return "VEX-REQ-" + uuid.uuid4().hex[:12].upper()


def new_agent_id() -> str:
    return "VEX-AGT-" + uuid.uuid4().hex[:8].upper()


class Trace:
    """Collects the evaluation trace shown in the UI and stored in the audit event."""

    def __init__(self) -> None:
        self.steps: List[Dict[str, Any]] = []

    def ok(self, step: str, detail: str) -> None:
        self.steps.append({"step": step, "label": _label(step), "status": "pass", "detail": detail})

    def info(self, step: str, detail: str) -> None:
        self.steps.append({"step": step, "label": _label(step), "status": "info", "detail": detail})

    def fail(self, step: str, detail: str) -> None:
        self.steps.append({"step": step, "label": _label(step), "status": "fail", "detail": detail})

    def escalate(self, step: str, detail: str) -> None:
        self.steps.append({"step": step, "label": _label(step), "status": "escalate", "detail": detail})

    def skip(self, step: str, detail: str) -> None:
        self.steps.append({"step": step, "label": _label(step), "status": "skip", "detail": detail})


_LABELS = dict(STEP_LABELS)


def _label(step: str) -> str:
    return _LABELS.get(step, step.replace("_", " ").title())


# ---------------------------------------------------------------------------
# Permission matching
# ---------------------------------------------------------------------------
def find_permission(permissions: Sequence[Dict[str, Any]], key: str) -> Optional[Dict[str, Any]]:
    """Exact match wins; then the most specific wildcard match."""
    exact = [p for p in permissions if p.get("key") == key]
    if exact:
        # An explicit BLOCK always beats an explicit ALLOW on the same key.
        for p in exact:
            if p.get("decision") == GRANT_BLOCK:
                return p
        return exact[0]
    wildcard = [p for p in permissions if "*" in str(p.get("key", "")) and fnmatch(key, p["key"])]
    if not wildcard:
        return None
    wildcard.sort(key=lambda p: len(str(p.get("key", ""))), reverse=True)
    for p in wildcard:
        if p.get("decision") == GRANT_BLOCK:
            return p
    return wildcard[0]


def _matches_any(value: Optional[str], patterns: Sequence[str]) -> bool:
    if not patterns:
        return False
    target = value or ""
    return any(fnmatch(target, str(pattern)) for pattern in patterns)


def policy_applies(policy: Dict[str, Any], *, agent: Dict[str, Any], permission_key: str,
                   resource_id: Optional[str], amount: Optional[float], sensitive: bool) -> bool:
    if not policy.get("enabled", True):
        return False
    match = policy.get("match") or {}
    perms = match.get("permissions") or ["*"]
    if not _matches_any(permission_key, perms):
        return False
    agents = match.get("agents") or ["*"]
    if "*" not in agents:
        identifiers = {
            str(agent.get("agent_id") or ""),
            str(agent.get("id") or ""),
            str(agent.get("template_id") or ""),
        }
        if not (identifiers & set(str(a) for a in agents)):
            return False
    resources = match.get("resources") or ["*"]
    if resources != ["*"] and not _matches_any(resource_id, resources):
        return False
    if match.get("sensitive_only") and not sensitive:
        return False
    amount_gt = match.get("amount_gt")
    if amount_gt is not None:
        if amount is None or float(amount) <= float(amount_gt):
            return False
    return True


# ---------------------------------------------------------------------------
# Risk
# ---------------------------------------------------------------------------
def risk_band(score: int) -> str:
    if score >= 75:
        return RISK_CRITICAL
    if score >= 50:
        return RISK_HIGH
    if score >= 25:
        return RISK_MEDIUM
    return RISK_LOW


def calculate_risk(*, permission_key: str, decision: str, amount: Optional[float],
                   sensitive: bool, recent_blocked: int = 0) -> Dict[str, Any]:
    meta = permission_meta(permission_key)
    factors: List[str] = []
    score = int(meta["risk_weight"])
    factors.append(f"{meta['label']} base risk {meta['risk_weight']}")

    if sensitive:
        score += 15
        factors.append("Sensitive resource +15")

    if amount is not None:
        if amount > 1000:
            score += 25
            factors.append("Amount over $1,000 +25")
        elif amount > 500:
            score += 18
            factors.append("Amount over $500 +18")
        elif amount > 100:
            score += 10
            factors.append("Amount over $100 +10")

    if decision == BLOCK:
        score += 15
        factors.append("Action was blocked +15")
    elif decision == APPROVAL_REQUIRED:
        score += 8
        factors.append("Human approval required +8")

    if recent_blocked:
        bump = min(20, recent_blocked * 5)
        score += bump
        factors.append(f"{recent_blocked} recent blocked attempts +{bump}")

    score = max(0, min(100, score))
    return {"risk": risk_band(score), "risk_score": score, "risk_factors": factors}


def compute_agent_risk(permissions: Sequence[Dict[str, Any]], *, recent_blocked: int = 0) -> Dict[str, Any]:
    """Standing risk level of an agent, derived from the breadth of its grants."""
    score = 0
    reasons: List[str] = []
    granted = [p for p in permissions if p.get("decision") != GRANT_BLOCK]
    if not granted:
        return {"risk": RISK_LOW, "risk_score": 0, "risk_factors": ["No active grants"]}

    top = 0
    sensitive_count = 0
    spend_total = 0.0
    for p in granted:
        meta = permission_meta(p.get("key", ""))
        top = max(top, int(meta["risk_weight"]))
        if meta["sensitive"]:
            sensitive_count += 1
        constraints = p.get("constraints") or {}
        if meta["supports_amount"]:
            cap = constraints.get("hard_max_amount") or constraints.get("max_amount")
            if cap is None:
                spend_total += 5000
            else:
                spend_total += float(cap)

    score += top
    reasons.append(f"Highest-risk grant weight {top}")

    breadth = len(granted)
    if breadth >= 12:
        score += 18
        reasons.append(f"{breadth} active permissions (broad) +18")
    elif breadth >= 8:
        score += 10
        reasons.append(f"{breadth} active permissions +10")
    elif breadth >= 5:
        score += 5
        reasons.append(f"{breadth} active permissions +5")

    if sensitive_count:
        score += 12 * sensitive_count
        reasons.append(f"{sensitive_count} sensitive permission(s) +{12 * sensitive_count}")

    if spend_total >= 5000:
        score += 15
        reasons.append("Combined spend authority over $5,000 +15")
    elif spend_total >= 500:
        score += 8
        reasons.append("Combined spend authority over $500 +8")

    if recent_blocked:
        bump = min(15, recent_blocked * 3)
        score += bump
        reasons.append(f"{recent_blocked} blocked attempts recently +{bump}")

    score = max(0, min(100, score))
    return {"risk": risk_band(score), "risk_score": score, "risk_factors": reasons}


# ---------------------------------------------------------------------------
# The engine
# ---------------------------------------------------------------------------
def _result(*, decision: str, reason: str, reason_code: str, trace: Trace,
            permission_key: str, request: Dict[str, Any], agent: Dict[str, Any],
            policy_name: str, policy_id: Optional[str], sensitive: bool,
            amount: Optional[float], expiration: Optional[str],
            recent_blocked: int, effective_limit: Optional[float],
            approval_id: Optional[str] = None,
            approval_status: str = "not_required") -> Dict[str, Any]:
    risk = calculate_risk(
        permission_key=permission_key,
        decision=decision,
        amount=amount,
        sensitive=sensitive,
        recent_blocked=recent_blocked,
    )
    trace.info("risk_assessment", f"Risk {risk['risk']} (score {risk['risk_score']})")
    return {
        "decision": decision,
        "reason": reason,
        "reason_code": reason_code,
        "policy": policy_name,
        "policy_id": policy_id,
        "risk": risk["risk"],
        "risk_score": risk["risk_score"],
        "risk_factors": risk["risk_factors"],
        "expiration": expiration,
        "audit_id": new_audit_id(),
        "request_id": new_request_id(),
        "permission_key": permission_key,
        "resource": request.get("resource"),
        "action": request.get("action"),
        "resource_id": request.get("resource_id"),
        "amount": amount,
        "currency": request.get("currency") or "USD",
        "sensitive": sensitive,
        "effective_limit": effective_limit,
        "approval_id": approval_id,
        "approval_status": approval_status,
        "agent_id": agent.get("agent_id"),
        "agent_name": agent.get("name"),
        "evaluated_at": utcnow().isoformat(),
        "trace": trace.steps,
    }


def authorize(
    agent: Optional[Dict[str, Any]],
    permissions: Sequence[Dict[str, Any]],
    policies: Sequence[Dict[str, Any]],
    request: Dict[str, Any],
    *,
    now: Optional[datetime] = None,
    authenticated: bool = False,
    approval: Optional[Dict[str, Any]] = None,
    recent_blocked: int = 0,
) -> Dict[str, Any]:
    """Evaluate a single agent action request.

    ``approval`` must be a server-loaded approval record (or None).  Anything the
    caller puts inside ``request`` about approval state is ignored.
    """
    now = now or utcnow()
    trace = Trace()
    request = dict(request or {})
    # Strip any caller-supplied privilege claims - never trusted.
    for forbidden in ("approved", "approval_granted", "decision", "risk", "permissions",
                      "org_id", "bypass", "max_amount", "policy"):
        request.pop(forbidden, None)

    empty_agent: Dict[str, Any] = agent or {}
    action = str(request.get("action") or "").strip()
    resource = str(request.get("resource") or "").strip()
    permission_key = f"{resource}.{action}" if resource and action else (resource or action)
    resource_id = request.get("resource_id")
    sensitive = permission_key in SENSITIVE_PERMISSIONS

    def deny(step: str, code: str, reason: str, *, policy_name: str = "Default deny",
             policy_id: Optional[str] = None, amount: Optional[float] = None,
             limit: Optional[float] = None) -> Dict[str, Any]:
        trace.fail(step, reason)
        return _result(
            decision=BLOCK, reason=reason, reason_code=code, trace=trace,
            permission_key=permission_key or "unknown", request=request, agent=empty_agent,
            policy_name=policy_name, policy_id=policy_id, sensitive=sensitive,
            amount=amount, expiration=None, recent_blocked=recent_blocked,
            effective_limit=limit, approval_status="not_required",
        )

    # -- 1. identity ------------------------------------------------------
    if not agent or not agent.get("agent_id") or not agent.get("org_id"):
        return deny("identity", "AGENT_IDENTITY_UNVERIFIED",
                    "No verified Vexen agent identity was presented with this request.")
    trace.ok("identity", f"Agent identity {agent['agent_id']} verified.")

    # -- 2. agent active --------------------------------------------------
    status = str(agent.get("status") or "").lower()
    if status != "active":
        return deny("agent_status", "AGENT_INACTIVE",
                    f"Agent is {status or 'unknown'}. Disabled agents cannot act.")
    trace.ok("agent_status", "Agent is active.")

    # -- 3. authentication ------------------------------------------------
    if not authenticated:
        return deny("authentication", "UNAUTHENTICATED",
                    "Request was not authenticated with a valid Vexen agent credential.")
    cred_expiry = _as_dt(agent.get("credential_expires_at"))
    if cred_expiry and cred_expiry <= now:
        return deny("authentication", "CREDENTIAL_EXPIRED",
                    "The agent credential used for this request has expired.")
    if agent.get("credential_status") in ("revoked", "expired"):
        return deny("authentication", "CREDENTIAL_REVOKED",
                    "The agent credential used for this request has been revoked.")
    trace.ok("authentication", "Request authenticated with a valid agent credential.")

    # -- 4. request shape -------------------------------------------------
    if not action or not resource:
        return deny("request_shape", "MALFORMED_REQUEST",
                    "Request must include both a resource and an action.")
    if not _TOKEN_RE.match(action) or not _TOKEN_RE.match(resource):
        return deny("request_shape", "MALFORMED_REQUEST",
                    "Resource and action must be simple dotted identifiers.")
    if resource_id is not None:
        if not isinstance(resource_id, str) or not _RESOURCE_ID_RE.match(resource_id):
            return deny("request_shape", "MALFORMED_REQUEST", "Resource identifier is not valid.")

    amount: Optional[float] = None
    raw_amount = request.get("amount")
    if raw_amount not in (None, ""):
        if isinstance(raw_amount, bool) or not isinstance(raw_amount, (int, float, str)):
            return deny("request_shape", "MALFORMED_REQUEST", "Amount must be a number.")
        try:
            amount = float(raw_amount)
        except (TypeError, ValueError):
            return deny("request_shape", "MALFORMED_REQUEST", "Amount must be a number.")
        if amount != amount or amount in (float("inf"), float("-inf")):
            return deny("request_shape", "MALFORMED_REQUEST", "Amount must be a finite number.")
        if amount < 0:
            return deny("request_shape", "AMOUNT_INVALID", "Negative amounts are rejected.")
        if amount > MAX_AMOUNT:
            return deny("request_shape", "AMOUNT_INVALID", "Amount exceeds the maximum representable value.",
                        amount=amount)
    trace.ok("request_shape", f"Request `{permission_key}` is well formed.")

    # -- 5. permission exists (DEFAULT DENY) ------------------------------
    permission = find_permission(permissions, permission_key)
    if permission is None:
        return deny("permission_lookup", "NO_PERMISSION",
                    f"Agent has no grant for `{permission_key}`. Vexen defaults to deny.",
                    amount=amount)
    grant_kind = str(permission.get("decision") or "").upper()
    if grant_kind not in (GRANT_ALLOW, GRANT_LIMITED, GRANT_APPROVAL, GRANT_BLOCK):
        return deny("permission_lookup", "PERMISSION_INVALID",
                    f"Grant for `{permission_key}` is not a recognised decision. Failing closed.",
                    amount=amount)
    if grant_kind == GRANT_BLOCK:
        return deny("permission_lookup", "PERMISSION_DENIED",
                    f"`{permission_key}` is explicitly blocked for this agent.",
                    policy_name=f"Agent grant: {permission_key} = BLOCK",
                    policy_id=permission.get("id"), amount=amount)
    trace.ok("permission_lookup", f"Grant found: `{permission_key}` = {grant_kind}.")

    constraints: Dict[str, Any] = dict(permission.get("constraints") or {})

    # -- 6. expiration ----------------------------------------------------
    expires_at = _as_dt(permission.get("expires_at"))
    if expires_at:
        if expires_at <= now:
            return deny("expiration", "PERMISSION_EXPIRED",
                        f"Temporary grant for `{permission_key}` expired at {expires_at.isoformat()}.",
                        policy_name="Temporary access expiry", policy_id=permission.get("id"),
                        amount=amount)
        remaining = int((expires_at - now).total_seconds() // 60)
        trace.ok("expiration", f"Temporary grant valid for another {remaining} minute(s).")
    else:
        trace.ok("expiration", "Grant has no expiry.")

    # -- 7. resource restrictions -----------------------------------------
    denied_resources = constraints.get("denied_resources") or []
    allowed_resources = constraints.get("allowed_resources") or []
    if denied_resources and _matches_any(resource_id, denied_resources):
        return deny("resource_scope", "RESOURCE_DENIED",
                    f"Resource `{resource_id}` is on this agent's deny list.",
                    policy_name="Resource scope", policy_id=permission.get("id"), amount=amount)
    if allowed_resources:
        if resource_id is None:
            return deny("resource_scope", "RESOURCE_SCOPE_REQUIRED",
                        "This grant is scoped to specific resources, but the request did not name one.",
                        policy_name="Resource scope", policy_id=permission.get("id"), amount=amount)
        if not _matches_any(resource_id, allowed_resources):
            return deny("resource_scope", "RESOURCE_NOT_ALLOWED",
                        f"Resource `{resource_id}` is outside this agent's granted scope "
                        f"({', '.join(allowed_resources)}).",
                        policy_name="Resource scope", policy_id=permission.get("id"), amount=amount)
        trace.ok("resource_scope", f"Resource `{resource_id}` is inside the granted scope.")
    else:
        trace.ok("resource_scope", "No resource restrictions on this grant.")

    # -- 8. action restrictions -------------------------------------------
    allowed_actions = constraints.get("allowed_actions") or []
    if allowed_actions and action not in allowed_actions:
        return deny("action_scope", "ACTION_NOT_ALLOWED",
                    f"Action `{action}` is not in the allowed action list for this grant.",
                    policy_name="Action scope", policy_id=permission.get("id"), amount=amount)
    calls_today = int(request.get("_calls_today") or 0)
    max_calls = constraints.get("max_calls_per_day")
    if max_calls is not None and calls_today >= int(max_calls):
        return deny("action_scope", "RATE_LIMIT_EXCEEDED",
                    f"Daily limit of {int(max_calls)} `{permission_key}` calls already reached.",
                    policy_name=f"Rate limit: {int(max_calls)}/day", policy_id=permission.get("id"),
                    amount=amount)
    trace.ok("action_scope", "Action restrictions satisfied.")

    # -- 9. numeric limits ------------------------------------------------
    escalate_reasons: List[str] = []
    governing_policy = f"Agent grant: {permission_key} = {grant_kind}"
    governing_policy_id = permission.get("id")
    effective_limit: Optional[float] = None
    meta = permission_meta(permission_key)

    if meta["supports_amount"]:
        soft = constraints.get("max_amount")
        hard = constraints.get("hard_max_amount")
        approval_above = constraints.get("approval_required_above")
        if grant_kind == GRANT_LIMITED and soft is None and approval_above is None:
            return deny("numeric_limits", "LIMIT_MISSING",
                        f"`{permission_key}` is marked LIMITED but no spend limit is configured. Failing closed.",
                        policy_name=governing_policy, policy_id=governing_policy_id, amount=amount)
        effective_limit = float(soft) if soft is not None else None
        if amount is None:
            if grant_kind == GRANT_LIMITED:
                return deny("numeric_limits", "AMOUNT_REQUIRED",
                            f"`{permission_key}` carries a spend limit, so the request must declare an amount.",
                            policy_name=governing_policy, policy_id=governing_policy_id)
            trace.ok("numeric_limits", "No amount in request; no numeric limit applies.")
        else:
            if hard is not None and amount > float(hard):
                return deny("numeric_limits", "HARD_LIMIT_EXCEEDED",
                            f"${amount:,.2f} exceeds the hard ceiling of ${float(hard):,.2f} for this agent. "
                            "Not even an approver can authorise this.",
                            policy_name=governing_policy, policy_id=governing_policy_id,
                            amount=amount, limit=float(hard))
            if soft is not None and amount > float(soft):
                if approval_above is not None and amount > float(approval_above):
                    escalate_reasons.append(
                        f"${amount:,.2f} exceeds the auto-approve limit of ${float(soft):,.2f}"
                    )
                    trace.escalate("numeric_limits", escalate_reasons[-1])
                else:
                    return deny("numeric_limits", "AMOUNT_LIMIT_EXCEEDED",
                                f"${amount:,.2f} exceeds the maximum of ${float(soft):,.2f} for `{permission_key}`.",
                                policy_name=governing_policy, policy_id=governing_policy_id,
                                amount=amount, limit=float(soft))
            else:
                trace.ok("numeric_limits",
                         f"${amount:,.2f} is within the ${float(soft):,.2f} limit."
                         if soft is not None else f"${amount:,.2f} accepted; no limit configured.")
    else:
        if amount is not None:
            trace.info("numeric_limits", f"`{permission_key}` is not a spend action; amount is informational.")
        else:
            trace.ok("numeric_limits", "No numerical limits apply to this action.")

    # -- 10. sensitive resource -------------------------------------------
    if sensitive and not constraints.get("allow_sensitive"):
        if grant_kind == GRANT_ALLOW:
            escalate_reasons.append(
                f"`{permission_key}` touches sensitive data; Vexen requires a human decision."
            )
            trace.escalate("sensitive_resource", escalate_reasons[-1])
        else:
            trace.info("sensitive_resource",
                       f"`{permission_key}` is sensitive; approval requirement enforced.")
            escalate_reasons.append(f"`{permission_key}` is a sensitive resource")
    else:
        trace.ok("sensitive_resource", "No sensitive-resource restriction triggered.")

    # -- 11. organization policies ----------------------------------------
    applied: List[Dict[str, Any]] = []
    ordered = sorted(policies or [], key=lambda p: int(p.get("priority", 100)))
    for policy in ordered:
        if not policy_applies(policy, agent=agent, permission_key=permission_key,
                              resource_id=resource_id, amount=amount, sensitive=sensitive):
            continue
        effect = str(policy.get("effect") or "").upper()
        params = policy.get("params") or {}
        applied.append({"id": policy.get("id"), "name": policy.get("name"), "effect": effect})
        if effect == "DENY":
            return deny("policy_evaluation", "POLICY_DENIED",
                        f"Blocked by policy \u201c{policy.get('name')}\u201d.",
                        policy_name=str(policy.get("name")), policy_id=policy.get("id"),
                        amount=amount, limit=effective_limit)
        if effect == "REQUIRE_SCOPE" and not allowed_resources:
            return deny("policy_evaluation", "POLICY_SCOPE_REQUIRED",
                        f"Policy \u201c{policy.get('name')}\u201d requires an explicit resource scope on "
                        f"`{permission_key}`, but this grant has none.",
                        policy_name=str(policy.get("name")), policy_id=policy.get("id"), amount=amount)
        if effect == "LIMIT":
            cap = params.get("max_amount")
            if cap is not None and amount is not None and amount > float(cap):
                escalate_reasons.append(
                    f"Policy \u201c{policy.get('name')}\u201d caps this action at ${float(cap):,.2f}"
                )
                trace.escalate("policy_evaluation", escalate_reasons[-1])
                governing_policy = str(policy.get("name"))
                governing_policy_id = policy.get("id")
                effective_limit = min(effective_limit, float(cap)) if effective_limit is not None else float(cap)
        if effect == "REQUIRE_APPROVAL":
            escalate_reasons.append(f"Policy \u201c{policy.get('name')}\u201d requires human approval")
            trace.escalate("policy_evaluation", escalate_reasons[-1])
            governing_policy = str(policy.get("name"))
            governing_policy_id = policy.get("id")
        if effect == "MAX_TTL":
            ttl = params.get("max_ttl_minutes")
            if ttl is not None:
                if expires_at is None:
                    if constraints.get("temporary"):
                        escalate_reasons.append(
                            f"Policy \u201c{policy.get('name')}\u201d requires temporary access to be time-boxed; "
                            "this grant has no expiry"
                        )
                        trace.escalate("policy_evaluation", escalate_reasons[-1])
                        governing_policy = str(policy.get("name"))
                        governing_policy_id = policy.get("id")
                    else:
                        trace.info("policy_evaluation",
                                   f"\u201c{policy.get('name')}\u201d applies to temporary grants only.")
                elif expires_at > now + timedelta(minutes=int(ttl)):
                    return deny("policy_evaluation", "POLICY_TTL_EXCEEDED",
                                f"Grant lifetime exceeds the {int(ttl)} minute maximum set by "
                                f"\u201c{policy.get('name')}\u201d.",
                                policy_name=str(policy.get("name")), policy_id=policy.get("id"),
                                amount=amount)
    if applied:
        trace.ok("policy_evaluation",
                 f"{len(applied)} policy/policies evaluated: " + ", ".join(p["name"] or "" for p in applied))
    else:
        trace.ok("policy_evaluation", "No organization policy restricts this action.")

    # -- 12. approval requirement -----------------------------------------
    needs_approval = bool(escalate_reasons) or grant_kind == GRANT_APPROVAL \
        or bool(constraints.get("require_approval"))
    if grant_kind == GRANT_APPROVAL or constraints.get("require_approval"):
        if not escalate_reasons:
            escalate_reasons.append(f"`{permission_key}` always requires human approval for this agent")
            trace.escalate("approval_requirement", escalate_reasons[-1])

    if needs_approval:
        # Only a server-loaded approval record can satisfy this step.
        if approval and str(approval.get("status")) == "approved":
            approver = approval.get("decided_by_email") or approval.get("decided_by") or "an approver"
            trace.ok("approval_requirement", f"Human approval granted by {approver}.")
            result = _result(
                decision=ALLOW,
                reason=f"Allowed after human approval by {approver}. " + "; ".join(escalate_reasons) + ".",
                reason_code="APPROVED_BY_HUMAN", trace=trace, permission_key=permission_key,
                request=request, agent=agent, policy_name=governing_policy,
                policy_id=governing_policy_id, sensitive=sensitive, amount=amount,
                expiration=_iso(expires_at), recent_blocked=recent_blocked,
                effective_limit=effective_limit, approval_id=approval.get("id"),
                approval_status="approved",
            )
            return result
        if approval and str(approval.get("status")) == "denied":
            decider = approval.get("decided_by_email") or "an approver"
            trace.fail("approval_requirement", f"Human approval denied by {decider}.")
            return _result(
                decision=BLOCK,
                reason=f"Denied by {decider}. " + "; ".join(escalate_reasons) + ".",
                reason_code="DENIED_BY_HUMAN", trace=trace, permission_key=permission_key,
                request=request, agent=agent, policy_name=governing_policy,
                policy_id=governing_policy_id, sensitive=sensitive, amount=amount,
                expiration=_iso(expires_at), recent_blocked=recent_blocked,
                effective_limit=effective_limit, approval_id=approval.get("id"),
                approval_status="denied",
            )
        trace.escalate("approval_requirement", "Human approval required before this action can proceed.")
        return _result(
            decision=APPROVAL_REQUIRED,
            reason="; ".join(escalate_reasons) + ". Human approval is required before this action can proceed.",
            reason_code="APPROVAL_REQUIRED", trace=trace, permission_key=permission_key,
            request=request, agent=agent, policy_name=governing_policy,
            policy_id=governing_policy_id, sensitive=sensitive, amount=amount,
            expiration=_iso(expires_at), recent_blocked=recent_blocked,
            effective_limit=effective_limit, approval_status="pending",
        )

    trace.ok("approval_requirement", "No human approval required.")

    # -- 13. allow --------------------------------------------------------
    detail = f"`{permission_key}` is granted to this agent"
    if effective_limit is not None and amount is not None:
        detail += f" and ${amount:,.2f} is within the ${effective_limit:,.2f} limit"
    return _result(
        decision=ALLOW, reason=detail + ".", reason_code="PERMISSION_GRANTED", trace=trace,
        permission_key=permission_key, request=request, agent=agent,
        policy_name=governing_policy, policy_id=governing_policy_id, sensitive=sensitive,
        amount=amount, expiration=_iso(expires_at), recent_blocked=recent_blocked,
        effective_limit=effective_limit,
    )
