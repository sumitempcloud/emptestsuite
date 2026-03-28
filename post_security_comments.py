#!/usr/bin/env python3
"""Post GitHub comments for security retest results with rate limit handling."""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import requests
import time

GITHUB_PAT = "$GITHUB_TOKEN"
REPO = "EmpCloud/EmpCloud"
TIMEOUT = 30

def gh_comment(issue_num, body):
    url = f"https://api.github.com/repos/{REPO}/issues/{issue_num}/comments"
    headers = {"Authorization": f"token {GITHUB_PAT}", "Accept": "application/vnd.github.v3+json"}
    r = requests.post(url, json={"body": body}, headers=headers, timeout=TIMEOUT)
    if r.status_code == 201:
        print(f"  OK: Comment posted on #{issue_num}")
    elif r.status_code == 403:
        print(f"  RATE LIMITED on #{issue_num}, waiting 60s...")
        time.sleep(60)
        r = requests.post(url, json={"body": body}, headers=headers, timeout=TIMEOUT)
        print(f"  Retry #{issue_num}: {r.status_code}")
    else:
        print(f"  FAIL #{issue_num}: {r.status_code} {r.text[:200]}")
    return r.status_code

def gh_reopen(issue_num):
    url = f"https://api.github.com/repos/{REPO}/issues/{issue_num}"
    headers = {"Authorization": f"token {GITHUB_PAT}", "Accept": "application/vnd.github.v3+json"}
    r = requests.patch(url, json={"state": "open"}, headers=headers, timeout=TIMEOUT)
    print(f"  Reopen #{issue_num}: {r.status_code}")

