"""Quick end-to-end smoke test against the running Vexen backend."""
import json
import os
import random
import string
import sys

import requests

# A stuck server must fail the run, not hang it.
_request = requests.Session.request


def _request_with_timeout(self, method, url, **kwargs):
    kwargs.setdefault("timeout", 30)
    return _request(self, method, url, **kwargs)


requests.Session.request = _request_with_timeout

SITE = os.environ.get("VEXEN_BASE", "http://127.0.0.1:8000")
BASE = SITE + "/api"
rand = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
EMAIL = f"smoke_{rand}@example.com"
PASSWORD = "SmokeTest123!"

ok, fail = [], []


def check(label, condition, detail=""):
    (ok if condition else fail).append(label)
    print(("PASS " if condition else "FAIL ") + label + (f" :: {detail}" if detail else ""))


def skip(label, why):
    print(f"SKIP {label} :: {why}")


s = requests.Session()

# 1. signup with only name + email + password
r = s.post(f"{BASE}/auth/signup", json={"name": "Smoke Tester", "email": EMAIL, "password": PASSWORD})
check("signup (name/email/password only)", r.status_code == 201, f"{r.status_code} {r.text[:200]}")
data = r.json()
token = data.get("access_token")
s.headers["Authorization"] = f"Bearer {token}"
check("workspace auto-named", bool(data.get("organization", {}).get("name")), json.dumps(data.get("organization", {}))[:120])

# 2. brand new workspace starts with ZERO agents
r = s.get(f"{BASE}/agents")
check("new workspace has 0 agents", r.json().get("total") == 0, str(r.json().get("total")))

# 3. baseline safety rules ARE installed
r = s.get(f"{BASE}/policies")
policies = r.json()
check("baseline rules installed", policies.get("total", 0) > 0, str(policies.get("total")))
# The AI features need a working Anthropic key on the server. Without one they must be
# switched off cleanly, and this script checks that instead of failing.
ai_on = policies.get("generator_available") is True
print(f"NOTE AI features are {'on' if ai_on else 'off'} on this server")

# 4. library is 10k+ and paginates
r = s.get(f"{BASE}/catalog/templates", params={"limit": 24, "page": 2})
lib = r.json()
check("library 10,000+", lib.get("library_size", 0) >= 10000, str(lib.get("library_size")))
check("library paginates", len(lib.get("items", [])) == 24, str(len(lib.get("items", []))))
check("library facets present", len(lib.get("industries", [])) > 5 and len(lib.get("tiers", [])) > 5)

# 5. library search
r = s.get(f"{BASE}/catalog/templates", params={"search": "email healthcare", "limit": 5})
check("library search works", r.json().get("total", 0) > 0, str(r.json().get("total")))

# 6. template detail
tid = lib["items"][0]["id"]
r = s.get(f"{BASE}/catalog/templates/{tid}")
check("template detail", r.status_code == 200 and len(r.json().get("permissions", [])) > 0, tid)

# 7. deploy an agent from a variant template
TEMPLATE = "shopping-agent--retail--standard"
r = s.post(f"{BASE}/agents", json={"name": "Smoke Shopper", "template_id": TEMPLATE})
check("deploy variant template", r.status_code == 201, f"{r.status_code} {r.text[:200]}")
agent = r.json()
agent_id = agent["agent_id"]
check("template applied permissions", agent.get("permission_count", 0) > 0, str(agent.get("permission_count")))

# 8. dry-run authorize (the Try an action page)
r = s.post(f"{BASE}/policies/test", json={"agent_id": agent_id, "resource": "shopping", "action": "purchase", "amount": 25})
small = r.json().get("result", {})
check("small purchase decided", small.get("decision") in {"ALLOW", "APPROVAL_REQUIRED", "BLOCK"}, small.get("decision"))
check("decision has trace", len(small.get("trace", [])) > 0, str(len(small.get("trace", []))))

r = s.post(f"{BASE}/policies/test", json={"agent_id": agent_id, "resource": "shopping", "action": "purchase", "amount": 999999})
big = r.json().get("result", {})
check("huge purchase not auto-allowed", big.get("decision") != "ALLOW", f"{big.get('decision')} :: {big.get('reason')}")

r = s.post(f"{BASE}/policies/test", json={"agent_id": agent_id, "resource": "payments", "action": "read"})
cards = r.json().get("result", {})
check("saved cards blocked (default deny)", cards.get("decision") == "BLOCK", f"{cards.get('decision')} :: {cards.get('reason')}")

