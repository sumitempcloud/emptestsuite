# EMP Cloud — Bug Report from E2E Testing

**Application:** https://test-empcloud.empcloud.com/
**Date:** 2026-03-27
**Tested via:** HTTP/API probing (curl), JS bundle analysis, header inspection

---

## CRITICAL SEVERITY (P0) — Fix Immediately

---

### BUG-001: Stored XSS — No Input Sanitization on Registration Fields
**Severity:** CRITICAL | **Category:** Security (OWASP A7 - XSS)

**Description:** The `/api/v1/auth/register` endpoint accepts and stores raw HTML/JavaScript in `first_name`, `last_name`, and `org_name` fields without any sanitization. The malicious payload is stored in the database and returned verbatim in API responses.

**Steps to Reproduce:**
```bash
POST /api/v1/auth/register
{
  "email": "xss@example.com",
  "password": "Test123!@#",
  "org_name": "<script>alert(1)</script>",
  "first_name": "<img src=x onerror=alert(1)>",
  "last_name": "Test"
}
```

**Actual Result:** Registration succeeds. The org name is stored as `<script>alert(1)</script>` and first name as `<img src=x onerror=alert(1)>`. These values are returned in API responses and will execute when rendered in the browser by any user viewing this data.

**Expected Result:** Input should be sanitized/escaped. HTML tags should be stripped or encoded before storage.

**Impact:** Any user viewing the organization name or employee name in the dashboard will have arbitrary JavaScript executed in their browser. This can lead to session hijacking, data theft, and full account takeover.

---

### BUG-002: Privilege Escalation — Users Can Change Their Own Role to super_admin
**Severity:** CRITICAL | **Category:** Security (OWASP A1 - Broken Access Control)

**Description:** A regular `org_admin` user can escalate their privileges to `super_admin` by sending a PUT request to their own user endpoint with a `role` field.

**Steps to Reproduce:**
```bash
PUT /api/v1/users/593
Authorization: Bearer <org_admin_token>
{"role": "super_admin"}
```

**Actual Result:** The role is changed to `super_admin` and confirmed on subsequent login. The JWT token now contains `"role": "super_admin"`.

**Expected Result:** The `role` field should not be updatable via the user update endpoint. Role changes should require a separate privileged endpoint with proper authorization checks.

**Impact:** Any authenticated user can become a super administrator, gaining full control over the platform and all tenant data.

---

### BUG-003: Open Registration — Anyone Can Create an Organization and Get Admin Access
**Severity:** CRITICAL | **Category:** Security (Business Logic Flaw)

**Description:** The `/api/v1/auth/register` endpoint is completely open with no restrictions. Anyone can create a new organization and immediately receive an `org_admin` role with full JWT tokens.

**Steps to Reproduce:**
```bash
POST /api/v1/auth/register
{
  "email": "anyone@example.com",
  "password": "Test123!@#",
  "org_name": "My Corp",
  "first_name": "John",
  "last_name": "Doe"
}
```

**Actual Result:** Organization created. User gets `org_admin` role. Full JWT access + refresh tokens returned. No email verification required. No CAPTCHA. No rate limiting on registration.

**Expected Result:** Registration should require:
- Email verification before account activation
- CAPTCHA to prevent automated abuse
- Possibly invitation-only or admin-approved registration
- Rate limiting

**Impact:** Attackers can mass-create organizations, pollute the database, and abuse the platform. Combined with BUG-002, any registered user can escalate to `super_admin`.

---

### BUG-004: Internal Server IP Address Leaked in JWT Token
**Severity:** CRITICAL | **Category:** Security (Information Disclosure)

**Description:** The JWT token's `iss` (issuer) field contains a raw internal IP address: `http://163.227.174.141:3000`.

**Evidence:**
```json
{
  "iss": "http://163.227.174.141:3000",
  "sub": 593,
  "org_id": 36,
  "role": "org_admin"
}
```

**Expected Result:** The issuer should be a public domain (e.g., `https://test-empcloud.empcloud.com`) and should never expose internal infrastructure IPs or ports.

**Impact:** Attackers know the internal server IP (`163.227.174.141`) and that the application runs on port 3000. This enables targeted attacks against the backend server directly, bypassing Cloudflare protection.

---

## HIGH SEVERITY (P1)

---

### BUG-005: Missing Security Headers on Frontend (Static Assets)
**Severity:** HIGH | **Category:** Security (OWASP A5 - Security Misconfiguration)

