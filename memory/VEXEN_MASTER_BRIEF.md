# VEXEN — MASTER BRIEF
Single source of truth. Every number below was verified against source code or an
existing submission document on the date this file was written. Nothing here is
estimated unless explicitly labelled.

---

## 0. THE FAST FACTS TABLE (for form fields)

| Field | Value |
| --- | --- |
| Name | Vexen |
| One-liner (95 chars) | The permission layer for AI agents - for any team whose agents can spend money on their behalf. |
| Category (primary) | Infrastructure / Developer Tools |
| Category (secondary) | Security / Cybersecurity |
| Stage | Pre-seed |
| Raise amount | $750,000 |
| Instrument | Post-money SAFE |
| Valuation cap | $8,000,000 post-money (comfortable $7–10M) |
| Previously raised | $0 |
| VC-backed | No |
| Investors | None |
| MRR / ARR | $0 (pre-revenue by choice) |
| Monthly burn | ~$200 |
| Cash on hand | $50,000 (founder-contributed) |
| Runway | 250 months at current burn (i.e. not a constraint) |
| Post-raise runway | ~20 months for a 3-person team |
| Team size | 1 (solo founder) |
| Employees / contractors | 0 |
| Incorporated | Not yet — Delaware C-corp intended at/before first financing |
| Registered users | 5,000+ |
| Time to build | 2 months, solo |
| Paid acquisition | $0 |
| Founded | June 2026 (CONFIRM) |
| Product launch | July 2026 (CONFIRM) |
| Live product | https://action-guard-1.preview.emergentagent.com |
| Demo video | https://youtu.be/V5SaKRhMmcM |
| Dilution at $750K/$8M | Founder 90.63% / investors 9.37% |

---

## 1. WHAT VEXEN IS

**One sentence:** Vexen is the permission and approval layer for AI agents — a
single API call that answers "is this specific agent allowed to do this specific
thing right now?" with ALLOW, BLOCK or ASK A HUMAN, and that genuinely stops the
action when the answer is no.

**The core API:**

```
POST /api/v1/authorize
X-Vexen-Key: <the agent's own key>

{ "resource": "shopping", "action": "purchase",
  "amount": 742.50, "currency": "USD", "resource_id": "order-4471" }
```

Returns exactly three decisions: **ALLOW**, **BLOCK**, **APPROVAL_REQUIRED** —
each with a machine-readable reason code, a human-readable reason, and a full
13-step evaluation trace.

---

## 2. THE PROBLEM

For two years AI could only talk. The blast radius of a mistake was
embarrassment. That era is over — agents now hold API keys. They place orders,
move money, refund customers, send email, write to production databases, book
travel, delete files. The blast radius is now your bank balance, your customer
relationships and your compliance posture.

The tooling did not keep up. The typical production agent holds a long-lived key
with roughly an employee's scope. Its constraints live in the prompt — "never
spend more than $100" — where they are advisory rather than enforced, **because a
prompt is not a permission.**

### Three failure modes

1. **The confident mistake.** Not attacked, not jailbroken — just wrong. Buys 500
   units instead of 5 because a price was per-case not per-item. Refunds twice
   because the first refund had not settled. Most common failure, almost entirely
   preventable with limits, and ignored by current tooling because it is not a
   safety or content problem — it is an authorization problem.
2. **The manipulated agent.** Indirect prompt injection: a malicious instruction
   hidden in a web page, PDF or support ticket. Every published model-layer
   defence has been bypassed. The only durable answer is the one we reached for
   human employees decades ago — the actor does not decide the limits of its own
   authority.
3. **The accountability vacuum.** Even when nothing goes wrong, teams cannot
   answer what an auditor, board or insurer asks: what is this agent permitted to
   do right now, what did it attempt, who approved the exception on the 14th, and
   can you prove the record was not edited. Without those answers agents stay
   stuck in pilots. The blocker is not model capability. It is governance.

### The framing line
> You cannot verify intent. You can only constrain consequence.

A bank teller can be completely honest and still not be permitted to move ten
million dollars alone. We never made humans trustworthy — we constrained them
with spending authority, dual control, segregation of duties and audit trails.

### The historical argument
Every computing generation grows a permission layer:
mainframes → RACF. Networks → Active Directory. Cloud → IAM. SaaS identity →
Okta. **Agents have nothing.** That gap opened about a year ago and widens every
week as more agents get more keys.

---

## 3. WHY EXISTING TOOLS DON'T COVER IT

| Category | Why it fails |
| --- | --- |
| **Cloud IAM** (AWS IAM, GCP, Okta, Entra) | Authorises a *principal* against a *resource*, statically. Cannot express "up to $100 per transaction, only these SKUs, only for 4 hours, above that Sarah says yes." No per-action amount, no human-in-the-loop primitive, no expiring approval. Sits at the infrastructure boundary, not the business-action boundary. |
| **Guardrail / safety libraries** | Inspect *text* — toxicity, PII, off-brand. Orthogonal. A polite, on-brand, PII-clean message that wires $40,000 to the wrong account passes every guardrail in the category. |
| **Observability** (LangSmith, Langfuse, Braintrust, W&B) | Read-only and after the fact. Does not stand between agent and action. "Observability is the flight recorder. We are the flight control." |
| **Framework human-in-the-loop** | Closest neighbour, right idea, wrong place. The interrupt lives *inside the agent process*: the agent decides when to ask, the pause dies if the process dies, approval is a value in memory not a record, no audit trail, non-technical approvers cannot participate, framework-specific, and a compromised agent can simply not interrupt. Asking the agent to police itself is the problem restated. |
| **Policy engines** (OPA, Cedar) | Block actions, but no non-replayable human approval, no tamper-evident audit, unusable by a non-engineer. |
| **Hand-rolled if-statements** | The real incumbent. |

