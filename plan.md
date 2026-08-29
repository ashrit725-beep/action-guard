# Vexen (AI Agent Security & Permissions) — Development Plan (Updated)

## 1) Objectives
- Deliver a production-quality **multi-user** web app where AI agents request actions and Vexen returns **ALLOW / BLOCK / APPROVAL_REQUIRED**, with a **tamper-evident audit trail**.
- Keep the **deterministic server-side authorization engine** (**default-deny**) as the backend source of truth.
- Ship a **real public authorization API**: `POST /api/v1/authorize` callable by external agents using **real agent API keys** (generated once, shown once; stored hashed).
- Implement end-to-end features: **agents**, **permissions**, **limits**, **policies**, **approvals**, **audit log**, **security center**, and a **Try It guide/checker**.
- Add an **AI natural-language → policy rule generator** (Anthropic Claude) with strict schema validation and safe failure modes (fail closed).
- Provide premium UI/UX: **LIGHT-FIRST** design (airy enterprise UI), with a **Dark/Light theme toggle** and plain-language UX.
- Provide a **massive Agent Template Library (10,000+ templates)** with search/filter and one-click deploy.
- Include public marketing pages: **Landing** (with embedded demo video), **Contact**, plus a **Developer API** page.

**Objective (Phase 6/7): “100,000 devices + real app at scale”**
- Ensure the app behaves like a **real enforcement layer**, not a simulator:
  - approvals are **single-use**, **short-lived**, and **atomically claimed** (no replay)
  - external agents can **poll approval status** via an agent-authenticated endpoint
  - Developers page must only show **publicly reachable URLs** (no internal cluster hostnames)
- Ensure wide device/browser compatibility:
  - no mobile horizontal overflow
  - resilient storage (localStorage/sessionStorage can be blocked)
  - robust date parsing/formatting across strict Safari/WebViews
  - clipboard-copy fallback
  - cross-engine demo video playback (Chrome-class, Firefox, Safari/iOS)
- Ensure baseline scale viability:
  - concurrent signups/logins don’t crash or get incorrectly throttled
  - password hashing doesn’t block the event loop
  - unique org/workspace creation never 500s under race

**Objective (Phase 8): “It must actually stop agents” (in-path enforcement)**
- Provide a **drop-in guard** that wraps the function that performs the real side effect.
- Default behavior is **fail-closed**: if Vexen is unreachable, the side effect must not run.
- Ensure enforcement claims are verifiable:
  - if Vexen blocks, the wrapped function never runs
  - a human approval enables **exactly one retry** within a short window
  - approval replay and scope escalation are refused

**Objective (Phase 9): “In-app help chatbot”**
- Add a plain-language helper that:
  - is **grounded in the user’s workspace state** (agents/rules/approvals/recent stops)
  - never requests or reveals passwords or API keys
  - does not block the backend event loop
  - is accessible and works on mobile + dark mode

**Objective (Phase 10): “Production cleanup & repo hygiene”**
- Remove non-production test scripts, one-off tooling, and artifact directories.
- Keep exactly one **legitimate** backend smoke test for regression checks.
- Do **not** modify or purge MongoDB data as part of cleanup.
- Ensure the application does not depend on any removed files at runtime.

**Objective (Phase 11): “Robust demo video fallback”**
- Ensure the Landing demo video modal doesn’t show a false “cannot play” fallback when the browser can play at least one provided format.
- Provide a safe fallback UX for codec-limited environments.

**Objective (Phase 12–14): “Enterprise operations: alerts + phone approvals + teams”**
- **Email alerts**: notify the right people the moment an agent is paused.
- **Approve-by-phone**: approvals can be decided from a phone without opening the console.
- **Team seats**: invite teammates and enforce roles server-side.
- **Browser push**: optional device notifications for approvals.

---

## 2) Implementation Steps

### Phase 1 — Core POC (single script `test_core.py`, fix-until-green)
**Goal:** prove the hardest pieces in isolation before building the app.

**Status:** ✅ Completed.

---

### Phase 2 — V1 App (FastAPI + MongoDB + React/Tailwind)
**Goal:** build the full product around the proven core, ensure it’s a real multi-user app, and deliver a polished, light-first UI.

#### Phase 2A — Backend
**Status:** ✅ Completed and integrated.

