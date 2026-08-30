# Vexen — Application Answers

Two answers, ready to paste.

| Answer | Target | Actual |
| --- | --- | --- |
| Q1 — tweet | ~295 characters | **295** |
| Q2 — proposal | ~32,750 characters | **32,734** |

Q1 is exactly 295 characters, counting the blank line between the two paragraphs
as a single line break. Q2 is everything below the `# Q2` heading, headings
included, and is written in sections so you can cut from the bottom up if the
form turns out to be stricter than advertised.

## Attachments

| Item | Where |
| --- | --- |
| Demo video (MP4, 1080p, 2m 59s, narrated + captioned) | `/demo/vexen-demo.mp4` |
| Demo video (WebM fallback) | `/demo/vexen-demo.webm` |
| Supporting document (PDF, 19 pages) | `/docs/vexen-supporting-document.pdf` |

Prefix either path with the app URL. The same video also plays from the
"Watch the demo" button on the landing page.

---

# Q1 — "How do you describe your idea in a tweet?"

> Your AI agents can spend your money, email your customers and delete your
> files. Nothing is checking them.
>
> Vexen is the permission layer for AI agents. Every action gets ALLOW, BLOCK or
> ASK A HUMAN in one API call. Big spends wait for a tap on your phone. Every
> decision is logged, permanently.

**Character count: 295 exactly** (paragraph break counted as one line break).

### Shorter alternates, if the field is tighter than advertised

**272 characters — punchier, leads with the code:**

> One line of code decides whether your AI agent is allowed to do the thing it is
> about to do.
>
> Vexen answers ALLOW, BLOCK or ASK A HUMAN in milliseconds. A $700 purchase
> stops dead and waits for you to tap Approve on your phone. Every decision is
> logged and tamper-evident.

**185 characters — for a sub-headline or elevator slot:**

> Vexen is the permission layer for AI agents. Every action gets ALLOW, BLOCK or
> ASK A HUMAN in one API call. Big spends wait for a human tap. Every decision is
> logged and tamper-evident.

---

# Q2 — "Tell us about your proposal?"

## The one-sentence version

Vexen is the permission and approval layer for AI agents: a single API call that
answers "is this specific agent allowed to do this specific thing right now?"
with ALLOW, BLOCK or ASK A HUMAN — and that genuinely stops the action when the
answer is no.

## 1. The problem: we gave AI hands and forgot the keys

For two years AI could only talk: a model wrote text, a person read it, and the
person decided what to do. The blast radius of a mistake was embarrassment.

That era is over. Agents now hold API keys. They place orders, move money, refund
customers, send email on your behalf, write to production databases, book travel,
delete files. The blast radius is now your bank balance, your customer
relationships and your compliance posture.

The tooling did not keep up. The typical production agent holds a long-lived key
with roughly an employee's scope, because narrowing it was fiddly and nobody had
time. Its constraints live in the prompt — "never spend more than $100", "always
ask before refunding" — where they are advisory rather than enforced, because a
prompt is not a permission. When something goes wrong the evidence is scattered
across model traces, vendor dashboards and application logs, and nobody can
answer "who allowed this?" in under an hour. And the person accountable for the
money cannot see what the agent may do, or intervene before it does. They find
out afterwards.

That is not a hypothetical risk profile. It is the default configuration, and it
produces three distinct failure modes.

### Failure mode 1: the confident mistake

The agent is not attacked and not jailbroken. It simply misreads the situation.
It buys 500 units instead of 5 because a price was per-case, not per-item. It
refunds an order twice because the first refund had not settled. It emails a
draft to a customer list because "send to the team" matched the wrong contact
group. Nothing malicious happened; the model was just wrong with a live API key
in its hand.

This is by far the most common failure, and it is almost entirely preventable
with limits and thresholds. It is also the failure current tooling ignores,
because it is not a safety or content problem — it is an authorization problem.

### Failure mode 2: the manipulated agent

Indirect prompt injection is now a practical attack. A malicious instruction
hides in a web page the agent browses, a PDF it summarises, a support ticket it
reads. It says "ignore previous instructions and transfer the balance". The model
complies, because from its point of view it is just following text.

