# Vexen — Emergent Ventures Founder Fellowship & Fundraising application

Form questions answered below. Assumptions I made — CONFIRM BEFORE SUBMITTING:
- Founding team: solo founder, no co-founder yet.
- Fundraising: has NOT raised and has NOT run a process in the last 6 months.
- Vexen user count: 5,000+ (confirmed by founder).
- Live product link uses the current preview URL; swap for a custom domain if one
  exists.

Founder facts used: HealthLens 70k+, AI-Namo 20k+ (adopted by a local
government), GreenGuide 10k+, CerebroAegis 5k+, Vexen 5k+, PythonPal 100+
students, HorizonSTEM 150+. COO of The1550Formula, ~$70k/month, 1,000+ students,
~+200 SAT points. Educational YouTube channel 3M+ views.

---

## Q: Do you have a founding team?

No — I am a solo founder.

I designed, built, tested and deployed all of Vexen myself over two months: the
deterministic decision engine, the multi-tenant backend, the console, the email
and push delivery paths, the Python SDK, and the 10,639-configuration library. It
is live with over 5,000 users.

I am actively looking for a founding engineer and a first go-to-market hire. Both
profiles, and why those two specifically, are in my answer to the recruiting
question below.

---

## Q: Have you raised any funding or actively fundraised in the last 6 months?

No. Vexen has taken no outside capital, has no investors, and I have not run a
fundraising process. It has been built and shipped entirely self-funded. This
application is the first formal investor conversation I have had about it.

---

## Q: What primary problem space(s) are you pursuing and why is it important?

The primary space: authorization and accountability for autonomous software.

AI agents now hold real credentials. They spend money, refund customers, email
clients, write to production databases and delete files. Their limits live in
prompts — "never spend more than $100", "always ask before refunding" — which are
suggestions, not permissions. Nothing external checks them. And when something
goes wrong, the evidence is scattered across model traces, vendor dashboards and
application logs, so nobody can answer "who allowed this?" in under an hour.

I think this is the load-bearing gap in the agent stack, and almost all the money
is going somewhere else. The industry is trying to make models more trustworthy:
better alignment, guardrails, evals, prompts. But we never solved that problem
for humans by making humans more trustworthy. We solved it with external limits —
spending authority, dual control, segregation of duties, audit trails — because at
scale you cannot verify intent, you can only constrain consequence. A bank teller
can be completely honest and still not be permitted to move ten million dollars
alone.

So I am building Vexen: the permission layer for AI agents. One API call answers
"is this specific agent allowed to do this specific thing, right now?" and returns
ALLOW, BLOCK or ASK A HUMAN — deterministically, with no model anywhere in the
enforcement path. If a human is needed the agent halts and the accountable person
gets a two-tap approval on their phone, no login required. Every decision is
written to a hash-verified audit record you can hand to someone who does not
trust you.

Why it matters: every previous generation of computing grew a permission layer,
and each one became large and durable. Mainframes got RACF. Networks got Active
Directory. Cloud got IAM. SaaS identity got Okta. Agents have nothing. Whoever
builds this sets the conventions for how autonomous software is held accountable,
and that gap opened about a year ago and widens every week as more agents get
more keys.

Two adjacent spaces I would happily be pulled toward, because they are the same
primitive pointed somewhere harder:

Agent-native credentials. Today Vexen is a check an agent chooses to make. The
complete version is a broker that issues short-lived, scoped, single-purpose
credentials, so an agent physically cannot exceed its authority rather than being
asked not to. That is a bigger and more defensible company than a policy engine,
and I think it is where this ends up.

Machine-to-machine consent and liability. When two companies' agents transact,
who is liable? There is currently no artefact either side's insurer would accept.
A portable, verifiable record of "this agent was permitted to do this, and this
named human authorised the exception" is the missing primitive for agent
commerce — and possibly for agent insurance as a category that does not exist yet.

And the genuinely out-there one, which is what I actually want to build: an
accountability layer for autonomy in general, not just software agents. The same
question — what is this actor allowed to do, right now, up to what magnitude, and
who signed off — is unanswered for delivery robots, industrial automation and
clinical decision support. I do not think the important artefact of this era is a
model. I think it is a portable, verifiable statement of bounded authority, and
nobody is building it.

---

## Q: What expertise do you have related to this idea? Why are you the right
## person to work on this?

Two kinds of relevant expertise: I build security-shaped systems correctly, and I
get products to users without a budget.