**Competitive matrix (deck slide 19)** — columns: blocks the action / non-replayable
human approval / tamper-evident audit / usable by non-engineer / no model in
decision path. Vexen is the only row with all five.

---

## 4. THE INSIGHT

Mature high-consequence systems separate three things that agent deployments fuse
into one:

1. **Who is asking** (identity)
2. **What they are allowed to do** (policy — decided elsewhere, by someone else)
3. **What actually happens** (execution)

Agents fuse all three inside one model call. Vexen pulls the middle one out and
puts it where the agent cannot reach or argue with it:

- Rules live **server-side**, owned by a human, in a workspace the agent cannot write to
- The decision is **deterministic** — no model in the enforcement path
- The decision is **per-action** — this permission, this resource id, this amount, this moment
- **Humans are a first-class decision outcome**, not a bolted-on exception path
- **Everything is recorded** in a form you can hand to someone who does not trust you

---

## 5. THE PRODUCT (all built and running)

### 5.1 The engine — 13 ordered steps
Pure, deterministic, side-effect free. No I/O, no model. Default-deny: the only
path to ALLOW is an explicit grant that survives every step.

1. Verify agent identity
2. Verify the agent is active
3. Verify the request is authenticated
4. Validate the request shape
5. Check the permission exists at all
6. Check the permission has not expired
7. Check resource restrictions
8. Check action restrictions
9. Check numeric limits
10. Check sensitive-resource restrictions
11. Evaluate workspace policies
12. Check the human-approval requirement
13. Calculate risk

Each step is recorded in the trace. **The trace IS the explanation** — the console,
the audit record and the SDK error all tell the same story from one source.

Source: `/app/backend/vexen/engine.py` (696 lines).

The engine also strips any caller-supplied privilege claims before evaluating:
`approved`, `approval_granted`, `decision`, `risk`, `permissions`, `org_id`,
`bypass`, `max_amount`, `policy`. Nothing the caller asserts about its own
authority is trusted.

### 5.2 The permission model — verified counts
- **67 permissions** across **18 categories** (`PERMISSION_CATALOG`)
- Categories: Account, Commerce, Communication, Data, Engineering, Files,
  Finance, HR, Healthcare, Identity, Legal, Marketing, Payments, Productivity,
  Research, Sales, Support, Travel
- **10 flagged sensitive**, with stricter defaults:
  `account.password.write`, `database.delete`, `health.record.read`,
  `identity.role.write`, `infra.delete`, `invoices.pay`, `payments.create`,
  `payments.read`, `payments.refund`, `secrets.read`
- **9 amount-bearing permissions**: `ads.spend`, `invoices.create`, `invoices.pay`,
  `payments.create`, `payments.refund`, `shopping.purchase`, `sms.send`,
  `support.refund.issue`, `travel.book`
- Written in business language (*issue refund*, *send email*, *delete file*), not
  endpoint language, because the person who should set them is not an engineer

**Grant kinds (4):** ALLOW, LIMITED, APPROVAL_REQUIRED, BLOCK.
An explicit BLOCK always beats an explicit ALLOW on the same key. Exact match
wins; then the most specific wildcard.

**Per-grant constraints:** `max_amount`, `hard_max_amount` (not even an approver
can exceed), `approval_required_above`, `require_approval`, `allow_sensitive`,
`temporary`, `max_calls_per_day`, `allowed_resources`, `denied_resources`,
`allowed_actions`, plus **expiry** — temporary access that genuinely lapses.

### 5.3 Policies — plain English in, validated rule out
Workspace-wide rules above per-agent permissions. **5 effects:** `DENY`,
`REQUIRE_APPROVAL`, `LIMIT`, `MAX_TTL`, `REQUIRE_SCOPE`.

You type *"any purchase over $100 needs a person to approve it"* and Claude turns
it into a schema-validated rule, shown back in plain language before it takes
effect. **The AI writes rules. The AI never enforces them.** If generation fails
it fails closed and visibly.

**7 system policies ship by default:**
- Never allow agents to access payment credentials — DENY
- Agents cannot modify passwords — DENY
- Purchases above $100 require approval — REQUIRE_APPROVAL
- Temporary file access expires after 60 minutes — MAX_TTL
- Agents can only access files explicitly granted to them — REQUIRE_SCOPE
- Agents cannot destroy infrastructure or data — DENY
- Bulk data export requires approval — REQUIRE_APPROVAL

### 5.4 Approvals — the five invariants (the genuinely hard part)
1. **Single-use** — consumed the moment it is spent, no replay
2. **Short-lived** — 30 minutes by default
3. **Atomically claimed** — conditional single-document update, not read-then-write,
   so two concurrent requests can never both spend it
4. **Scope-bound to the exact action** — same permission, same resource id, same
   amount to the cent. No amount escalation, no substituting a different order,
   no reuse for a different permission
5. **Server-loaded only** — nothing the caller claims about approval state is trusted

> Most implementations get one or two of those. Missing any single one gives you an
> approval that can be escalated, replayed or forged — worse than no approval at
> all, because now a signed-looking record says a human agreed.

