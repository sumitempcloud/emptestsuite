#!/usr/bin/env python3
import sys, json, urllib.request, ssl
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

urls = [
    "https://test-empcloud-api.empcloud.com/api/v1/auth/login",
    "https://test-empcloud-api.empcloud.com/auth/login",
    "https://test-empcloud-api.empcloud.com/api/auth/login",
    "https://test-empcloud.empcloud.com/api/v1/auth/login",
    "https://test-empcloud.empcloud.com/auth/login",
]

for url in urls:
    print(f"\n--- {url} ---")
    try:
        data = json.dumps({"email": "ananya@technova.in", "password": "Welcome@123"}).encode()
        req = urllib.request.Request(url, data=data, method="POST", headers={
            "Content-Type": "application/json",
            "User-Agent": "Test/1.0",
            "Accept": "application/json",
        })
        resp = urllib.request.urlopen(req, timeout=15, context=ctx)
        body = resp.read().decode()
        print(f"Status: {resp.status}")
        print(f"Body: {body[:1500]}")
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        print(f"HTTP {e.code}: {body[:500]}")
    except Exception as e:
        print(f"Error: {e}")