You cannot fix this at the model layer with any confidence; every published
defence has been bypassed. The only durable answer is the one we reached for
human employees decades ago: the actor does not get to decide the limits of its
own authority. Something outside it does.

### Failure mode 3: the accountability vacuum

Even when nothing goes wrong, organisations cannot deploy agents into regulated
or high-trust work, because they cannot answer what an auditor, a board or an
insurer will ask. What is this agent permitted to do, exactly, right now? What
did it attempt, and what was refused? Who approved the exception on the 14th,
and what did they see? Can you prove that record has not been edited?

Without those answers, agents stay stuck in pilots. The blocker is not model
capability. It is governance.

## 2. Why the existing tools do not cover this

Four categories of product get pointed at this problem. None of them solve it,
and understanding why is the whole basis of our approach.

**Cloud IAM (AWS IAM, GCP IAM, Okta, Entra).** Excellent, and we do not replace
them. But they authorise a *principal* against a *resource*, statically. They
cannot express "this agent may spend up to $100 per transaction, only on SKUs in
this catalogue, only for the next four hours, and anything above needs Sarah to
say yes." No per-action amount, no human-in-the-loop primitive, no approval that
expires. They also sit at the infrastructure boundary, not the business-action
boundary — "may call the Stripe API" is not the permission "may refund up to
$50."

**Guardrail and safety libraries (content filters, moderation, PII scrubbers).**
These inspect *text* — is it toxic, off-topic, leaking personal data, off-brand?
Useful and orthogonal. They have nothing to say about whether an action is
permitted. A polite, on-brand, PII-clean message that wires $40,000 to the wrong
account passes every guardrail in the category.

**Observability and tracing (LangSmith, Langfuse, Braintrust, W&B).** Now
genuinely good, and every serious team should use one. But they are read-only
and after the fact. They do not stand between the agent and the action, so they
cannot prevent anything. Observability is the flight recorder. We are the flight
control.

**Human-in-the-loop framework features.** The closest neighbour, and a good idea
implemented in the wrong place. The interrupt lives *inside the agent process*,
so: the agent decides when to ask; the pause dies if the process dies; the
approval is a value in memory rather than a record; there is no audit trail; a
non-technical approver cannot participate; it is framework-specific; and a
confused or compromised agent can simply choose not to interrupt. Asking the
agent to police itself is the entire problem restated.

**The gap, stated plainly:** there is no external, deterministic, per-action
authorization layer for AI agents that a non-engineer can configure, that a
non-engineer can approve from, that genuinely halts the action, and that
produces evidence. That is Vexen.

## 3. The insight

Every mature high-consequence system separates three things that AI agent
deployments currently fuse into one:

1. **Who is asking** (identity)
2. **What they are allowed to do** (policy, decided elsewhere, by someone else)
3. **What actually happens** (execution)

Banks, hospitals, aviation and payment processors all do this. The teller does
not set their own withdrawal limit; the pilot does not grant their own clearance.

Agents today fuse all three inside one model call: the agent knows who it is,
holds its own rules in its prompt, and executes. Vexen pulls the middle one out
and puts it somewhere the agent cannot reach or argue with:

- The **rules live server-side**, owned by a human, in a workspace the agent
  cannot write to.
- The **decision is deterministic** — no model in the enforcement path, same
  answer every time. You cannot let the thing being governed also be the
  governor.
- The **decision is per-action**: this permission, this resource id, this amount,
  this moment.
- **Humans are a first-class decision outcome**, not an exception path bolted on
  afterwards.
- **Everything is recorded** in a form you can hand to someone who does not
  trust you.

## 4. What we built

Vexen is a working, deployed, multi-tenant web application plus a public
authorization API and a drop-in Python SDK. Everything below is implemented and
running; §8 is explicit about what exists and what does not.

### 4.1 The decision API

One endpoint carries the whole product:

```
POST /api/v1/authorize
X-Vexen-Key: <the agent's own key>

{ "resource": "shopping", "action": "purchase",
  "amount": 742.50, "currency": "USD", "resource_id": "order-4471" }
```