# 9. AI natural-language rule generation (Anthropic only)
PROMPT = "Never let any agent spend more than 200 dollars without asking me first"
if ai_on:
    r = s.post(f"{BASE}/policies/generate", json={"prompt": PROMPT}, timeout=130)
    check("AI rule generated", r.status_code == 200, f"{r.status_code} {r.text[:250]}")
    if r.status_code == 200:
        rule = r.json().get("rule", {})
        check("AI rule has an effect", rule.get("effect") in {"DENY", "REQUIRE_APPROVAL", "LIMIT", "MAX_TTL", "REQUIRE_SCOPE"}, str(rule.get("effect")))
        check("AI rule was written by Anthropic", str(rule.get("generated_by", "")).startswith("anthropic:claude-"),
              str(rule.get("generated_by")))
        rr = s.post(f"{BASE}/policies", json={
            "name": rule.get("name", "AI rule"), "description": rule.get("description"),
            "effect": rule["effect"], "match": rule.get("match", {}), "params": rule.get("params", {}),
            "priority": rule.get("priority", 30), "enabled": True, "source": "ai",
        })
        check("AI rule saves", rr.status_code == 201, f"{rr.status_code} {rr.text[:200]}")
    r = s.get(f"{BASE}/assistant/status")
    check("help assistant is offered", r.status_code == 200 and r.json().get("available") is True, r.text[:120])
else:
    r = s.post(f"{BASE}/policies/generate", json={"prompt": PROMPT})
    check("AI rule writer says it is off (503)", r.status_code == 503, f"{r.status_code} {r.text[:160]}")
    r = s.get(f"{BASE}/assistant/status")
    check("help assistant is hidden", r.status_code == 200 and r.json().get("available") is False, r.text[:120])
    skip("AI rule generation", "no working Anthropic key on this server")

# 10. credentials + real API authorize
r = s.post(f"{BASE}/agents/{agent_id}/credentials", json={"name": "Smoke key"})
check("credential issued", r.status_code == 201 and r.json().get("secret"), f"{r.status_code}")
secret = r.json().get("secret")
r = requests.post(f"{BASE}/v1/authorize", headers={"X-Vexen-Key": secret},
                  json={"resource": "shopping", "action": "purchase", "amount": 40})
check("real /v1/authorize works", r.status_code == 200 and r.json().get("decision"), f"{r.status_code} {r.text[:200]}")
r = requests.post(f"{BASE}/v1/authorize", headers={"X-Vexen-Key": secret},
                  data=json.dumps({"resource": "shopping", "action": "purchase", "amount": 41}))  # no Content-Type
check("agent API accepts a JSON body sent without a Content-Type header",
      r.status_code == 200 and r.json().get("decision"), f"{r.status_code} {r.text[:120]}")
r = requests.post(f"{BASE}/v1/authorize", headers={"X-Vexen-Key": "vex_sk_live_bogus"},
                  json={"resource": "shopping", "action": "purchase"})
check("bad key rejected 401", r.status_code == 401, str(r.status_code))

# 11. dashboard / security / audit / approvals / developers / organization / sessions
for label, path in [
    ("dashboard", "/dashboard"), ("security", "/security"), ("audit", "/audit"),
    ("approvals", "/approvals"), ("developers", "/developers"),
    ("organization", "/organization"), ("sessions", "/auth/sessions"),
    ("notifications", "/notifications"), ("catalog permissions", "/catalog/permissions"),
]:
    r = s.get(f"{BASE}{path}")
    check(f"GET {label}", r.status_code == 200, f"{r.status_code} {r.text[:120]}")

# 12. audit chain verification
r = s.get(f"{BASE}/audit/verify")
v = r.json()
check("audit chain intact", v.get("intact") is True, json.dumps(v)[:200])

# 13. profile / notifications / password endpoints
check("profile patch", s.patch(f"{BASE}/auth/profile", json={"name": "Smoke Tester 2"}).status_code == 200)
check("notification prefs patch", s.patch(f"{BASE}/auth/notifications", json={"weekly_digest": True}).status_code == 200)
check("organization patch", s.patch(f"{BASE}/organization", json={"name": "Smoke Workspace"}).status_code == 200)

# 14. tenant isolation — a second user must not see the first user's agent
s2 = requests.Session()
r = s2.post(f"{BASE}/auth/signup", json={"name": "Other Person", "email": f"other_{rand}@example.com", "password": PASSWORD})
s2.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
check("second user isolated (0 agents)", s2.get(f"{BASE}/agents").json().get("total") == 0)
check("cannot read other tenant agent", s2.get(f"{BASE}/agents/{agent_id}").status_code == 404)

# 15. alerts plumbing — email and per-device notifications must be reachable
r = s.get(f"{BASE}/notifications/email")
check("email status endpoint", r.status_code == 200 and "counts" in r.json(), r.text[:140])
r = s.patch(f"{BASE}/auth/notifications", json={"email_approval_requests": False})
check("email prefs save", r.status_code == 200, str(r.status_code))
r = s.get(f"{BASE}/auth/me")
prefs = (r.json().get("user") or {}).get("notification_prefs") or {}
check("email prefs persist", prefs.get("email_approval_requests") is False,
      json.dumps(prefs)[:160])
