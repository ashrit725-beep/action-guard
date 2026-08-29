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

**New objective (Phase 8): “It must actually stop agents” (in-path enforcement)**
- Provide a **drop-in guard** that wraps the function that performs the real side effect.
- Default behavior is **fail-closed**: if Vexen is unreachable, the side effect must not run.
- Ensure enforcement claims are verifiable:
  - if Vexen blocks, the wrapped function never runs
  - a human approval enables **exactly one retry** within a short window
  - approval replay and scope escalation are refused

**New objective (Phase 9): “In-app help chatbot”**
- Add a plain-language helper that:
  - is **grounded in the user’s workspace state** (agents/rules/approvals/recent stops)
  - never requests or reveals passwords or API keys
  - does not block the backend event loop
  - is accessible and works on mobile + dark mode

**New objective (Phase 10): “Production cleanup & repo hygiene”**
- Remove non-production test scripts, one-off tooling, and artifact directories.
- Keep exactly one **legitimate** backend smoke test for regression checks.
- Do **not** modify or purge MongoDB data as part of cleanup.
- Ensure the application does not depend on any removed files at runtime.

**New objective (Phase 11): “Robust demo video fallback”**
- Ensure the Landing demo video modal doesn’t show a false “cannot play” fallback when the browser can play at least one provided format.
- Provide a safe fallback UX for codec-limited environments.

---

## 2) Implementation Steps

### Phase 1 — Core POC (single script `test_core.py`, fix-until-green)
**Goal:** prove the hardest pieces in isolation before building the app.

**Build (in script + minimal modules as needed):**
1. Implement data structures (in-memory) for: Organization, Agent, AgentKey(hashed), Permission(with limits/expiry/approval), Policy, Approval, AuditEvent(immutable).
2. Implement `authorize(agent_key, action, resource, context)` pipeline with **DEFAULT DENY**.
3. Implement risk scoring (simple deterministic rules: sensitive resources, blocked attempts, high spend, repeated denies).
4. Implement approval flow: create pending approval for approval-required decisions; approving/denying produces audit events; enforce no approval bypass.
5. Implement API key generation + hashing + verification (prefix-visible, secret shown once; verify constant-time compare).
6. Implement cross-tenant isolation checks.
7. Implement Anthropic NL→policy generator: prompt → strict JSON schema output (validate) for rules.

**POC Tests:** allow/block/approval-required/policy override/default deny/audit/cross-tenant/schema validation.

**Status:** ✅ Completed.

---

### Phase 2 — V1 App (FastAPI + MongoDB + React/Tailwind)
**Goal:** build the full product around the proven core, ensure it’s a real multi-user app, and deliver a polished, light-first UI.

#### Phase 2A — Backend (FastAPI, motor/MongoDB)
1. Core models/collections.
2. Auth: email+password, bcrypt hashing, JWT session.
3. Multi-user enforcement.
4. Authorization engine + persistence (audit/approvals).
5. Public agent API (`/api/v1/authorize`) + keys.
6. App endpoints for console pages.
7. AI policy generator endpoint.

**Status:** ✅ Completed and integrated.

---

### Phase 2B — Frontend Completion + UX Polish (React, Tailwind)
**Goal:** ship a fully navigable, polished console with light-first design, and ensure every feature is wired to the backend.

- Landing, Contact, Login, Signup
- Dashboard
- Agents + AgentDetail
- Policies
- Approvals
- Audit Log
- Security Center
- Try It + Guide
- Developers
- Settings

**Status:** ✅ Completed.

---

### Phase 3 — End-to-End Testing + Fixes (required)
- Auth flows
- Agents + template deploy
- Policies CRUD + AI generate
- Approvals workflow
- Audit log + integrity verify
- Security Center
- Try It / Guide
- Developers docs + key flows
- Settings

**Status:** ✅ Completed (iterations 1–5), plus continued verification thereafter.

---

### Phase 4 — Demo Video (very high quality)
**Goal:** ensure the demo video is reliably accessible from the Landing page.

**What was discovered:**
- Previously shipped MP4 was **corrupt** (missing `moov` atom).

**What was done:**
1. Regenerated the demo end-to-end.
2. Published as H.264/AAC MP4 with `+faststart` and normalised loudness.
3. (Later revised) Retained WebM as an additional fallback source for codec-limited environments.
4. Verified playback + seeking in Chromium/Firefox/WebKit + iPhone-sized WebKit.

**Status:** ✅ Completed and verified.

---

### Phase 5 — Final Polish: Dark Mode QA + Cleanup
**Goal:** ship a visually impeccable console and remove non-production artifacts.

