# Vexen - second application form (fundraising / general VC form)

Plain-text answers, straight hyphens only, no markdown inside the answers so they
paste cleanly into a web form. No character limits shown on this form, so these
are sized to be read in 60-90 seconds each.

CONFIRM BEFORE SUBMITTING:
- "How did you hear about us" - pick the option that is actually true.
- Fundraise amount and valuation - my recommendation is $750K on an $8M
  post-money SAFE cap. Change the numbers if you have a different target.
- Re-applying box - leave blank if this is your first submission.

---

## Q: How did you hear about us?

PRIMARY (use if true):
I build on Emergent - Vexen is developed and deployed there - and found Emergent
Ventures through the platform. I read what you back at pre-seed and it is the
closest fit I have found for where I actually am: a live product with 5,000+
users built solo, and a need for the two things capital alone does not solve - a
founding engineer out of authorization infrastructure, and someone who has sold
security through an enterprise procurement cycle.

SHORT ALTERNATIVES:
- Through the Emergent platform and its builder community - I build and deploy on
  Emergent, and Vexen itself runs on it.
- On X, from founders in the AI infrastructure space.
- Referred by [NAME], who suggested this was the right fit for a solo technical
  founder with a live product.

---

## Q: If you're re-applying, milestones hit since your earlier application

Leave blank - this is a first application.

IF RE-APPLYING, use this:
Since the earlier application: passed 5,000 users with no paid acquisition;
shipped the fail-closed Python SDK, hash-verified audit with an integrity
checker, and two-tap phone approvals over signed POST-only links; expanded the
configuration library to 10,639 ready-made agent setups; and moved from ad-hoc
testing to a maintained 55-check end-to-end regression suite, currently 55/55,
plus an independent 110/110 backend pass with no critical defects.

---

## Q: What's your startup called?

Vexen

---

## Q: What is the one-liner for your startup?

The permission layer for AI agents - for any team whose agents can spend money on
their behalf.

---

## Q: How much are you aiming to fundraise in this round? Valuation target/range?

Raising $750K as a pre-seed, on a post-money SAFE, targeting an $8M post-money
valuation cap. I am comfortable anywhere in a $7M-$10M range depending on partner
fit and speed, and open to a smaller first cheque with a larger round behind it.

What it buys: roughly 20 months of runway for a three-person team. About 55% goes
to two hires - a founding engineer out of IAM, fraud or payments to own the
credential broker, and a first go-to-market hire to run a ten-company
design-partner programme. About 25% to my own full-time focus and infrastructure.
About 20% to the things that unlock enterprise revenue: an external security
review and published penetration test, SOC 2 Type I, SSO and SCIM.

The milestones I am underwriting with it: the credential broker shipped, so
bypassing Vexen becomes impossible rather than merely discouraged; a TypeScript
SDK and native framework guards, the two most requested items from current users;
ten design partners with agents in production behind Vexen; and first paid
contracts. That set is the shape of a seed round.

I have taken no outside capital, have no investors and have not run a process, so
I am flexible on structure. I would rather optimise for the right partner than
the highest cap.

---

## Q: What's been your progress (tech, customer traction, funding, etc.) so far?

Vexen is live with over 5,000 users, built solo in two months, no paid
acquisition, no outside capital. It is a deployed product, not a prototype.

Tech, in production today. A per-action decision API returning ALLOW, BLOCK or
APPROVAL_REQUIRED with a machine-readable reason code and a full evaluation
trace. A deterministic 13-step, default-deny engine with no I/O and no model
anywhere in the enforcement path, so the same request always returns the same
answer and the trace is the explanation. 67 business-language permissions across
18 categories, each grant supporting numeric limits, resource restrictions,
action restrictions and expiry. Plain-English rule authoring - you type "any
purchase over $100 needs a person to approve it" and a model turns it into a
schema-validated rule, shown back to you before it takes effect; the AI writes
rules, the AI never enforces them. Approvals that are single-use, TTL-bound,
atomically claimed so two concurrent requests can never both spend one, and
scope-bound to permission plus resource id plus amount to the cent. Two-tap phone
approval with no login, over per-recipient signed email links where the decision
is POST-only, because corporate link scanners fetch every URL in a message and
would otherwise approve a $40,000 purchase before the human opened the email.
SHA-256 hash-verified audit with a verification pass that reports exactly which
rows were altered. A library of 10,639 ready-made agent configurations - 55
archetypes across 28 industries - so nobody configures a security posture from a
blank page. Multi-tenant workspaces with four server-side roles across 18
individually guarded mutating endpoints. And a fail-closed Python SDK: one
decorator above the function that performs the side effect. If Vexen blocks, it
never runs. If a human is needed, it never runs until they say yes, and then
exactly once. If Vexen is unreachable, it does not run.

