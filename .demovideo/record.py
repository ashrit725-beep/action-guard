"""Record every scene of the Vexen demo (v2) with Playwright.

One video file per scene, paced against the real narration timings in
manifest.json so the visuals land on the words. Everything shown is the real
running app: a real signup, a real deployed agent, a real authorization
decision, a real queued alert email and a real signed one-tap approval link.
"""
import json
import os
import re
import subprocess
import sys
import time

import requests
from playwright.sync_api import sync_playwright

BASE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(BASE, "raw")
CARDS = os.path.join(BASE, "cards")
TMP_PUBLIC = "/app/frontend/public/demo-tmp"

APP = "http://localhost:3000"
API = "http://localhost:8001"

W, H = 1536, 864
PW, PH = 390, 844

MANIFEST = json.load(open(os.path.join(BASE, "manifest.json")))
SCENES = {s["id"]: s for s in MANIFEST["scenes"]}
GAP = MANIFEST["line_gap"]

DEMO_PASSWORD = os.environ.get("DEMO_PASSWORD", "Vexen-Demo-2026")
EMAIL_CANDIDATES = [
    "alex.morgan@northwind.demo",
    "alex.morgan@northwind.co",
    "alex@northwind.demo",
    "a.morgan@northwind.demo",
    "alex.morgan@northwind.team",
]

state = {"clips": {}}


# ----------------------------------------------------------------- pacing ----
def beats(scene_id):
    """Cumulative (start, end) seconds for each narration line in a scene."""
    out, t = [], 0.0
    for line in SCENES[scene_id]["lines"]:
        out.append((t, t + line["dur"]))
        t += line["dur"] + GAP
    return out


class Pacer:
    def __init__(self, scene_id):
        self.scene_id = scene_id
        self.beats = beats(scene_id)
        self.total = SCENES[scene_id]["dur"]
        self.t0 = None
        self.shift = 0.0
        self.cuts = []

    def start(self):
        self.t0 = time.time()
        self.lead_in = max(0.0, self.t0 - state["t_page"])

    @property
    def elapsed(self):
        return time.time() - self.t0

    def cut(self, t_from, t_to):
        """Mark a dead stretch (e.g. waiting on a model) to be edited out."""
        if t_to - t_from <= 0.15:
            return
        self.cuts.append([round(t_from, 3), round(t_to, 3)])
        self.shift += t_to - t_from

    def hold_until(self, page, seconds):
        remaining = (seconds + self.shift) - self.elapsed
        if remaining > 0:
            page.wait_for_timeout(int(remaining * 1000))

    def hold_line(self, page, index, offset=0.0):
        """Hold until narration line `index` has finished speaking."""
        if index < len(self.beats):
            self.hold_until(page, self.beats[index][1] + offset)

    def finish(self, page):
        self.hold_until(page, self.total)
        state["clips"][self.scene_id] = {
            "lead_in": round(self.lead_in, 3),
            "cuts": self.cuts,
            "need": self.total,
        }


# ------------------------------------------------------------- primitives ----
def smooth_scroll(page, delta, steps=26, pause=22):
    step = delta / steps
    for _ in range(steps):
        page.mouse.wheel(0, step)
        page.wait_for_timeout(pause)


def scroll_to(page, selector, block="center"):
    try:
        page.eval_on_selector(
            selector,
            f"el => el.scrollIntoView({{behavior:'smooth', block:'{block}'}})",
        )
        page.wait_for_timeout(700)
    except Exception:
        pass


def type_slow(page, selector, text, delay=55):
    page.click(selector)
    page.wait_for_timeout(180)
    page.type(selector, text, delay=delay)


def pick_select(page, trigger_testid, option_text):
    """Radix Select: open the trigger, then click the matching option."""
    page.click(f'[data-testid="{trigger_testid}"]')
    page.wait_for_timeout(450)
    page.click(f'[role="option"]:has-text("{option_text}")')
    page.wait_for_timeout(400)


