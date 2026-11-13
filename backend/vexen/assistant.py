"""The in-app helper: a plain-language assistant that knows this workspace.

It is deliberately grounded. Before answering, we hand the model a small, honest
snapshot of what the person actually has — how many agents, what is waiting for
them, what was blocked recently — so questions like "why did my agent get
stopped?" get a real answer instead of a generic one.

It never sees passwords, API keys, or another workspace's data.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Tuple

from . import llm

logger = logging.getLogger("vexen.assistant")

MODEL = llm.MODEL
EFFORT = "low"
# If a safety classifier declines the request, Anthropic re-runs it on its
# recommended fallback model inside the same call instead of failing it.
FALLBACK_BETA = "server-side-fallback-2026-07-01"

MAX_TURNS = 12
MAX_CHARS = 1200


class AssistantError(RuntimeError):
    """Raised when no model could answer."""


SYSTEM_PROMPT = """You are the help assistant inside Vexen, a tool that decides what
someone's AI agents are allowed to do.

How Vexen works, in the words the product uses:
- Every time an agent tries to do something, Vexen gives one of three answers:
  "Allowed", "Blocked", or "Needs your OK".
- An agent starts with nothing. Permissions are added one at a time, and can have
  limits, like a spending cap or a daily count.
- Rules (the "Rules" page) are written in plain language and can allow, block, or
  require approval for a whole class of actions.
- Anything that needs a person waits on the "Waiting for you" page. Saying yes
  gives a one-time pass that works once, within 30 minutes.
- "History" is the record of every decision. It is sealed so tampering shows up.
- "Try an action" is a safe practice run: it shows what Vexen would decide and
  changes nothing.
- "For developers" has the API key, the code snippets, and a one-file guard
  (vexen.py) that developers put in front of the function that does the real
  thing, so a refusal means it never runs.
- If Vexen cannot be reached, the guard refuses the action rather than allowing it.

The pages are named: Home, How to use Vexen, My agents, Try an action,
Waiting for you, Rules, History, Safety check, For developers, Settings.

How to answer:
- Short. Two to four sentences, or a tight list of steps. No preamble.
- Plain English. Never say "policy engine", "RBAC", "OAuth scopes", "middleware".
- Use the person's actual workspace details when they are relevant.
- When something needs doing, name the page: "Open Rules and add..." .
- If you do not know, say so and suggest where to look. Never invent a feature,
  a page, a price, or a number.
- You cannot see or change anything yourself: you explain, the person clicks.
- Never ask for or repeat passwords or API keys.
"""


async def workspace_snapshot(db, org_id: str, user_name: str) -> str:
    """A few honest facts about this workspace, for grounding the answer."""
    agents = await db.agents.find(
        {"org_id": org_id}, {"name": 1, "status": 1, "risk_level": 1, "_id": 0}
    ).limit(12).to_list(length=12)
    agent_total = await db.agents.count_documents({"org_id": org_id})
    pending = await db.approvals.count_documents({"org_id": org_id, "status": "pending"})
    policy_total = await db.policies.count_documents({"org_id": org_id, "enabled": True})
    keys = await db.credentials.count_documents({"org_id": org_id, "status": "active"})

    recent = await db.audit_events.find(
        {"org_id": org_id, "decision": {"$in": ["BLOCK", "APPROVAL_REQUIRED"]}},
        {"decision": 1, "reason": 1, "permission_key": 1, "agent_name": 1, "_id": 0},
    ).sort("created_at", -1).limit(4).to_list(length=4)

    lines = [f"Person's name: {user_name or 'unknown'}"]
    lines.append(f"Agents: {agent_total}" + (
        " (" + ", ".join(
            f"{a.get('name')} — {a.get('status')}, {a.get('risk_level') or 'unknown'} risk"
            for a in agents[:6]
        ) + ")" if agents else " — none yet, the workspace is empty"))
    lines.append(f"Waiting for a person: {pending}")
    lines.append(f"Rules switched on: {policy_total}")
    lines.append(f"Live agent keys: {keys}")
    if recent:
        lines.append("Most recent stops:")
        for e in recent:
            lines.append(
                f"  - {e.get('agent_name') or 'an agent'} tried {e.get('permission_key')}: "
                f"{e.get('decision')} — {(e.get('reason') or '')[:130]}"
            )
    else:
        lines.append("No blocked or paused actions recorded yet.")
    return "\n".join(lines)


def _clean_history(messages: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    for m in messages[-MAX_TURNS:]:
        role = "assistant" if str(m.get("role")) == "assistant" else "user"
        content = str(m.get("content") or "").strip()[:MAX_CHARS]
        if content:
            out.append({"role": role, "content": content})
    # a conversation must start with the person speaking
    while out and out[0]["role"] != "user":
        out.pop(0)
    # ...and end with them: a trailing assistant turn is a prefill, which the
    # model rejects
    while out and out[-1]["role"] != "user":
        out.pop()
    return out


def _anthropic_reply(system: str, history: List[Dict[str, str]]) -> Tuple[str, str]:
    import anthropic

    try:
        client = llm.client(timeout=40.0)
    except llm.ProviderKeyError as exc:
        raise AssistantError(f"not configured ({exc.code})") from exc
    try:
        resp = client.beta.messages.create(
            model=MODEL,
            max_tokens=4096,  # thinking is always on and counts toward this
            system=system,
            messages=history,
            output_config={"effort": EFFORT},
            betas=[FALLBACK_BETA],
            fallbacks="default",
        )
    except (anthropic.AuthenticationError, anthropic.PermissionDeniedError) as exc:
        llm.mark_rejected()
        raise AssistantError("the AI key was refused") from exc
    except anthropic.NotFoundError as exc:
        llm.mark_model_unavailable()
        raise AssistantError("the AI key cannot use the model") from exc
    except anthropic.APIStatusError as exc:
        logger.warning("Assistant error %s (request %s): %s",
                       exc.status_code, exc.request_id, exc.message)
        raise AssistantError(f"api error {exc.status_code}") from exc
    except anthropic.APIConnectionError as exc:
        logger.warning("Assistant could not reach Anthropic: %s", exc)
        raise AssistantError("connection error") from exc
    llm.mark_working()
    if resp.stop_reason == "refusal":
        raise AssistantError("declined")
    text = " ".join(b.text for b in resp.content if b.type == "text").strip()
    if not text:
        raise AssistantError("empty reply")
    return text, f"anthropic:{resp.model}"


def follow_ups(snapshot: str) -> List[str]:
    """Cheap, honest next questions based on what this workspace looks like."""
    tips: List[str] = []
    if "none yet, the workspace is empty" in snapshot:
        tips.append("How do I add my first agent?")
    if "Waiting for a person: 0" not in snapshot and "Waiting for a person:" in snapshot:
        tips.append("Why is something waiting for me?")
    if "Most recent stops:" in snapshot:
        tips.append("Why was my agent stopped?")
    if "Live agent keys: 0" in snapshot:
        tips.append("How do I connect my own agent in code?")
    tips.extend([
        "How do I stop an agent spending too much?",
        "What is the difference between Blocked and Needs your OK?",
    ])
    seen, unique = set(), []
    for t in tips:
        if t not in seen:
            seen.add(t)
            unique.append(t)
    return unique[:4]