#### Phase 2B — Frontend Completion + UX Polish
**Status:** ✅ Completed.

---

### Phase 3 — End-to-End Testing + Fixes
**Status:** ✅ Completed (iterations 1–5), plus continued verification thereafter.

---

### Phase 4 — Demo Video
**Status:** ✅ Completed and verified.

---

### Phase 5 — Final Polish: Dark Mode QA + Cleanup
**Status:** ✅ Completed.

---

### Phase 6 — Device & Browser Compatibility (“100,000 devices”)
**Status:** ✅ Completed.

---

### Phase 7 — “Genuinely real” enforcement + scale readiness
**Status:** ✅ Completed.

---

### Phase 8 — Genuine in-path enforcement (“actually stops agents”)
**Status:** ✅ Completed.

---

### Phase 9 — In-app help chatbot
**Status:** ✅ Completed.

---

### Phase 10 — Production Cleanup
**Status:** ✅ Completed.

---

### Phase 11 — Cross-browser demo-video fallback fix
**Status:** ✅ Completed.

**Fix recorded:** browsers without H.264 previously triggered a false failure because React forwarded `<source>` errors to the `<video>` handler. Landing modal now waits for `NETWORK_NO_SOURCE` before showing the fallback and includes a direct WebM fallback link.

---

### Phase 12 — Email alerts + one-tap approve/refuse by phone
**Goal:** the moment an agent is paused waiting for a human, the right people get an email with big Approve / Refuse buttons that work on any phone.

**Locked decisions (from user):**
- Email transport: **Gmail SMTP** (sender: `email.vexanai@gmail.com`, app password).
- Approve-by-phone: **email one-tap links** + **browser push** (Phase 14). **NO SMS / no Twilio**.
- Recipients: **per-person toggle**, default recipients are **Owners + Admins + Approvers**.

#### Phase 12A — Mail plumbing (backend)
**Status:** ✅ Completed.
- New `/app/backend/vexen/mailer.py`:
  - Gmail SMTP sender using `aiosmtplib`
  - STARTTLS on `smtp.gmail.com:587` (465 implicit TLS fallback)
  - multipart (plain + HTML), friendly From (`Vexen Security`), Reply-To, Message-ID, Auto-Submitted
  - strips cosmetic spaces from Gmail app passwords
- Mongo `email_outbox`:
  - `{id, org_id, user_id, to, subject, html, text, kind, status, attempts, last_error, created_at, next_attempt_at, sent_at}`
  - indexes: status/next_attempt_at/created_at; org_id/created_at; id unique; dedupe_key unique (partial)
- Background drain worker started in FastAPI lifespan:
  - atomic claim (`find_one_and_update`) → cannot send twice
  - retries capped at 5 with exponential backoff up to 30m
  - terminal errors: auth failures (535/534) / authentication exceptions
  - spacing: 0.6s between sends to stay under Gmail quotas
  - request paths never touch SMTP

#### Phase 12B — Signed one-tap approval links (secure + scan-safe)
**Status:** ✅ Completed.
- New `/app/backend/vexen/links.py`:
  - HMAC-SHA256 signed tokens w/ domain separation (`vexen-link-v1:` + `JWT_SECRET`)
  - carries org id + approval id + **recipient user id**; TTL 24h
  - verify returns None (never raises, never explains)
- New `/app/backend/vexen/routes_public.py`:
  - `GET /api/public/approvals/{token}` is read-only preview
  - `POST /api/public/approvals/{token}/decision` decides (approve/deny)
  - **Security design**: GET never mutates (scan-safe against link-prefetch)
  - reuses the same decision logic as console and re-evaluates request so enforcement invariants remain real

#### Phase 12C — Recipient selection + per-person Settings
**Status:** ✅ Completed.
- `NotificationPrefs` extended:
  - `email_approval_requests` (default on)
  - `email_blocked_actions` (default off)
  - `email_team_activity` (default on)
- Recipients:
  - membership role in `(owner, admin, approver)` AND user’s own toggle enabled

#### Phase 12D — Frontend approve-by-link page
**Status:** ✅ Completed.
- New public page `/approve/:token` (`/app/frontend/src/pages/ApproveByLink.js`)
  - mobile-first, large touch targets, optional note
  - all states: loading, pending, approved/refused, already decided, expired/invalid
  - light/dark supported

