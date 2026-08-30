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

**Objective (Submission packaging): “answers must fit exact length constraints”**
- Maintain `/app/memory/SUBMISSION.md` with:
  - Q1 tweet answer at ~295 characters
  - Q2 proposal answer at ~32,750 characters (within acceptable tolerance)
  - counts verified by tooling (scripted count, not eyeballed)
  - include a paste-ready attachments list

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

**Objective (Phases 12–14): “Enterprise operations: alerts + phone approvals + teams”**
- **Email alerts**: notify the right people the moment an agent is paused.
- **Approve-by-phone**: approvals can be decided from a phone without opening the console.
- **Team seats**: invite teammates and enforce roles server-side.
- **Browser push**: optional device notifications for approvals.

**Objective (Phase 15): “Demo video v2: enterprise-grade, captioned, covers newest features”**
- Rebuild the demo video to be **“very very good”**:
  - 1080p master (plus WebM)
  - chapter structure and burned-in captions/cards (watchable muted)
  - explicitly demonstrates the newest differentiators:
    - email alert + one-tap phone approval
    - SDK fail-closed genuine enforcement semantics
    - team seats + roles

**Objective (Phase 16): “Supporting document PDF”**
- Produce a polished, brand-consistent **supporting document PDF** for applications/sales:
  - A4, selectable text, no clipped/overlapping layout, consistent headers/footers
  - Uses real screenshots from the running app
  - Exported and served from a stable public URL

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

### Phase 4 — Demo Video (v1)
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

#### Phase 12B — Signed one-tap approval links (secure + scan-safe)
**Status:** ✅ Completed.

#### Phase 12C — Recipient selection + per-person Settings
**Status:** ✅ Completed.

#### Phase 12D — Frontend approve-by-link page
**Status:** ✅ Completed.

#### Phase 12E — Hook into hot path (queue only)
**Status:** ✅ Completed.

#### Phase 12 Verification Evidence
**Status:** ✅ Completed.

---

### Phase 13 — Team seats: invites + roles
**Goal:** multi-user workspaces with roles and invites; strict backend enforcement.

#### Phase 13A — Roles model + enforcement
**Status:** ✅ Completed.

#### Phase 13B — Invitations
**Status:** ✅ Completed.

#### Phase 13C — Team page (frontend)
**Status:** ✅ Completed.

#### Phase 13 Verification Evidence
**Status:** ✅ Completed.

---

### Phase 14 — Browser push notifications
**Goal:** optional device notifications that can take the user straight to the approval decision page.

#### Phase 14A — VAPID + backend
**Status:** ✅ Completed.

#### Phase 14B — Frontend + service worker
**Status:** ✅ Completed.

#### Phase 14 Verification Evidence
**Status:** ✅ Completed (with note that real lock-screen delivery requires a real device).

---

### Phase 15 — Submission answers: finalize `/app/memory/SUBMISSION.md`
**Goal:** produce paste-ready application answers with strict character-count constraints.

**Status:** ✅ Completed.

**Acceptance constraints (met):**
- Q1 tweet answer: **295 characters exactly**.
- Q2 proposal answer: **32,734 characters** (target range **32,500–32,750**, as close to 32,750 as possible without going over).

**Edits performed:**
- Condensed repetitive passages while preserving story, technical depth, and differentiators.
- Corrected mislabeled alternate tweet lengths.
- Added a count table + attachments table for copy/paste confidence.

---

### Phase 16 — Demo video v2 (“make it very very good”) — REBUILD
**Goal:** replace/augment the current demo video with a higher-quality, captioned, feature-complete walkthrough.

**Status:** ✅ Completed.

**Built pipeline (scripts retained, intermediates deleted):** `/app/.demovideo/`
- `narration.py` — 14-scene storyboard, 33 narration lines.
- `gen_tts.py` — edge-tts (en-US-AndrewNeural), per-line clips + durations manifest.
- `record.py` — Playwright capture (desktop 1536×864, phone 390×844) paced against narration, with lead-in trimming and an “edit out the model thinking” cut marker.
- `make_assets.py` — on-brand 1920×1080 intro/outro + phone-stage card rendered in Chromium.
- `make_captions.py` — 35 caption plates (PIL + Figtree/Roboto Mono) so the demo reads on mute.
- `build.py` — scene cuts, 1080p scaling, caption burn-in, concatenation, narration bed loudnorm, MP4/WebM encode.

