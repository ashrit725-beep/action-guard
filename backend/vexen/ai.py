"""
Natural-language -> structured Vexen policy rule generator.

Uses Anthropic Claude with structured outputs (a JSON schema the response must
match) so the model can only reply with a structurally valid policy rule.  The
result is then validated again in Python: if anything is off we fail CLOSED
(raise) rather than saving a policy we do not fully understand.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Tuple

from .catalog import PERMISSION_CATALOG, POLICY_EFFECTS

logger = logging.getLogger("vexen.ai")

MODEL = "claude-opus-5-5"
EFFORT = "medium"
# If a safety classifier declines the request, Anthropic re-runs it on its
# recommended fallback model inside the same call instead of failing it.
FALLBACK_BETA = "server-side-fallback-2026-07-01"

_PERMISSION_KEYS = [p["key"] for p in PERMISSION_CATALOG]

POLICY_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "name": {"type": "string", "description": "Short imperative policy title, max 70 chars."},
        "description": {"type": "string", "description": "One or two plain-English sentences a non-technical admin understands."},
        "effect": {
            "type": "string",
            "enum": ["DENY", "REQUIRE_APPROVAL", "LIMIT", "MAX_TTL", "REQUIRE_SCOPE"],
            "description": "DENY = never allow. REQUIRE_APPROVAL = escalate to a human. LIMIT = cap an amount. MAX_TTL = force time-boxed access. REQUIRE_SCOPE = require explicit resource scoping.",
        },
        "permissions": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Permission keys this policy matches. Glob '*' is allowed, e.g. 'payments.*'. Must come from the supplied catalog.",
        },
        "resources": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Resource id glob patterns, or ['*'] for all resources.",
        },
        "amount_gt": {
            "type": "number",
            "description": "Only apply when the request amount is strictly greater than this. Omit if not amount based.",
        },
        "max_amount": {"type": "number", "description": "For LIMIT: the cap in USD."},
        "max_ttl_minutes": {"type": "integer", "description": "For MAX_TTL: maximum grant lifetime in minutes."},
        "priority": {"type": "integer", "description": "10-99. Lower runs first. Use 10-19 for denies, 20-29 for approvals, 30+ for limits."},
        "rationale": {"type": "string", "description": "One or two plain sentences for the administrator on why this rule matches the request (or, at low confidence, why it cannot)."},
        "confidence": {"type": "number", "description": "0-1 confidence that this rule faithfully captures the request."},
    },
    "required": ["name", "description", "effect", "permissions", "priority", "rationale", "confidence"],
    "additionalProperties": False,
}

SYSTEM_PROMPT = """You are the policy compiler for Vexen, a security platform that controls what AI agents are allowed to do.

You convert a plain-English security requirement written by an administrator into exactly ONE structured Vexen policy rule.