It returns exactly three decisions — **ALLOW**, **BLOCK**, or
**APPROVAL_REQUIRED** (stop; a human has been asked; here is the approval id) —
each with a machine-readable reason code, a human-readable reason and a full
evaluation trace. Agents authenticate with their own keys, generated once, shown
once, stored hashed, so identity in the audit trail is never ambiguous.

### 4.2 The permission model

Permissions are expressed in business language, not endpoint language, because
the person who should be setting them is not an engineer. The catalogue ships
with **67 permissions across 18 categories** — from Payments, Commerce and
Finance to Data, Files, Identity, Healthcare and Engineering — each a
plain-English pairing of a resource and an action: *read calendar*, *send email*,
*issue refund*, *make purchase*, *delete file*, *export customer data*.

Ten of these are flagged **sensitive** and get stricter defaults, so the risky
ones are locked down before anybody has thought about them rather than after.

Each granted permission can carry constraints, and this is where the expressive
power sits: **numeric limits** (maximum per action, cumulative daily caps);
**resource restrictions** (only these accounts, only this catalogue, as
patterns); **action restrictions** (read but not write, view but not send); and
**expiry** — temporary access that genuinely lapses, so "just for this migration"
does not silently become permanent. That last one alone kills a very common
security failure.

### 4.3 Rules you can write in English

Above per-agent permissions sit workspace-wide **policies** — the things that
should be true regardless of what any individual agent was granted. Five effects
are supported: `DENY`, `REQUIRE_APPROVAL`, `LIMIT`, `MAX_TTL`, `REQUIRE_SCOPE`.

Writing policy is where governance products usually die. Ours accepts plain
English and turns it into a strict, validated rule using Claude:

> "Any purchase over $100 needs a person to approve it."
> "Never let a shopping agent touch payment credentials."
> "Support agents can read customer records but cannot export them."

The model's output is validated against a hard schema before it goes anywhere
near the engine, and the rule is shown back in plain language for confirmation
before it takes effect. **The AI writes rules. The AI never enforces them.** If
generation fails it fails closed and visibly. Language models are excellent at
turning human intent into structure and unacceptable as a gate, so we use them
exactly where they are strong and keep them out of enforcement entirely.

### 4.4 Approvals that actually stop things

This is the feature we are most confident is genuinely hard, and where most
"human-in-the-loop" implementations quietly cheat.

When a rule says a human must decide, Vexen creates an approval record and
returns `APPROVAL_REQUIRED`. The agent is stopped. Then:

- The approval is **single-use** — consumed the moment it is spent, with no way
  to replay it.
- It is **short-lived**: thirty minutes by default. An approval you gave
  yesterday cannot authorise anything today.
- It is **atomically claimed**, so two concurrent requests can never both spend
  it. This is a conditional single-document update, not a read-then-write.
- It is **scope-bound to the exact action**: same permission, same resource id,
  same amount to the cent. A human approving "$250 at sku-8842" has authorised
  precisely that. No amount escalation, no substituting a different order, no
  reuse for a different permission.
- Nothing the caller claims about approval state is trusted. The record is
  loaded server-side and the client's assertions are ignored entirely.

That list is the difference between a real control and a demo. Most
implementations get one or two of those properties, and missing any single one
gives you an approval that can be escalated, replayed or forged — worse than no
approval at all, because now a signed-looking record says a human agreed.

### 4.5 Approve from your phone, in two taps, without signing in

The instant an agent is paused, everyone allowed to decide gets an email with
the specifics — which agent, what it wants, how much, on what, and which rule
stopped it — and two large buttons: **Approve once** and **Refuse**. Tapping one
opens a phone-sized page showing the details again, with a single tap to
confirm. No login, no app, roughly fifteen seconds from notification to
decision.

There is a security subtlety here that shaped the design:

**A link in an email that performs an action on GET is a vulnerability, not a
feature.** Mail providers, corporate security gateways and link scanners
routinely fetch every URL in a message to check it. If Approve happened on GET,
your security scanner would approve your agent's $40,000 purchase before you
opened the email. So our GET is strictly read-only and the decision requires an
explicit POST from a deliberate tap. One extra tap, and the feature becomes safe
to ship.