**Description:** The static HTML/frontend served by Cloudflare is missing all critical security headers. While the API backend has proper security headers (CSP, HSTS, X-Frame-Options, etc.), the frontend does not.

**Frontend response headers (MISSING):**
- ❌ `Content-Security-Policy` — not set
- ❌ `X-Content-Type-Options` — not set
- ❌ `X-Frame-Options` — not set (clickjacking possible)
- ❌ `Strict-Transport-Security` — not set
- ❌ `Referrer-Policy` — not set
- ❌ `Permissions-Policy` — not set
- ❌ `X-XSS-Protection` — not set

**API backend headers (present):**
- ✅ `Content-Security-Policy`
- ✅ `X-Content-Type-Options: nosniff`
- ✅ `X-Frame-Options: SAMEORIGIN`
- ✅ `Strict-Transport-Security: max-age=31536000; includeSubDomains`

**Impact:** The frontend is vulnerable to clickjacking, MIME-type sniffing, and other attacks. The discrepancy between frontend and API security headers suggests the static file server (Cloudflare Pages/CDN) was not configured with security headers.

---

### BUG-006: No Rate Limiting on Login Endpoint
**Severity:** HIGH | **Category:** Security (OWASP A7 - Identification and Authentication Failures)

**Description:** The login endpoint allows unlimited rapid requests with no rate limiting, account lockout, or CAPTCHA.

**Steps to Reproduce:** Sent 10 rapid failed login requests — all returned `401` with no throttling:
```
Request 1: 401
Request 2: 401
...
Request 10: 401
```
The API-level rate limit is set to 500 requests per 60 seconds (`ratelimit-policy: 500;w=60`), which is far too permissive for an authentication endpoint.

**Expected Result:** After 5 failed attempts:
- Account temporarily locked (15-30 minutes)
- CAPTCHA required
- Rate limit of ~5-10 attempts per minute on auth endpoints

**Impact:** Brute-force and credential stuffing attacks are feasible.

---

### BUG-007: TLS 1.0 and TLS 1.1 Are Still Supported
**Severity:** HIGH | **Category:** Security (OWASP A2 - Cryptographic Failures)

**Description:** The server accepts connections using deprecated TLS versions 1.0 and 1.1, which have known vulnerabilities (BEAST, POODLE, etc.).

**Evidence:**
```
TLS 1.0: HTTP/2 200 ✅ (should be rejected)
TLS 1.1: HTTP/2 200 ✅ (should be rejected)
TLS 1.2: HTTP/2 200 ✅ (acceptable)
```

**Expected Result:** Only TLS 1.2+ should be accepted. TLS 1.0 and 1.1 should return connection errors.

**Impact:** Attackers can force protocol downgrade to weaker TLS versions and exploit known vulnerabilities.

---

### BUG-008: JWT Token Uses HTTP Issuer (Not HTTPS)
**Severity:** HIGH | **Category:** Security

**Description:** The JWT `iss` field uses `http://` (not `https://`): `http://163.227.174.141:3000`. This indicates the backend is not using TLS internally.

**Impact:** If inter-service communication is over HTTP, tokens and data in transit are vulnerable to interception within the network.

---

### BUG-009: Express Default Error Page Exposed
**Severity:** HIGH | **Category:** Security (Information Disclosure)

**Description:** Invalid API routes return the default Express.js HTML error page (`Cannot GET /api/`) instead of a JSON error response. This reveals the backend framework.

**Evidence:**
```html
<pre>Cannot GET /api/</pre>
```

**Expected Result:** API should return a consistent JSON error: `{"success": false, "error": {"code": "NOT_FOUND"}}`. Framework-specific error pages should be disabled.

---

## MEDIUM SEVERITY (P2)

---

### BUG-010: Inconsistent API Route Responses (404 vs 401)
**Severity:** MEDIUM | **Category:** API Design / Security

**Description:** API endpoints behave inconsistently for unauthenticated requests. Some return `401 Unauthorized` (proper) while others return `404 Not Found` (HTML error page). This inconsistency reveals which endpoints exist.

| Endpoint | Response | Correct? |
|----------|----------|----------|
| `/api/v1/users` | 401 JSON | ✅ |
| `/api/v1/announcements` | 401 JSON | ✅ |
| `/api/v1/employees` | 404 HTML | ❌ |
| `/api/v1/attendance` | 404 HTML | ❌ |
| `/api/v1/leaves` | 404 HTML | ❌ |
| `/api/v1/payroll` | 404 HTML | ❌ |
| `/api/v1/departments` | 404 HTML | ❌ |