Hard rules:
- Only use permission keys from the catalog provided by the user message. If the request mentions something with no matching key, choose the closest catalog keys and lower your confidence.
- Prefer the most restrictive effect that satisfies the request. "never", "cannot", "must not", "block" => DENY.
- "needs sign-off", "ask me first", "requires approval", "only with permission" => REQUIRE_APPROVAL.
- A spending or numeric ceiling that should still be possible with a human in the loop => REQUIRE_APPROVAL with amount_gt.
- A hard numeric ceiling that should never be exceeded => LIMIT with max_amount.
- Time-boxed / temporary / expires access => MAX_TTL with max_ttl_minutes.
- "only files/resources explicitly granted" => REQUIRE_SCOPE.
- If the request is vague, contradictory, not a security policy, or you cannot map it safely, set confidence below 0.4 and explain why in rationale. Vexen will refuse to save it.
- Never invent a permission key that is not in the catalog.
"""


class PolicyGenerationError(RuntimeError):
    """Raised when a natural-language policy cannot be safely compiled."""


def _catalog_block() -> str:
    lines = []
    for p in PERMISSION_CATALOG:
        flags = []
        if p["sensitive"]:
            flags.append("sensitive")
        if p["supports_amount"]:
            flags.append("amount")
        suffix = f" [{', '.join(flags)}]" if flags else ""
        lines.append(f"- {p['key']}: {p['label']}{suffix}")
    return "\n".join(lines)


def _validate(raw: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(raw, dict):
        raise PolicyGenerationError("Model returned a non-object policy.")

    effect = str(raw.get("effect", "")).upper()
    if effect not in POLICY_EFFECTS:
        raise PolicyGenerationError(f"Unsupported policy effect: {effect or 'missing'}")

    name = str(raw.get("name") or "").strip()
    if not (3 <= len(name) <= 120):
        raise PolicyGenerationError("Policy name is missing or unusable.")

    permissions = raw.get("permissions") or []
    if not isinstance(permissions, list) or not permissions:
        raise PolicyGenerationError("Policy did not target any permission.")
    cleaned: List[str] = []
    for item in permissions:
        key = str(item).strip()
        if not key:
            continue
        if "*" in key:
            stem = key.split("*")[0]
            if not any(k.startswith(stem) for k in _PERMISSION_KEYS):
                raise PolicyGenerationError(f"Unknown permission pattern: {key}")
        elif key not in _PERMISSION_KEYS:
            raise PolicyGenerationError(f"Unknown permission key: {key}")
        cleaned.append(key)
    if not cleaned:
        raise PolicyGenerationError("Policy did not target any valid permission.")

    confidence = raw.get("confidence")
    try:
        confidence = float(confidence)
    except (TypeError, ValueError):
        confidence = 0.0
    if confidence < 0.4:
        raise PolicyGenerationError(
            "That request could not be translated into a safe policy rule with confidence. "
            + str(raw.get("rationale") or "Try describing the exact permission and the exact restriction.")
        )

    resources = raw.get("resources") or ["*"]
    if not isinstance(resources, list) or not resources:
        resources = ["*"]

    match: Dict[str, Any] = {
        "permissions": cleaned,
        "agents": ["*"],
        "resources": [str(r) for r in resources],
    }
    amount_gt = raw.get("amount_gt")
    if amount_gt is not None:
        try:
            match["amount_gt"] = max(0.0, float(amount_gt))
        except (TypeError, ValueError):
            pass

    params: Dict[str, Any] = {}
    if effect == "LIMIT":
        try:
            params["max_amount"] = max(0.0, float(raw.get("max_amount")))
        except (TypeError, ValueError):
            raise PolicyGenerationError("A LIMIT policy needs a numeric max_amount.")
    if effect == "MAX_TTL":
        try:
            params["max_ttl_minutes"] = max(1, int(raw.get("max_ttl_minutes")))
        except (TypeError, ValueError):
            raise PolicyGenerationError("A MAX_TTL policy needs max_ttl_minutes.")

    try:
        priority = int(raw.get("priority", 50))
    except (TypeError, ValueError):
        priority = 50
    priority = min(99, max(10, priority))

    return {
        "name": name[:120],
        "description": str(raw.get("description") or "")[:600],
        "effect": effect,
        "match": match,
        "params": params,
        "priority": priority,
        "rationale": str(raw.get("rationale") or "")[:800],
        "confidence": round(confidence, 2),
    }


def _anthropic_call(prompt: str) -> Tuple[Dict[str, Any], str]:
    import anthropic

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise PolicyGenerationError("Policy generator is not configured.")
    client = anthropic.Anthropic(api_key=api_key, max_retries=1, timeout=45.0)
    user = (
        "Permission catalog:\n" + _catalog_block()
        + "\n\nAdministrator's requirement:\n\"\"\"\n" + prompt.strip() + "\n\"\"\"\n\n"
        "Emit the single Vexen policy rule that enforces this."
    )
    try:
        resp = client.beta.messages.create(
            model=MODEL,
            max_tokens=16000,  # thinking is always on and counts toward this
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user}],
            output_config={
                "effort": EFFORT,
                "format": {"type": "json_schema", "schema": POLICY_SCHEMA},
            },
            betas=[FALLBACK_BETA],
            fallbacks="default",
        )
    except anthropic.RateLimitError as exc:
        logger.warning("Policy generator rate limited (request %s)", exc.request_id)
        raise PolicyGenerationError("The policy generator is busy. Try again in a minute.") from exc
    except anthropic.APIStatusError as exc:
        logger.error("Policy generator error %s (request %s): %s",
                     exc.status_code, exc.request_id, exc.message)
        raise PolicyGenerationError(f"Policy generator unavailable: {type(exc).__name__}") from exc
    except anthropic.APIConnectionError as exc:
        logger.error("Policy generator could not reach Anthropic: %s", exc)
        raise PolicyGenerationError(f"Policy generator unavailable: {type(exc).__name__}") from exc

    if resp.stop_reason == "refusal":
        raise PolicyGenerationError(
            "The AI model's safety checks declined that request, so no rule was drafted. "
            "Try describing the exact permission and the exact restriction."
        )
    if resp.stop_reason != "end_turn":
        raise PolicyGenerationError("Model did not emit a complete policy.")
    try:
        raw = json.loads("".join(b.text for b in resp.content if b.type == "text"))
    except ValueError as exc:
        raise PolicyGenerationError("Model did not emit a policy.") from exc
    return raw, f"anthropic:{resp.model}"


def generate_policy(prompt: str) -> Dict[str, Any]:
    """Compile natural language into a validated Vexen policy rule. Fails closed."""
    text = (prompt or "").strip()
    if len(text) < 8:
        raise PolicyGenerationError("Describe the rule in a full sentence so it can be compiled safely.")
    if len(text) > 2000:
        raise PolicyGenerationError("Policy description is too long. Keep it under 2000 characters.")

    raw, model = _anthropic_call(text)
    rule = _validate(raw)
    rule["generated_by"] = model
    rule["source_prompt"] = text
    return rule


def generator_available() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY"))