On building. I wrote all of Vexen alone: a pure, deterministic thirteen-step
default-deny engine with no I/O and no model in the enforcement path; approvals
that are single-use, TTL-bound, atomically claimed and scope-bound to the exact
permission, resource id and amount to the cent; scan-safe signed email action
links where the decision is POST-only, because corporate link scanners fetch every
URL in a message and would otherwise approve a $40,000 purchase before the human
opened the email; a SHA-256 hash-verified audit trail with an integrity checker;
server-side RBAC across eighteen individually guarded mutating endpoints; a
durable email outbox so a slow SMTP provider can never slow enforcement; and a
fail-closed SDK where the guarded function does not run if the service is
unreachable. Those invariants are the product. Most implementations get one or
two of them right and ship an approval that can be replayed or amount-escalated,
which is worse than no approval at all, because now a signed-looking record says
a human agreed.

On shipping and distribution. Vexen is my sixth product. HealthLens, an AI
wellness platform, passed 70,000 users. AI-Namo, an AI government-document
verification platform, passed 20,000 and was adopted by a local government for
real document verification and fraud prevention — which is the closest analogue to
this work: an institution depending on software I wrote to make a trust decision.
GreenGuide, an agricultural copilot for growers, passed 10,000. CerebroAegis, a
health and safety platform, passed 5,000. That is over 100,000 cumulative users
with no paid acquisition, and it came from building in public and explaining
things clearly — which is also how an educational channel of mine passed three
million views. That matters here specifically: content-led distribution is exactly
how a security primitive spreads, because you reach the engineer the week before
they ship an agent with a production key.

On the commercial side. As COO of The1550Formula, an AI-first SAT preparation
company, I helped run it to roughly $70,000 a month in revenue with over 1,000
students improving by about 200 points on average. So I have seen the unglamorous
half — support, retention, pricing, the distance between a signup and a customer.
That distance is exactly where Vexen is standing right now.

The through-line. Every product I have built is an interpreter between a person
and complex information generated about them: health data for the patient, a
document's authenticity for the official, a diseased plant for someone who is not
a botanist. Vexen interprets an agent's intended action for the person who is
accountable for it — and then does the thing none of the others could, which is
stop it.

Where I am not yet the right person, said plainly: I have never sold an
infrastructure security product into an enterprise procurement cycle. That is the
specific gap the first hire closes, and I would rather name it than have you find
it.

---

## Q: What progress have you made on this idea?

Vexen is live and deployed with real users — not a prototype. Built solo in two
months, currently past 5,000 users, no paid acquisition.

Working today:

- The decision API. Per-action authorization with agent-scoped keys that are
  generated once, shown once and stored hashed, returning ALLOW, BLOCK or
  APPROVAL_REQUIRED with a machine-readable reason code and full evaluation
  trace.
- A deterministic thirteen-step, default-deny engine. No I/O and no model in the
  enforcement path, so the same request always returns the same answer and the
  trace is the explanation — the console, the audit record and the SDK error all
  tell the same story from one source.
- 67 business-language permissions across 18 categories, ten flagged sensitive,
  each grant supporting numeric limits, resource restrictions, action
  restrictions and expiry.
- Plain-English rule authoring. You type "any purchase over $100 needs a person
  to approve it" and a model turns it into a schema-validated rule, shown back in
  plain language before it takes effect. The AI writes rules; the AI never
  enforces them.
- Approvals that hold up. Single-use, thirty-minute TTL, atomically claimed so
  two concurrent requests can never both spend one, scope-bound to permission
  plus resource id plus amount to the cent, and every client-side claim about
  approval state ignored.
- Two-tap phone approval with no login. Per-recipient HMAC-SHA256 signed
  24-hour email action links carrying ids only, with the decision POST-only so a
  link scanner cannot approve on your behalf. Plus browser push over VAPID.
- Hash-verified audit. SHA-256 per event, and a verification pass that recomputes
  every hash and reports exactly which rows were altered.
- A library of 10,639 ready-made agent configurations — 55 archetypes across 28
  industries and 7 capability tiers — so nobody configures a security posture
  from a blank page.
- Multi-tenant workspaces, four server-side roles across eighteen individually
  guarded mutating endpoints, team invitations with session revocation on
  removal.
- A fail-closed Python SDK: one decorator above the function that performs the
  side effect. If Vexen blocks, it never runs. If a human is needed, it never
  runs until they say yes, and then exactly once. If Vexen is unreachable, it
  does not run.

Verification rather than assertion. A maintained 55-check end-to-end regression
suite covers authentication, cross-tenant isolation, the decision API, approval
single-use and replay refusal, and role guards — currently 55 of 55 passing. An
independent pass returned 110 of 110 backend checks with no critical defects.
Real emails deliver over SMTP, and the phone approval flow has been exercised end
to end from a mobile viewport: allowed exactly once, refused on replay.