**Expected Result:** All protected endpoints should return `401` with JSON for unauthenticated requests. Non-existent endpoints should also return JSON (not HTML).

**Impact:** Attackers can enumerate which API routes exist vs which are genuinely not implemented.

---

### BUG-011: Validation Error Messages Leak Internal Schema Details
**Severity:** MEDIUM | **Category:** Information Disclosure

**Description:** The registration validation errors reveal the exact Zod schema used internally, including field names, types, regex patterns, and minimum lengths.

**Evidence:**
```json
{
  "details": [
    {"code": "too_small", "minimum": 8, "type": "string", "inclusive": true},
    {"validation": "regex", "message": "Must contain at least one uppercase letter"},
    {"validation": "regex", "message": "Must contain at least one lowercase letter"},
    {"validation": "regex", "message": "Must contain at least one special character"}
  ]
}
```

**Impact:** While helpful for the frontend, this level of detail helps attackers understand exact password requirements and data schemas for crafting payloads.

---

### BUG-012: No Email Verification on Registration
**Severity:** MEDIUM | **Category:** Business Logic

**Description:** After registration, the account is immediately active with full admin access. No email verification step exists.

**Impact:** Fake/disposable email addresses can be used to create accounts. No way to verify user identity.

---

### BUG-013: Health Endpoint Exposes Version Information
**Severity:** MEDIUM | **Category:** Information Disclosure

**Description:** The `/health` endpoint is publicly accessible and returns the application version.

**Evidence:**
```json
{"success": true, "data": {"status": "healthy", "version": "1.0.0", "timestamp": "2026-03-27T14:01:24.328Z"}}
```

**Expected Result:** Health endpoint should return minimal info (just `{"status": "ok"}`). Version info should be behind authentication.

---

### BUG-014: Module Base URLs Expose Internal Service Architecture
**Severity:** MEDIUM | **Category:** Information Disclosure

**Description:** The `/api/v1/modules` endpoint returns full internal service URLs for all microservices:

| Module | Exposed URL |
|--------|-------------|
| Biometrics | `https://biometrics.empcloud.com` |
| Monitoring | `https://test-empmonitor.empcloud.com` |
| Exit Management | `https://test-exit.empcloud.com` |
| Field Force | `https://test-field.empcloud.com` |
| LMS | `https://testlms.empcloud.com` |
| Payroll | `https://testpayroll.empcloud.com` |
| Performance | `https://test-performance.empcloud.com` |
| Projects | `https://test-project.empcloud.com` |
| Recruitment | `https://test-recruit.empcloud.com` |
| Rewards | `https://test-rewards.empcloud.com` |

**Impact:** Complete microservice architecture map is exposed to any authenticated user. This aids targeted attacks on individual services.

---

### BUG-015: User Update Returns Full User Object Including Sensitive Fields
**Severity:** MEDIUM | **Category:** Information Disclosure

**Description:** The `PUT /api/v1/users/:id` response returns the complete user object including all fields. Sensitive fields like `role`, `organization_id`, and dates should be filtered from responses.

---

### BUG-016: Inconsistent Naming in Subdomain URLs
**Severity:** LOW | **Category:** Configuration

**Description:** Module base URLs use inconsistent naming patterns: `test-empmonitor`, `testlms`, `testpayroll`, `test-recruit`. Some use hyphens, others don't. Some prefix `test-`, others prefix `test`.

---

## SUMMARY

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL (P0) | 4 | BUG-001 to BUG-004 |
| HIGH (P1) | 5 | BUG-005 to BUG-009 |
| MEDIUM (P2) | 7 | BUG-010 to BUG-016 |
| **Total** | **16** | |

### Top 3 Most Urgent Fixes:
1. **BUG-002** — Privilege escalation to `super_admin` (anyone can become a platform super admin)
2. **BUG-001** — Stored XSS in registration fields (can compromise any user's browser session)
3. **BUG-003** — Open registration with no verification (enables mass account creation + abuse)

---

*Note: These tests were performed via HTTP/API-level probing only (no browser automation). Additional UI-level bugs (broken layouts, JS errors, workflow issues) would require Selenium/Playwright testing with actual browser interaction.*