def new_ctx(browser, scene_id, width=W, height=H, auth=True):
    ctx = browser.new_context(
        viewport={"width": width, "height": height},
        record_video_dir=os.path.join(RAW, scene_id),
        record_video_size={"width": width, "height": height},
        device_scale_factor=1,
        color_scheme="light",
        reduced_motion="no-preference",
    )
    if auth and state.get("access"):
        ctx.add_init_script(
            "try{localStorage.setItem('vexen.access',%s);"
            "localStorage.setItem('vexen.refresh',%s);"
            "localStorage.setItem('vexen.theme','light');}catch(e){}"
            % (json.dumps(state["access"]), json.dumps(state["refresh"]))
        )
    else:
        ctx.add_init_script("try{localStorage.setItem('vexen.theme','light');}catch(e){}")
    page = ctx.new_page()
    page.set_default_timeout(30000)
    state["t_page"] = time.time()
    return ctx, page


def close_ctx(ctx, page, scene_id):
    path = page.video.path()
    ctx.close()
    target = os.path.join(RAW, f"{scene_id}.webm")
    if os.path.exists(target):
        os.remove(target)
    os.rename(path, target)
    dur = float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", target],
        capture_output=True, text=True,
    ).stdout.strip())
    clip = state["clips"].setdefault(scene_id, {"lead_in": 0.0, "cuts": [], "need": SCENES[scene_id]["dur"]})
    clip["raw"] = round(dur, 3)
    print(f"    saved {scene_id}.webm  raw={dur:.2f}s lead_in={clip['lead_in']:.2f}s "
          f"cuts={clip['cuts']} need={clip['need']}s", flush=True)


def api(method, path, token=None, **kw):
    headers = kw.pop("headers", {})
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = requests.request(method, f"{API}{path}", headers=headers, timeout=30, **kw)
    return r


# ------------------------------------------------------------------ scenes ----
def scene_landing(browser):
    sid = "s01_landing"
    print(f"  {sid}", flush=True)
    ctx, page = new_ctx(browser, sid, auth=False)
    page.goto(APP + "/", wait_until="domcontentloaded")
    page.wait_for_selector("text=Stay in control", timeout=30000)
    page.wait_for_timeout(1400)
    p = Pacer(sid)
    p.start()
    p.hold_line(page, 0, 0.2)
    scroll_to(page, 'h2:has-text("How it works")', "start")
    page.wait_for_timeout(600)
    smooth_scroll(page, 130, steps=12, pause=26)
    p.hold_line(page, 1, 0.1)
    p.finish(page)
    close_ctx(ctx, page, sid)


def scene_signup(browser):
    sid = "s02_signup"
    print(f"  {sid}", flush=True)
    ctx, page = new_ctx(browser, sid, auth=False)
    page.goto(APP + "/signup", wait_until="domcontentloaded")
    page.wait_for_selector('[data-testid="signup-form"]')
    page.wait_for_timeout(900)
    p = Pacer(sid)
    p.start()
    type_slow(page, '[data-testid="signup-name-input"]', "Alex Morgan", 62)
    type_slow(page, '[data-testid="signup-email-input"]', state["email"], 34)
    type_slow(page, '[data-testid="signup-password-input"]', DEMO_PASSWORD, 46)
    page.wait_for_timeout(500)
    page.click('[data-testid="signup-submit-button"]')
    page.wait_for_url("**/app**", timeout=40000)
    page.wait_for_timeout(2200)
    p.hold_line(page, 0, 0.2)
    smooth_scroll(page, 380, steps=22, pause=26)
    p.finish(page)

    state["access"] = page.evaluate("localStorage.getItem('vexen.access')")
    state["refresh"] = page.evaluate("localStorage.getItem('vexen.refresh')")
    close_ctx(ctx, page, sid)
    assert state["access"], "signup did not produce a session"
    print("    session captured", flush=True)