### 5.5 Two-tap phone approval, no login
The instant an agent is paused, every eligible approver gets an email with the
specifics — which agent, what it wants, how much, on what, which rule stopped it —
and two buttons: **Approve once** / **Refuse**. Phone-sized confirm page. ~15
seconds from notification to decision.

**The security subtlety that shaped the design:** a link in an email that performs
an action on GET is a vulnerability, not a feature. Mail providers and corporate
link scanners fetch every URL in a message. If Approve happened on GET, **your
security scanner would approve your agent's $40,000 purchase before you opened
the email.** So GET is strictly read-only and the decision requires an explicit
**POST** from a deliberate tap.

Links are **HMAC-SHA256 signed with domain separation** (a link token can never be
used as a session token), carry **ids only** — never a password or session —
**expire in 24 hours**, and are minted **per recipient** so the audit trail names
exactly which human decided even though nobody signed in. Verification never
explains why a token failed, denying an attacker an oracle.

Plus browser push over **Web Push with VAPID**, through a deliberately minimal
service worker that handles push and notification-click and nothing else — no
caching, no request interception — so it cannot alter app behaviour. Dead
subscriptions pruned automatically.

### 5.6 Hash-verified audit
Every decision — allowed, blocked, escalated — written to an audit event with the
full evaluation trace. Each event carries a **SHA-256 integrity hash** over audit
id, workspace, agent, permission, decision, reason code, amount and timestamp.
The workspace exposes a verification pass that recomputes every hash and reports
whether the record is intact and **which rows, if any, were altered**.

So "our agent did not do that" and "a human approved this on the 14th" become
checkable claims rather than assertions.

### 5.7 The configuration library — 10,639 configs
Verified: `LIBRARY_SIZE = 10639`, `AGENT_TEMPLATES = 55`, `INDUSTRIES = 28`,
`TIERS = 7`, `TEMPLATE_CATEGORIES = 17`.

**Tiers:** starter, standard, pro, team, enterprise, observer, guarded.
**Template categories:** Personal & Productivity, Commerce, Travel, Research,
Finance, Engineering, Sales & CRM, Support, Marketing, HR & Recruiting, Legal &
Compliance, Data & Analytics, IT Operations, Healthcare Admin, Education,
Operations, Custom.
**Starter templates:** personal-assistant, shopping-agent, travel-agent,
research-agent, company-ops.

**Why it exists:** governance products fail at the blank page. Nobody knows which
of 67 permissions their shopping agent needs, so they grant everything — and now
the product is worse than useless because it provides false assurance. Search
"refund", "invoice" or "travel" and deploy a sensible posture in one click.
**Defaults are the product.**

### 5.8 The rest of the console
- **Try an action** — describe an action in plain language, watch the decision
  resolve step by step, no agent and no code
- **Waiting for you** — queue of paused agents
- **History** — searchable audit trail with the integrity check
- **Safety check** — standing review surfacing over-permissioned agents, stale
  temporary access, repeatedly-blocked agents (misconfigured or compromised), and
  risky grant combinations
- **Ask for help** — in-app assistant grounded in actual workspace state,
  answering *why was my agent stopped and what should I change?* Never touches
  credentials, stays off the enforcement path
- **My team** — 4 roles enforced server-side

**Roles (4):** `owner`, `admin`, `approver`, `viewer`
- Owner — everything
- Admin — manage agents and rules; cannot remove people or mint other admins
- Approver — decide what is waiting, change nothing
- Viewer — read-only

**18 mutating endpoints individually guarded.** The UI hides what your role cannot
do rather than letting you click into a refusal. Separating *can change the rules*
from *can approve an exception* is the classic segregation-of-duties control, and
it is what makes Vexen usable by a finance approver who should never edit policy.

### 5.9 The SDK — where the guarantee becomes real
```python
from vexen import Vexen

vexen = Vexen(api_key=VEXEN_AGENT_KEY, base_url=VEXEN_URL)

@vexen.guard("shopping", "purchase", amount="price", resource_id="sku")
def buy(sku, price):
    return stripe.PaymentIntent.create(...)   # the real thing
```

- If Vexen blocks, `buy` never runs
- If a human is needed, `buy` never runs until they say yes, and then exactly once
- **If Vexen is unreachable, `buy` does not run** — fail-closed by default

> An authorization layer that fails open is a compliance decoration; the first
> network blip silently returns you to an ungoverned agent at the exact moment you
> are least likely to notice.

Exceptions: `VexenBlocked`, `VexenNeedsApproval`, `VexenUnavailable`.
Source: `/app/sdk/python/vexen.py`.

---

## 6. HOW IT IS BUILT

**Stack:** FastAPI (async Python) + React + MongoDB + Tailwind + shadcn/ui.
Anthropic Claude for rule authoring and the help assistant. Gmail SMTP over
`aiosmtplib`. `pywebpush` with VAPID for push.

**Auth:** JWT HS256, access token 60 min, refresh 30 days. bcrypt rounds=12.
Agent API keys generated once, shown once, stored SHA-256 hashed with a pepper,
compared with `hmac.compare_digest`.

**Multi-tenancy:** every record carries a workspace id, every query scoped to it.
Cross-tenant isolation verified explicitly in the test suite, **including through
the unauthenticated public routes** — the obvious place for a leak.