#### Phase 12E — Hook into hot path (queue only)
**Status:** ✅ Completed.
- `service.evaluate_and_record(...)` now accepts `base_url`
- callers pass `public_base_url(request)` so links are publicly reachable
- approvals queue email into outbox only (non-blocking)

#### Phase 12 Verification Evidence
- Targeted suite: **22/22** checks passed, including a **real Gmail delivery**.
- Security: GET does not approve; tampered token returns 404; token is single-use; decision recorded to the correct recipient.
- Regression: global smoke still green.

---

### Phase 13 — Team seats: invites + roles
**Goal:** multi-user workspaces with roles and invites; strict backend enforcement.

#### Phase 13A — Roles model + enforcement
**Status:** ✅ Completed.
- Roles:
  - `owner`: everything
  - `admin`: manage agents/policies/keys; invite approver/viewer; cannot manage members
  - `approver`: approve/deny + read-only
  - `viewer`: read-only
- `Principal` now includes `role`; role guards added:
  - `editor_principal` (owner/admin)
  - `approver_principal` (owner/admin/approver)
  - `owner_principal` (owner only)
- Applied to **18** mutating endpoints across agents, governance, org settings, simulator, approvals.

#### Phase 13B — Invitations
**Status:** ✅ Completed.
- New `/app/backend/vexen/routes_team.py`:
  - `GET /api/team`
  - `POST /api/team/invites`
  - `POST /api/team/invites/{id}/resend`
  - `DELETE /api/team/invites/{id}`
  - `PATCH /api/team/members/{user_id}` (owner only)
  - `DELETE /api/team/members/{user_id}` (owner only; revokes sessions)
  - public:
    - `GET /api/public/invites/{token}` preview
    - `POST /api/public/invites/{token}/accept` (creates user inside org)
- Rules:
  - owner can invite admin/approver/viewer
  - admin can invite approver/viewer only
  - approver/viewer cannot invite
  - role=owner rejected
- Invite delivered via email outbox; link is `/join/<token>` (7 days)
- Team changes are recorded as **in-app notifications** (not in the audit hash chain, which is reserved for agent decisions).

**Bug found + fixed (Phase 13):**
- Invite acceptance previously allowed weak passwords; now uses same `password_problems()` rules as signup (returns 422).

**Known MVP limitation:**
- One account belongs to one workspace; accepting invite for an email that already has a Vexen account returns 409 with a clear explanation.

#### Phase 13C — Team page (frontend)
**Status:** ✅ Completed.
- New `/app/team` page:
  - members list + role badges
  - invite dialog with role cards + descriptions
  - pending invites: resend/cancel, copy link
  - owner Manage menu: role change and remove member with confirmation
  - role-aware UI (approver/viewer cannot invite; only owner sees manage)
- New public `/join/:token` page:
  - shows workspace + role + invited email
  - requires strong password
  - on success signs in and lands in `/app/guide`
- Sidebar includes “My team”; account menu shows user’s role.

#### Phase 13 Verification Evidence
- Targeted suite: **44/44** checks passed.
- Verified all role restrictions across all mutating endpoints.

---

### Phase 14 — Browser push notifications
**Goal:** optional device notifications that can take the user straight to the approval decision page.

#### Phase 14A — VAPID + backend
**Status:** ✅ Completed.
- Installed: `pywebpush`, `py-vapid`
- VAPID keys generated once and appended to backend `.env`:
  - `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`, `VAPID_SUBJECT`
- New `/app/backend/vexen/push.py`:
  - uses `asyncio.to_thread` (blocking library)
  - prunes dead subscriptions on 404/410
  - never raises to the caller
- New endpoints:
  - `GET /api/push/status`
  - `POST /api/push/subscribe` (https-only endpoint)
  - `DELETE /api/push/subscribe` (one endpoint or all)
  - `POST /api/push/test` (honest messaging)
- Subscriptions stored in `push_subscriptions` with indexes:
  - unique `endpoint`
  - `(org_id, user_id)`
- `push_approval_alerts()` is fired via `asyncio.create_task(...)` from approval creation; never blocks `/api/v1/authorize`.

#### Phase 14B — Frontend + service worker
**Status:** ✅ Completed.
- New minimal service worker `/sw.js`:
  - handles `push` and `notificationclick` only
  - no caching and no fetch interception (normal app behavior unchanged)