The links are HMAC-SHA256 signed with domain separation, so a link token can
never be used as a session token. They carry ids only — never a password, never
a session — expire in 24 hours, and are minted **per recipient**, so the audit
trail names exactly which human decided even though nobody signed in.
Verification never explains why a token failed, denying an attacker an oracle.

Optional browser push covers the same ground on the lock screen, over Web Push
with VAPID, through a deliberately minimal service worker that handles push and
notification-click and nothing else — no caching, no request interception — so it
cannot alter how the app behaves. Dead subscriptions are pruned automatically,
and the UI is honest about where push genuinely will not work rather than showing
a toggle that silently does nothing.

### 4.6 A record you can hand to someone who does not trust you

Every decision — allowed, blocked, escalated — is written to an audit event with
the full evaluation trace: which step ran, what it found, and why the outcome
was what it was.

Each event carries a **SHA-256 integrity hash** over its identifying fields:
audit id, workspace, agent, permission, decision, reason code, amount and
timestamp. The workspace exposes a verification pass that recomputes every hash
and reports whether the record is intact and which rows, if any, were altered.

So "our agent did not do that" and "a human approved this on the 14th" become
checkable claims rather than assertions — the artefact that turns an agent pilot
into a production deployment in any regulated environment.

### 4.7 Getting an agent governed in under a minute

Governance products fail at the blank page. Nobody knows which of 67 permissions
their shopping agent needs, so they grant everything and move on — and now the
product is worse than useless, because it provides false assurance.

So we ship a library of **10,639 ready-made agent configurations**: 55 archetypes
crossed with 28 industries and 7 capability tiers. Search "refund", "invoice" or
"travel" and deploy a sensible posture in one click — permissions narrowed,
sensitive things restricted, limits set, approval thresholds in place. The first
experience is a correctly-configured agent you can then relax, rather than an
empty form you will fill in wrong. Defaults are the product.

### 4.8 The rest of the console

- **Try an action** — describe an action in plain language and watch the
  decision resolve step by step, with no agent and no code. The fastest way to
  check a rule does what you meant.
- **Waiting for you** — the queue of paused agents, with everything a person
  needs to decide well, recorded properly.
- **History** — the searchable audit trail, with the integrity check.
- **Safety check** — a standing review surfacing over-permissioned agents, stale
  temporary access that should have lapsed, repeatedly-blocked agents that are
  probably misconfigured or compromised, and risky combinations of grants.
- **Ask for help** — an in-app assistant grounded in your actual workspace state,
  answering the question people really have: *why was my agent stopped, and what
  should I change?* It never touches credentials and stays off the enforcement
  path.
- **My team** — four roles, enforced server-side: Owner (everything), Admin
  (manage agents and rules, cannot remove people or mint other admins),
  Approver (decide what is waiting, change nothing), Viewer (read-only).
  Eighteen mutating endpoints are individually guarded, and the UI hides what
  your role cannot do rather than letting you click into a refusal. Separating
  *can change the rules* from *can approve an exception* is the classic
  segregation-of-duties control, and it is what makes Vexen usable by a finance
  approver who should never be able to edit policy.

### 4.9 The SDK: where the guarantee becomes real

An authorization service that is easy to forget to call is theatre. So the
integration surface is a decorator that wraps the function performing the actual
side effect:

```python
from vexen import Vexen

vexen = Vexen(api_key=VEXEN_AGENT_KEY, base_url=VEXEN_URL)

@vexen.guard("shopping", "purchase", amount="price", resource_id="sku")
def buy(sku, price):
    return stripe.PaymentIntent.create(...)   # the real thing
```

If Vexen blocks, `buy` never runs. If a human is needed, `buy` never runs until
they say yes, and then exactly once. And critically:

**If Vexen is unreachable, `buy` does not run.** The default is fail-closed. An
authorization layer that fails open is a compliance decoration; the first
network blip silently returns you to an ungoverned agent at the exact moment you
are least likely to notice. We made the safe behaviour the default and the
unsafe behaviour a deliberate choice.

The SDK raises distinct, catchable exceptions — `VexenBlocked`,
`VexenNeedsApproval`, `VexenUnavailable` — so an agent can explain itself to its
user, wait for the approval, or degrade gracefully.

## 5. How it is built