**Never blocking the event loop:** password hashing runs in a threadpool, because
bcrypt on the event loop turns a burst of concurrent sign-ins into a full-service
stall. `pywebpush` blocks too, so push sends also go to a thread. Both came out of
load testing, not theory.

**The email outbox:** nothing on a request path ever talks to an SMTP server. The
authorization endpoint writes a row into an outbox; one background worker drains
it, claiming messages atomically so two workers can never send the same one
twice. Retries capped with exponential backoff, authentication failures terminal
rather than retried forever, sends spaced to respect provider rate limits. **A
broken mailbox can never take down enforcement.**

**Fire-and-forget where optional:** push dispatched as a background task, because
a slow push service must never delay an agent. Email is the reliable channel;
push is a convenience.

**18 Mongo collections:** users, organizations, memberships, sessions, agents,
permissions, policies, credentials, approvals, audit_events,
authorization_requests, security_events, notifications, email_outbox,
push_subscriptions, invites, simulator_runs, contact_messages.

**32 reason codes:** ACTION_NOT_ALLOWED, AGENT_IDENTITY_UNVERIFIED,
AGENT_INACTIVE, AMOUNT_INVALID, AMOUNT_LIMIT_EXCEEDED, AMOUNT_REQUIRED,
APPROVAL_REQUIRED, APPROVED_BY_HUMAN, CREDENTIAL_EXPIRED, CREDENTIAL_REVOKED,
DENIED_BY_HUMAN, HARD_LIMIT_EXCEEDED, LIMIT_MISSING, MALFORMED_REQUEST,
NO_PERMISSION, PERMISSION_DENIED, PERMISSION_EXPIRED, PERMISSION_GRANTED,
PERMISSION_INVALID, POLICY_DENIED, POLICY_SCOPE_REQUIRED, POLICY_TTL_EXCEEDED,
RATE_LIMIT_EXCEEDED, RESOURCE_DENIED, RESOURCE_NOT_ALLOWED,
RESOURCE_SCOPE_REQUIRED, UNAUTHENTICATED (+ policy effect codes).

**Risk scoring:** 0–100, banded low (<25) / medium (25–49) / high (50–74) /
critical (75+). Factors include permission base weight, sensitive resource +15,
amount over $1,000 +25 / $500 +18 / $100 +10, blocked +15, approval required +8,
recent blocked attempts up to +20. Standing agent risk also factors grant breadth
(12+ permissions +18) and combined spend authority (>$5,000 +15).

---

## 7. DESIGN PRINCIPLES

1. **Deterministic enforcement, probabilistic authoring.** A model may help write
   a rule. A model may never decide whether an action is allowed. You cannot
   certify a gate that might answer differently tomorrow.
2. **Fail closed, everywhere.** Unreachable: refuse. Malformed: refuse.
   Unrecognised: refuse. Expired: refuse. Ambiguous: refuse. Every ambiguity
   resolves toward *no*.
3. **The governed thing does not get a vote.** Rules live outside the agent's
   reach. Approval state loaded server-side, client claims ignored.
4. **Plain language, always.** Whoever is accountable for the money should own the
   permissions, and that person is usually not an engineer.
5. **Honest UI over flattering UI.** If push cannot work we say so and disable the
   switch. If email is not configured we say queued, not sent. Security products
   that overstate their status are worse than none, because people rely on them.
6. **Convenience is a security feature.** A control humans find annoying gets
   disabled, and a disabled control protects nothing.

---

## 8. TRACTION (verified figures, deck slide 14)

| Metric | Value |
| --- | --- |
| Registered users | 5,000+ in 2 months |
| Monthly active | 2,000+ (40% of signups) |
| Weekly active | 800+ |
| Daily active | 300+ (15% DAU/MAU) |
| Actions completed in product | 10,000+ |
| Month-over-month user growth | ~12% |
| End-to-end regression checks | 55/55 passing |
| Independent backend pass | 110/110, no critical defects |
| Paid acquisition | $0 |
| Revenue | $0 — pre-revenue by choice |

### Observed behaviour sequence (deck slide 15)
1. Deploy a ready-made configuration
2. Write a rule in plain English and test it
3. Trigger an approval, approve it on a phone
4. **Go looking for the SDK**
→ Outcome: guarded calls in their own codebase

### What users ask for, unprompted
- TypeScript SDK — Python-only is the current stopping point
- MCP gateway and framework guards — enforce where agents already run
- **"Can I stop the agent bypassing this at all?"** — a request for the credential broker

> Nobody asks for a stricter constraint on themselves for a nice-to-have. Users are
> pulling the product toward its more defensible version.

---

## 9. WHO IT IS FOR

**Immediate wedge:** teams putting agents near money or customers. E-commerce and
retail ops (purchasing, pricing), support (refunds, account changes), finance
(invoices, reconciliation), recruiting (outreach). 20–200 person companies with
the exposure and no security team.

**The buyer is frequently NOT the engineer who built the agent.** It is the ops
lead, finance manager or founder who is accountable when it goes wrong and
currently has no instrument at all — a very specific, very motivated person that
almost nothing in the market is built for.

**Second wave:** platforms. Agent frameworks, vertical AI products and automation
platforms that need to offer their own customers permissions and approvals and
would rather not build a governance layer badly.

**Third wave:** regulated industries — financial services, healthcare, legal,
government — where the audit trail and segregation of duties are preconditions
rather than features. Slower, and where the durable value sits.

---

## 10. BUSINESS MODEL — priced per decision, not per seat