Verified rather than asserted. A maintained 55-check end-to-end regression suite
covering authentication, cross-tenant isolation, the decision API, approval
single-use and replay refusal, and role guards - currently 55 of 55 passing. An
independent pass returned 110 of 110 backend checks with no critical defects.
Approval replay and amount escalation are covered tests, not intentions.

Traction. 5,000+ users in two months, content-led, the same way my previous five
products reached 100,000+ users between them with no marketing budget. What
matters more than the count is the sequence: users deploy a configuration from
the library, test a rule they wrote in plain English, then go looking for the
SDK. That sequence ends in production traffic. The most common requests are not
more permissions - they are TypeScript, native framework guards, and "can I stop
the agent bypassing this at all?", which is a request for the credential broker
already on the roadmap.

Funding. None. No investors, no process, entirely self-funded.

Not done yet, so you are not surprised later: no revenue, Python-only SDK, one
workspace per account, no SSO, SCIM or SOC 2, and the credential broker - the
piece that makes bypassing impossible rather than discouraged - is designed but
unbuilt. That is the next thing I ship.

---

## Q: Who are your customers? What specific problem are you solving and why is it
## important to them?

Customers. Teams that have put an AI agent somewhere near money, customers or
production. Concretely: e-commerce and retail ops running purchasing agents,
support teams running refunds and account changes, finance teams with invoice and
reconciliation agents, and platform teams at fintech and health companies who
need to offer their own customers permissions and approvals and would rather not
build a governance layer badly. There are two people in the room. The engineer
who deploys the agent integrates Vexen. The person who has to answer for what
that agent did - an ops lead, a finance lead, a CISO - is the reason they are
allowed to deploy it at all.

The problem. An agent's limits currently live in the prompt: "never spend more
than $100", "always ask before refunding". Those are suggestions, not
permissions. Nothing external checks them, nothing halts the action, and when
something goes wrong the evidence is scattered across model traces, vendor
dashboards and application logs, so nobody can answer "who allowed this?" in
under an hour.

Why it is important to them. The blocker on agents in production is no longer
capability, it is authority. So teams do one of two expensive things: keep the
agent in read-only demo mode and forfeit the entire return, or hand it a real key
and absorb a tail risk they cannot quantify, cap or explain to an auditor. The
first is expensive quietly. The second is expensive once.

What Vexen changes. One API call answers "is this specific agent allowed to do
this specific thing, right now?" and returns ALLOW, BLOCK or ASK A HUMAN,
deterministically, with no model in the enforcement path. If a human is needed
the agent halts and the accountable person approves in two taps on their phone,
no login. Every decision lands in a hash-verified record you can hand to somebody
who does not trust you. It turns "should we let the agent do this?" from a leap of
faith into a normal engineering decision with a limit, an owner and a receipt.

---

## Q: Why did you / your co-founding team start this startup? Why are you the
## right founder to lead it?

Why I started it. Vexen is my sixth product, and every one before it was an
interpreter between a person and complex information about their own life:
HealthLens for health data, past 70,000 users; AI-Namo for document authenticity,
past 20,000 and adopted by a local government for fraud prevention; GreenGuide
for plant disease, past 10,000; CerebroAegis for health and safety, past 5,000.
Building agentic features into those, I kept hitting the same wall from the other
side. I had systems that could act, and the only thing between a bug and a real
consequence was a sentence in a prompt politely asking the model to behave. That
is not a control. We never solved this for humans by making humans more
trustworthy either - we constrained them: spending authority, dual control,
segregation of duties, audit trails. At scale you cannot verify intent, you can
only constrain consequence. Agents got the capability and skipped the control
layer entirely, and every previous era of computing eventually grew one -
mainframes got RACF, networks got Active Directory, cloud got IAM, SaaS identity
got Okta. Agents have nothing, that gap opened about a year ago, and it widens
every week as more agents get more keys.

