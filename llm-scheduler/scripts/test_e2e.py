#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
End-to-end smoke test for the LLM Scheduler System.

Tests:
 1. Gateway health check
 2. Register a user
 3. Login as user -> get token
 4. Submit inference request (user)
 5. User can only see own history
 6. Login as admin
 7. Admin sees all history
 8. Scheduler node list
 9. Authorization enforcement

Usage:
    python scripts/test_e2e.py [--base-url http://localhost:8080]
"""
import sys
import time
import argparse
import requests

# Fix Windows GBK terminal encoding
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

parser = argparse.ArgumentParser()
parser.add_argument("--base-url", default="http://localhost:8080")
args = parser.parse_args()

BASE = args.base_url
SCHED = "http://localhost:8001"
MON = "http://localhost:8002"

errors = 0


def check(label, condition, detail=""):
    global errors
    if condition:
        print(f"  [PASS] {label}")
    else:
        print(f"  [FAIL] {label}  {detail}")
        errors += 1


def section(title):
    print(f"\n{'=' * 50}")
    print(f"  {title}")
    print(f"{'=' * 50}")


# 1. Health checks
section("1. Health Checks")
try:
    r = requests.get(f"{BASE}/health", timeout=5)
    check("Gateway /health", r.status_code == 200 and r.json().get("status") == "ok")
except Exception as e:
    check("Gateway /health", False, str(e))

try:
    r = requests.get(f"{SCHED}/health", timeout=5,
                     headers={"X-Internal-Token": "internal-secret-change-me"})
    check("Scheduler /health", r.status_code == 200)
except Exception as e:
    check("Scheduler /health", False, str(e))

try:
    r = requests.get(f"{MON}/health", timeout=5)
    check("Monitoring /health", r.status_code == 200)
except Exception as e:
    check("Monitoring /health", False, str(e))

# 2. Register + login as regular user
section("2. User Registration & Login")
TEST_USER = f"testuser_{int(time.time())}"
TEST_PASS = "password123"

r = requests.post(f"{BASE}/auth/register",
                  json={"username": TEST_USER, "password": TEST_PASS})
check("Register new user (201)", r.status_code == 201, r.text)

r = requests.post(f"{BASE}/auth/login",
                  data={"username": TEST_USER, "password": TEST_PASS})
check("Login as user (200)", r.status_code == 200, r.text)
user_token = r.json().get("access_token", "") if r.status_code == 200 else ""
user_role = r.json().get("role", "") if r.status_code == 200 else ""
check("User role is 'user'", user_role == "user")

USER_HEADERS = {"Authorization": f"Bearer {user_token}"}

# 3. Inference request
section("3. Inference via Gateway")
r = requests.post(
    f"{BASE}/v1/chat/completions",
    json={
        "model": "auto",
        "messages": [{"role": "user", "content": "Say hello in one sentence."}],
        "max_tokens": 50,
        "temperature": 0.5,
    },
    headers=USER_HEADERS,
    timeout=60,
)
check("Inference request (200)", r.status_code == 200, r.text[:200])
if r.status_code == 200:
    reply = r.json().get("choices", [{}])[0].get("message", {}).get("content", "")
    check("Inference reply non-empty", len(reply) > 0, f"reply={reply[:80]}")

# 4. History scoping
section("4. History Scoping")
time.sleep(1)
r = requests.get(f"{BASE}/api/history", headers=USER_HEADERS)
check("User can get history (200)", r.status_code == 200, r.text[:200])
if r.status_code == 200:
    items = r.json().get("items", [])
    all_mine = all(i.get("username") == TEST_USER for i in items)
    check("User only sees own records", all_mine or len(items) == 0,
          f"usernames={[i.get('username') for i in items]}")

# 5. Admin login + full access
section("5. Admin Access")
r = requests.post(f"{BASE}/auth/login",
                  data={"username": "admin", "password": "admin123"})
check("Login as admin (200)", r.status_code == 200, r.text)
admin_token = r.json().get("access_token", "") if r.status_code == 200 else ""
admin_role = r.json().get("role", "") if r.status_code == 200 else ""
check("Admin role is 'admin'", admin_role == "admin")

ADMIN_HEADERS = {"Authorization": f"Bearer {admin_token}"}

r = requests.get(f"{BASE}/api/history", headers=ADMIN_HEADERS)
check("Admin can get all history (200)", r.status_code == 200)

r = requests.get(f"{BASE}/api/admin/users", headers=ADMIN_HEADERS)
check("Admin can list users (200)", r.status_code == 200)
if r.status_code == 200:
    users = r.json()
    check("Users list non-empty", len(users) > 0)
    test_found = any(u["username"] == TEST_USER for u in users)
    check("Registered user appears in admin list", test_found)

# 6. Authorization enforcement
section("6. Authorization Enforcement")
r = requests.get(f"{BASE}/api/admin/users", headers=USER_HEADERS)
check("Regular user blocked from /admin/users (403)", r.status_code == 403, r.text[:100])

r = requests.get(f"{BASE}/api/history")   # no token
check("Unauthenticated request rejected (401)", r.status_code == 401)

# 7. Scheduler nodes
section("7. Scheduler Nodes")
INT_HEADERS = {"X-Internal-Token": "internal-secret-change-me"}
r = requests.get(f"{SCHED}/api/nodes", headers=INT_HEADERS, timeout=5)
check("Scheduler node list (200)", r.status_code == 200)
if r.status_code == 200:
    nodes = r.json()
    print(f"      Registered nodes: {[n['node_id'] for n in nodes]}")
    healthy = [n for n in nodes if n["status"] == "healthy"]
    check("At least one healthy node", len(healthy) > 0)

# Summary
print(f"\n{'=' * 50}")
if errors == 0:
    print("  [ALL PASSED]")
else:
    print(f"  [{errors} FAILED]")
print(f"{'=' * 50}\n")
sys.exit(0 if errors == 0 else 1)