> Revenue grows with how much a customer automates, not with how many people they
> employ — one of the few software lines that expands as headcount falls.

| Tier | Price | Trigger | Gated on |
| --- | --- | --- | --- |
| Free | $0 | Developer installs the SDK | Nothing — this is the adoption path |
| Self-serve | $99–$999/mo | Crosses the allowance | Decision volume, seats, retention |
| Mid-market | $12K–$25K/yr | A second team adopts it | RBAC, reporting, support |
| Enterprise | $50K–$100K/yr | Security review of an agent going to production | SSO, SCIM, retention, pentest, SOC 2, credential broker |

**Land** — one engineer, one decorator, free tier.
**Expand** — more agents → more decisions → higher tier, no new seats sold.
**Convert** — the security review is the pricing event. The broker and SOC 2 are
what make it a line item.

**Two principles:** we never charge for the audit trail on any tier (evidence
should not sit behind a paywall in a security product, and accumulating history is
our best retention mechanism anyway); and allowances stay loose relative to seat
price, because pricing that discourages checking more actions is a perverse
incentive.

---

## 11. PATH TO REVENUE (deck slide 17)

| Window | ARR | Milestones |
| --- | --- | --- |
| Months 0–6 | $250K | Credential broker shipped; TypeScript SDK; MCP gateway; 10 design partners in production; first 25 paying accounts |
| Months 7–12 | $1.2–1.5M | Published external pentest; SOC 2 Type I; SSO; SCIM; first 10 enterprise contracts; founding engineer hired |
| Months 13–18 | $4M | 3 platform embeds; open authority spec v0.1; logos growing faster than headcount |
| Months 19–24 | $10M | 100 enterprise @ $60K = $6.0M; 250 mid-market @ $14K = $3.5M; 250 self-serve @ $2.4K = $0.6M |

**The one metric that decides it:** decisions per account per month. Users grow
because I write; decisions grow only if agents genuinely run behind it. Needs
~30–40% quarterly compounding.

**Said plainly:** $10M in 24 months is the aggressive case. Base case is **$3–5M**,
with $10M reachable only if the platform embeds land and carry distribution.

---

## 12. MARKET (deck slide 18)

- **Bottom-up SAM:** ~150K companies running action-taking agents by 2028 × ~$20K
  average annual spend ≈ **$3B**. Nearer-term 50K × $20K ≈ **$1B**.
- **Comparables:** IAM software is a **$20B+** market; Okta alone ~**$2.6B** revenue.
  Agent authority is the same shape of layer, one level down.
- **Better unit of growth:** every company has more actions than employees, and the
  ratio is moving in one direction.
- **Stickiness:** permission layers are bought once and removed almost never,
  because removing one means choosing to run an ungoverned system. Nobody does
  that to save money.

---

## 13. MOAT — four defences in increasing order of durability

1. **Position** — on the write path, not the read path. Observability sits beside
   the action; Vexen sits in front of it. Once a guarded call is in production
   code, removing it is a decision to run ungoverned.
2. **Correctness** — invariants that take real adversarial work: atomic single-use
   claims, cent-level scope binding, scan-safe POST-only actions, hash-verified
   audit, fail-closed defaults. Easy to demo, hard to get right. A competitor can
   copy the screens in a fortnight; the invariants take much longer, and most
   teams will not realise which ones matter until something goes wrong in
   production.
3. **Both personas** — the engineer integrates, the accountable human signs. Policy
   engines serve only developers, so nobody with a budget can use them.
4. **Standard** — the credential broker, then the artefact. Short-lived scoped
   credentials make bypass impossible. Then a portable, verifiable statement of
   bounded authority that travels between companies — the primitive agent commerce
   and agent insurance both need, and neither has.

**Who could enter:** Okta or Auth0 from identity, Stripe from payments, or a
framework bundling a "good enough" feature. Speed and correctness are the defence.

**Category is unowned** — no standard vocabulary, no pricing norm, no analyst
category. That is the opportunity and the risk.

---

## 14. RISKS AND MITIGATIONS

| Risk | Mitigation |
| --- | --- |
| **"The frameworks will just build this."** | Their incentive is a feature that keeps developers inside their framework, not a neutral control plane with an auditable record. We work with all of them and are trusted because we are owned by none. A framework's in-process interrupt is architecturally weaker anyway. Bundled features stop at logging and pausing; correct approval invariants, scan-safe delivery and tamper-evident audit are the hard 20% nobody bundles — and an open spec makes us the reference, not the competitor. |
| **Adoption friction** (biggest risk) | If Vexen is annoying it gets removed. Already mitigated in-product: one-line decorator, 10,639-config library, two-tap phone approvals, plain-language refusals that say what to change. |
| **Latency on the critical path** | Pure in-memory engine, zero I/O in the decision. Also the framing is wrong — the actions worth governing already take hundreds of ms, and nobody minds twenty more before a $700 purchase. |
| **Fail-closed will cause outages** | It will occasionally stop legitimate work, and that is the correct trade for actions of this consequence. Managed with clear errors, an explicit opt-out for low-stakes actions, and eventually a cache for safely-cacheable decisions. |
| **Agents will route around it** | If an agent holds raw credentials it can bypass a voluntary check. End state is Vexen brokering short-lived scoped credentials so bypassing is impossible. The decorator is the pragmatic first step; the broker is the architecturally complete one. |
| **Solo founder / execution gaps** | 55% of the round is two hires that close exactly those gaps. Runway is not the constraint: $50K in the bank against ~$200/month burn. |