#### Phase 5A — Full dark-mode screenshot pass
Completed fixes:
- Disabled filled buttons look muted/inert in dark mode.
- Toasts follow Vexen’s **ThemeContext**.
- Removed nested `<button>` console error by changing metric cards to `div role="button"`.

**Status:** ✅ Completed.

#### Phase 5B — Cleanup non-production artifacts
- Removed older demo-generation scripts and clutter (earlier pass).

**Status:** ✅ Completed.

#### Phase 5C — Health checks
- Frontend compiles cleanly.
- Services healthy.
- Production build verified.

**Status:** ✅ Completed.

---

### Phase 6 — Device & Browser Compatibility (“100,000 devices”)
**Goal:** reduce real-world breakage across browsers, old phones, strict privacy modes, embedded webviews, and different viewport sizes.

#### Phase 6A — Runtime compatibility hardening
- Added robust date parsing via `parseDate()` (microsecond ISO normalisation).
- Intl fallbacks for currency/compact formatting.
- Clipboard fallback via `copyText()`.
- Safe storage wrapper (`lib/storage.js`) wired into tokens + ThemeContext.

**Status:** ✅ Completed.

#### Phase 6B — Mobile layout + touch ergonomics
- No horizontal overflow:
  - marketing header compresses below 400px (`xs`)
  - TabsList scrolls horizontally instead of widening the page
- Better tap targets:
  - password visibility toggle sized to 32px
  - switch/toggle has larger hit area
  - sidebar guide link + contact phone links are >= 32px

**Status:** ✅ Completed.

#### Phase 6C — Cross-engine verification
- Verified critical flows across system Chromium, Firefox, WebKit/iPhone.

**Status:** ✅ Completed.

---

### Phase 7 — “Genuinely real” enforcement + scale readiness
**Goal:** ensure Vexen behaves like a real security/control plane for agents and holds up under concurrency.

#### Phase 7A — Real approvals lifecycle (backend)
- Approvals are **single-use**, expire after **30 minutes**.
- Atomic claim via `find_one_and_update`.
- Correct consumption point: only in `/api/v1/authorize`.

**Status:** ✅ Completed.

#### Phase 7B — Agent-facing approval polling
- Added `GET /api/v1/approvals/{approval_id}` (agent-authenticated).

**Status:** ✅ Completed.

#### Phase 7C — Developers page truthfulness
- Added `public_base_url()` via `x-forwarded-proto/host`.
- `/api/developers` includes enforcement details.
- Snippets demonstrate real loop: authorize → poll → retry once.

**Status:** ✅ Completed.

#### Phase 7D — Approvals UI lifecycle clarity
- Approvals page clearly shows used/expired/pending states.

**Status:** ✅ Completed.

#### Phase 7E — Scale fixes (backend)
- Workspace slug race-proofing.
- Rate limiting rebalance.
- Non-blocking password hashing (threadpool).

**Status:** ✅ Completed and load-tested.

#### Phase 7F — Real-world tests (added)
- Real-agent and load-testing scripts were created to prove enforcement + scale.

**Status:** ✅ Completed (and later removed in Phase 10, except smoke test).

---

### Phase 8 — Genuine in-path enforcement (“actually stops agents”)
**Goal:** provide the missing piece that makes Vexen *physically* stop real side effects.

#### Phase 8A — Ship a drop-in guard SDK (Python)
- Implemented `/app/sdk/python/vexen.py` with `authorize`, approval polling, `wait_for_approval`, and `@guard` decorator.
- Fail closed (`VexenUnavailable`) if Vexen cannot be reached.

**Status:** ✅ Completed.

#### Phase 8B — Distribute the SDK inside the product
- The app serves the file at `/sdk/vexen.py`.
- Developers page includes “Stop it in your code” guidance and download button.

**Status:** ✅ Completed.

#### Phase 8C — Proof test with a real LLM agent and real side effects
- Proved approvals are single-use, replay refused, and Vexen-unreachable fails closed.

**Status:** ✅ Passing.

---

### Phase 9 — In-app help chatbot (“help users work the app”)
**Goal:** help non-technical users succeed with approvals/rules/agents in plain language.

#### Phase 9A — Backend assistant (grounded)
- Added `backend/vexen/assistant.py`.
- Added `POST /api/assistant/chat` (auth required).

**Status:** ✅ Completed.

#### Phase 9B — Frontend chat widget
- Added `frontend/src/components/AssistantWidget.js`.

**Status:** ✅ Completed.

---

### Phase 10 — Production Cleanup (✅ Completed)
**Goal:** remove throwaway test scripts and artifacts so they do not ship to production, while keeping one small, legitimate regression smoke test.