def scene_library(browser):
    sid = "s03_library"
    print(f"  {sid}", flush=True)
    ctx, page = new_ctx(browser, sid)
    page.goto(APP + "/app/agents", wait_until="domcontentloaded")
    page.wait_for_selector('[data-testid="agents-page"]')
    page.wait_for_timeout(1200)
    p = Pacer(sid)
    p.start()
    btn = '[data-testid="agents-empty-cta"]'
    if page.locator(btn).count() == 0:
        btn = '[data-testid="open-template-library-button"]'
    page.click(btn)
    page.wait_for_selector('[data-testid="template-search-input"]')
    page.wait_for_timeout(700)
    p.hold_line(page, 0, 0.1)
    type_slow(page, '[data-testid="template-search-input"]', "shopping", 90)
    page.wait_for_timeout(1400)
    p.hold_line(page, 1, 0.1)
    smooth_scroll(page, 260, steps=16, pause=26)
    page.wait_for_timeout(300)
    smooth_scroll(page, -260, steps=14, pause=22)
    deploy = page.locator('[data-testid^="deploy-template-"]').first
    deploy.scroll_into_view_if_needed()
    page.wait_for_timeout(400)
    deploy.click()
    page.wait_for_timeout(2600)
    p.finish(page)
    close_ctx(ctx, page, sid)


def scene_tryit(browser):
    sid = "s04_tryit"
    print(f"  {sid}", flush=True)
    ctx, page = new_ctx(browser, sid)
    page.goto(APP + "/app/try", wait_until="domcontentloaded")
    page.wait_for_selector('[data-testid="try-page"]')
    page.wait_for_timeout(1500)
    p = Pacer(sid)
    p.start()
    pick_select(page, "try-permission-select", "Purchase products")
    page.fill('[data-testid="try-resource-input"]', "")
    type_slow(page, '[data-testid="try-resource-input"]', "sku-8842", 70)
    page.fill('[data-testid="try-amount-input"]', "")
    type_slow(page, '[data-testid="try-amount-input"]', "250", 130)
    p.hold_line(page, 0, 0.05)
    page.click('[data-testid="try-run-button"]')
    page.wait_for_selector('[data-testid="try-result-card"]', timeout=30000)
    page.wait_for_timeout(600)
    scroll_to(page, '[data-testid="try-result-headline"]', "start")
    p.hold_line(page, 2, 0.15)
    page.click('[data-testid="try-toggle-trace"]')
    page.wait_for_timeout(900)
    smooth_scroll(page, 520, steps=30, pause=34)
    smooth_scroll(page, 420, steps=24, pause=34)
    p.finish(page)
    close_ctx(ctx, page, sid)


def scene_blocked(browser):
    sid = "s05_blocked"
    print(f"  {sid}", flush=True)
    ctx, page = new_ctx(browser, sid)
    page.goto(APP + "/app/try", wait_until="domcontentloaded")
    page.wait_for_selector('[data-testid="try-page"]')
    page.wait_for_timeout(1200)
    p = Pacer(sid)
    p.start()
    preset = '[data-testid="try-preset-payments-read"]'
    if page.locator(preset).count() == 0:
        pick_select(page, "try-permission-select", "saved card")
        page.click('[data-testid="try-run-button"]')
    else:
        scroll_to(page, preset)
        page.click(preset)
    page.wait_for_selector('[data-testid="try-result-card"]', timeout=30000)
    page.wait_for_timeout(500)
    scroll_to(page, '[data-testid="try-result-headline"]', "start")
    p.finish(page)
    close_ctx(ctx, page, sid)


def scene_rules(browser):
    sid = "s06_rules"
    print(f"  {sid}", flush=True)
    ctx, page = new_ctx(browser, sid)
    page.goto(APP + "/app/policies", wait_until="domcontentloaded")
    page.wait_for_selector('[data-testid="policies-page"]')
    page.wait_for_timeout(1300)
    p = Pacer(sid)
    p.start()
    example = page.locator('[data-testid="policies-ai-example"]').first
    example.scroll_into_view_if_needed()
    page.wait_for_timeout(500)
    example.click()
    page.wait_for_timeout(900)
    p.hold_line(page, 0, 0.05)
    page.click('[data-testid="policies-ai-generate"]')
    t_gen = p.elapsed
    page.wait_for_selector('[data-testid="policies-ai-draft"]', timeout=90000)
    # Nobody wants to watch a model think. Keep a beat of it, edit out the rest.
    p.cut(t_gen + 3.4, max(t_gen + 3.6, p.elapsed - 0.25))
    page.wait_for_timeout(700)
    scroll_to(page, '[data-testid="policies-ai-draft"]', "start")
    p.hold_line(page, 1, 0.3)
    save = page.locator('[data-testid="policies-ai-save"]')
    if save.count():
        save.scroll_into_view_if_needed()
        page.wait_for_timeout(400)
        save.click()
        page.wait_for_timeout(2000)
    p.finish(page)
    close_ctx(ctx, page, sid)