---

## 15. ROADMAP

**Next (weeks).** Multi-workspace membership. TypeScript SDK. Delivery log of every
alert sent. Weekly digest of what agents spent and what was approved. Escalation
if an approval sits unanswered.

**Then (months).** Native framework guards. MCP gateway. Approval delegation and
on-call rotations, so the right person is asked at 2am. Anomaly detection on
decision patterns — an agent whose behaviour changes shape is the earliest signal
of compromise or misconfiguration. Policy simulation against historical traffic:
"if I add this rule, what would it have blocked last month?"

**Later.** SOC 2. SSO and SCIM. Data residency. Exportable signed compliance
reports. **An open specification for agent permissions**, because being the
reference implementation of an open standard beats owning a closed one.

**The big one — the credential broker.** Today Vexen is a check an agent chooses to
make. The complete version issues short-lived, scoped, single-purpose credentials
so an agent *physically cannot* exceed its authority rather than being asked not
to. Designed but unbuilt. This is the #1 use of funds.

---

## 16. THE HONEST LEDGER — what does NOT exist

- **No revenue, no paying users.** Working product, not a business with traction.
- **One account belongs to one workspace.** Multi-workspace membership is a known
  limitation with a clear fix, and the API says so rather than failing silently.
- **The SDK is Python only.** TypeScript is next; the API is plain HTTP so any
  language can call it today.
- **Single-region deployment.** No data residency controls.
- **No SSO, no SCIM, no SOC 2.** Table stakes for enterprise, scheduled not done.
- **The credential broker is designed but unbuilt.**
- **Push delivery to a real lock screen** can only be proven on a real device;
  headless automation reports notifications as blocked. Mechanism verified; last
  mile needs a human with a phone.
- **Not incorporated yet.** Delaware C-corp intended at or before first financing.

> Being precise about this boundary is itself evidence about how we build. A
> security product that overstates its readiness is the specific thing we are
> arguing against.

---

## 17. HOW WE WANT TO BE JUDGED — the five tests

1. **Does it actually stop an agent?** Point a real agent at it, block it, confirm
   the side effect never happened.
2. **Can you break an approval?** Try to replay one, escalate the amount, reuse it
   for a different order, forge a token. It should refuse every time.
3. **Can a non-engineer use it?** Give the console to somebody who has never seen
   an API key and see if they can grant a permission, write a rule and approve a
   paused action.
4. **Does the evidence hold up?** Alter an audit row directly in the database and
   confirm the integrity check catches it.
5. **Does it fail safely?** Take the service offline and confirm the guarded
   function refuses to run.

> Those five are the product. Everything else is packaging.

**Fastest possible evaluation:** deploy an agent, set the threshold to $10, then try
to make it spend $50.

---

## 18. GO TO MARKET

**Land through the SDK, expand through the approver.** An engineer adopts the guard
decorator for one dangerous function — usually the one that spends money. The
first time an agent is stopped and their ops lead gets the email and taps
Approve, the product has acquired its real champion.

**Content that is genuinely useful.** Publishing honestly on single-use-approval
design, scan-safe email actions, fail-closed defaults and audit hashing reaches
exactly the people about to ship an agent with a production key — and demonstrates
competence rather than asserting it.

**Framework integrations**, so adoption is one import rather than a refactor.
**Partner with the observability layer** rather than compete: complements, their
users have our problem, and they have no interest in becoming an enforcement layer.

---

## 19. THE FOUNDER

**Solo founder.** No co-founder, no employees, no contractors. Built, tested and
deployed all of Vexen alone over two months.

### Prior products — 100,000+ cumulative users, zero paid acquisition
| Product | Users | What it is |
| --- | --- | --- |
| HealthLens | 70,000+ | AI wellness / health platform |
| AI-Namo | 20,000+ | AI government-document verification and fraud detection — **adopted by a local government inside their real process** |
| GreenGuide | 10,000+ | Agricultural copilot (plant disease) |
| CerebroAegis | 5,000+ | Health and safety guidance in plain language |
| Vexen | 5,000+ | This one — sixth product |
| PythonPal | 100+ students | Nonprofit teaching programming; recruited and led volunteers |
| HorizonSTEM | 150+ | STEM workshops for middle schoolers |

**Commercial:** COO of **The1550Formula**, an AI-first SAT prep company — helped run
it to **~$70,000/month** with **1,000+ students** improving by **~200 SAT points**
on average.

**Distribution:** educational YouTube channel past **3 million views**. Content-led
distribution is exactly how a security primitive spreads — you reach the engineer
the week before they ship an agent with a production key.

### The through-line
Every product built so far is an interpreter between a person and complex
information generated about them: health data for the patient, a document's
authenticity for the official, a diseased plant for someone who is not a botanist.
Vexen interprets an agent's intended action for the person accountable for it —
and then does the thing none of the others could, which is **stop it**.

### The proudest thing (AI-Namo)
Not the number. Everything built before it was optional to its users. This one
became part of how an institution decided whether to trust a piece of paper.
Someone was going to be approved or refused partly because of code written alone,
with nobody checking. That changed how I build — I started thinking harder about
what happens when the system is *wrong* than when it is right: false positives,
appeals, accountability, what evidence exists afterwards.

### The admitted gap
**"I have never sold an infrastructure security product into an enterprise
procurement cycle."** That is what hire #2 is for. Stated rather than hidden.

