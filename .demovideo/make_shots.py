"""Capture the product screenshots used in the supporting-document PDF.

Reuses the demo workspace created by record.py, and mints a genuinely fresh
paused decision so the phone-approval screenshot shows a live request.
"""
import json
import os
import re
import time

import requests
from playwright.sync_api import sync_playwright

BASE = os.path.dirname(os.path.abspath(__file__))
SHOTS = os.path.join(BASE, "shots")
APP = "http://localhost:3000"
API = "http://localhost:8001"

REC = json.load(open(os.path.join(BASE, "recording.json")))
W, H = 1600, 1000


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


def fresh_approval():
    token = REC["access"]
    agents = requests.get(f"{API}/api/agents", headers={"Authorization": f"Bearer {token}"},
                          timeout=20).json()
    agent = (agents.get("items") or agents.get("agents"))[0]
    cred = requests.post(f"{API}/api/agents/{agent['agent_id']}/credentials",
                         headers={"Authorization": f"Bearer {token}"},
                         json={"name": "Docs key"}, timeout=20).json()
    secret = cred.get("secret") or cred.get("api_key")
    r = requests.post(f"{API}/api/v1/authorize", headers={"X-Vexen-Key": secret}, json={
        "resource": "shopping", "action": "purchase", "amount": 742.50,
        "currency": "USD", "resource_id": "order-4471",
    }, timeout=30).json()
    print("authorize ->", r.get("decision"), r.get("approval_id"))

    client, db = mongo()
    row = None
    for _ in range(30):
        row = db.email_outbox.find_one({"kind": {"$regex": "approval"}}, sort=[("created_at", -1)])
        if row and row.get("html"):
            break
        time.sleep(0.6)
    link = re.search(r"(https?://[^\s\"'<>]+/approve/[A-Za-z0-9_\-\.]+)", row.get("text") or "")
    url = link.group(1).split("?")[0]
    db.email_outbox.update_many({"id": row["id"]},
                                {"$set": {"status": "sent", "last_error": "held back: docs"}})
    db.email_outbox.update_many({"status": "queued", "to": {"$regex": "northwind"}},
                                {"$set": {"status": "sent", "last_error": "held back: docs"}})
    os.makedirs("/app/frontend/public/demo-tmp", exist_ok=True)
    with open("/app/frontend/public/demo-tmp/mail.html", "w") as fh:
        fh.write(row["html"])
    client.close()
    return APP + "/approve/" + url.rsplit("/approve/", 1)[1]


def shot(page, name, full=False):
    page.wait_for_timeout(900)
    page.screenshot(path=os.path.join(SHOTS, f"{name}.png"), full_page=full)
    print("  shot", name)


def main():
    os.makedirs(SHOTS, exist_ok=True)
    approve_url = fresh_approval()

    with sync_playwright() as p:
        b = p.chromium.launch(args=["--no-sandbox", "--disable-dev-shm-usage",
                                    "--force-color-profile=srgb", "--hide-scrollbars"])

        pub = b.new_context(viewport={"width": W, "height": H}, device_scale_factor=2,
                            color_scheme="light")
        pg = pub.new_page()
        pg.set_default_timeout(30000)
        pg.goto(APP + "/", wait_until="domcontentloaded")
        pg.wait_for_timeout(2600)
        shot(pg, "01_landing")
        pg.goto(APP + "/demo-tmp/mail.html", wait_until="domcontentloaded")
        pg.wait_for_timeout(1500)
        shot(pg, "07_email")
        pub.close()

        auth = b.new_context(viewport={"width": W, "height": H}, device_scale_factor=2,
                             color_scheme="light")
        auth.add_init_script(
            "try{localStorage.setItem('vexen.access',%s);"
            "localStorage.setItem('vexen.refresh',%s);"
            "localStorage.setItem('vexen.theme','light');}catch(e){}"
            % (json.dumps(REC["access"]), json.dumps(REC["refresh"])))
        pg = auth.new_page()
        pg.set_default_timeout(30000)

        pg.goto(APP + "/app", wait_until="domcontentloaded")
        pg.wait_for_timeout(2600)
        shot(pg, "02_guide")

        pg.goto(APP + "/app/agents", wait_until="domcontentloaded")
        pg.wait_for_timeout(2200)
        try:
            pg.click('[data-testid="open-template-library-button"]')
            pg.wait_for_selector('[data-testid="template-search-input"]')
            pg.fill('[data-testid="template-search-input"]', "refund")
            pg.wait_for_timeout(2000)
        except Exception as exc:
            print("  library:", exc)
        shot(pg, "03_library")

        pg.goto(APP + "/app/try", wait_until="domcontentloaded")
        pg.wait_for_selector('[data-testid="try-page"]')
        pg.wait_for_timeout(1600)
        pg.click('[data-testid="try-permission-select"]')
        pg.wait_for_timeout(400)
        pg.click('[role="option"]:has-text("Purchase products")')
        pg.fill('[data-testid="try-resource-input"]', "sku-8842")
        pg.fill('[data-testid="try-amount-input"]', "250")
        pg.click('[data-testid="try-run-button"]')
        pg.wait_for_selector('[data-testid="try-result-card"]')
        pg.wait_for_timeout(900)
        pg.click('[data-testid="try-toggle-trace"]')
        pg.wait_for_timeout(1200)
        pg.eval_on_selector('[data-testid="try-result-card"]',
                            "el => el.scrollIntoView({block:'start'})")
        shot(pg, "04_decision")
        pg.eval_on_selector('[data-testid="try-result-card"]',
                            "el => window.scrollBy({top: 520})")
        shot(pg, "05_trace")

        pg.goto(APP + "/app/policies", wait_until="domcontentloaded")
        pg.wait_for_timeout(2400)
        shot(pg, "06_rules")

        pg.goto(APP + "/app/approvals", wait_until="domcontentloaded")
        pg.wait_for_timeout(2400)
        shot(pg, "09_approvals")

        pg.goto(APP + "/app/audit", wait_until="domcontentloaded")
        pg.wait_for_timeout(2400)
        try:
            pg.click('[data-testid="verify-audit-button"]')
            pg.wait_for_timeout(2600)
        except Exception as exc:
            print("  verify:", exc)
        shot(pg, "11_history")

        pg.goto(APP + "/app/developers", wait_until="domcontentloaded")
        pg.wait_for_timeout(2000)
        try:
            pg.click('[data-testid="developers-tab-guard"]')
            pg.wait_for_timeout(1100)
            pg.eval_on_selector('[data-testid="developers-snippet-tabs"]',
                                "el => el.scrollIntoView({block:'start'})")
        except Exception as exc:
            print("  developers:", exc)
        shot(pg, "10_sdk")

        pg.goto(APP + "/app/security", wait_until="domcontentloaded")
        pg.wait_for_timeout(2400)
        shot(pg, "12_safety")

        pg.goto(APP + "/app/team", wait_until="domcontentloaded")
        pg.wait_for_timeout(2400)
        shot(pg, "13_team")
        auth.close()

        phone = b.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=3,
                             color_scheme="light", is_mobile=True, has_touch=True)
        pg = phone.new_page()
        pg.goto(approve_url + "?intent=approve", wait_until="domcontentloaded")
        pg.wait_for_selector('[data-testid="approve-request-card"]', timeout=40000)
        pg.wait_for_timeout(1400)
        shot(pg, "08_phone")
        phone.close()
        b.close()
    print("SHOTS COMPLETE")


if __name__ == "__main__":
    main()