comments = [
    (76, """Comment by E2E Testing Agent

**Deep Security Retest - #76 Stored XSS in Registration**
Date: 2026-03-28

**Test Performed:**
- POST /api/v1/auth/register with `first_name: <script>alert(1)</script>`
- Also tested XSS in `organization_name` field
- Both rejected with 400 VALIDATION_ERROR

**Result: FIXED**
Server rejects XSS payloads with 400 validation error - input sanitization is in place.
Note: Per project rules, XSS stored in DB would not be a bug anyway since React auto-escapes."""),

    (77, """Comment by E2E Testing Agent

**Deep Security Retest - #77 Privilege Escalation (Role Change to super_admin)**
Date: 2026-03-28

**Attack Attempted:**
1. Logged in as Org Admin (ananya@technova.in)
2. PUT /api/v1/users/522 with `{"role": "super_admin"}` -> **403 FORBIDDEN** ("Only super admins can assign the super_admin role")
3. PATCH /api/v1/users/522 -> **404** (endpoint doesn't exist)
4. Re-logged in and verified role remains `org_admin`

**Result: FIXED**
Server properly validates role changes - only super admins can assign super_admin role."""),

    (65, """Comment by E2E Testing Agent

**Deep Security Retest - #65 Internal Server IP in JWT**
Date: 2026-03-28

**Test Performed:**
1. Logged in, obtained JWT token
2. Decoded JWT payload (base64)
3. Checked `iss` field: `https://test-empcloud-api.empcloud.com`
4. No internal IP (163.227.174.141) found anywhere in JWT payload
5. Full payload keys: sub, org_id, email, role, first_name, last_name, org_name, scope, client_id, jti, iat, exp, iss

**Result: FIXED**
JWT `iss` now uses public domain `https://test-empcloud-api.empcloud.com` instead of internal IP."""),

    (67, """Comment by E2E Testing Agent

**Deep Security Retest - #67 JWT Uses HTTP Instead of HTTPS**
Date: 2026-03-28

**Test Performed:**
1. Decoded JWT payload
2. `iss` field: `https://test-empcloud-api.empcloud.com`
3. Confirmed starts with `https://`

**Result: FIXED**
JWT `iss` field now uses HTTPS protocol."""),

    (171, """Comment by E2E Testing Agent

**Deep Security Retest - #171 Email Takeover via Mass Assignment**
Date: 2026-03-28

**Attack Attempted:**
1. Logged in as Employee (priya@technova.in)
2. PUT /api/v1/users/524 with `{"email": "hacked@evil.com"}` -> **403 FORBIDDEN**
3. PATCH /api/v1/users/524 -> **404** (endpoint doesn't exist)
4. PUT /api/v1/users/profile with email change -> **403 FORBIDDEN**
5. Verified via GET /api/v1/users/524 - email still `priya@technova.in`

**Result: FIXED**
Server rejects unauthorized email changes with 403 Forbidden."""),

    (169, """Comment by E2E Testing Agent

**Deep Security Retest - #169 Mass Assignment (org_id)**
Date: 2026-03-28

**Attack Attempted:**
- PUT /api/v1/users/524 with `{"org_id": 9999}` -> **403 FORBIDDEN**
- PATCH -> **404**
- PUT /users/profile with org_id -> **403 FORBIDDEN**

**Result: FIXED**
Server rejects org_id changes from employees."""),

    (170, """Comment by E2E Testing Agent

**Deep Security Retest - #170 Mass Assignment (status)**
Date: 2026-03-28

**Attack Attempted:**
- PUT /api/v1/users/524 with `{"status": "inactive"}` -> **403 FORBIDDEN**
- PATCH -> **404**
- PUT /users/profile -> **403 FORBIDDEN**

**Result: FIXED**
Server rejects status changes from employees."""),

    (172, """Comment by E2E Testing Agent

**Deep Security Retest - #172 Mass Assignment (salary)**
Date: 2026-03-28

**Attack Attempted:**
- PUT /api/v1/users/524 with `{"salary": 999999, "base_salary": 999999, "ctc": 999999}` -> **403 FORBIDDEN**
- PATCH -> **404**
- PUT /users/profile -> **403 FORBIDDEN**

**Result: FIXED**
Server rejects salary changes from employees."""),

    (173, """Comment by E2E Testing Agent

**Deep Security Retest - #173 Mass Assignment (verified flag)**
Date: 2026-03-28

**Attack Attempted:**
- PUT /api/v1/users/524 with `{"verified": true, "is_verified": true}` -> **403 FORBIDDEN**
- PATCH -> **404**
- PUT /users/profile -> **403 FORBIDDEN**

**Result: FIXED**
Server rejects verified flag changes from employees."""),

    (317, """Comment by E2E Testing Agent

**Deep Security Retest - #317 Token Valid After Logout**
Date: 2026-03-28

**Test Performed:**
1. Logged in as Employee, got fresh JWT
2. Verified token works (GET /users -> 200)
3. POST /auth/logout -> **404** (endpoint does not exist)
4. Also tried GET /auth/logout -> 404, DELETE /auth/session -> 404
5. Used OLD token: GET /users -> **200** (still works!)

**Result: STILL FAILING**
No logout endpoint exists. JWT tokens cannot be server-side invalidated. Old tokens remain valid until expiry. This is a session security gap - users cannot securely log out."""),

    (79, """Comment by E2E Testing Agent

**Deep Security Retest - #79 Missing Security Headers**
Date: 2026-03-28

**Test Performed:**
- Checked both frontend (test-empcloud.empcloud.com) and API (test-empcloud-api.empcloud.com) headers

**API Headers (all present):**
- X-Frame-Options: SAMEORIGIN
- X-Content-Type-Options: nosniff
- Strict-Transport-Security: max-age=31536000; includeSubDomains
- Content-Security-Policy: full policy with upgrade-insecure-requests
- X-XSS-Protection: 0 (correct modern value)
- Referrer-Policy: no-referrer
- Plus: Cross-Origin-Opener-Policy, Cross-Origin-Resource-Policy, X-DNS-Prefetch-Control, X-Download-Options, X-Permitted-Cross-Domain-Policies

**Frontend:** Headers served by Cloudflare (static site), security headers on API responses.

**Result: FIXED**
All standard security headers present on API responses."""),

    (68, """Comment by E2E Testing Agent

**Deep Security Retest - #68 Express Default Error Page**
Date: 2026-03-28

**Test Performed:**
1. GET /api/ -> **404** with proper JSON: `{"success":false,"error":{"code":"NOT_FOUND","message":"Endpoint not found"}}`
2. X-Powered-By header: **NOT PRESENT** (Express fingerprint removed)
3. GET / (root) -> still shows HTML "Cannot GET /" but this is outside /api/ routes

**Result: FIXED**
API routes return proper JSON errors. Express fingerprint (X-Powered-By) removed. Default Express error page no longer shown on API endpoints."""),

    (69, """Comment by E2E Testing Agent

**Deep Security Retest - #69 Inconsistent 404 vs 401 Responses**
Date: 2026-03-28

**Test Performed:**
1. GET /api/v1/users (no auth) -> **401** `{"success":false,"error":{"code":"UNAUTHORIZED","message":"Missing or invalid authorization header"}}` (JSON)
2. GET /api/v1/nonexistent (no auth) -> **404** `{"success":false,"error":{"code":"NOT_FOUND","message":"Endpoint not found"}}` (JSON)
3. GET /api/v1/admin/super (no auth) -> **401** (JSON)

**Analysis:**
- Protected endpoints consistently return 401 without auth
- Unknown endpoints return 404
- All responses are JSON with consistent `{success, error: {code, message}}` format

**Result: FIXED**
Error responses are now consistent JSON with proper status codes."""),
]

for issue_num, body in comments:
    gh_comment(issue_num, body)
    time.sleep(5)  # 5 second delay between comments

# Reopen #317
print("\nReopening #317...")
gh_reopen(317)

print("\nDone!")