def scene_email(browser):
    sid = "s07_email"
    print(f"  {sid}", flush=True)
    ctx, page = new_ctx(browser, sid, auth=False)
    page.goto(APP + "/demo-tmp/email.html", wait_until="domcontentloaded")
    page.wait_for_timeout(1600)
    p = Pacer(sid)
    p.start()
    p.hold_line(page, 0, 0.2)
    page.evaluate("document.querySelector('#mailbody').contentWindow.scrollBy({top:150,behavior:'smooth'})")
    p.finish(page)
    close_ctx(ctx, page, sid)


def scene_phone(browser):
    sid = "s08_phone"
    print(f"  {sid}", flush=True)
    ctx, page = new_ctx(browser, sid, width=PW, height=PH, auth=False)
    page.goto(state["approve_local"] + "?intent=approve", wait_until="domcontentloaded")
    page.wait_for_selector('[data-testid="approve-request-card"]', timeout=40000)
    page.wait_for_timeout(1200)
    p = Pacer(sid)
    p.start()
    p.hold_line(page, 0, 0.15)
    smooth_scroll(page, 230, steps=16, pause=26)
    p.hold_line(page, 1, 0.1)
    page.click('[data-testid="approve-approve-button"]')
    page.wait_for_timeout(2600)
    smooth_scroll(page, -260, steps=14, pause=22)
    p.finish(page)
    close_ctx(ctx, page, sid)


def scene_approvals(browser):
    sid = "s09_approvals"
    print(f"  {sid}", flush=True)
    ctx, page = new_ctx(browser, sid)
    page.goto(APP + "/app/approvals", wait_until="domcontentloaded")
    page.wait_for_timeout(2000)
    p = Pacer(sid)
    p.start()
    tab = '[data-testid="approvals-tab-all"]'
    if page.locator(tab).count():
        page.click(tab)
        page.wait_for_timeout(1300)
    p.hold_line(page, 0, 0.2)
    smooth_scroll(page, 300, steps=20, pause=28)
    p.finish(page)
    close_ctx(ctx, page, sid)


def scene_developers(browser):
    sid = "s10_developers"
    print(f"  {sid}", flush=True)
    ctx, page = new_ctx(browser, sid)
    page.goto(APP + "/app/developers", wait_until="domcontentloaded")
    page.wait_for_selector('[data-testid="developers-page"]')
    page.wait_for_timeout(1400)
    p = Pacer(sid)
    p.start()
    tab = '[data-testid="developers-tab-guard"]'
    scroll_to(page, '[data-testid="developers-snippet-tabs"]', "start")
    page.click(tab)
    page.wait_for_timeout(1100)
    p.hold_line(page, 0, 0.2)
    smooth_scroll(page, 300, steps=22, pause=30)
    p.hold_line(page, 1, 0.2)
    smooth_scroll(page, 240, steps=18, pause=30)
    p.finish(page)
    close_ctx(ctx, page, sid)


def scene_history(browser):
    sid = "s11_history"
    print(f"  {sid}", flush=True)
    ctx, page = new_ctx(browser, sid)
    page.goto(APP + "/app/audit", wait_until="domcontentloaded")
    page.wait_for_timeout(2200)
    p = Pacer(sid)
    p.start()
    p.hold_line(page, 0, 0.25)
    page.click('[data-testid="verify-audit-button"]')
    page.wait_for_timeout(2400)
    smooth_scroll(page, 200, steps=14, pause=26)
    p.finish(page)
    close_ctx(ctx, page, sid)