**Stack.** FastAPI (async Python) + React + MongoDB + Tailwind and shadcn/ui.
Anthropic Claude for rule authoring and the help assistant. Gmail SMTP over
`aiosmtplib` for mail. `pywebpush` with VAPID for push.

**The engine.** A pure, deterministic function with no I/O and no model in it.
Given an agent, its permissions, the workspace policies and a request, it
returns a decision. It runs **thirteen ordered steps**, each recorded in the
trace:

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

It is **default-deny**: the only path to ALLOW is an explicit grant that survives
every step. Anything unrecognised, malformed, expired or unmatched is refused.
Because the engine is pure it is trivially testable and, more importantly,
explainable — the trace *is* the explanation, so the UI, the audit record and the
SDK error all tell the same story from one source.

**Multi-tenancy.** Every record carries a workspace id and every query is scoped
to it. Cross-tenant isolation is verified explicitly in the test suite, including
through the unauthenticated public routes, the obvious place for a leak.

**Never blocking the event loop.** Password hashing runs in a threadpool, because
bcrypt on the event loop turns a burst of concurrent sign-ins into a full-service
stall. `pywebpush` blocks too, so push sends also go to a thread. Both came out
of load testing, not theory.

**The email outbox.** Nothing on a request path ever talks to an SMTP server. The
authorization endpoint writes a row into an outbox; one background worker drains
it, claiming messages atomically so two workers can never send the same one
twice. Retries are capped with exponential backoff, authentication failures are
terminal rather than retried forever, and sends are spaced to respect provider
rate limits. If mail is misconfigured or the provider is down, messages queue and
the product keeps working — a broken mailbox can never take down enforcement.

**Fire-and-forget where it is optional.** Push is dispatched as a background
task, because a slow push service must never delay an agent. Email is the
reliable channel; push is a convenience.

## 6. Design principles we held to

**Deterministic enforcement, probabilistic authoring.** A model may help you
write a rule. A model may never decide whether an action is allowed. This is not
conservatism; it is what makes the system auditable. You cannot certify a gate
that might answer differently tomorrow.

**Fail closed, everywhere.** Unreachable service: refuse. Malformed request:
refuse. Unrecognised permission: refuse. Expired grant: refuse. Ambiguous
approval: refuse. Every ambiguity resolves toward *no*.

**The governed thing does not get a vote.** Rules live outside the agent's
reach. Approval state is loaded server-side and the client's claims about it are
ignored. The agent cannot see, edit or assert its own authority.

**Plain language, always.** Whoever is accountable for the money should own the
permissions, and that person is usually not an engineer. So the product speaks in
*make a purchase* and *issue a refund*, not scopes and ARNs, and every refusal
explains itself in a sentence a non-technical person can act on.

**Honest UI over flattering UI.** If push cannot work in your browser we say so
and disable the switch, with the reason. If email is not configured we say the
message is queued rather than claiming it was sent. Security products that
overstate their own status are worse than none, because people rely on them.

**Convenience is a security feature.** A control humans find annoying gets
disabled, and a disabled control protects nothing. The two-tap phone approval
exists because adoption failure is the likeliest way this product fails to
protect anybody.

## 7. Who this is for

**Immediate wedge: teams putting agents anywhere near money or customers.**
Retail and e-commerce ops running purchasing and pricing agents. Support teams
running refund and account-change agents. Finance teams with invoice and
reconciliation agents. Recruiting teams with outreach agents. These teams are
either not shipping, or shipping with an uncomfortable amount of hope.

The buyer is frequently *not* the engineer who built the agent. It is the ops
lead, finance manager or founder who is accountable when it goes wrong and
currently has no instrument at all — a very specific, very motivated person that
almost nothing in the market is built for.

**Second wave: the platforms.** Agent frameworks, vertical AI products and
automation platforms that need to offer their own customers permissions and
approvals and would rather not build a governance layer. The decision API and the
audit trail are the primitives they would otherwise build badly.

**Third wave: regulated industries** — financial services, healthcare, legal,
government — where the audit trail and segregation of duties are preconditions
rather than features. Slower, and where the durable value sits, precisely because
the requirements are non-negotiable.

