"""Vexen guard — the piece that actually stops an agent.

Vexen can only stop what runs through it, so this sits *inside* your agent, in
front of the function that does the real thing. If Vexen says no, the wrapped
function never executes: no charge, no email, no file read.

    from vexen import Vexen

    vexen = Vexen(api_key=os.environ["VEXEN_KEY"], base_url="https://your-vexen-host")

    @vexen.guard("shopping", "purchase", amount=lambda kwargs: kwargs["price"],
                 resource_id=lambda kwargs: kwargs["sku"])
    def buy(sku, price):
        return store.charge_card(sku, price)   # only ever runs when allowed

Behaviour:
  * ALLOW              -> your function runs
  * BLOCK              -> raises VexenBlocked, function never runs
  * APPROVAL_REQUIRED  -> raises VexenNeedsApproval, or waits for a person if
                          you pass wait_for_approval=True
  * Vexen unreachable  -> raises VexenUnavailable (fails closed: doing nothing
                          is safer than doing something unapproved)

Only dependency is `requests`.
"""
from __future__ import annotations

import functools
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional

import requests

__all__ = [
    "Vexen",
    "Decision",
    "VexenError",
    "VexenBlocked",
    "VexenNeedsApproval",
    "VexenUnavailable",
]


class VexenError(Exception):
    """Base class so callers can catch everything Vexen raises."""


class VexenBlocked(VexenError):
    """Vexen refused the action outright."""

    def __init__(self, decision: "Decision"):
        super().__init__(decision.reason or "Blocked by Vexen")
        self.decision = decision


class VexenNeedsApproval(VexenError):
    """A person has to say yes first."""

    def __init__(self, decision: "Decision"):
        super().__init__(decision.reason or "A person needs to approve this")
        self.decision = decision
        self.approval_id = decision.approval_id


class VexenUnavailable(VexenError):
    """Vexen could not be reached, so the action was refused."""


@dataclass
class Decision:
    decision: str
    reason: str = ""
    reason_code: str = ""
    policy: Optional[str] = None
    risk: Optional[str] = None
    approval_id: Optional[str] = None
    approval_expires_at: Optional[str] = None
    audit_id: Optional[str] = None
    request_id: Optional[str] = None
    permission: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict)

    @property
    def allowed(self) -> bool:
        return self.decision == "ALLOW"

    @property
    def needs_approval(self) -> bool:
        return self.decision == "APPROVAL_REQUIRED"

    @property
    def blocked(self) -> bool:
        return self.decision == "BLOCK"

    @classmethod
    def from_payload(cls, payload: Dict[str, Any]) -> "Decision":
        return cls(
            decision=payload.get("decision", "BLOCK"),
            reason=payload.get("reason", ""),
            reason_code=payload.get("reason_code", ""),
            policy=payload.get("policy"),
            risk=payload.get("risk"),
            approval_id=payload.get("approval_id"),
            approval_expires_at=payload.get("approval_expires_at"),
            audit_id=payload.get("audit_id"),
            request_id=payload.get("request_id"),
            permission=payload.get("permission"),
            raw=payload,
        )


def _resolve(value: Any, kwargs: Dict[str, Any]) -> Any:
    """Allow either a fixed value or a function of the call arguments."""
    return value(kwargs) if callable(value) else value