**Delivered assets (installed + verified):**
- `/app/frontend/public/demo/vexen-demo.mp4` — 1920×1080, ~2m59s, narrated + captioned.
- `/app/frontend/public/demo/vexen-demo.webm` — VP9 fallback.
- `/app/frontend/public/demo/vexen-demo-poster.png`.

**Landing update:** `Landing.js` copy updated from “two minutes” → “three minutes” and mentions captions.

**Verification:** playback verified in the landing modal (duration ~179.2s, 1920×1080, readyState 4).

---

### Phase 17 — Supporting document PDF
**Goal:** provide a polished PDF supporting document for applications and enterprise buyers.

**Status:** ✅ Completed.

**Pipeline:** `/app/.demovideo/`
- `make_shots.py` — captured 13 retina screenshots of the live app, including a freshly minted pending approval on a phone.
- `make_pdf.py` — renders a **19-page A4** supporting document via Chromium with:
  - full-bleed cover
  - consistent header/footer with CSS counter page numbers
  - comparison tables, the 13-step engine table, and code blocks
  - real screenshots
- `check_pdf.py` — programmatic overflow detection; **0 overflows**.

**Delivered assets (installed + verified):**
- `/app/frontend/public/docs/vexen-supporting-document.pdf`
- copy stored at `/app/memory/vexen-supporting-document.pdf`

---

## 3) Next Actions
1. **User acceptance checks (optional):**
   - confirm the Landing modal plays the demo video in your environment
   - confirm muted viewing is understandable (captions)
   - open the supporting PDF and confirm it matches your submission expectations
2. (Optional hardening) Add a small admin “Delivery” panel for email outbox if desired (currently visible via API).
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

**Success criteria (Submission answers):**
- `/app/memory/SUBMISSION.md` meets character-count constraints:
  - Q1: **295 chars**
  - Q2: **32,734 chars** (≤ 32,750 and ≥ 32,500)

**Success criteria (Demo video v2):**
- 1080p master plus WebM alternative shipped.
- Captions/chapter cards burned in; video is comprehensible muted.
- Demonstrates:
  - approve-by-phone from email
  - SDK fail-closed enforcement guarantee
  - team seats + roles

**Success criteria (Supporting document PDF):**
- PDF shipped at a stable URL: `/docs/vexen-supporting-document.pdf`
- 19 pages, A4, selectable text, no layout overlap/clipping
- Uses real screenshots from the live app

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
  - tenant isolation confirmed including unauthenticated `/api/public/*` routes
- `/app/tests/smoke_e2e.py` — maintained regression test:
  - extended to **55/55** checks covering Phases 12–14
- `/app/memory/SUBMISSION.md` — submission answers:
  - Q1 **295 chars**, Q2 **32,734 chars** (verified by script)
- Demo assets:
  - `/app/frontend/public/demo/vexen-demo.mp4`
  - `/app/frontend/public/demo/vexen-demo.webm`
  - `/app/frontend/public/demo/vexen-demo-poster.png`
- Supporting document:
  - `/app/frontend/public/docs/vexen-supporting-document.pdf`
  - `/app/memory/vexen-supporting-document.pdf`
- Demo video + PDF direct-link checks:
  - URLs return 206 and correct content types over the preview base URL

---

## 6) Deployment Notes (Required environment variables)
Backend `.env` (in addition to existing keys) may include:
- SMTP:
  - `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM_EMAIL`, `SMTP_FROM_NAME`
  - `PUBLIC_APP_URL`
- Push:
  - `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`, `VAPID_SUBJECT`

**Fail-safe behavior:** If SMTP or VAPID are missing, the app still works; emails remain queued and the push card reports that notifications are not set up.
