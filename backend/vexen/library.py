"""
Vexen agent library — the browsable catalog of ready-made agents.

`catalog.AGENT_TEMPLATES` holds 55 hand-written base agents.  Real customers
work in wildly different fields and at wildly different scales, so this module
expands every base agent across:

  * INDUSTRIES — the field the agent works in (changes wording + scoping)
  * TIERS      — how much freedom the agent gets (changes caps + approvals)

That produces a library of 10,000+ concrete, ready-to-deploy agents while
staying honest: every variant is a deterministic transform of a reviewed base
bundle, so no variant can invent a permission that Vexen does not understand.

Memory note: only *light* summaries are materialised at import time.  The full
permission bundle for a variant is built on demand by `resolve_template()`.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from .catalog import (
    AGENT_TEMPLATES,
    GRANT_ALLOW,
    GRANT_APPROVAL,
    GRANT_BLOCK,
    GRANT_LIMITED,
    SENSITIVE_PERMISSIONS,
    TEMPLATE_BY_ID,
    TEMPLATE_CATEGORIES,
    permission_meta,
)

# Base agents that should never be varied (they are deliberately singular).
NO_VARIANT_IDS = {"custom-agent"}

VARIANT_SEP = "--"

# ---------------------------------------------------------------------------
# Variant dimensions
# ---------------------------------------------------------------------------
INDUSTRIES: List[Dict[str, str]] = [
    {"slug": "retail", "label": "Retail", "noun": "store"},
    {"slug": "ecommerce", "label": "E-commerce", "noun": "online shop"},
    {"slug": "healthcare", "label": "Healthcare", "noun": "clinic"},
    {"slug": "finance", "label": "Financial Services", "noun": "finance team"},
    {"slug": "insurance", "label": "Insurance", "noun": "insurance team"},
    {"slug": "education", "label": "Education", "noun": "school"},
    {"slug": "realestate", "label": "Real Estate", "noun": "brokerage"},
    {"slug": "legal", "label": "Legal", "noun": "law practice"},
    {"slug": "manufacturing", "label": "Manufacturing", "noun": "plant"},
    {"slug": "logistics", "label": "Logistics", "noun": "depot"},
    {"slug": "hospitality", "label": "Hospitality", "noun": "hotel"},
    {"slug": "travel", "label": "Travel & Tourism", "noun": "travel desk"},
    {"slug": "media", "label": "Media & Publishing", "noun": "newsroom"},
    {"slug": "gaming", "label": "Gaming", "noun": "studio"},
    {"slug": "nonprofit", "label": "Non-profit", "noun": "charity"},
    {"slug": "government", "label": "Public Sector", "noun": "department"},
    {"slug": "energy", "label": "Energy & Utilities", "noun": "utility"},
    {"slug": "agriculture", "label": "Agriculture", "noun": "farm"},
    {"slug": "construction", "label": "Construction", "noun": "site office"},
    {"slug": "automotive", "label": "Automotive", "noun": "dealership"},
    {"slug": "telecom", "label": "Telecom", "noun": "network team"},
    {"slug": "saas", "label": "SaaS & Software", "noun": "product team"},
    {"slug": "consulting", "label": "Consulting", "noun": "practice"},
    {"slug": "recruiting", "label": "Recruiting", "noun": "talent team"},
    {"slug": "fitness", "label": "Fitness & Wellness", "noun": "studio"},
    {"slug": "food", "label": "Food & Beverage", "noun": "kitchen"},
    {"slug": "events", "label": "Events", "noun": "events team"},
    {"slug": "freelance", "label": "Freelance & Solo", "noun": "one-person business"},
]

TIERS: List[Dict[str, Any]] = [
    {
        "slug": "starter",
        "label": "Starter",
        "mult": 0.25,
        "mode": "normal",
        "plain": "Small limits. Good for trying an agent out safely.",
    },
    {
        "slug": "standard",
        "label": "Standard",
        "mult": 1.0,
        "mode": "normal",
        "plain": "Everyday limits. A sensible default for most people.",
    },
    {
        "slug": "pro",
        "label": "Pro",
        "mult": 3.0,
        "mode": "normal",
        "plain": "Higher limits for an agent you already trust.",
    },
    {
        "slug": "team",
        "label": "Team",
        "mult": 6.0,
        "mode": "normal",
        "plain": "Shared across a team, so the limits are larger.",
    },
    {
        "slug": "enterprise",
        "label": "Enterprise",
        "mult": 12.0,
        "mode": "normal",
        "plain": "Large limits for high-volume work. Watch this one closely.",
    },
    {
        "slug": "observer",
        "label": "Look, don't touch",
        "mult": 0.0,
        "mode": "readonly",
        "plain": "Can read and search, but can never change or buy anything.",
    },
    {
        "slug": "guarded",
        "label": "Ask me first",
        "mult": 1.0,
        "mode": "escalate",
        "plain": "Can read freely, but every action waits for your approval.",
    },
]

INDUSTRY_BY_SLUG = {i["slug"]: i for i in INDUSTRIES}
TIER_BY_SLUG = {t["slug"]: t for t in TIERS}

READ_ACTIONS = {"read", "search", "list", "fetch", "view", "get", "verify"}


def _is_read(key: str) -> bool:
    return key.rpartition(".")[2] in READ_ACTIONS


# ---------------------------------------------------------------------------
# Grant transforms
# ---------------------------------------------------------------------------
_AMOUNT_FIELDS = ("max_amount", "hard_max_amount", "approval_required_above")


def _scale(grant: Dict[str, Any], mult: float) -> Dict[str, Any]:
    constraints = dict(grant.get("constraints") or {})
    for field in _AMOUNT_FIELDS:
        value = constraints.get(field)
        if value is None:
            continue
        scaled = round(float(value) * mult, 2)
        constraints[field] = max(1.0, scaled)
    if constraints.get("max_calls_per_day") is not None:
        constraints["max_calls_per_day"] = max(
            1, int(round(float(constraints["max_calls_per_day"]) * mult))
        )
    out = dict(grant)
    out["constraints"] = constraints
    return out


def _readonly(grant: Dict[str, Any]) -> Dict[str, Any]:
    """Reading stays; anything that changes the world is blocked outright."""
    if grant["decision"] == GRANT_BLOCK:
        return dict(grant)
    if _is_read(grant["key"]) and grant["key"] not in SENSITIVE_PERMISSIONS:
        return {"key": grant["key"], "decision": GRANT_ALLOW, "constraints": {}}
    return {"key": grant["key"], "decision": GRANT_BLOCK, "constraints": {}}


def _escalate(grant: Dict[str, Any]) -> Dict[str, Any]:
    """Reading stays; everything else needs a human every single time."""
    if grant["decision"] == GRANT_BLOCK:
        return dict(grant)
    if _is_read(grant["key"]) and grant["key"] not in SENSITIVE_PERMISSIONS:
        return {"key": grant["key"], "decision": GRANT_ALLOW, "constraints": {}}
    constraints = dict(grant.get("constraints") or {})
    constraints["require_approval"] = True
    constraints.pop("max_amount", None)
    constraints.pop("approval_required_above", None)
    return {"key": grant["key"], "decision": GRANT_APPROVAL, "constraints": constraints}


def _apply_tier(grants: List[Dict[str, Any]], tier: Dict[str, Any]) -> List[Dict[str, Any]]:
    mode = tier["mode"]
    if mode == "readonly":
        return [_readonly(g) for g in grants]
    if mode == "escalate":
        return [_escalate(g) for g in grants]
    return [_scale(g, tier["mult"]) for g in grants]


# ---------------------------------------------------------------------------
# Ids
# ---------------------------------------------------------------------------
def make_variant_id(base_id: str, industry_slug: str, tier_slug: str) -> str:
    return f"{base_id}{VARIANT_SEP}{industry_slug}{VARIANT_SEP}{tier_slug}"


def parse_template_id(template_id: str) -> Optional[Tuple[Dict[str, Any], Optional[Dict[str, str]], Optional[Dict[str, Any]]]]:
    """Return (base, industry, tier). Industry/tier are None for base templates."""
    if not template_id:
        return None
    if template_id in TEMPLATE_BY_ID:
        return TEMPLATE_BY_ID[template_id], None, None
    parts = template_id.split(VARIANT_SEP)
    if len(parts) != 3:
        return None
    base_id, industry_slug, tier_slug = parts
    base = TEMPLATE_BY_ID.get(base_id)
    industry = INDUSTRY_BY_SLUG.get(industry_slug)
    tier = TIER_BY_SLUG.get(tier_slug)
    if not base or not industry or not tier or base_id in NO_VARIANT_IDS:
        return None
    return base, industry, tier


# ---------------------------------------------------------------------------
# Summaries (light — safe to hold 10k+ of these in memory)
# ---------------------------------------------------------------------------
def _grant_stats(grants: List[Dict[str, Any]]) -> Dict[str, Any]:
    counts = {"allow": 0, "limited": 0, "approval": 0, "blocked": 0}
    sensitive = 0
    max_amount: Optional[float] = None
    for g in grants:
        decision = g["decision"]
        if decision == GRANT_ALLOW:
            counts["allow"] += 1
        elif decision == GRANT_LIMITED:
            counts["limited"] += 1
        elif decision == GRANT_APPROVAL:
            counts["approval"] += 1
        elif decision == GRANT_BLOCK:
            counts["blocked"] += 1
        if g["key"] in SENSITIVE_PERMISSIONS and decision != GRANT_BLOCK:
            sensitive += 1
        amount = (g.get("constraints") or {}).get("max_amount")
        if amount is not None:
            max_amount = amount if max_amount is None else max(max_amount, float(amount))
    return {
        "grant_counts": counts,
        "sensitive_count": sensitive,
        "spend_cap": max_amount,
        "permission_count": len(grants),
    }


def _risk_hint(stats: Dict[str, Any]) -> str:
    if stats["sensitive_count"]:
        return "HIGH"
    allowed = stats["grant_counts"]["allow"] + stats["grant_counts"]["limited"]
    if allowed >= 10 or (stats["spend_cap"] or 0) >= 5000:
        return "MEDIUM"
    return "LOW"


def _summary(
    *,
    template_id: str,
    name: str,
    base: Dict[str, Any],
    tagline: str,
    industry: Optional[Dict[str, str]],
    tier: Optional[Dict[str, Any]],
    grants: List[Dict[str, Any]],
) -> Dict[str, Any]:
    stats = _grant_stats(grants)
    return {
        "id": template_id,
        "name": name,
        "base_id": base["id"],
        "base_name": base["name"],
        "category": base["category"],
        "icon": base["icon"],
        "tagline": tagline,
        "industry": industry["label"] if industry else None,
        "industry_slug": industry["slug"] if industry else None,
        "tier": tier["label"] if tier else None,
        "tier_slug": tier["slug"] if tier else None,
        "tier_plain": tier["plain"] if tier else None,
        "is_base": industry is None,
        "risk_hint": _risk_hint(stats),
        **stats,
    }


def _variant_tagline(base: Dict[str, Any], industry: Dict[str, str], tier: Dict[str, Any]) -> str:
    core = base["tagline"].rstrip(".")
    return f"{core}, set up for a {industry['noun']}. {tier['plain']}"


def _variant_name(base: Dict[str, Any], industry: Dict[str, str]) -> str:
    return f"{base['name']} · {industry['label']}"


# ---------------------------------------------------------------------------
# Build the index once at import
# ---------------------------------------------------------------------------
def _build_index() -> List[Dict[str, Any]]:
    index: List[Dict[str, Any]] = []
    for base in AGENT_TEMPLATES:
        index.append(
            _summary(
                template_id=base["id"],
                name=base["name"],
                base=base,
                tagline=base["tagline"],
                industry=None,
                tier=None,
                grants=base["permissions"],
            )
        )
    for base in AGENT_TEMPLATES:
        if base["id"] in NO_VARIANT_IDS:
            continue
        for industry in INDUSTRIES:
            for tier in TIERS:
                grants = _apply_tier(base["permissions"], tier)
                index.append(
                    _summary(
                        template_id=make_variant_id(base["id"], industry["slug"], tier["slug"]),
                        name=_variant_name(base, industry),
                        base=base,
                        tagline=_variant_tagline(base, industry, tier),
                        industry=industry,
                        tier=tier,
                        grants=grants,
                    )
                )
    return index


TEMPLATE_INDEX: List[Dict[str, Any]] = _build_index()
TEMPLATE_INDEX_BY_ID: Dict[str, Dict[str, Any]] = {t["id"]: t for t in TEMPLATE_INDEX}
LIBRARY_SIZE = len(TEMPLATE_INDEX)

# Pre-lowered search haystack so 10k-row filtering stays fast.
_HAYSTACK: List[Tuple[str, Dict[str, Any]]] = [
    (
        " ".join(
            filter(
                None,
                [
                    t["name"],
                    t["category"],
                    t["tagline"],
                    t.get("industry") or "",
                    t.get("tier") or "",
                    t["base_name"],
                ],
            )
        ).lower(),
        t,
    )
    for t in TEMPLATE_INDEX
]


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------
def resolve_template(template_id: str) -> Optional[Dict[str, Any]]:
    """Full template (including the permission bundle), built on demand."""
    parsed = parse_template_id(template_id)
    if not parsed:
        return None
    base, industry, tier = parsed
    if industry is None or tier is None:
        return dict(base)
    grants = _apply_tier(base["permissions"], tier)
    return {
        "id": make_variant_id(base["id"], industry["slug"], tier["slug"]),
        "name": _variant_name(base, industry),
        "category": base["category"],
        "tagline": _variant_tagline(base, industry, tier),
        "description": _variant_tagline(base, industry, tier),
        "icon": base["icon"],
        "permissions": grants,
        "base_id": base["id"],
        "industry": industry["label"],
        "tier": tier["label"],
    }


def template_detail(template_id: str) -> Optional[Dict[str, Any]]:
    """Full template plus per-permission metadata, for the library detail view."""
    template = resolve_template(template_id)
    if not template:
        return None
    summary = TEMPLATE_INDEX_BY_ID.get(template_id) or {}
    grants = []
    for grant in template["permissions"]:
        meta = permission_meta(grant["key"])
        grants.append(
            {
                "key": grant["key"],
                "decision": grant["decision"],
                "constraints": grant.get("constraints") or {},
                "expires_in_minutes": grant.get("expires_in_minutes"),
                "label": meta["label"],
                "category": meta["category"],
                "sensitive": meta["sensitive"],
                "supports_amount": meta["supports_amount"],
                "description": meta["description"],
            }
        )
    return {**summary, **template, "permissions": grants}


def search_templates(
    *,
    search: Optional[str] = None,
    category: Optional[str] = None,
    industry: Optional[str] = None,
    tier: Optional[str] = None,
    only_base: bool = False,
    page: int = 1,
    limit: int = 24,
) -> Dict[str, Any]:
    rows: List[Dict[str, Any]] = TEMPLATE_INDEX

    if only_base:
        rows = [t for t in rows if t["is_base"]]
    if category and category != "All":
        rows = [t for t in rows if t["category"] == category]
    if industry and industry != "All":
        rows = [t for t in rows if t.get("industry_slug") == industry]
    if tier and tier != "All":
        rows = [t for t in rows if t.get("tier_slug") == tier]

    needle = (search or "").strip().lower()
    if needle:
        terms = [t for t in re.split(r"\s+", needle) if t][:6]
        if rows is TEMPLATE_INDEX:
            rows = [t for hay, t in _HAYSTACK if all(term in hay for term in terms)]
        else:
            def _matches(t: Dict[str, Any]) -> bool:
                hay = " ".join(
                    filter(
                        None,
                        [t["name"], t["category"], t["tagline"], t.get("industry") or "",
                         t.get("tier") or "", t["base_name"]],
                    )
                ).lower()
                return all(term in hay for term in terms)

            rows = [t for t in rows if _matches(t)]

    total = len(rows)
    start = max(0, (page - 1) * limit)
    page_rows = rows[start:start + limit]
    return {
        "items": page_rows,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": max(1, (total + limit - 1) // limit),
        "library_size": LIBRARY_SIZE,
        "categories": ["All"] + list(TEMPLATE_CATEGORIES),
        "industries": [{"slug": "All", "label": "Every field"}]
        + [{"slug": i["slug"], "label": i["label"]} for i in INDUSTRIES],
        "tiers": [{"slug": "All", "label": "Any freedom level", "plain": ""}]
        + [{"slug": t["slug"], "label": t["label"], "plain": t["plain"]} for t in TIERS],
    }


def library_facets() -> Dict[str, Any]:
    return {
        "library_size": LIBRARY_SIZE,
        "categories": ["All"] + list(TEMPLATE_CATEGORIES),
        "industries": [{"slug": "All", "label": "Every field"}]
        + [{"slug": i["slug"], "label": i["label"]} for i in INDUSTRIES],
        "tiers": [{"slug": "All", "label": "Any freedom level", "plain": ""}]
        + [{"slug": t["slug"], "label": t["label"], "plain": t["plain"]} for t in TIERS],
    }
