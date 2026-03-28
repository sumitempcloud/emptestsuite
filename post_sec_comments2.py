#!/usr/bin/env python3
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import requests, time

PAT = "$GITHUB_TOKEN"
REPO = "EmpCloud/EmpCloud"
HDR = {"Authorization": f"token {PAT}", "Accept": "application/vnd.github.v3+json"}

def comment(num, body):
    for attempt in range(3):
        r = requests.post(f"https://api.github.com/repos/{REPO}/issues/{num}/comments",
                         json={"body": body}, headers=HDR, timeout=30)
        if r.status_code == 201:
            print(f"  OK #{num}")
            return True
        elif r.status_code == 403 and "secondary" in r.text.lower():
            wait = 30 * (attempt + 1)
            print(f"  Rate limited #{num}, waiting {wait}s (attempt {attempt+1})")
            time.sleep(wait)
        else:
            print(f"  FAIL #{num}: {r.status_code}")
            return False
    return False

def reopen(num):
    r = requests.patch(f"https://api.github.com/repos/{REPO}/issues/{num}",
                      json={"state": "open"}, headers=HDR, timeout=30)
    print(f"  Reopen #{num}: {r.status_code}")

items = [
(76, "FIXED", """Comment by E2E Testing Agent

**Deep Security Retest - #76 Stored XSS in Registration** (2026-03-28)

**Test:** POST /api/v1/auth/register with `first_name: <script>alert(1)</script>` and XSS in `organization_name`
**Response:** 400 VALIDATION_ERROR (both fields rejected)
**Verdict: FIXED** - Server-side input validation rejects XSS payloads."""),

(77, "FIXED", """Comment by E2E Testing Agent

**Deep Security Retest - #77 Privilege Escalation** (2026-03-28)

**Attack:** PUT /api/v1/users/522 with `{"role":"super_admin"}` as Org Admin
**Response:** 403 FORBIDDEN - "Only super admins can assign the super_admin role"
**Verdict: FIXED** - Role changes properly restricted to super admins."""),

(65, "FIXED", """Comment by E2E Testing Agent

**Deep Security Retest - #65 Internal Server IP in JWT** (2026-03-28)

**Test:** Decoded JWT payload, checked `iss` field
**iss:** `https://test-empcloud-api.empcloud.com` (was `http://163.227.174.141:5001`)
**Verdict: FIXED** - No internal IP leak, uses public domain with HTTPS."""),

(67, "FIXED", """Comment by E2E Testing Agent

**Deep Security Retest - #67 JWT Uses HTTP Not HTTPS** (2026-03-28)

**Test:** JWT `iss` = `https://test-empcloud-api.empcloud.com`
**Verdict: FIXED** - Uses HTTPS protocol."""),

(171, "FIXED", """Comment by E2E Testing Agent

**Deep Security Retest - #171 Email Takeover via Mass Assignment** (2026-03-28)

**Attack:** PUT /api/v1/users/524 with `{"email":"hacked@evil.com"}` as Employee
**Response:** 403 FORBIDDEN. Email remains `priya@technova.in`.
**Verdict: FIXED** - Unauthorized email changes blocked."""),

(169, "FIXED", """Comment by E2E Testing Agent

**Deep Security Retest - #169 Mass Assignment (org_id)** (2026-03-28)

**Attack:** PUT /api/v1/users/524 with `{"org_id":9999}` as Employee -> 403 FORBIDDEN
**Verdict: FIXED** - org_id changes blocked for employees."""),

(170, "FIXED", """Comment by E2E Testing Agent

**Deep Security Retest - #170 Mass Assignment (status)** (2026-03-28)

**Attack:** PUT /api/v1/users/524 with `{"status":"inactive"}` as Employee -> 403 FORBIDDEN
**Verdict: FIXED** - Status changes blocked for employees."""),

(172, "FIXED", """Comment by E2E Testing Agent

**Deep Security Retest - #172 Mass Assignment (salary)** (2026-03-28)

**Attack:** PUT /api/v1/users/524 with `{"salary":999999}` as Employee -> 403 FORBIDDEN
**Verdict: FIXED** - Salary changes blocked for employees."""),

(173, "FIXED", """Comment by E2E Testing Agent

**Deep Security Retest - #173 Mass Assignment (verified)** (2026-03-28)

**Attack:** PUT /api/v1/users/524 with `{"verified":true}` as Employee -> 403 FORBIDDEN
**Verdict: FIXED** - Verified flag changes blocked for employees."""),

(317, "STILL FAILING", """Comment by E2E Testing Agent

**Deep Security Retest - #317 Token Valid After Logout** (2026-03-28)

**Test:**
1. Login as Employee, got JWT
2. POST /auth/logout -> **404** (no logout endpoint)
3. GET /auth/logout -> 404, DELETE /auth/session -> 404
4. Old token still works: GET /users -> **200**

**Verdict: STILL FAILING** - No logout endpoint exists. JWT tokens cannot be invalidated server-side. Users cannot securely terminate sessions."""),

(79, "FIXED", """Comment by E2E Testing Agent

**Deep Security Retest - #79 Missing Security Headers** (2026-03-28)

**API headers now present:**
- X-Frame-Options: SAMEORIGIN
- X-Content-Type-Options: nosniff
- Strict-Transport-Security: max-age=31536000; includeSubDomains
- Content-Security-Policy: full policy
- Referrer-Policy: no-referrer
- Cross-Origin-Opener-Policy, Cross-Origin-Resource-Policy, X-DNS-Prefetch-Control
**Verdict: FIXED** - All security headers present on API."""),

(68, "FIXED", """Comment by E2E Testing Agent

**Deep Security Retest - #68 Express Default Error Page** (2026-03-28)

**Test:**
- GET /api/ -> 404 with JSON `{"success":false,"error":{"code":"NOT_FOUND",...}}`
- X-Powered-By: NOT PRESENT (Express fingerprint removed)
**Verdict: FIXED** - API routes return proper JSON errors, no Express leak."""),

(69, "FIXED", """Comment by E2E Testing Agent

**Deep Security Retest - #69 Inconsistent 404 vs 401** (2026-03-28)

**Test:**
- GET /users (no auth) -> 401 JSON `{"code":"UNAUTHORIZED",...}`
- GET /nonexistent (no auth) -> 404 JSON `{"code":"NOT_FOUND",...}`
- GET /admin/super (no auth) -> 401 JSON
**Verdict: FIXED** - Consistent JSON error responses with proper status codes."""),
]

for num, verdict, body in items:
    comment(num, body)
    if verdict == "STILL FAILING":
        time.sleep(3)
        reopen(num)
    time.sleep(10)

print("\nAll done!")