**User confirmations applied:**
- Delete throwaway test scripts (do not archive).
- Do **not** purge MongoDB dummy/load-test accounts.
- Keep one legitimate smoke test.

#### Phase 10A — Delete throwaway tests (keep only smoke test) (✅ Completed)
**Deleted from `/app/tests/`:**
- `load_check.py`
- `real_agent_e2e.py`
- `real_enforcement_proof.py`
- `chatbot_backend_test.py`
- `my_enforcement_test.py`
- `additional_tests.py`
- `verify_issues.py`

**Kept:**
- `/app/tests/smoke_e2e.py`
- `/app/tests/__init__.py`

#### Phase 10B — Delete root-level throwaway test scripts (✅ Completed)
**Deleted:**
- `/app/backend_test.py`
- `/app/test_api.py`
- `/app/test_core.py`
- `/app/test_core_flows.py`
- `/app/test_backend_scale.py`
- `/app/test_device_compatibility.py`
- `/app/test_device_compatibility_results.json`
- `/app/test_video_cross_browser.py`

#### Phase 10C — Delete one-off demo/recording/sweep tooling (✅ Completed)
**Deleted:**
- Entire `/app/scripts/` directory

#### Phase 10D — Remove artifact directories and leftover logs (✅ Completed)
**Deleted:**
- `/app/.darkshots/`
- `/app/.darkshots2/`
- `/app/.demo_build/` (~58MB)
- `/app/.device_sweep/`
- `/app/.ruff_cache/`
- Sweep logs: `.darkpass*.log`, `.demo_build_narration.log`, `.device_sweep*.log`
- `DEMO_NARRATION_SCRIPT.md`

**Cleanup impact:** removed ~64MB of non-production artifacts.

#### Phase 10E — SDK hygiene (✅ Completed)
- Removed `/app/sdk/python/__pycache__/` and `.pyc` files.

**Kept:**
- `/app/sdk/python/vexen.py` (verified byte-identical to `frontend/public/sdk/vexen.py`)

#### Phase 10F — Explicit DB policy (✅ Completed)
- **No DB data was purged or modified** as part of cleanup (per user instruction).

#### Phase 10G — Post-cleanup verification (✅ Completed)
Verification results:
1. Backend restarted cleanly (startup logged: “Vexen indexes ready”).
2. Smoke test passed:
   - `python /app/tests/smoke_e2e.py` → **PASSED 38/38**
3. Frontend compiles:
   - `esbuild` bundle check clean
4. Public asset checks:
   - `/sdk/vexen.py` → 200
   - `/demo/vexen-demo.mp4` range request → 206
   - `/demo/vexen-demo.webm` → 200
   - `/demo/vexen-demo-poster.png` → 200
5. UI sanity (screenshots): Landing, demo modal (light/dark), guide/console.
6. Developers page: correct public preview URLs; **Download vexen.py** works under “Stop it in your code” tab.
7. Assistant chatbot API: `/api/assistant/chat` returned grounded response (200).

---

### Phase 11 — Cross-browser demo-video fallback fix (✅ Completed)
**Goal:** prevent a false “This browser could not play the video” fallback when only one `<source>` fails.

**Bug discovered:**
- React forwards `error` events from child `<source>` elements up to the `<video onError>` handler.
- On browsers **without H.264** (codec-stripped Linux/ARM Chromium builds, some headless environments), the MP4 `<source>` fails and immediately triggered the fallback UI—despite the WebM `<source>` being playable.

**Fix implemented (in `/app/frontend/src/pages/Landing.js`):**
- Added `handleMediaError()`:
  - Ignores errors where `event.target` is not the `<video>` element.
  - Schedules a re-check after 2s and only sets failure if `video.networkState === 3` (`NETWORK_NO_SOURCE`).
- Added `recheckRef` timeout cleanup on close/unmount.
- Improved fallback UX: added a second button to open the WebM version directly.

**Verification:**
- In a codec-limited Headless Chrome environment (`canPlayType` H.264 empty; VP9 “probably”):
  - video plays using `/demo/vexen-demo.webm`
  - `readyState: 4`, duration ~156s, currentTime advances
  - no premature fallback, confirmed in light + dark.

---

## 3) Next Actions
- **None outstanding (engineering).**
- Await **user testing/feedback** and any requested follow-up work (deployment readiness, monitoring, additional policies, enterprise features).

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
- **Production hygiene:**
  - throwaway test scripts, one-off tooling, and artifact directories are removed
  - only `/app/tests/smoke_e2e.py` remains as a supported regression test
  - no DB records were modified/purged during cleanup
  - backend still runs and smoke test passes after cleanup
