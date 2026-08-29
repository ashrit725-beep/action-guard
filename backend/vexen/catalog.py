"""
Vexen permission catalog, agent template library and built-in system policies.

This module is the single declarative source of truth for:
  * PERMISSION_CATALOG  — every permission Vexen understands
  * AGENT_TEMPLATES     — the agent template library (50+ real templates)
  * SYSTEM_POLICIES     — built-in org policies seeded for every new organization

Nothing here is UI-only: the authorization engine, the seeding routine and the
frontend all read from these definitions.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Decisions
# ---------------------------------------------------------------------------
ALLOW = "ALLOW"
BLOCK = "BLOCK"
APPROVAL_REQUIRED = "APPROVAL_REQUIRED"

# Permission grant kinds (what the user configures on an agent)
GRANT_ALLOW = "ALLOW"
GRANT_LIMITED = "LIMITED"
GRANT_APPROVAL = "APPROVAL_REQUIRED"
GRANT_BLOCK = "BLOCK"
GRANT_KINDS = (GRANT_ALLOW, GRANT_LIMITED, GRANT_APPROVAL, GRANT_BLOCK)

RISK_LOW = "LOW"
RISK_MEDIUM = "MEDIUM"
RISK_HIGH = "HIGH"
RISK_CRITICAL = "CRITICAL"


def _p(
    key: str,
    label: str,
    category: str,
    risk: int,
    *,
    sensitive: bool = False,
    amount: bool = False,
    description: str = "",
) -> Dict[str, Any]:
    resource, _, action = key.rpartition(".")
    return {
        "key": key,
        "resource": resource,
        "action": action,
        "label": label,
        "category": category,
        "risk_weight": risk,
        "sensitive": sensitive,
        "supports_amount": amount,
        "description": description or label,
    }


# ---------------------------------------------------------------------------
# Permission catalog
# ---------------------------------------------------------------------------
PERMISSION_CATALOG: List[Dict[str, Any]] = [
    # Productivity
    _p("calendar.read", "Read calendar", "Productivity", 5, description="View events, availability and invitees."),
    _p("calendar.write", "Create / modify calendar events", "Productivity", 15, description="Create, move or cancel events."),
    _p("email.read", "Read email", "Communication", 12, description="Read inbox messages and threads."),
    _p("email.send", "Send email", "Communication", 22, description="Send email on the user's behalf."),
    _p("email.delete", "Delete email", "Communication", 28, description="Permanently remove messages."),
    _p("notes.read", "Read notes", "Productivity", 4),
    _p("notes.write", "Write notes", "Productivity", 8),
    _p("tasks.read", "Read tasks", "Productivity", 4),
    _p("tasks.write", "Create / update tasks", "Productivity", 8),
    _p("contacts.read", "Read contacts", "Productivity", 10),
    _p("contacts.write", "Modify contacts", "Productivity", 16),
    # Files & documents
    _p("files.read", "Read files", "Files", 14, description="Read files the agent has been explicitly granted."),
    _p("files.write", "Write files", "Files", 24),
    _p("files.delete", "Delete files", "Files", 34),
    _p("files.share", "Share files externally", "Files", 32),
    _p("docs.read", "Read documents", "Files", 10),
    _p("docs.write", "Write documents", "Files", 18),
    # Commerce
    _p("shopping.search", "Search products", "Commerce", 3),
    _p("shopping.cart", "Add to cart", "Commerce", 6),
    _p("shopping.purchase", "Purchase products", "Commerce", 34, amount=True, description="Spend real money to buy products."),
    _p("inventory.read", "Read inventory", "Commerce", 6),
    _p("inventory.write", "Update inventory", "Commerce", 18),
    _p("invoices.read", "Read invoices", "Finance", 12),
    _p("invoices.create", "Create invoices", "Finance", 24, amount=True),
    _p("invoices.pay", "Pay invoices", "Finance", 42, amount=True, sensitive=True),
    # Payments & credentials (sensitive)
    _p("payments.read", "Read payment credentials", "Payments", 48, sensitive=True, description="Read stored cards, bank details and tokens."),
    _p("payments.create", "Initiate payment", "Payments", 46, amount=True, sensitive=True),
    _p("payments.refund", "Issue refund", "Payments", 38, amount=True, sensitive=True),
    _p("secrets.read", "Read secrets / API keys", "Payments", 50, sensitive=True),
    # Account & identity
    _p("account.settings.write", "Change account settings", "Account", 30),
    _p("account.password.write", "Change password", "Account", 50, sensitive=True),
    _p("identity.user.read", "Read user directory", "Identity", 12),
    _p("identity.user.write", "Create / modify users", "Identity", 34),
    _p("identity.role.write", "Grant roles / privileges", "Identity", 48, sensitive=True),
    # Travel
    _p("travel.search", "Search travel", "Travel", 3),
    _p("travel.book", "Book travel", "Travel", 34, amount=True),
    _p("travel.cancel", "Cancel travel", "Travel", 26),
    # Research / web
    _p("web.search", "Search the web", "Research", 4),
    _p("web.fetch", "Fetch a URL", "Research", 8),
    # CRM / sales
    _p("crm.read", "Read CRM records", "Sales", 12),
    _p("crm.write", "Write CRM records", "Sales", 20),
    _p("crm.export", "Export CRM data", "Sales", 40, description="Bulk export of customer data."),
    # Support
    _p("support.ticket.read", "Read support tickets", "Support", 8),
    _p("support.ticket.write", "Reply to support tickets", "Support", 16),
    _p("support.refund.issue", "Issue customer refund", "Support", 36, amount=True),
    # Engineering
    _p("code.read", "Read source code", "Engineering", 10),
    _p("code.write", "Write source code", "Engineering", 26),
    _p("code.deploy", "Deploy to production", "Engineering", 44),
    _p("infra.read", "Read infrastructure state", "Engineering", 10),
    _p("infra.restart", "Restart services", "Engineering", 32),
    _p("infra.delete", "Destroy infrastructure", "Engineering", 50, sensitive=True),
    _p("database.read", "Read database", "Data", 16),
    _p("database.write", "Write database", "Data", 32),
    _p("database.delete", "Delete database records", "Data", 48, sensitive=True),
    # Data / analytics
    _p("analytics.read", "Read analytics", "Data", 6),
    _p("analytics.export", "Export analytics", "Data", 22),
    # Messaging / social
    _p("messaging.read", "Read team messages", "Communication", 10),
    _p("messaging.send", "Send team messages", "Communication", 16),
    _p("sms.send", "Send SMS", "Communication", 24, amount=True),
    _p("social.post", "Publish social post", "Marketing", 30),
    _p("ads.read", "Read ad performance", "Marketing", 8),
    _p("ads.spend", "Spend ad budget", "Marketing", 40, amount=True),
    # HR / legal / health / education
    _p("hr.read", "Read HR records", "HR", 26),
    _p("hr.write", "Write HR records", "HR", 38),
    _p("legal.contract.read", "Read contracts", "Legal", 14),
    _p("legal.contract.write", "Modify / sign contracts", "Legal", 44),
    _p("health.record.read", "Read health records", "Healthcare", 50, sensitive=True),
]

PERMISSION_BY_KEY: Dict[str, Dict[str, Any]] = {p["key"]: p for p in PERMISSION_CATALOG}
SENSITIVE_PERMISSIONS = {p["key"] for p in PERMISSION_CATALOG if p["sensitive"]}
AMOUNT_PERMISSIONS = {p["key"] for p in PERMISSION_CATALOG if p["supports_amount"]}
PERMISSION_CATEGORIES = sorted({p["category"] for p in PERMISSION_CATALOG})


def permission_meta(key: str) -> Dict[str, Any]:
    """Return catalog metadata for a permission key (safe fallback for unknown keys)."""
    if key in PERMISSION_BY_KEY:
        return PERMISSION_BY_KEY[key]
    resource, _, action = key.rpartition(".")
    return {
        "key": key,
        "resource": resource,
        "action": action,
        "label": key,
        "category": "Unknown",
        "risk_weight": 40,
        "sensitive": False,
        "supports_amount": False,
        "description": "Unrecognised permission — Vexen defaults to deny.",
    }


# ---------------------------------------------------------------------------
# Grant helpers used by the template library
# ---------------------------------------------------------------------------
def allow(key: str, **constraints: Any) -> Dict[str, Any]:
    return {"key": key, "decision": GRANT_ALLOW, "constraints": constraints or {}}


def limited(key: str, max_amount: float, *, hard_max_amount: Optional[float] = None, **constraints: Any) -> Dict[str, Any]:
    c: Dict[str, Any] = {"max_amount": max_amount, "approval_required_above": max_amount}
    if hard_max_amount is not None:
        c["hard_max_amount"] = hard_max_amount
    c.update(constraints)
    return {"key": key, "decision": GRANT_LIMITED, "constraints": c}


def rate_limited(key: str, per_day: int, **constraints: Any) -> Dict[str, Any]:
    c = {"max_calls_per_day": per_day}
    c.update(constraints)
    return {"key": key, "decision": GRANT_ALLOW, "constraints": c}


def needs_approval(key: str, **constraints: Any) -> Dict[str, Any]:
    c = {"require_approval": True}
    c.update(constraints)
    return {"key": key, "decision": GRANT_APPROVAL, "constraints": c}


def blocked(key: str) -> Dict[str, Any]:
    return {"key": key, "decision": GRANT_BLOCK, "constraints": {}}


def temporary(grant: Dict[str, Any], minutes: int) -> Dict[str, Any]:
    g = dict(grant)
    g["expires_in_minutes"] = minutes
    return g


def scoped(grant: Dict[str, Any], *patterns: str) -> Dict[str, Any]:
    g = dict(grant)
    c = dict(g.get("constraints") or {})
    c["allowed_resources"] = list(patterns)
    g["constraints"] = c
    return g


def _t(
    tid: str,
    name: str,
    category: str,
    tagline: str,
    permissions: List[Dict[str, Any]],
    *,
    icon: str = "Bot",
    description: str = "",
) -> Dict[str, Any]:
    return {
        "id": tid,
        "name": name,
        "category": category,
        "tagline": tagline,
        "description": description or tagline,
        "icon": icon,
        "permissions": permissions,
    }


# ---------------------------------------------------------------------------
# Agent template library
# ---------------------------------------------------------------------------
AGENT_TEMPLATES: List[Dict[str, Any]] = [
    # ---------------- Personal & Productivity ----------------
    _t("personal-assistant", "Personal Assistant", "Personal & Productivity",
       "Manages calendar, tasks and light email on your behalf.",
       [allow("calendar.read"), allow("calendar.write"), allow("email.read"),
        rate_limited("email.send", 25), allow("tasks.read"), allow("tasks.write"),
        allow("contacts.read"), allow("notes.write"),
        blocked("payments.read"), blocked("account.password.write"), blocked("email.delete")],
       icon="CalendarClock"),
    _t("email-triage", "Email Triage Agent", "Personal & Productivity",
       "Reads and classifies inbox; drafts need approval before sending.",
       [allow("email.read"), needs_approval("email.send"), allow("tasks.write"), allow("notes.write"),
        blocked("email.delete"), blocked("payments.read")], icon="Inbox"),
    _t("meeting-scheduler", "Meeting Scheduler", "Personal & Productivity",
       "Finds slots and books meetings with internal and external guests.",
       [allow("calendar.read"), allow("calendar.write"), allow("contacts.read"),
        rate_limited("email.send", 40), blocked("contacts.write")], icon="CalendarPlus"),
    _t("note-summarizer", "Note Summarizer", "Personal & Productivity",
       "Turns meeting notes and documents into summaries.",
       [allow("notes.read"), allow("notes.write"), allow("docs.read"), blocked("docs.write")], icon="NotebookPen"),
    _t("task-manager", "Task Manager Agent", "Personal & Productivity",
       "Keeps your task backlog groomed and deadlines aligned to your calendar.",
       [allow("tasks.read"), allow("tasks.write"), allow("calendar.read"), allow("notes.read")], icon="ListChecks"),
    _t("inbox-cleanup", "Inbox Cleanup Agent", "Personal & Productivity",
       "Archives clutter; every deletion requires a human decision.",
       [allow("email.read"), needs_approval("email.delete"), allow("notes.write"), blocked("email.send")], icon="Trash2"),

    # ---------------- Commerce ----------------
    _t("shopping-agent", "Shopping Agent", "Commerce",
       "Searches products and buys under $100; larger purchases need approval.",
       [allow("shopping.search"), allow("shopping.cart"),
        limited("shopping.purchase", 100, hard_max_amount=5000),
        blocked("payments.read"), blocked("payments.create"), blocked("account.password.write")],
       icon="ShoppingCart"),
    _t("procurement-agent", "Procurement Agent", "Commerce",
       "Raises purchase orders against approved vendors with a hard spend ceiling.",
       [allow("inventory.read"), allow("shopping.search"), limited("shopping.purchase", 2500, hard_max_amount=25000),
        needs_approval("invoices.create"), allow("invoices.read"), blocked("payments.read"), blocked("invoices.pay")],
       icon="Package"),
    _t("invoice-matcher", "Invoice Matching Agent", "Commerce",
       "Reconciles invoices against purchase orders. Read-only on money.",
       [allow("invoices.read"), scoped(allow("files.read"), "finance/invoices/*"), allow("analytics.read"),
        blocked("invoices.pay"), blocked("payments.read")], icon="ReceiptText"),
    _t("price-monitor", "Price Monitor Agent", "Commerce",
       "Watches competitor pricing and reports changes.",
       [allow("web.search"), allow("web.fetch"), allow("shopping.search"), allow("notes.write"),
        blocked("shopping.purchase")], icon="TrendingUp"),
    _t("returns-agent", "Returns & Refunds Agent", "Commerce",
       "Handles return requests and issues small refunds automatically.",
       [allow("support.ticket.read"), allow("support.ticket.write"),
        limited("support.refund.issue", 200, hard_max_amount=2000), blocked("payments.read")], icon="Undo2"),
    _t("subscription-manager", "Subscription Manager", "Commerce",
       "Tracks recurring spend; any renewal change requires approval.",
       [allow("invoices.read"), allow("analytics.read"), needs_approval("shopping.purchase"),
        blocked("payments.read")], icon="RefreshCw"),

    # ---------------- Travel ----------------
    _t("travel-agent", "Travel Booking Agent", "Travel",
       "Searches and books trips within policy; expensive fares need approval.",
       [allow("travel.search"), limited("travel.book", 750, hard_max_amount=10000),
        needs_approval("travel.cancel"), allow("calendar.write"), rate_limited("email.send", 20),
        blocked("payments.read")], icon="Plane"),
    _t("itinerary-manager", "Itinerary Manager", "Travel",
       "Keeps trip details, calendar and travellers in sync.",
       [allow("travel.search"), allow("calendar.read"), allow("calendar.write"),
        rate_limited("email.send", 30), blocked("travel.book")], icon="Map"),
    _t("travel-expense", "Travel Expense Reconciler", "Travel",
       "Matches travel receipts to expense reports.",
       [allow("invoices.read"), scoped(allow("files.read"), "expenses/*"), allow("analytics.read"),
        blocked("payments.read")], icon="Wallet"),

    # ---------------- Research ----------------
    _t("research-agent", "Research Agent", "Research",
       "Gathers and summarises public information into internal notes.",
       [allow("web.search"), allow("web.fetch"), allow("notes.write"),
        scoped(allow("files.read"), "research/*"), allow("docs.write"),
        blocked("files.write"), blocked("crm.export")], icon="Microscope"),
    _t("literature-review", "Literature Review Agent", "Research",
       "Reviews internal documents and builds a cited synthesis.",
       [allow("docs.read"), allow("docs.write"), allow("web.search"), blocked("files.delete")], icon="BookOpen"),
    _t("competitive-intel", "Competitive Intel Agent", "Research",
       "Tracks competitors across the web and your CRM.",
       [allow("web.search"), allow("web.fetch"), allow("crm.read"), allow("analytics.read"),
        allow("docs.write"), blocked("crm.export")], icon="Radar"),
    _t("market-data", "Market Data Agent", "Research",
       "Pulls market data into read-only analytics workflows.",
       [allow("web.fetch"), allow("analytics.read"), scoped(allow("database.read"), "market/*"),
        blocked("database.write")], icon="LineChart"),

    # ---------------- Finance ----------------
    _t("expense-auditor", "Expense Auditor", "Finance",
       "Flags policy-violating expenses. Cannot move money.",
       [allow("invoices.read"), allow("analytics.read"), scoped(allow("files.read"), "finance/*"),
        allow("messaging.send"), blocked("payments.read"), blocked("payments.create")], icon="ShieldCheck"),
    _t("payment-initiator", "Payment Initiator", "Finance",
       "Prepares payments up to a strict cap; credentials always blocked.",
       [allow("invoices.read"), limited("payments.create", 500, hard_max_amount=5000),
        blocked("payments.read"), blocked("secrets.read")], icon="Banknote"),
    _t("payroll-assistant", "Payroll Assistant", "Finance",
       "Prepares payroll runs for human execution.",
       [allow("hr.read"), scoped(allow("files.read"), "payroll/*"), allow("analytics.read"),
        blocked("payments.create"), blocked("payments.read"), blocked("hr.write")], icon="Users"),
    _t("budget-monitor", "Budget Monitor", "Finance",
       "Watches burn rate and alerts owners.",
       [allow("analytics.read"), allow("invoices.read"), allow("messaging.send"),
        blocked("payments.create")], icon="PieChart"),

    # ---------------- Engineering / DevOps ----------------
    _t("ci-assistant", "CI Assistant", "Engineering",
       "Fixes failing builds; code changes need review, deploys are blocked.",
       [allow("code.read"), needs_approval("code.write"), allow("infra.read"),
        allow("messaging.send"), blocked("code.deploy"), blocked("infra.delete")], icon="GitBranch"),
    _t("incident-response", "Incident Response Agent", "Engineering",
       "Diagnoses incidents; restarts require a human in the loop.",
       [allow("infra.read"), needs_approval("infra.restart"), scoped(allow("database.read"), "logs/*"),
        allow("messaging.send"), blocked("infra.delete"), blocked("database.delete")], icon="Siren"),
    _t("code-review", "Code Review Agent", "Engineering",
       "Reviews pull requests and writes review notes only.",
       [allow("code.read"), allow("docs.write"), allow("messaging.send"),
        blocked("code.write"), blocked("code.deploy")], icon="Code2"),
    _t("release-manager", "Release Manager", "Engineering",
       "Coordinates releases; every production deploy needs approval.",
       [allow("code.read"), needs_approval("code.deploy"), allow("infra.read"), allow("messaging.send"),
        blocked("infra.delete")], icon="Rocket"),
    _t("cost-optimizer", "Infra Cost Optimizer", "Engineering",
       "Finds waste in cloud spend. Never destroys resources.",
       [allow("infra.read"), allow("analytics.read"), allow("docs.write"),
        blocked("infra.delete"), blocked("infra.restart")], icon="Gauge"),

    # ---------------- Sales / CRM ----------------
    _t("lead-enrichment", "Lead Enrichment Agent", "Sales & CRM",
       "Enriches inbound leads from public sources. Bulk export blocked.",
       [allow("crm.read"), allow("crm.write"), allow("web.search"), allow("web.fetch"),
        blocked("crm.export")], icon="UserPlus"),
    _t("outreach-agent", "Outreach Agent", "Sales & CRM",
       "Sends sequenced outreach with a daily send ceiling.",
       [allow("crm.read"), rate_limited("email.send", 100), allow("contacts.read"),
        blocked("crm.export"), blocked("email.delete")], icon="Send"),
    _t("deal-desk", "Deal Desk Agent", "Sales & CRM",
       "Assembles quotes and contract packets for review.",
       [allow("crm.read"), allow("docs.read"), allow("legal.contract.read"),
        needs_approval("invoices.create"), blocked("legal.contract.write")], icon="FileSignature"),
    _t("crm-hygiene", "CRM Hygiene Agent", "Sales & CRM",
       "De-duplicates and normalises CRM records.",
       [allow("crm.read"), allow("crm.write"), blocked("crm.export")], icon="Sparkles"),

    # ---------------- Support ----------------
    _t("ticket-triage", "Ticket Triage Agent", "Support",
       "Classifies and routes incoming support tickets.",
       [allow("support.ticket.read"), allow("support.ticket.write"), allow("crm.read"),
        blocked("support.refund.issue")], icon="Headphones"),
    _t("refund-agent", "Refund Approval Agent", "Support",
       "Issues goodwill refunds up to $100 automatically.",
       [allow("support.ticket.read"), limited("support.refund.issue", 100, hard_max_amount=1000),
        allow("crm.read"), blocked("payments.read")], icon="BadgeDollarSign"),
    _t("knowledge-base", "Knowledge Base Agent", "Support",
       "Keeps help-centre articles accurate from resolved tickets.",
       [allow("docs.read"), allow("docs.write"), allow("support.ticket.read"),
        blocked("files.delete")], icon="Library"),

    # ---------------- Marketing ----------------
    _t("campaign-assistant", "Campaign Assistant", "Marketing",
       "Builds campaigns and spends a capped ad budget.",
       [allow("analytics.read"), allow("docs.write"), needs_approval("social.post"),
        limited("ads.spend", 250, hard_max_amount=5000), allow("ads.read")], icon="Megaphone"),
    _t("social-scheduler", "Social Scheduler", "Marketing",
       "Queues social content; publishing always needs a human.",
       [needs_approval("social.post"), scoped(allow("files.read"), "brand/*"), allow("calendar.read"),
        blocked("ads.spend")], icon="Share2"),
    _t("seo-content", "SEO Content Agent", "Marketing",
       "Researches keywords and drafts content.",
       [allow("web.search"), allow("web.fetch"), allow("docs.write"), allow("analytics.read")], icon="Search"),

    # ---------------- HR & Recruiting ----------------
    _t("candidate-screening", "Candidate Screening Agent", "HR & Recruiting",
       "Screens applications against role requirements.",
       [allow("hr.read"), scoped(allow("files.read"), "recruiting/*"),
        rate_limited("email.send", 50), blocked("hr.write"), blocked("identity.role.write")],
       icon="UserSearch"),
    _t("onboarding-agent", "Onboarding Agent", "HR & Recruiting",
       "Provisions new hires; privilege grants always need approval.",
       [allow("identity.user.read"), needs_approval("identity.user.write"), allow("calendar.write"),
        rate_limited("email.send", 30), blocked("identity.role.write"),
        blocked("account.password.write")], icon="IdCard"),
    _t("hr-policy-assistant", "HR Policy Assistant", "HR & Recruiting",
       "Answers policy questions from approved documents only.",
       [allow("docs.read"), allow("notes.write"), blocked("hr.read"), blocked("hr.write")], icon="BookMarked"),

    # ---------------- Legal & Compliance ----------------
    _t("contract-review", "Contract Review Agent", "Legal & Compliance",
       "Reviews contracts and flags risky clauses. Cannot sign.",
       [allow("legal.contract.read"), allow("docs.write"), allow("notes.write"),
        blocked("legal.contract.write")], icon="Scale"),
    _t("compliance-monitor", "Compliance Monitor", "Legal & Compliance",
       "Continuously checks controls and reports drift.",
       [allow("analytics.read"), scoped(allow("files.read"), "compliance/*"), allow("docs.write"),
        allow("messaging.send"), blocked("files.write")], icon="ClipboardCheck"),

    # ---------------- Data & Analytics ----------------
    _t("report-generator", "Report Generator", "Data & Analytics",
       "Builds recurring reports; exports require approval.",
       [allow("analytics.read"), needs_approval("analytics.export"), allow("docs.write"),
        scoped(allow("database.read"), "warehouse/*"), blocked("database.write")], icon="BarChart3"),
    _t("data-pipeline", "Data Pipeline Agent", "Data & Analytics",
       "Runs ETL jobs. Destructive operations are blocked.",
       [allow("database.read"), needs_approval("database.write"), allow("infra.read"),
        blocked("database.delete")], icon="Workflow"),

    # ---------------- IT Operations ----------------
    _t("access-request", "Access Request Agent", "IT Operations",
       "Collects access requests; privilege changes need approval.",
       [allow("identity.user.read"), needs_approval("identity.role.write"), allow("messaging.send"),
        blocked("account.password.write"), blocked("secrets.read")], icon="KeyRound"),
    _t("device-compliance", "Device Compliance Agent", "IT Operations",
       "Audits endpoint compliance and nudges owners.",
       [allow("infra.read"), allow("identity.user.read"), allow("messaging.send"),
        blocked("account.settings.write")], icon="Laptop"),

    # ---------------- Healthcare admin ----------------
    _t("clinic-scheduling", "Clinic Scheduling Agent", "Healthcare Admin",
       "Books appointments without ever touching clinical records.",
       [allow("calendar.read"), allow("calendar.write"), allow("contacts.read"),
        limited("sms.send", 50), blocked("health.record.read")], icon="Stethoscope"),
    _t("claims-assistant", "Insurance Claims Assistant", "Healthcare Admin",
       "Prepares claim paperwork from billing data only.",
       [allow("invoices.read"), scoped(allow("files.read"), "billing/*"), allow("docs.write"),
        blocked("health.record.read"), blocked("payments.read")], icon="FileHeart"),

    # ---------------- Education ----------------
    _t("course-assistant", "Course Assistant", "Education",
       "Answers student questions from course material.",
       [allow("docs.read"), allow("docs.write"), allow("calendar.read"),
        rate_limited("email.send", 60)], icon="GraduationCap"),
    _t("grading-assistant", "Grading Assistant", "Education",
       "Drafts feedback on submissions for instructor review.",
       [scoped(allow("files.read"), "submissions/*"), allow("docs.write"), allow("identity.user.read"),
        blocked("identity.user.write")], icon="PenLine"),

    # ---------------- Operations ----------------
    _t("company-ops", "Company Operations Agent", "Operations",
       "Runs internal ops across documents, calendars and vendors.",
       [scoped(allow("files.read"), "company/public/*", "company/ops/*"), allow("docs.read"),
        allow("docs.write"), allow("calendar.read"), allow("messaging.send"), allow("invoices.read"),
        blocked("payments.read"), blocked("account.password.write"), blocked("hr.read")], icon="Building2"),
    _t("vendor-management", "Vendor Management Agent", "Operations",
       "Tracks vendors, renewals and contract dates.",
       [allow("crm.read"), allow("legal.contract.read"), needs_approval("invoices.create"),
        allow("messaging.send"), blocked("invoices.pay")], icon="Handshake"),
    _t("facilities-agent", "Facilities Agent", "Operations",
       "Handles office supplies with a small spend cap.",
       [allow("calendar.write"), allow("shopping.search"), limited("shopping.purchase", 150, hard_max_amount=1500),
        allow("messaging.send"), blocked("payments.read")], icon="Wrench"),
    _t("custom-agent", "Custom Agent", "Custom",
       "Starts locked down with zero permissions. You grant exactly what it needs.",
       [], icon="SlidersHorizontal",
       description="Default-deny starting point. The agent can do nothing until you explicitly grant permissions."),
]

TEMPLATE_BY_ID: Dict[str, Dict[str, Any]] = {t["id"]: t for t in AGENT_TEMPLATES}
TEMPLATE_CATEGORIES = []
for _tpl in AGENT_TEMPLATES:
    if _tpl["category"] not in TEMPLATE_CATEGORIES:
        TEMPLATE_CATEGORIES.append(_tpl["category"])

# Templates deployed for a brand new organization so the workspace is usable immediately.
STARTER_TEMPLATE_IDS = [
    "personal-assistant",
    "shopping-agent",
    "travel-agent",
    "research-agent",
    "company-ops",
]


# ---------------------------------------------------------------------------
# Built-in organization policies
# ---------------------------------------------------------------------------
SYSTEM_POLICIES: List[Dict[str, Any]] = [
    {
        "slug": "deny-payment-credentials",
        "name": "Never allow agents to access payment credentials",
        "description": "Stored cards, bank details, payment tokens and API secrets are never readable by an agent.",
        "effect": "DENY",
        "priority": 10,
        "match": {"permissions": ["payments.read", "secrets.read"], "agents": ["*"], "resources": ["*"]},
        "params": {},
        "system": True,
        "enabled": True,
    },
    {
        "slug": "deny-password-change",
        "name": "Agents cannot modify passwords",
        "description": "No agent may change an account password or reset credentials.",
        "effect": "DENY",
        "priority": 11,
        "match": {"permissions": ["account.password.write"], "agents": ["*"], "resources": ["*"]},
        "params": {},
        "system": True,
        "enabled": True,
    },
    {
        "slug": "approval-over-100",
        "name": "Purchases above $100 require approval",
        "description": "Any spend action over $100 is escalated to a human approver before it can proceed.",
        "effect": "REQUIRE_APPROVAL",
        "priority": 20,
        "match": {
            "permissions": ["shopping.purchase", "travel.book", "payments.create", "invoices.pay", "ads.spend"],
            "agents": ["*"],
            "resources": ["*"],
            "amount_gt": 100,
        },
        "params": {},
        "system": True,
        "enabled": True,
    },
    {
        "slug": "temporary-file-access",
        "name": "Temporary file access expires after 60 minutes",
        "description": "File grants marked temporary are automatically clamped to a 60 minute lifetime.",
        "effect": "MAX_TTL",
        "priority": 30,
        "match": {"permissions": ["files.read", "files.write", "files.share"], "agents": ["*"], "resources": ["*"]},
        "params": {"max_ttl_minutes": 60},
        "system": True,
        "enabled": True,
    },
    {
        "slug": "explicit-file-scope",
        "name": "Agents can only access files explicitly granted to them",
        "description": "File access without an explicit resource scope is denied — no implicit access to the whole drive.",
        "effect": "REQUIRE_SCOPE",
        "priority": 31,
        "match": {"permissions": ["files.read", "files.write", "files.delete", "files.share"], "agents": ["*"], "resources": ["*"]},
        "params": {},
        "system": True,
        "enabled": True,
    },
    {
        "slug": "deny-destructive-infra",
        "name": "Agents cannot destroy infrastructure or data",
        "description": "Destructive infrastructure and database operations are always denied.",
        "effect": "DENY",
        "priority": 12,
        "match": {"permissions": ["infra.delete", "database.delete"], "agents": ["*"], "resources": ["*"]},
        "params": {},
        "system": True,
        "enabled": True,
    },
    {
        "slug": "approval-bulk-export",
        "name": "Bulk data export requires approval",
        "description": "Exporting customer or analytics data in bulk always escalates to a human.",
        "effect": "REQUIRE_APPROVAL",
        "priority": 21,
        "match": {"permissions": ["crm.export", "analytics.export"], "agents": ["*"], "resources": ["*"]},
        "params": {},
        "system": True,
        "enabled": True,
    },
]

POLICY_EFFECTS = ("DENY", "REQUIRE_APPROVAL", "LIMIT", "MAX_TTL", "REQUIRE_SCOPE")