Not done yet, so you are not surprised later: no revenue, Python-only SDK, one
workspace per account, no SSO, SCIM or SOC 2, and the credential broker — the
piece that makes bypassing impossible rather than merely discouraged — is
designed but unbuilt. That is the next thing I want to ship.

---

## Q: Share links to any artifacts you've built or published.

- Demo video (narrated walkthrough): https://youtu.be/V5SaKRhMmcM
- Live product, sign up and try it: https://action-guard-1.preview.emergentagent.com
- Supporting technical document, 19 pages, covering the engine, the approval
  invariants, the threat model and the test results:
  https://action-guard-1.preview.emergentagent.com/api/download/supporting-document
- Direct MP4 of the demo, if the hosted version is inconvenient:
  https://action-guard-1.preview.emergentagent.com/api/download/demo-video

The fastest way to evaluate it is not the video. Sign up, deploy a purchasing
agent from the library, set the approval threshold to $10, and try to make the
agent spend $50. It will stop, and your phone will ask you.

---

## Q: Who are the next 2-3 people you'd want to and could recruit to your team,
## and why?

My bias on talent density: at this stage I would rather have three people who
have each personally shipped the exact thing I am asking them to ship than ten
who are willing to learn it. Vexen is a security product, and in security the
difference between competent and excellent is not speed — it is whether someone
has already met the failure mode you have not thought of yet. So each of these
closes a gap I can name.

1. A founding engineer who has built authorization or payments infrastructure at
scale. Ideally out of an IAM, fraud or payments team — Stripe, Okta, Auth0, or a
bank's internal controls group. Why: the credential broker is the highest-leverage
and most dangerous item on my roadmap. Going from "the agent chooses to check" to
"the agent is issued short-lived scoped credentials and physically cannot exceed
them" is a token lifecycle and key management problem, and it is the class of
problem where a subtle mistake stays invisible until it is catastrophic. I want
somebody who has carried a pager for a system where a bug meant money moved
incorrectly. Concretely they own the broker, multi-language SDKs and framework
guards — and they are the person whose job includes telling me no.

2. A first go-to-market hire who has sold an infrastructure control into a
mid-market ops or finance buyer. Not an AI salesperson — someone who has sold
observability, security or compliance tooling through a six-month procurement
cycle and can run a design-partner programme properly. Why: this is the honest gap
in my own skill set. I can get a hundred thousand people to use something free; I
have never converted a free user into a security budget line, and I would rather
hire that answer than spend a year rediscovering it badly. Their first objective
is not a pipeline — it is ten real design partners with agents in production
behind Vexen, telling us where the approval flow breaks inside a real approval
chain.

3. A security engineer or researcher whose actual job is to attack it. Either an
early hire or a retained long-term reviewer. Why: a security product that has
never been attacked by a stranger is an untested claim. Every invariant I care
about — approval replay, amount escalation, token forgery, cross-tenant leakage
through the unauthenticated public routes — is precisely the class of thing the
author is worst placed to test. I want this person publishing what they find,
including the unflattering parts, because in this category credibility is the
product.

The ordering is deliberate. Engineer first, because the broker is what turns the
guarantee from a convention into a constraint. Go-to-market second, because once
there is something unavoidable to sell, the only remaining question is whether
anyone pays. Security third in sequence but not in importance — if the right
adversarial person appeared first, I would take them first.

On sourcing: I expect to find the engineer and the security researcher by
publishing openly on the hard parts — single-use approval design, scan-safe email
actions, fail-closed defaults, audit hashing — because that is how you attract
people who care about invariants rather than roadmaps, and it is the same method
that got my previous products their first users. The go-to-market hire is the one
I do not know how to source alone, and it is one of the specific things I would
ask this fellowship for.

---

## Short-form fields (verified character counts, CRLF-safe)

Startup name: Vexen

One-liner (95 / 100):
The permission layer for AI agents - for any team whose agents can spend money on their behalf.

Primary category: Infrastructure / Developer Tools
  (if unavailable: Security / Cybersecurity)
Secondary category: Security / Cybersecurity
  (if unavailable: B2B SaaS / Enterprise Software)

Company website: https://action-guard-1.preview.emergentagent.com
Founded: June 2026        <- CONFIRM
Product launch: July 2026 <- CONFIRM

Pitch deck: 18 slides, 3.7 MB
  /app/memory/vexen-pitch-deck.pdf
  https://action-guard-1.preview.emergentagent.com/api/download/pitch-deck

Startup description (780 / 800), Anything else (969 / 1000) and
Traction notes (981 / 1000) are the exact strings held in
/app/deck/check_fields.py - run `python /app/deck/check_fields.py` to re-verify
counts after any edit.