Why I am the right person. Two arguments and one admitted gap. First, I build
security-shaped systems correctly, and here the invariants are the product:
single-use, TTL-bound, atomically-claimed, scope-bound approvals; POST-only
signed email actions so a link scanner cannot approve on your behalf; a
hash-verified audit; a fail-closed SDK. Most implementations get one or two of
those right and ship an approval that can be replayed or amount-escalated, which
is worse than no approval, because now a signed-looking record claims a human
agreed. Second, I ship and I distribute: 100,000+ cumulative users across five
products with no paid acquisition, plus an educational channel past 3 million
views. That is precisely how a security primitive spreads - you reach the
engineer the week before they ship an agent with a production key. And on the
commercial side, as COO of The1550Formula, an AI-first SAT prep company, I helped
run it to roughly $70,000 a month with 1,000+ students improving about 200 points
on average, so I have seen the unglamorous distance between a signup and a
customer. That distance is exactly where Vexen stands now.

The gap, stated plainly: I have never sold an infrastructure security product
through an enterprise procurement cycle. That is what my second hire is for, and
I would rather name it than have you find it.

---

## Q: What will your startup look like in 10 years?

In ten years Vexen is the answer to one question every organisation has to answer
continuously: what is this non-human actor allowed to do, right now, up to what
magnitude, and who signed off?

The path there has three steps. First, the enforcement layer teams choose - where
we are now. Second, the credential broker, which is the real product: instead of
an agent choosing to ask permission, it is issued short-lived, scoped,
single-purpose credentials and physically cannot exceed its authority. That turns
a convention into a constraint. Third, the artefact - a portable, verifiable
statement of bounded authority that travels between organisations, so when two
companies' agents transact there is a record their auditors, regulators and
insurers will accept. That primitive does not exist today, and agent commerce
needs it. So, plausibly, does agent insurance, which is not yet a category.

The version I actually care about is an open standard. Every team inventing agent
permissions right now is inventing them differently, so there is no way to ask
"what is this agent allowed to do?" across two systems, no way to carry an
approval between them, and no shared vocabulary a regulator can point at.
Identity got SAML and OAuth. Payments got card network rules. Agent authority has
nothing, and the window in which those conventions get set is open now and will
not stay open. I would rather be the reference implementation of an open standard
than the owner of a closed one - and I think that is the larger outcome, because
it is the version one person can start and an incumbent structurally cannot.

Commercially, that is a layer used once per action rather than once per employee,
so usage grows with automation rather than headcount, sitting on the write path
in commerce, financial services, healthcare and government, where removing it
means accepting an ungoverned system - which nobody does to save money.
Permission layers, once chosen, are almost never removed.

And eventually it is not only software agents. The same question is unanswered
for delivery robots, industrial automation and clinical decision support. I do
not think the important artefact of this era is a model. I think it is a
portable, verifiable statement of bounded authority, and almost nobody is
building it.

---

## Q: Answer 1 of 3 (chose #1: proudest accomplishment before the age of 21)

AI-Namo. I built an AI platform that verifies government documents and flags
altered or fraudulent ones, and a local government adopted it and used it inside
their real process. It passed 20,000 users.

The reason it is the one I am proudest of is not the number. Everything I had
built before it was optional to the people using it - genuinely useful, but if it
vanished overnight their day still worked. This one became part of how an
institution decided whether to trust a piece of paper. Someone was going to be
approved or refused partly because of code I had written alone, and nobody was
checking my work.

That changed how I build. It was the first time I thought harder about what
happens when the system is wrong than about what happens when it is right - false
positives, appeals, who is accountable, what evidence exists afterwards. I became
noticeably more careful, and much more interested in the boring parts: defaults,
failure modes, records.

Everything about Vexen comes from that. It is the same instinct pointed at a
larger asymmetry: a system taking a consequential action on somebody's behalf,
and the discipline of making sure that when it is wrong, it fails in a direction
a human can see, explain and undo. I am prouder of learning that than of the user
count.

ALTERNATIVE - if you would rather answer #3 (unrelated hobby), tell me the hobby
and I will write it in the same voice.