def scene_team(browser):
    sid = "s12_team"
    print(f"  {sid}", flush=True)
    ctx, page = new_ctx(browser, sid)
    page.goto(APP + "/app/security", wait_until="domcontentloaded")
    page.wait_for_timeout(2200)
    p = Pacer(sid)
    p.start()
    smooth_scroll(page, 300, steps=20, pause=28)
    p.hold_line(page, 0, 0.2)
    page.goto(APP + "/app/team", wait_until="domcontentloaded")
    page.wait_for_selector('[data-testid="team-page"]', timeout=30000)
    page.wait_for_timeout(1500)
    p.hold_line(page, 1, 0.2)
    smooth_scroll(page, 320, steps=22, pause=30)
    p.finish(page)
    close_ctx(ctx, page, sid)


# ------------------------------------------------------------------- seed ----
def mongo():
    from pymongo import MongoClient

    url = name = None
    for line in open("/app/backend/.env"):
        if line.startswith("MONGO_URL="):
            url = line.split("=", 1)[1].strip().strip('"')
        if line.startswith("DB_NAME="):
            name = line.split("=", 1)[1].strip().strip('"')
    client = MongoClient(url)
    return client, client[name or "vexen"]


def pick_email():
    client, db = mongo()
    try:
        for candidate in EMAIL_CANDIDATES:
            if not db.users.find_one({"email": candidate}):
                return candidate
    finally:
        client.close()
    raise RuntimeError("no free demo email — add another candidate")


def seed_after_rules():
    """Create a real paused decision, its alert email and a few teammates."""
    token = state["access"]
    agents = api("GET", "/api/agents", token=token).json()
    items = agents.get("items") or agents.get("agents") or []
    assert items, "no agent deployed"
    agent = items[0]
    aid = agent["agent_id"]
    state["agent_name"] = agent.get("name")
    print(f"    agent: {state['agent_name']} ({aid})", flush=True)

    cred = api("POST", f"/api/agents/{aid}/credentials", token=token,
               json={"name": "Production key"})
    secret = cred.json().get("secret") or cred.json().get("api_key")
    assert secret, f"no credential secret: {cred.status_code} {cred.text[:200]}"

    r = api("POST", "/api/v1/authorize", headers={"X-Vexen-Key": secret}, json={
        "resource": "shopping", "action": "purchase",
        "amount": 742.50, "currency": "USD", "resource_id": "order-4471",
    })
    body = r.json()
    print(f"    authorize -> {body.get('decision')} {body.get('approval_id') or ''}", flush=True)
    assert body.get("decision") == "APPROVAL_REQUIRED", body
    state["approval_id"] = body["approval_id"]

    for role, mail in [
        ("admin", "priya.raman@northwind.demo"),
        ("approver", "dan.whitfield@northwind.demo"),
        ("viewer", "mei.tanaka@northwind.demo"),
    ]:
        inv = api("POST", "/api/team/invites", token=token, json={"email": mail, "role": role})
        print(f"    invite {role} -> {inv.status_code}", flush=True)


def grab_email_and_link():
    """Read the queued alert straight out of the outbox, then stop it sending."""
    client, db = mongo()

    row = None
    for _ in range(30):
        row = db.email_outbox.find_one({"kind": {"$regex": "approval"}},
                                       sort=[("created_at", -1)])
        if row and row.get("html"):
            break
        time.sleep(0.6)
    assert row, "no approval alert in the outbox"

    match = re.search(r"(https?://[^\s\"'<>]+/approve/[A-Za-z0-9_\-\.]+)", row.get("text") or "")
    if not match:
        match = re.search(r"href=\"(https?://[^\"]+/approve/[^\"?]+)", row.get("html") or "")
    assert match, "no approve link in the alert"
    url = match.group(1).split("?")[0]
    state["approve_public"] = url
    state["approve_local"] = APP + "/approve/" + url.rsplit("/approve/", 1)[1]
    print(f"    approve link: .../approve/{url.rsplit('/', 1)[1][:22]}...", flush=True)

    db.email_outbox.update_many(
        {"id": row["id"]},
        {"$set": {"status": "sent", "sent_at": row["created_at"],
                  "last_error": "held back: demo recording"}},
    )
    db.email_outbox.update_many(
        {"status": "queued", "to": {"$regex": "northwind"}},
        {"$set": {"status": "sent", "last_error": "held back: demo recording"}},
    )

    os.makedirs(TMP_PUBLIC, exist_ok=True)
    with open(os.path.join(TMP_PUBLIC, "mail.html"), "w") as fh:
        fh.write(row["html"])
    with open(os.path.join(TMP_PUBLIC, "email.html"), "w") as fh:
        fh.write(mail_client_shell(row["subject"], state["email"]))
    client.close()