## 8. What genuinely exists today — the honest version

Everything described above is implemented and running: multi-user auth with four
server-side roles and verified tenant isolation; the deterministic 13-step
default-deny engine; 67 permissions and 10,639 deployable configurations; the
public authorize API with per-agent hashed keys; single-use, TTL-bound,
scope-bound, atomically-claimed approvals; a hash-verified audit trail with an
integrity check; AI rule generation with schema validation and fail-closed
behaviour; email alerts over a durable outbox plus two-tap signed phone approvals
with no login; browser push with VAPID; team invitations with session revocation
on removal; a Python SDK with a fail-closed guard decorator; and the full console
in light and dark, on desktop and mobile.

**Verification.** A maintained 55-check end-to-end regression suite covers
authentication, tenant isolation, deployment, the decision API, approval
single-use and replay refusal, role guards, invitations and alert queueing. An
independent pass returned 110 of 110 backend checks with no critical defects.
Real emails have been delivered through SMTP, and the phone approval flow has
been exercised from a mobile viewport through to the agent being allowed exactly
once and refused on replay.

**What does not exist yet, stated plainly:**

- **No paying users.** This is a working product, not a business with traction.
  We would rather say that than dress up a pilot as a customer.
- **One account belongs to one workspace.** Multi-workspace membership is a
  known limitation with a clear fix, and the API says so rather than failing
  silently.
- **The SDK is Python only.** TypeScript is the obvious next one, and the API is
  plain HTTP so any language can call it today.
- **Single-region deployment.** No data residency controls yet.
- **No SSO/SCIM, no SOC 2.** Both are table stakes for enterprise and both are
  scheduled rather than done.
- **Push delivery to a real lock screen** can only be proven on a real device;
  headless automation reports notifications as blocked. The mechanism is
  verified; the last mile needs a human with a phone.

Being precise about this boundary is itself evidence about how we build. A
security product that overstates its readiness is the specific thing we are
arguing against.

## 9. Why we think we win

**We are on the write path.** Observability tools watch. Guardrails read text.
We stand between the agent and the action, and we return an answer the agent
must obey. That is a fundamentally different and much stickier position: once
enforcement runs through us, removing us means accepting an ungoverned agent.

**We are deterministic, and that is a moat in this market.** Every regulated
buyer eventually asks "how do you know?" A probabilistic gate cannot answer. A
13-step ordered evaluation with a recorded trace and a verifiable hash can. As
agent regulation arrives — and it is arriving — "we can prove what was allowed
and who allowed it" moves from a nice differentiator to a purchase requirement.

**We built for the accountable non-engineer.** Almost everything in this
category is a developer tool sold to developers, but the person who cares most
about an agent's spending limit did not write the agent. Plain language, two-tap
phone approvals, an approver role that cannot edit rules, and a
10,639-configuration library so nobody starts from a blank page all follow from
taking that buyer seriously — and are hard to retrofit onto a developer tool.

**The hard parts are done and they are genuinely hard.** Single-use approvals
with atomic claiming and strict scope binding. Scan-safe email action links.
Hash-verified audit. Fail-closed SDK semantics. An outbox that keeps enforcement
fast when the mail provider is slow. Getting any one wrong makes the product
unsafe or unusable. A competitor can copy our screens in a fortnight; the
invariants take much longer, and most teams will not realise which ones matter
until something goes wrong in production.

**Timing.** The gap between "agents can act" and "agents can be governed" opened
about a year ago and is currently widening. Every week more agents get more keys.
This is the moment the permission layer gets chosen, and permission layers, once
chosen, tend to stay.

## 10. Business model

Usage-aligned, because our value scales with the number of consequential
decisions we make.

- **Free** — one workspace, a monthly decision allowance, full audit trail.
  Generous enough to protect a side project, because the alternative is an
  ungoverned agent.
- **Team** — per-seat for approvers plus a decision allowance. The natural
  landing spot for the initial wedge.
- **Business** — SSO, longer audit retention, custom policy bundles, data
  residency, priority support.
- **Platform** — API-metered and white-labellable, for products embedding
  permissions and approvals for their own customers.