### Why solo is currently an advantage
Vexen is one tightly-coupled guarantee: the engine, the approval invariants, the
SDK semantics and the audit format all have to agree, because a gap between any
two of them is a vulnerability. Holding that whole model in one head is a real
advantage at this stage. A three-person team with divided ownership would probably
have shipped more screens and a weaker guarantee.

### Where solo hurts
Concentration risk. Single point of failure on the roadmap, and the bottleneck on
the one thing never done before.

---

## 20. THE THREE HIRES

1. **Founding engineer — authorization or payments infrastructure at scale.**
   Ideally out of an IAM, fraud or payments team (Stripe, Okta, Auth0, or a bank's
   internal controls group). Owns the **credential broker**, multi-language SDKs
   and framework guards. Going from "the agent chooses to check" to "the agent is
   issued short-lived scoped credentials and physically cannot exceed them" is a
   token lifecycle and key management problem — the class where a subtle mistake
   stays invisible until it is catastrophic. *Want somebody who has carried a
   pager for a system where a bug meant money moved incorrectly.* **They are the
   person whose job includes telling me no.**
2. **First go-to-market hire — has sold an infrastructure control to a mid-market
   ops or finance buyer.** Not an AI salesperson — someone who has sold
   observability, security or compliance tooling through a six-month procurement
   cycle and can run a design-partner programme. First objective is not pipeline —
   it is **ten real design partners with agents in production behind Vexen**,
   telling us where the approval flow breaks inside a real approval chain.
3. **Security engineer / researcher whose actual job is to attack it.** Early hire
   or retained long-term reviewer. *A security product that has never been
   attacked by a stranger is an untested claim.* Every invariant that matters —
   approval replay, amount escalation, token forgery, cross-tenant leakage
   through the unauthenticated public routes — is precisely the class of thing the
   author is worst placed to test. Want them publishing what they find, including
   the unflattering parts, **because in this category credibility is the product.**

Ordering is deliberate: engineer first (the broker turns the guarantee from a
convention into a constraint), GTM second (once there is something unavoidable to
sell, the only question is whether anyone pays), security third in sequence but
not in importance.

**Sourcing:** expect to find the engineer and researcher by publishing openly on
the hard parts. The GTM hire is the one I do not know how to source alone.

### Advisors
None formal — would rather say so than list people who took one call. What is
wanted: three people who answer a text within the hour — (a) a security or
compliance leader at a fintech or health company (the buyer, who says when I am
wrong about procurement), (b) an authorization architect (technical adversary who
reviews the broker design before it ships), (c) an operator who has taken a
bottom-up developer tool into enterprise contracts.

---

## 21. THE RAISE

- **$750,000 pre-seed**, post-money SAFE, **$8M post-money cap**, comfortable
  $7–10M depending on partner fit and speed. Open to a smaller first cheque with a
  larger round behind it.
- **Buys ~20 months of runway for a three-person team.**

| % | Use of funds |
| --- | --- |
| 55% | Two hires — founding engineer (IAM/fraud/payments) to own the credential broker; first GTM hire to run a ten-company design-partner programme |
| 25% | Founder full-time and infrastructure — *"the first product I want to be the only thing I do"* |
| 20% | Security and compliance — published external pentest, SOC 2 Type I, SSO, SCIM. The enterprise gate. |

**Milestones underwritten:** credential broker shipped (bypassing becomes
impossible rather than discouraged); TypeScript SDK and native framework guards
(the two most requested items); ten design partners with agents in production;
first paid contracts. **That set is the shape of a seed round.**

### Cap table
- 100% founder-owned. No SAFEs, convertible notes, warrants, options, phantom
  equity or revenue share. Nothing promised to anyone.
- Intended structure: Delaware C-corp, **10,000,000 shares** of common authorised
  and issued to founder, standard **4-year vest with 1-year cliff** from
  incorporation (so an investor is not funding fully vested founder equity).
- Illustrative post-raise at $750K/$8M cap: founder **9,062,500 shares / 90.63%**;
  new investors **937,500 / 9.37%**. Not committed, no terms agreed.
- **All IP created solely by the founder** — no contractors, agencies or
  co-authors; no employer, university or third party has any claim. Assigned to
  the company on incorporation.
- Cash $50,000 (founder-contributed), burn ~$200/month (hosting, domains, API).

---

## 22. THE TEN-YEAR VIEW

In ten years Vexen answers one question every organisation has to answer
continuously: **what is this non-human actor allowed to do, right now, up to what
magnitude, and who signed off?**

Three steps:
1. **The enforcement layer teams choose** — where we are now.
2. **The credential broker** — the real product. Instead of an agent choosing to
   ask permission, it is issued short-lived scoped single-purpose credentials and
   physically cannot exceed its authority. Turns a convention into a constraint.
3. **The artefact** — a portable, verifiable statement of bounded authority that
   travels between organisations, so when two companies' agents transact there is
   a record their auditors, regulators and insurers will accept. That primitive
   does not exist today. Agent commerce needs it. So, plausibly, does **agent
   insurance**, which is not yet a category.

**The version actually wanted: an open standard.** Every team inventing agent
permissions right now is inventing them differently — no way to ask "what is this
agent allowed to do?" across two systems, no way to carry an approval between
them, no shared vocabulary a regulator or insurer can point at. Identity got SAML
and OAuth. Payments got card network rules. **Agent authority has nothing, and the
window in which those conventions get set is open now and will not stay open.**
Rather be the reference implementation of an open standard than the owner of a
closed one — and that is the larger outcome, because it is the version one person
can start and an incumbent structurally cannot.

