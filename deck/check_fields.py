#!/usr/bin/env python3
"""Character-limit check for the Emergent Ventures form fields."""

FIELDS = {
    "one_liner": (100, """The permission layer for AI agents — for any team whose agents can spend money on their behalf."""),

    "team_1000": (1000, """It is one person: me. No co-founder, no employees. I would rather say that plainly than dress a solo project up as a team.

Have I worked with others? Yes. As COO of The1550Formula I ran ops with a founder and small team to ~$70,000/month and 1,000+ students. I founded PythonPal, a nonprofit that has taught 100+ students, so I have recruited and led volunteers, and I run HorizonSTEM workshops for 150 more.

Why this team now: Vexen is one tightly-coupled guarantee - engine, approval invariants, SDK and audit must agree, because a gap between any two is a vulnerability. Holding that in one head is an advantage now. It is also my sixth product; the previous five reached 100,000+ users with no marketing budget, so "will he ship" is well evidenced.

The gap: I have never sold security through enterprise procurement. Hire 1: a founding engineer from IAM, fraud or payments to own the credential broker. Hire 2: GTM, to run design partners. No formal advisors yet - what I most want here."""),

    "anything_else_v2": (1000, """Three things.

1. The version I care about. The small Vexen is a B2B tool that stops agents overspending. The version I want is an open standard: every team is inventing agent permissions differently, so nothing carries across systems and a regulator has no vocabulary to point at. Identity got OAuth; payments got card network rules; agent authority has nothing, and that window is open now. I would rather build the reference implementation of an open standard than own a closed one.

2. How to judge me. Not the deck. Point a real agent at it and confirm the blocked side effect never happened. Try to replay, escalate or forge an approval. Hand the console to a non-engineer. Alter an audit row and watch the integrity check catch it. Take the service offline and confirm the guarded call refuses to run.

3. The honest ledger. No revenue, Python-only SDK, no SOC 2, credential broker designed but unbuilt. Every product before this was built in the gaps. Vexen is the first I want full-time."""),

    "description": (800, """AI agents now hold real credentials. They spend money, refund customers, email clients and delete files. Their limits live in prompts — "never spend more than $100" — which are suggestions, not permissions. Nothing external checks them, and when something goes wrong nobody can answer "who allowed this?" in under an hour.

Vexen is the permission and approval layer. One API call answers "is this specific agent allowed to do this specific thing, right now?" and returns ALLOW, BLOCK or ASK A HUMAN — deterministically, with no model in the enforcement path. If a human is needed the agent halts and the accountable person approves in two taps on their phone, no login. Every decision is written to a hash-verified audit record.

Live, built solo in two months, past 5,000 users."""),

    "anything_else": (1000, """Vexen is my sixth product. The previous five reached 100,000+ users with no marketing budget: HealthLens, an AI wellness platform (70,000+); AI-Namo, AI document verification adopted by a local government for fraud prevention (20,000+); GreenGuide, an agricultural copilot (10,000+); CerebroAegis, health and safety (5,000+). As COO of The1550Formula, an AI test-prep company, I helped run it to ~$70,000/month with 1,000+ students gaining ~200 SAT points.

Two things make this credible rather than a claim. The hard invariants are done: single-use, TTL-bound, atomically-claimed, scope-bound approvals; POST-only signed email links so a link scanner cannot approve on your behalf; SHA-256 hash-verified audit; a fail-closed SDK. And it is verified — 55/55 end-to-end regression checks, plus an independent 110/110 backend pass, no critical defects.

Where I am weak: no revenue, and I have never sold security through an enterprise procurement cycle. That is hire #1."""),

    "traction_notes": (1000, """5,000+ users in two months, built solo, no paid acquisition — content-led, the same way my previous products reached 100,000+ users between them.

What matters more than the count is the sequence. Users deploy a configuration from the 10,639-template library, test a rule they wrote in plain English, then go looking for the SDK. That sequence ends in production traffic, which is what makes this sticky.

The most common request is not more permissions. It is TypeScript, native framework guards, and "can I stop the agent bypassing this at all?" — a request for the credential broker on the roadmap. Users are pulling the product toward its more defensible version.

Shipped: 67 permissions, 10,639 configurations, the deterministic 13-step engine, hash-verified audit, two-tap phone approvals, a fail-closed Python SDK, four-role RBAC. Verified by 55/55 regression checks and an independent 110/110 backend pass.

No revenue yet. No SOC 2. Credential broker designed, not built."""),
}

print(f"{'field':<18} {'used':>6} {'limit':>6} {'left':>6}   status")
print("-" * 58)
ok = True
for name, (limit, text) in FIELDS.items():
    n = len(text)
    left = limit - n
    status = "OK" if left >= 0 else "OVER LIMIT"
    if left < 0:
        ok = False
    print(f"{name:<18} {n:>6} {limit:>6} {left:>6}   {status}")
print("-" * 58)
print("all fields fit" if ok else "FIX REQUIRED")