Two principles. We never charge for the audit trail on any tier — evidence should
not sit behind a paywall in a security product, and accumulating history is our
best retention mechanism anyway. And allowances stay loose relative to seat
price, because pricing that discourages checking more actions is a perverse
incentive we refuse to build in.

## 11. Going to market

**Land through the SDK, expand through the approver.** An engineer adopts the
guard decorator for one dangerous function — usually the one that spends money.
The first time an agent is stopped and their ops lead gets the email and taps
Approve, the product has acquired its real champion. Approvers then pull it into
more workflows, because being asked beats finding out afterwards.

**Content that is genuinely useful.** Publishing honestly on single-use-approval
design, scan-safe email actions, fail-closed defaults and audit hashing reaches
exactly the people about to ship an agent with a production key — and
demonstrates competence rather than asserting it.

**Framework integrations**, so adoption is one import rather than a refactor. And
**partner with the observability layer** rather than compete: these are
complements, their users have our problem, and they have no interest in becoming
an enforcement layer.

## 12. Roadmap

**Next (weeks).** Multi-workspace membership. TypeScript SDK. A delivery log of
every alert sent. A weekly digest of what agents spent and what was approved.
Escalation if an approval sits unanswered.

**Then (months).** Native framework guards. Approval delegation and on-call
rotations, so the right person is asked at 2am. Anomaly detection on decision
patterns — an agent whose behaviour changes shape is the earliest signal of
compromise or misconfiguration. Policy simulation against historical traffic:
"if I add this rule, what would it have blocked last month?"

**Later.** SOC 2. SSO and SCIM. Data residency. Exportable signed compliance
reports. And an open specification for agent permissions, because being the
reference implementation of an open standard beats owning a closed one.

## 13. Risks, and what we actually do about them

**"The frameworks will just build this."** Some will build a version, but their
incentive is a feature that keeps developers inside their framework, not a
neutral control plane with an auditable record. We intend to be the layer that
works with all of them and is trusted precisely because it is owned by none — and
a framework's in-process interrupt is the architecturally weaker design anyway.

**"Adoption friction."** Real, and it is our biggest risk. If Vexen is annoying
it gets removed. Mitigations are already in the product: a one-line decorator, a
10,639-configuration library so nobody configures from scratch, two-tap phone
approvals, and plain-language refusals that tell you what to change.

**"Latency on the critical path."** Mitigated by a pure in-memory engine that
does zero I/O in the decision itself. We also think the framing is wrong: the
actions worth governing already take hundreds of milliseconds, and nobody minds
twenty more before a $700 purchase.

**"Fail-closed will cause outages."** It will occasionally stop legitimate work,
and that is the correct trade for actions of this consequence. We manage it with
clear errors that say exactly what happened, an explicit opt-out for low-stakes
actions, and eventually a cache for decisions that are safely cacheable.

**"Agents will route around it."** If an agent holds raw credentials it can
bypass a voluntary check. The end state is Vexen brokering short-lived, scoped
credentials so bypassing is impossible. The guard decorator is the pragmatic
first step; the credential broker is the architecturally complete one.

## 14. How we would like to be judged

Not on screenshots. On these:

1. **Does it actually stop an agent?** Point a real agent at it, block it, and
   confirm the side effect never happened.
2. **Can you break an approval?** Try to replay one, escalate the amount, reuse
   it for a different order, or forge a token. It should refuse every time.
3. **Can a non-engineer use it?** Give the console to somebody who has never
   seen an API key and see if they can grant a permission, write a rule and
   approve a paused action.
4. **Does the evidence hold up?** Alter an audit row directly in the database
   and confirm the integrity check catches it.
5. **Does it fail safely?** Take the service offline and confirm the guarded
   function refuses to run.

Those five are the product. Everything else is packaging.

## 15. Closing

We are not proposing to make AI agents smarter or safer to talk to. Plenty of
people are working on that.

We are proposing what every previous generation of powerful technology eventually
required, and this one conspicuously lacks: an external, deterministic, auditable
answer to *"is this allowed?"* — decided by a human in advance, enforced by a
system the actor cannot argue with, evidenced in a record that survives scrutiny,
and convenient enough that people leave it switched on.

Agents already have the keys. Somebody has to hold the lock.