**And eventually not only software agents.** The same question is unanswered for
delivery robots, industrial automation and clinical decision support. *I do not
think the important artefact of this era is a model. I think it is a portable,
verifiable statement of bounded authority, and almost nobody is building it.*

---

## 23. THE BEST LINES (for tweets, one-liners, closers)

- **"Agents already have the keys. Somebody has to hold the lock."**
- "A prompt is not a permission."
- "We gave AI hands and forgot the keys."
- "You cannot verify intent. You can only constrain consequence."
- "Observability is the flight recorder. We are the flight control."
- "The AI writes rules. The AI never enforces them."
- "You cannot let the thing being governed also be the governor."
- "Asking the agent to police itself is the entire problem restated."
- "A record you can hand to someone who does not trust you."
- "An authorization layer that fails open is a compliance decoration."
- "A security product that has never been attacked by a stranger is an untested claim."
- "Defaults are the product."
- "Convenience is a security feature. A disabled control protects nothing."
- "Every computing generation grows a permission layer. This one hasn't."
- "Bought once. Removed almost never."
- "A competitor can copy our screens in a fortnight; the invariants take much longer."
- "Those five are the product. Everything else is packaging."
- "Every product I have built so far was built in the gaps around everything else.
  Vexen is the first one I want to do as the only thing I do."

### Tweet-length descriptions (verified counts)
**295 chars:**
> Your AI agents can spend your money, email your customers and delete your files. Nothing is checking them.
>
> Vexen is the permission layer for AI agents. Every action gets ALLOW, BLOCK or ASK A HUMAN in one API call. Big spends wait for a tap on your phone. Every decision is logged, permanently.

**272 chars:**
> One line of code decides whether your AI agent is allowed to do the thing it is about to do.
>
> Vexen answers ALLOW, BLOCK or ASK A HUMAN in milliseconds. A $700 purchase stops dead and waits for you to tap Approve on your phone. Every decision is logged and tamper-evident.

**185 chars:**
> Vexen is the permission layer for AI agents. Every action gets ALLOW, BLOCK or ASK A HUMAN in one API call. Big spends wait for a human tap. Every decision is logged and tamper-evident.

---

## 24. ASSETS AND LINKS

| Asset | Location |
| --- | --- |
| Live product | https://action-guard-1.preview.emergentagent.com |
| Demo video (YouTube) | https://youtu.be/V5SaKRhMmcM |
| Demo video (MP4, 1080p, 2m59s, narrated + captioned) | `/api/download/demo-video` |
| Demo video (WebM fallback) | `/api/download/demo-video-webm` |
| Supporting document (PDF, 19 pages) | `/api/download/supporting-document` |
| Pitch deck (25 slides) | `/api/download/pitch-deck` |
| Cap table | `/api/download/cap-table` |
| Idea one-pager | `/api/download/one-pager` |

**Demo login:** `alex.morgan@northwind.demo` / `Vexen-Demo-2026`

### Pitch deck v2 — 25 slides
01 Cover · 02 Shift · 03 Problem · 04 Cost · 05 Why now · 06 Insight · 07 Product ·
08 Engine · 09 Approvals · 10 Approval UX · 11 Audit · 12 Activation ·
13 In practice · 14 Traction · 15 Behaviour · 16 Business model · 17 Path ·
18 Market · 19 Competition · 20 Moat · 21 Roadmap · 22 Team · 23 Risks · 24 Ask ·
25 Close

### Repo layout
```
/app/backend/server.py            entry, health, downloads
/app/backend/vexen/               engine.py (696) service.py (1137)
                                  catalog.py (601) library.py (472)
                                  routes_* (auth/agents/governance/ops/team/public)
                                  mailer.py links.py push.py ai.py security.py
/app/frontend/src/pages/          19 pages (Landing, Dashboard, Agents, Approvals,
                                  AuditLog, Policies, SecurityCenter, TryIt,
                                  Team, Developers, Guide, ApproveByLink, ...)
/app/sdk/python/vexen.py          the fail-closed SDK
/app/deck/                        deck2.html/css, cap-table.html, one-pager.html
/app/memory/                      all submission answers + generated PDFs
```

### Source docs
- `/app/memory/SUBMISSION.md` — the 32,734-char master proposal + tweet answers
- `/app/memory/SUBMISSION_EMERGENT_VC.md`
- `/app/memory/SUBMISSION_FORM_FUNDRAISE.md` — general VC form answers
- `/app/memory/SUBMISSION_FOUNDER_FELLOWSHIP.md` — team, recruiting, 1000-char versions
- `/app/deck/check_fields.py` — exact character-counted strings; run it to re-verify
- `/app/memory/short_bullets_1000.txt`, `winning_team_1000.txt`

---

## 25. THE CLOSING ARGUMENT

We are not proposing to make AI agents smarter or safer to talk to. Plenty of
people are working on that.

We are proposing what every previous generation of powerful technology eventually
required, and this one conspicuously lacks: an external, deterministic, auditable
answer to *"is this allowed?"* — decided by a human in advance, enforced by a
system the actor cannot argue with, evidenced in a record that survives scrutiny,
and convenient enough that people leave it switched on.

**Agents already have the keys. Somebody has to hold the lock.**