def mail_client_shell(subject, to_address):
    return f"""<!doctype html>
<html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Figtree:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
  *{{box-sizing:border-box}}
  body{{margin:0;background:#eef1f4;font-family:Figtree,sans-serif;color:#0f172a}}
  .win{{max-width:1040px;margin:16px auto;background:#fff;border:1px solid #dfe4ea;
        border-radius:14px;overflow:hidden;box-shadow:0 18px 50px rgba(15,23,42,.09)}}
  .bar{{display:flex;align-items:center;gap:10px;padding:12px 18px;background:#f7f9fb;
        border-bottom:1px solid #e6eaef}}
  .dot{{width:11px;height:11px;border-radius:50%}}
  .app{{margin-left:10px;font-size:12.5px;font-weight:600;color:#64748b;letter-spacing:.02em}}
  .hdr{{padding:20px 26px 14px}}
  .subj{{font-size:21px;font-weight:700;letter-spacing:-.01em}}
  .meta{{margin-top:9px;display:flex;align-items:center;gap:11px;font-size:13px;color:#64748b}}
  .av{{width:34px;height:34px;border-radius:50%;background:#0f766e;color:#fff;display:flex;
       align-items:center;justify-content:center;font-weight:700;font-size:13px}}
  .from strong{{color:#0f172a;font-weight:600}}
  .when{{margin-left:auto;font-size:12.5px;color:#94a3b8}}
  iframe{{width:100%;height:672px;border:0;border-top:1px solid #eef1f4;display:block}}
</style></head>
<body>
  <div class="win">
    <div class="bar">
      <span class="dot" style="background:#f2665a"></span>
      <span class="dot" style="background:#f7c04a"></span>
      <span class="dot" style="background:#57c98a"></span>
      <span class="app">Inbox — {to_address}</span>
    </div>
    <div class="hdr">
      <div class="subj">{subject}</div>
      <div class="meta">
        <span class="av">V</span>
        <span class="from"><strong>Vexen</strong> &lt;alerts@vexen.app&gt; &nbsp;to me</span>
        <span class="when">just now</span>
      </div>
    </div>
    <iframe id="mailbody" src="./mail.html" title="Approval alert"></iframe>
  </div>
</body></html>"""


# ------------------------------------------------------------------- main ----
def main():
    os.makedirs(RAW, exist_ok=True)
    state["email"] = os.environ.get("DEMO_EMAIL") or pick_email()
    print(f"demo account: {state['email']}", flush=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(args=[
            "--no-sandbox", "--disable-dev-shm-usage", "--hide-scrollbars",
            "--force-color-profile=srgb", "--font-render-hinting=none",
            "--disable-lcd-text", "--autoplay-policy=no-user-gesture-required",
        ])
        scene_landing(browser)
        scene_signup(browser)
        scene_library(browser)
        scene_tryit(browser)
        scene_blocked(browser)
        scene_rules(browser)
        print("  seeding a real paused decision...", flush=True)
        seed_after_rules()
        grab_email_and_link()
        scene_email(browser)
        scene_phone(browser)
        scene_approvals(browser)
        scene_developers(browser)
        scene_history(browser)
        scene_team(browser)
        browser.close()

    with open(os.path.join(BASE, "recording.json"), "w") as fh:
        json.dump(state, fh, indent=2)
    with open(os.path.join(BASE, "clips.json"), "w") as fh:
        json.dump(state["clips"], fh, indent=2)
    print("RECORDING COMPLETE")


if __name__ == "__main__":
    main()