s.patch(f"{BASE}/auth/notifications", json={"email_approval_requests": True})
r = s.get(f"{BASE}/push/status")
check("push status endpoint", r.status_code == 200 and "public_key" in r.json(), r.text[:140])

# 16. team seats — invite, roles, and what each role may do
MATE = f"mate_{rand}@example.com"
r = s.get(f"{BASE}/team")
check("team endpoint", r.status_code == 200 and r.json().get("your_role") == "owner", r.text[:140])
r = s.post(f"{BASE}/team/invites", json={"email": MATE, "role": "viewer"})
check("invite created", r.status_code == 201, f"{r.status_code} {r.text[:140]}")
join_url = r.json().get("join_url", "")
check("invite link is absolute", join_url.startswith("http") and "/join/" in join_url, join_url[:60])
expected = os.environ.get("VEXEN_EXPECT_PUBLIC_URL", "").rstrip("/")
if expected:
    check("invite link uses the configured public address", join_url.startswith(expected + "/join/"), join_url[:80])
join_token = join_url.rsplit("/join/", 1)[-1]
r = requests.get(f"{BASE}/public/invites/{join_token}")
check("invite preview (no login)", r.status_code == 200 and r.json().get("state") == "pending",
      r.text[:140])
r = requests.get(f"{BASE}/public/invites/{join_token[:-2]}aa")
check("tampered invite refused", r.status_code == 404, str(r.status_code))
r = requests.post(f"{BASE}/public/invites/{join_token}/accept",
                  json={"name": "Mate Person", "password": "alllowercase"})
check("weak password refused on join", r.status_code == 422, str(r.status_code))
r = requests.post(f"{BASE}/public/invites/{join_token}/accept",
                  json={"name": "Mate Person", "password": PASSWORD})
check("invite accepted", r.status_code == 201, f"{r.status_code} {r.text[:140]}")
s3 = requests.Session()
s3.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
check("viewer can read agents", s3.get(f"{BASE}/agents").status_code == 200)
check("viewer cannot create an agent",
      s3.post(f"{BASE}/agents", json={"name": "Nope", "template_id": TEMPLATE}).status_code == 403)
check("viewer cannot invite",
      s3.post(f"{BASE}/team/invites", json={"email": f"x_{rand}@example.com", "role": "viewer"}).status_code == 403)
check("viewer cannot manage people",
      s3.delete(f"{BASE}/team/members/some-id").status_code == 403)

# 17. deciding an approval from an emailed phone link
r = s.post(f"{BASE}/agents", json={"name": "Link Shopper", "template_id": TEMPLATE})
link_agent = r.json()["agent_id"]
link_secret = s.post(f"{BASE}/agents/{link_agent}/credentials",
                     json={"name": "Smoke link key"}).json()["secret"]
r = requests.post(f"{BASE}/v1/authorize", headers={"X-Vexen-Key": link_secret},
                  json={"resource": "shopping", "action": "purchase", "amount": 640,
                        "resource_id": "smoke-ord-1"})
body = r.json()
check("big purchase needs a human", body.get("decision") == "APPROVAL_REQUIRED",
      str(body.get("decision")))
link_approval = body.get("approval_id")
r = s.get(f"{BASE}/notifications/email")
queued = [m for m in r.json().get("recent", []) if m.get("kind") == "approval_alert"]
check("approval alert was queued for email", bool(queued), str(len(queued)))
s.delete(f"{BASE}/agents/{link_agent}")

# 18. cleanup
check("agent delete", s.delete(f"{BASE}/agents/{agent_id}").status_code == 200)

# 19. the public contact form
r = requests.post(f"{BASE}/public/contact", json={
    "name": "Smoke Tester", "email": EMAIL, "topic": "general",
    "message": "This is an automated smoke test message."})
check("contact form accepts a message", r.status_code == 201 and str(r.json().get("reference", "")).startswith("VEX-MSG-"),
      f"{r.status_code} {r.text[:120]}")

# 20. readiness, and the website served from the same address (when a build is present)
r = requests.get(f"{BASE}/ready")
check("ready check reaches the database", r.status_code == 200 and r.json().get("database") == "ok", r.text[:140])
home = requests.get(SITE + "/")
if home.headers.get("content-type", "").startswith("text/html"):
    check("website is served", 'id="root"' in home.text)
    check("a signed-link address opens the app", 'id="root"' in requests.get(SITE + "/approve/abc.def").text)
    check("a missing script is a 404, not a page", requests.get(SITE + "/static/js/nope.js").status_code == 404)
    check("an unknown API path is a JSON 404", requests.get(f"{BASE}/nope").status_code == 404)
else:
    skip("website checks", "this server has no frontend build (API only)")

print("\n" + "=" * 60)
print(f"PASSED {len(ok)} / {len(ok) + len(fail)}")
if fail:
    print("FAILURES:")
    for f in fail:
        print("  -", f)
sys.exit(1 if fail else 0)
