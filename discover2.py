#!/usr/bin/env python3
import sys, json, requests, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE = "https://test-empcloud.empcloud.com"
API = f"{BASE}/api/v1"

# Get the full login response
r = requests.post(f"{API}/auth/login", json={
    "email": "ananya@technova.in", "password": "Welcome@123"
}, timeout=15)
print(f"Status: {r.status_code}")
data = r.json()
print(f"Full response keys: {list(data.keys())}")
print(f"data keys: {list(data.get('data', {}).keys())}")
print(f"Full response:\n{json.dumps(data, indent=2)[:2000]}")

# Extract token
token = data.get("data", {}).get("token") or data.get("data", {}).get("access_token") or data.get("token")
print(f"\nToken: {token[:50] if token else 'NOT FOUND'}...")

# Also check response headers for tokens
print(f"\nResponse headers:")
for k, v in r.headers.items():
    if "token" in k.lower() or "auth" in k.lower() or "cookie" in k.lower() or "set" in k.lower():
        print(f"  {k}: {v[:100]}")

# Check cookies
print(f"Cookies from response: {dict(r.cookies)}")

if token:
    headers = {"Authorization": f"Bearer {token}"}
    print("\n=== Testing endpoints with token ===")
    endpoints = [
        "/employees", "/departments", "/leaves", "/leave", "/attendance",
        "/documents", "/announcements", "/events", "/surveys", "/tickets",
        "/helpdesk", "/assets", "/positions", "/forum", "/wellness",
        "/feedback", "/whistleblowing", "/me", "/auth/me", "/profile",
        "/organization", "/company", "/settings", "/notifications",
        "/leave/balance", "/leave/types", "/attendance/today",
        "/announcements/list", "/documents/list", "/employees/list"
    ]
    for ep in endpoints:
        try:
            r2 = requests.get(f"{API}{ep}", headers=headers, timeout=8)
            if r2.status_code != 404:
                try:
                    body = r2.json()
                    txt = json.dumps(body)[:200]
                except:
                    txt = r2.text[:200]
                print(f"  GET {ep} -> {r2.status_code}: {txt}")
        except Exception as e:
            print(f"  GET {ep} -> ERROR: {e}")
else:
    print("No token, trying with cookies...")
    sess = requests.Session()
    r2 = sess.post(f"{API}/auth/login", json={
        "email": "ananya@technova.in", "password": "Welcome@123"
    }, timeout=15)
    print(f"Session cookies: {dict(sess.cookies)}")
    for ep in ["/employees", "/me", "/departments"]:
        r3 = sess.get(f"{API}{ep}", timeout=8)
        print(f"  GET {ep} -> {r3.status_code}: {r3.text[:200]}")
