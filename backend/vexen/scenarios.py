"""
Simulator scenarios.

Every step here is a real authorization request. The simulator does not fake any
outcome: it posts each step through the same engine the public API uses, and the
UI renders whatever the engine decides.
"""
from __future__ import annotations

from typing import Any, Dict, List

SCENARIOS: List[Dict[str, Any]] = [
    {
        "id": "shopping-demo",
        "name": "Shopping Agent buys a laptop",
        "template_id": "shopping-agent",
        "agent_name": "Shopping Agent",
        "featured": True,
        "summary": "The flagship walk-through: two allowed actions, one spend that needs your approval, "
                   "and one hard block on payment credentials.",
        "expected": "2 allowed / 1 approval required / 1 blocked / $0 unauthorized spend",
        "steps": [
            {"label": "Searching products for \u201claptop\u201d", "detail": "shopping.search",
             "resource": "shopping", "action": "search", "resource_id": "laptop"},
            {"label": "Adding MacBook Pro 14\u201d to cart", "detail": "shopping.cart",
             "resource": "shopping", "action": "cart", "resource_id": "sku-mbp14-1249"},
            {"label": "Attempting purchase: $1,249.00", "detail": "shopping.purchase",
             "resource": "shopping", "action": "purchase", "resource_id": "sku-mbp14-1249",
             "amount": 1249.0},
            {"label": "Reading saved payment credentials", "detail": "payments.read",
             "resource": "payments", "action": "read", "resource_id": "card-primary"},
        ],
    },
    {
        "id": "assistant-day",
        "name": "Personal Assistant runs your morning",
        "template_id": "personal-assistant",
        "agent_name": "Personal Assistant",
        "summary": "Reads your calendar and inbox, sends a reply, then tries to change your password.",
        "expected": "3 allowed / 1 blocked",
        "steps": [
            {"label": "Reading today\u2019s calendar", "detail": "calendar.read",
             "resource": "calendar", "action": "read", "resource_id": "primary"},
            {"label": "Reading unread email", "detail": "email.read",
             "resource": "email", "action": "read", "resource_id": "inbox"},
            {"label": "Sending a reply to the 10am invite", "detail": "email.send",
             "resource": "email", "action": "send", "resource_id": "thread-8821"},
            {"label": "Attempting to change the account password", "detail": "account.password.write",
             "resource": "account.password", "action": "write", "resource_id": "self"},
        ],
    },
    {
        "id": "research-files",
        "name": "Research Agent reaches outside its scope",
        "template_id": "research-agent",
        "agent_name": "Research Agent",
        "summary": "Searches the web and reads a granted research file, then tries to open HR salary data.",
        "expected": "3 allowed / 1 blocked",
        "steps": [
            {"label": "Searching the web for market sizing", "detail": "web.search",
             "resource": "web", "action": "search", "resource_id": "ai-agent-market-2026"},
            {"label": "Reading research/market-brief.pdf", "detail": "files.read",
             "resource": "files", "action": "read", "resource_id": "research/market-brief.pdf"},
            {"label": "Writing a summary document", "detail": "docs.write",
             "resource": "docs", "action": "write", "resource_id": "docs/market-summary"},
            {"label": "Reading hr/salaries-2026.xlsx", "detail": "files.read",
             "resource": "files", "action": "read", "resource_id": "hr/salaries-2026.xlsx"},
        ],
    },
    {
        "id": "travel-booking",
        "name": "Travel Agent books a trip",
        "template_id": "travel-agent",
        "agent_name": "Travel Booking Agent",
        "summary": "Books an in-policy flight, then a business-class fare that breaches the limit.",
        "expected": "2 allowed / 1 approval required / 1 blocked",
        "steps": [
            {"label": "Searching flights SFO \u2192 LHR", "detail": "travel.search",
             "resource": "travel", "action": "search", "resource_id": "sfo-lhr-2026-04-11"},
            {"label": "Booking economy fare: $612.00", "detail": "travel.book",
             "resource": "travel", "action": "book", "resource_id": "flight-BA286-eco", "amount": 612.0},
            {"label": "Booking business fare: $3,480.00", "detail": "travel.book",
             "resource": "travel", "action": "book", "resource_id": "flight-BA286-biz", "amount": 3480.0},
            {"label": "Reading the stored corporate card", "detail": "payments.read",
             "resource": "payments", "action": "read", "resource_id": "card-corporate"},
        ],
    },
    {
        "id": "finance-payments",
        "name": "Payment Initiator moves money",
        "template_id": "payment-initiator",
        "agent_name": "Payment Initiator",
        "summary": "Sensitive money movement: even an in-limit payment escalates to a human.",
        "expected": "1 allowed / 1 approval required / 2 blocked",
        "steps": [
            {"label": "Reading invoice INV-2291", "detail": "invoices.read",
             "resource": "invoices", "action": "read", "resource_id": "INV-2291"},
            {"label": "Initiating payment: $480.00", "detail": "payments.create",
             "resource": "payments", "action": "create", "resource_id": "INV-2291", "amount": 480.0},
            {"label": "Initiating payment: $9,400.00", "detail": "payments.create",
             "resource": "payments", "action": "create", "resource_id": "INV-2404", "amount": 9400.0},
            {"label": "Reading stored bank credentials", "detail": "payments.read",
             "resource": "payments", "action": "read", "resource_id": "bank-primary"},
        ],
    },
    {
        "id": "devops-incident",
        "name": "Incident Response Agent during an outage",
        "template_id": "incident-response",
        "agent_name": "Incident Response Agent",
        "summary": "Reads infrastructure state, asks to restart a service, then tries to delete a cluster.",
        "expected": "2 allowed / 1 approval required / 1 blocked",
        "steps": [
            {"label": "Reading service health for api-gateway", "detail": "infra.read",
             "resource": "infra", "action": "read", "resource_id": "api-gateway"},
            {"label": "Posting an incident update to #ops", "detail": "messaging.send",
             "resource": "messaging", "action": "send", "resource_id": "channel-ops"},
            {"label": "Requesting restart of api-gateway", "detail": "infra.restart",
             "resource": "infra", "action": "restart", "resource_id": "api-gateway"},
            {"label": "Attempting to delete the staging cluster", "detail": "infra.delete",
             "resource": "infra", "action": "delete", "resource_id": "cluster-staging"},
        ],
    },
    {
        "id": "support-refunds",
        "name": "Refund Agent handles two refunds",
        "template_id": "refund-agent",
        "agent_name": "Refund Approval Agent",
        "summary": "A small goodwill refund clears automatically; a large one needs a human.",
        "expected": "2 allowed / 1 approval required / 1 blocked",
        "steps": [
            {"label": "Reading ticket #48120", "detail": "support.ticket.read",
             "resource": "support.ticket", "action": "read", "resource_id": "48120"},
            {"label": "Issuing refund: $42.00", "detail": "support.refund.issue",
             "resource": "support.refund", "action": "issue", "resource_id": "48120", "amount": 42.0},
            {"label": "Issuing refund: $860.00", "detail": "support.refund.issue",
             "resource": "support.refund", "action": "issue", "resource_id": "48121", "amount": 860.0},
            {"label": "Reading the customer\u2019s stored card", "detail": "payments.read",
             "resource": "payments", "action": "read", "resource_id": "card-cust-9931"},
        ],
    },
    {
        "id": "ops-company",
        "name": "Company Operations Agent audits vendors",
        "template_id": "company-ops",
        "agent_name": "Company Operations Agent",
        "summary": "Works inside its granted file scope, then reaches for payroll and credentials.",
        "expected": "2 allowed / 2 blocked",
        "steps": [
            {"label": "Reading company/ops/vendor-list.csv", "detail": "files.read",
             "resource": "files", "action": "read", "resource_id": "company/ops/vendor-list.csv"},
            {"label": "Reading open invoices", "detail": "invoices.read",
             "resource": "invoices", "action": "read", "resource_id": "open"},
            {"label": "Reading payroll/2026-q1.xlsx", "detail": "files.read",
             "resource": "files", "action": "read", "resource_id": "payroll/2026-q1.xlsx"},
            {"label": "Reading stored payment credentials", "detail": "payments.read",
             "resource": "payments", "action": "read", "resource_id": "card-primary"},
        ],
    },
]

SCENARIO_BY_ID: Dict[str, Dict[str, Any]] = {s["id"]: s for s in SCENARIOS}