class Vexen:
    def __init__(self, api_key: str, base_url: str, *, timeout: float = 10.0,
                 retries: int = 2, session: Optional[requests.Session] = None):
        if not api_key:
            raise ValueError("api_key is required")
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.retries = max(0, retries)
        self._session = session or requests.Session()

    # ---------------------------------------------------------------- plumbing
    @property
    def _headers(self) -> Dict[str, str]:
        return {"X-Vexen-Key": self.api_key, "Content-Type": "application/json"}

    def _post(self, path: str, body: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        last: Optional[Exception] = None
        for attempt in range(self.retries + 1):
            try:
                r = self._session.post(url, json=body, headers=self._headers, timeout=self.timeout)
                if r.status_code == 401:
                    raise VexenBlocked(Decision(
                        decision="BLOCK",
                        reason="This agent's key is missing, revoked or expired.",
                        reason_code="UNAUTHENTICATED",
                    ))
                if r.status_code == 429:
                    time.sleep(0.4 * (attempt + 1))
                    last = VexenUnavailable("Vexen is rate limiting this agent.")
                    continue
                r.raise_for_status()
                return r.json()
            except VexenBlocked:
                raise
            except Exception as exc:  # network, timeout, 5xx
                last = exc
                if attempt < self.retries:
                    time.sleep(0.3 * (attempt + 1))
        raise VexenUnavailable(f"Could not reach Vexen: {last}") from last

    def _get(self, path: str) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        try:
            r = self._session.get(url, headers=self._headers, timeout=self.timeout)
            r.raise_for_status()
            return r.json()
        except Exception as exc:
            raise VexenUnavailable(f"Could not reach Vexen: {exc}") from exc

    # ------------------------------------------------------------------ public
    def authorize(self, resource: str, action: str, *, amount: Optional[float] = None,
                  resource_id: Optional[str] = None, currency: str = "USD",
                  approval_id: Optional[str] = None,
                  context: Optional[Dict[str, Any]] = None) -> Decision:
        """Ask Vexen whether this exact action is allowed, right now."""
        body: Dict[str, Any] = {"resource": resource, "action": action, "currency": currency}
        if amount is not None:
            body["amount"] = amount
        if resource_id is not None:
            body["resource_id"] = resource_id
        if approval_id:
            body["approval_id"] = approval_id
        if context:
            body["context"] = context
        return Decision.from_payload(self._post("/api/v1/authorize", body))

    def approval_status(self, approval_id: str) -> Dict[str, Any]:
        """Has a person decided yet? Reading this never authorises anything."""
        return self._get(f"/api/v1/approvals/{approval_id}")

    def wait_for_approval(self, approval_id: str, *, timeout: float = 300.0) -> Dict[str, Any]:
        """Block until a person decides, or the wait runs out."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            status = self.approval_status(approval_id)
            if status.get("state") != "pending":
                return status
            time.sleep(float(status.get("poll_after_seconds") or 3))
        return {"state": "timeout", "may_proceed": False, "approval_id": approval_id}

    def permissions(self) -> Dict[str, Any]:
        """What is this agent allowed to do at all? Useful at start-up."""
        return self._get("/api/v1/agent")

    def check(self, resource: str, action: str, **details: Any) -> Decision:
        """Authorise or raise. Use this when you want plain if/else control."""
        decision = self.authorize(resource, action, **details)
        if decision.allowed:
            return decision
        if decision.needs_approval:
            raise VexenNeedsApproval(decision)
        raise VexenBlocked(decision)

    # --------------------------------------------------------------- decorator
    def guard(self, resource: str, action: str, *, amount: Any = None,
              resource_id: Any = None, currency: str = "USD",
              wait_for_approval: bool = False, approval_timeout: float = 300.0,
              context: Any = None) -> Callable:
        """Put Vexen in front of a function that does something real.

        `amount`, `resource_id` and `context` accept either a fixed value or a
        callable taking the function's arguments as a dict, e.g.
        `amount=lambda kwargs: kwargs["price"]`.
        """
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args: Any, **kwargs: Any):
                bound = _bind(func, args, kwargs)
                decision = self.authorize(
                    resource, action,
                    amount=_resolve(amount, bound),
                    resource_id=_resolve(resource_id, bound),
                    currency=currency,
                    context=_resolve(context, bound),
                )
                if decision.needs_approval and wait_for_approval and decision.approval_id:
                    answer = self.wait_for_approval(decision.approval_id, timeout=approval_timeout)
                    if answer.get("may_proceed"):
                        decision = self.authorize(
                            resource, action,
                            amount=_resolve(amount, bound),
                            resource_id=_resolve(resource_id, bound),
                            currency=currency,
                            approval_id=decision.approval_id,
                            context=_resolve(context, bound),
                        )
                if decision.allowed:
                    return func(*args, **kwargs)
                if decision.needs_approval:
                    raise VexenNeedsApproval(decision)
                raise VexenBlocked(decision)

            wrapper.vexen_permission = f"{resource}.{action}"  # type: ignore[attr-defined]
            return wrapper
        return decorator


def _bind(func: Callable, args: tuple, kwargs: Dict[str, Any]) -> Dict[str, Any]:
    """Best-effort map of a call's arguments to names, for the lambdas above."""
    import inspect

    try:
        bound = inspect.signature(func).bind_partial(*args, **kwargs)
        bound.apply_defaults()
        return dict(bound.arguments)
    except Exception:
        return dict(kwargs)