- Added `/manifest.json` + icons (`/icons/*`, `/favicon.png`)
  - enables Add-to-Home-Screen for iOS push
- New `/app/frontend/src/lib/push.js`:
  - honest capability detection: unsupported, permission denied, iOS needs install
- Settings “Alerts” tab:
  - new “Notify me on this device” card with toggle and “Send me a test” button
  - disables toggle with clear text when push cannot work

#### Phase 14 Verification Evidence
- API endpoints exercised end-to-end.
- Static assets verified 200: `/sw.js`, `/manifest.json`, icons.
- Service worker registration verified without breaking the landing page.
- Note: actual lock-screen delivery cannot be proven from headless automation; requires user confirmation on their own device.

---

## 3) Next Actions
1. **User acceptance testing**:
   - Confirm approval emails land quickly and the approve/refuse link works on your phone.
   - Turn on “Notify me on this device” on a real phone (iOS requires add-to-home-screen).
   - Invite a teammate and confirm role restrictions match expectation.
2. (Optional hardening) Add a small admin “Delivery” panel for the email outbox if desired (currently visible via API).
3. (Optional future) Multi-workspace switching (removes the 1-account/1-org limitation).

---

## 4) Success Criteria
- Demo video reliably plays from the Landing page popup on real browsers (Chrome/Edge, Firefox, Safari/iOS), with seeking; UX is helpful if autoplay is blocked.
- Demo fallback logic does not falsely fail when one format fails but another works.
- Dark mode is aesthetically consistent and legible across **all routes**, including modals, tables, toasts, and disabled states.
- App remains usable when localStorage/sessionStorage are blocked or throw.
- No mobile horizontal overflow for common device widths (320, 360, 390, 768, 1280, 1920).
- No console-blocking errors.
- App builds for production (`yarn build`) and core flows remain green.
- **Real enforcement correctness:** approvals are single-use, short-lived, and cannot be replayed; claim is atomic.
- **External-developer correctness:** Developers page and API only advertise public URLs; copied commands work from another machine.
- **Scale sanity:** concurrent signups/logins don’t crash; rate limits don’t lock out shared-IP users; password hashing doesn’t block other requests.
- **In-path enforcement:** the shipped guard SDK prevents side effects when blocked/unreachable, and only allows the approved action once.
- **In-app assistant:** grounded, plain-language answers; no key/password leakage; does not block the server; works on desktop + mobile + dark mode.
- **Production hygiene:** throwaway scripts/artifacts removed; smoke test passes.

**Success criteria (Phases 12–14):**
- When an agent enters `APPROVAL_REQUIRED`, Vexen queues **exactly one** approval alert per eligible recipient (subject to per-person toggles) without slowing `/api/v1/authorize`.
- Approval alert email arrives (Gmail SMTP) and includes an approve-by-link URL that works on mobile.
- Approve-by-link is scan-safe (GET never performs the decision); user must tap confirm.
- Role enforcement:
  - viewers cannot mutate anything (403)
  - approvers can decide approvals but cannot edit policies/agents
  - admins can manage policies/agents but cannot remove members or create new admins
  - only owners can change roles and remove members
- Invite flow:
  - invite email sent via outbox
  - accept invite creates account in org and assigns role
  - invite token is single-use; revoked invites cannot be used
- Push notifications:
  - subscription stored per-device
  - push message opens the correct decision screen
  - dead subscriptions are pruned automatically on 404/410

---

## 5) Verification Evidence (Artifacts)
- `/app/test_reports/iteration_6.json` — **testing_agent_v3** independent verification:
  - **110/110 backend tests passed**
  - no critical bugs, no regressions
  - tenant isolation confirmed including new unauthenticated `/api/public/*` routes
- `/app/tests/smoke_e2e.py` — maintained regression test:
  - extended to **55/55** checks covering Phases 12–14

---

## 6) Deployment Notes (Required environment variables)
Backend `.env` (in addition to existing keys) may include:
- SMTP:
  - `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM_EMAIL`, `SMTP_FROM_NAME`
  - `PUBLIC_APP_URL`
- Push:
  - `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`, `VAPID_SUBJECT`

**Fail-safe behavior:** If SMTP or VAPID are missing, the app still works; emails remain queued and the push card reports that notifications are not set up.
