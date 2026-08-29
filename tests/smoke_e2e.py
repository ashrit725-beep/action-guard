"""Quick end-to-end smoke test against the running Vexen backend."""
import json
import os
import random
import string
import sys

import requests

BASE = os.environ.get("VEXEN_BASE", "http://localhost:8001") + "/api"
rand = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
EMAIL = f"smoke_{rand}@example.com"
PASSWORD = "SmokeTest123!"

ok, fail = [], []


def check(label, condition, detail=""):
    (ok if condition else fail).append(label)
    print(("PASS " if condition else "FAIL ") + label + (f" :: {detail}" if detail else ""))


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
check("ai generator available", policies.get("generator_available") is True)

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
r = s.post(f"{BASE}/agents", json={"name": "Smoke Shopper", "template_id": "shopping-agent--retail--standard"})
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

# 9. AI natural-language rule generation
r = s.post(f"{BASE}/policies/generate", json={"prompt": "Never let any agent spend more than 200 dollars without asking me first"})
check("AI rule generated", r.status_code == 200, f"{r.status_code} {r.text[:250]}")
if r.status_code == 200:
    rule = r.json().get("rule", {})
    check("AI rule has an effect", rule.get("effect") in {"DENY", "REQUIRE_APPROVAL", "LIMIT", "MAX_TTL", "REQUIRE_SCOPE"}, str(rule.get("effect")))
    rr = s.post(f"{BASE}/policies", json={
        "name": rule.get("name", "AI rule"), "description": rule.get("description"),
        "effect": rule["effect"], "match": rule.get("match", {}), "params": rule.get("params", {}),
        "priority": rule.get("priority", 30), "enabled": True, "source": "ai",
    })
    check("AI rule saves", rr.status_code == 201, f"{rr.status_code} {rr.text[:200]}")

# 10. credentials + real API authorize
r = s.post(f"{BASE}/agents/{agent_id}/credentials", json={"name": "Smoke key"})
check("credential issued", r.status_code == 201 and r.json().get("secret"), f"{r.status_code}")
secret = r.json().get("secret")
r = requests.post(f"{BASE}/v1/authorize", headers={"X-Vexen-Key": secret},
                  json={"resource": "shopping", "action": "purchase", "amount": 40})
check("real /v1/authorize works", r.status_code == 200 and r.json().get("decision"), f"{r.status_code} {r.text[:200]}")
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

# 15. cleanup
check("agent delete", s.delete(f"{BASE}/agents/{agent_id}").status_code == 200)

print("\n" + "=" * 60)
print(f"PASSED {len(ok)} / {len(ok) + len(fail)}")
if fail:
    print("FAILURES:")
    for f in fail:
        print("  -", f)
sys.exit(1 if fail else 0)
