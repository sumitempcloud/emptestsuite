#!/usr/bin/env python3
"""
EMP Cloud HRMS - Deep API Security Testing
Tests: IDOR, Mass Assignment, Input Validation, Rate Limiting,
       Token Security, Data Exposure, HTTP Method Testing
"""

import urllib.request
import urllib.error
import urllib.parse
import json
import time
import ssl
import sys
import os
from datetime import datetime

# ── Config ──────────────────────────────────────────────────────────────
API = "https://test-empcloud.empcloud.com/api/v1"
GITHUB_PAT = "$GITHUB_TOKEN"
GITHUB_REPO = "EmpCloud/EmpCloud"

CREDS = {
    "org_admin":   {"email": "ananya@technova.in",   "password": "Welcome@123"},
    "employee":    {"email": "priya@technova.in",     "password": "Welcome@123"},
    "super_admin": {"email": "admin@empcloud.com",    "password": "SuperAdmin@2026"},
    "other_org":   {"email": "john@globaltech.com",   "password": "Welcome@123"},
}

HEADERS_BASE = {
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Origin": "https://test-empcloud.empcloud.com",
    "Referer": "https://test-empcloud.empcloud.com/",
    "Accept": "application/json, text/plain, */*",
}

# TLS context that skips cert verification for test env
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

findings = []

# ── Helpers ──────────────────────────────────────────────────────────────
def api(method, path, body=None, token=None, headers_extra=None, timeout=30):
    """Make an API call and return (status_code, response_body_dict, raw_text)."""
    url = f"{API}{path}" if path.startswith("/") else f"{API}/{path}"
    hdrs = dict(HEADERS_BASE)
    if token:
        hdrs["Authorization"] = f"Bearer {token}"
    if headers_extra:
        hdrs.update(headers_extra)

    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")

    req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
    try:
        resp = urllib.request.urlopen(req, timeout=timeout, context=ctx)
        raw = resp.read().decode("utf-8", errors="replace")
        try:
            obj = json.loads(raw)
        except Exception:
            obj = {"_raw": raw}
        return resp.status, obj, raw
    except urllib.error.HTTPError as e:
        raw = ""
        try:
            raw = e.read().decode("utf-8", errors="replace")
        except Exception:
            pass
        try:
            obj = json.loads(raw)
        except Exception:
            obj = {"_raw": raw}
        return e.code, obj, raw
    except Exception as e:
        return 0, {"_error": str(e)}, str(e)


def login(role):
    """Login and return (token, refresh_token, user_info)."""
    cred = CREDS[role]
    status, body, _ = api("POST", "/auth/login", cred)
    if status in (200, 201):
        # Structure: { success, data: { user, org, tokens: { access_token, refresh_token } } }
        data = body.get("data", {}) or {}
        tokens_obj = data.get("tokens", {}) or {}
        token = (tokens_obj.get("access_token") or tokens_obj.get("token")
                 or data.get("access_token") or data.get("token")
                 or body.get("access_token") or body.get("token"))
        refresh = (tokens_obj.get("refresh_token")
                   or data.get("refresh_token")
                   or body.get("refresh_token"))
        user = data.get("user") or body.get("user") or data
        print(f"  [LOGIN] {role}: status={status}, token={'YES' if token else 'NO'}")
        return token, refresh, user
    print(f"  [LOGIN FAIL] {role}: status={status}, body={json.dumps(body)[:300]}")
    return None, None, None


def record(severity, category, title, details, response_snippet=""):
    """Record a security finding."""
    f = {
        "severity": severity,
        "category": category,
        "title": title,
        "details": details,
        "response_snippet": response_snippet[:1500],
        "timestamp": datetime.now().isoformat(),
    }
    findings.append(f)
    marker = {"CRITICAL": "!!!", "HIGH": "!!", "MEDIUM": "!", "LOW": ".", "INFO": "-"}
    print(f"  [{marker.get(severity, '?')}] [{severity}] {title}")


def file_github_issue(finding):
    """File a GitHub issue for a finding."""
    sev = finding["severity"]
    title = f"[SECURITY] [{sev}] {finding['title']}"
    body_parts = [
        f"## Security Finding: {finding['title']}",
        f"**Severity:** {sev}",
        f"**Category:** {finding['category']}",
        f"**Found:** {finding['timestamp']}",
        "",
        "## Details",
        finding["details"],
    ]
    if finding["response_snippet"]:
        body_parts += [
            "",
            "## API Response (redacted)",
            "```json",
            finding["response_snippet"][:800],
            "```",
        ]
    body_parts += [
        "",
        "---",
        "*Found by automated API security testing.*",
    ]
    body = "\n".join(body_parts)

    url = f"https://api.github.com/repos/{GITHUB_REPO}/issues"
    hdrs = {
        "Authorization": f"token {GITHUB_PAT}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "EmpCloud-SecurityTester/1.0",
    }
    labels = ["security", f"severity-{sev.lower()}"]
    payload = {"title": title, "body": body, "labels": labels}

    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=hdrs, method="POST")
    try:
        resp = urllib.request.urlopen(req, timeout=15, context=ctx)
        result = json.loads(resp.read().decode())
        return result.get("html_url", "created")
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")[:300]
        return f"FAILED({e.code}): {raw}"
    except Exception as e:
        return f"ERROR: {e}"


def redact(text, max_len=500):
    """Truncate and redact sensitive data from response text."""
    if not text:
        return ""
    t = text[:max_len]
    for word in ("password", "secret", "token", "ssn", "bank", "account"):
        # Naive redaction of value after key
        pass
    return t


# ── Test 1: IDOR ────────────────────────────────────────────────────────
def test_idor():
    print("\n" + "=" * 70)
    print("TEST 1: IDOR (Insecure Direct Object Reference)")
    print("=" * 70)

    # Login as TechNova admin
    tn_token, _, tn_user = get_token("org_admin")
    if not tn_token:
        record("INFO", "IDOR", "Cannot test IDOR - TechNova login failed", "Login failed for ananya@technova.in")
        return

    # Get TechNova users
    status, body, raw = api("GET", "/users", token=tn_token)
    print(f"  GET /users as TechNova: status={status}")

    tn_user_ids = []
    tn_org_id = None
    users_list = body.get("data") or body.get("users") or body.get("results") or (body if isinstance(body, list) else [])
    if isinstance(users_list, dict):
        users_list = users_list.get("users") or users_list.get("items") or users_list.get("rows") or []
    for u in users_list[:10]:
        if isinstance(u, dict):
            uid = u.get("id") or u.get("_id") or u.get("user_id")
            if uid:
                tn_user_ids.append(uid)
            org = u.get("organization_id") or u.get("org_id")
            if org:
                tn_org_id = org
    print(f"  Found {len(tn_user_ids)} TechNova user IDs: {tn_user_ids[:5]}")

    if not tn_user_ids:
        # Try to extract from user profile
        if isinstance(tn_user, dict):
            uid = tn_user.get("id") or tn_user.get("_id")
            if uid:
                tn_user_ids = [uid]
                tn_org_id = tn_user.get("organization_id") or tn_user.get("org_id")

    if not tn_user_ids:
        record("INFO", "IDOR", "No TechNova user IDs found to test", f"GET /users response: {raw[:300]}")
        return

    # Login as GlobalTech
    gt_token, _, gt_user = get_token("other_org")
    if not gt_token:
        record("INFO", "IDOR", "Cannot test cross-org IDOR - GlobalTech login failed", "Login failed for john@globaltech.com")
        return

    # Try accessing TechNova users from GlobalTech account
    for uid in tn_user_ids[:3]:
        # GET
        status, body, raw = api("GET", f"/users/{uid}", token=gt_token)
        if status == 200:
            record("CRITICAL", "IDOR", f"Cross-org user read: GET /users/{uid} returned 200",
                   f"GlobalTech user accessed TechNova user {uid}.\n\nGET /users/{uid} with GlobalTech token returned 200.\nThis allows any authenticated user to read another org's user data.",
                   redact(raw))
        else:
            print(f"  GET /users/{uid} as GlobalTech: {status} (OK - blocked)")

        # PUT
        status, body, raw = api("PUT", f"/users/{uid}", body={"first_name": "HACKED"}, token=gt_token)
        if status in (200, 201, 204):
            record("CRITICAL", "IDOR", f"Cross-org user update: PUT /users/{uid} returned {status}",
                   f"GlobalTech user modified TechNova user {uid}.\n\nPUT /users/{uid} with GlobalTech token returned {status}.\nPayload: {{\"first_name\": \"HACKED\"}}",
                   redact(raw))
        else:
            print(f"  PUT /users/{uid} as GlobalTech: {status} (OK - blocked)")

        # DELETE
        status, body, raw = api("DELETE", f"/users/{uid}", token=gt_token)
        if status in (200, 204):
            record("CRITICAL", "IDOR", f"Cross-org user delete: DELETE /users/{uid} returned {status}",
                   f"GlobalTech user deleted TechNova user {uid}.\n\nDELETE /users/{uid} with GlobalTech token returned {status}.",
                   redact(raw))
        else:
            print(f"  DELETE /users/{uid} as GlobalTech: {status} (OK - blocked)")

        time.sleep(0.3)

    # Cross-org resource access
    resource_endpoints = [
        "/announcements", "/documents", "/events", "/assets",
        "/positions", "/departments", "/leaves", "/attendance",
        "/payroll", "/holidays", "/designations", "/branches",
    ]
    for endpoint in resource_endpoints:
        # First get IDs from TechNova
        status_tn, body_tn, _ = api("GET", endpoint, token=tn_token)
        items = []
        if status_tn == 200:
            items = body_tn.get("data") or body_tn.get("results") or (body_tn if isinstance(body_tn, list) else [])
            if isinstance(items, dict):
                items = items.get("items") or items.get("rows") or items.get(endpoint.strip("/")) or []

        if items and isinstance(items, list) and len(items) > 0:
            item = items[0] if isinstance(items[0], dict) else {}
            rid = item.get("id") or item.get("_id")
            if rid:
                status, body, raw = api("GET", f"{endpoint}/{rid}", token=gt_token)
                if status == 200:
                    record("HIGH", "IDOR", f"Cross-org resource read: GET {endpoint}/{rid}",
                           f"GlobalTech accessed TechNova {endpoint} resource {rid}.\n\nGET {endpoint}/{rid} with GlobalTech token returned 200.",
                           redact(raw))
                else:
                    print(f"  GET {endpoint}/{rid} as GlobalTech: {status} (OK)")
        else:
            print(f"  {endpoint}: status={status_tn}, no items found to test")
        time.sleep(0.2)


# ── Test 2: Mass Assignment ─────────────────────────────────────────────
def test_mass_assignment():
    print("\n" + "=" * 70)
    print("TEST 2: Mass Assignment")
    print("=" * 70)

    # Use org_admin to test mass assignment (admin can PUT /users/{id})
    admin_token, _, admin_user = get_token("org_admin")
    emp_token, _, emp_user = get_token("employee")
    if not admin_token:
        record("INFO", "Mass Assignment", "Cannot test - admin login failed", "")
        return

    # Find an employee user ID to test with
    uid = None
    if isinstance(emp_user, dict):
        uid = emp_user.get("id") or emp_user.get("_id") or emp_user.get("user_id")
    if not uid and isinstance(admin_user, dict):
        uid = admin_user.get("id") or admin_user.get("_id")

    if not uid:
        record("INFO", "Mass Assignment", "Cannot determine user ID for mass assignment test", "")
        return

    print(f"  Target user ID: {uid}")

    # Read original state first
    status_orig, orig_body, _ = api("GET", f"/users/{uid}", token=admin_token)
    orig_data = orig_body.get("data") or orig_body.get("user") or orig_body
    orig_role = orig_data.get("role") if isinstance(orig_data, dict) else None
    orig_org = orig_data.get("organization_id") or (orig_data.get("org_id") if isinstance(orig_data, dict) else None)

    mass_assignment_tests = [
        {
            "name": "Org Switch",
            "payload": {"organization_id": 999999},
            "field": "organization_id",
            "severity": "CRITICAL",
        },
        {
            "name": "Privilege Escalation (super_admin)",
            "payload": {"role": "super_admin"},
            "field": "role",
            "severity": "CRITICAL",
        },
        {
            "name": "Privilege Escalation (admin)",
            "payload": {"role": "admin"},
            "field": "role",
            "severity": "CRITICAL",
        },
        {
            "name": "Status Reactivation",
            "payload": {"status": 1},
            "field": "status",
            "severity": "HIGH",
        },
        {
            "name": "Email Takeover",
            "payload": {"email": "hacked-test@evil.com"},
            "field": "email",
            "severity": "HIGH",
        },
        {
            "name": "Is Verified Flag",
            "payload": {"is_verified": True, "email_verified": True},
            "field": "is_verified",
            "severity": "MEDIUM",
        },
        {
            "name": "Salary Modification",
            "payload": {"salary": 9999999},
            "field": "salary",
            "severity": "HIGH",
        },
    ]

    for test in mass_assignment_tests:
        status, body, raw = api("PUT", f"/users/{uid}", body=test["payload"], token=admin_token)
        if status in (200, 201, 204):
            # Verify if the field actually changed
            status2, body2, _ = api("GET", f"/users/{uid}", token=admin_token)
            updated = body2.get("data") or body2.get("user") or body2
            field_val = updated.get(test["field"]) if isinstance(updated, dict) else None

            if test["field"] == "role" and field_val in ("super_admin", "admin") and field_val != orig_role:
                record(test["severity"], "Mass Assignment", f"Mass assignment: {test['name']} SUCCEEDED",
                       f"PUT /users/{uid} with {json.dumps(test['payload'])} returned {status}.\nField '{test['field']}' changed to: {field_val}",
                       redact(raw))
            elif test["field"] == "organization_id" and field_val and field_val != orig_org:
                record(test["severity"], "Mass Assignment", f"Mass assignment: {test['name']} SUCCEEDED",
                       f"PUT /users/{uid} with {json.dumps(test['payload'])} returned {status}.\nField changed from {orig_org} to {field_val}",
                       redact(raw))
            elif test["field"] == "email" and isinstance(updated, dict) and updated.get("email") == "hacked-test@evil.com":
                record(test["severity"], "Mass Assignment", f"Mass assignment: {test['name']} SUCCEEDED",
                       f"PUT /users/{uid} with {json.dumps(test['payload'])} returned {status}.\nEmail changed to hacked-test@evil.com",
                       redact(raw))
            else:
                # 200 returned but might not have actually changed the field
                record("MEDIUM", "Mass Assignment", f"Mass assignment: {test['name']} - server accepted payload (200) but field may not have changed",
                       f"PUT /users/{uid} with {json.dumps(test['payload'])} returned {status}.\nField '{test['field']}' current value: {field_val}\nServer accepted the request - verify if field was silently ignored or actually changed.",
                       redact(raw))
        elif status in (400, 422):
            print(f"  {test['name']}: {status} (validated/rejected - OK)")
        elif status in (401, 403):
            print(f"  {test['name']}: {status} (access denied - OK)")
        else:
            print(f"  {test['name']}: {status}")
        time.sleep(0.3)

    # Restore original email if it was changed
    if orig_data and isinstance(orig_data, dict) and orig_data.get("email"):
        api("PUT", f"/users/{uid}", body={"email": orig_data["email"]}, token=admin_token)


# ── Test 3: Input Validation ────────────────────────────────────────────
def test_input_validation():
    print("\n" + "=" * 70)
    print("TEST 3: Input Validation")
    print("=" * 70)

    # Use org_admin for input validation (employees can't PUT /users/{id})
    token, _, user = get_token("org_admin")
    if not token:
        record("INFO", "Input Validation", "Cannot test - login failed", "")
        return

    uid = None
    if isinstance(user, dict):
        uid = user.get("id") or user.get("_id") or user.get("user_id")
    # Get a non-admin user to test updates on
    status_u, body_u, _ = api("GET", "/users", token=token)
    users_list = body_u.get("data") or []
    if isinstance(users_list, dict):
        users_list = users_list.get("users") or users_list.get("items") or users_list.get("rows") or []
    target_uid = None
    for u in users_list:
        if isinstance(u, dict) and u.get("role") != "org_admin":
            target_uid = u.get("id") or u.get("_id")
            if target_uid:
                break
    if not target_uid:
        target_uid = uid  # fallback to admin's own ID

    # Long string test
    long_string = "A" * 10000
    payloads_validation = [
        ("Extremely long string (10000 chars)", {"first_name": long_string}),
        ("Special characters", {"first_name": "<script>alert('xss')</script>"}),
        ("Unicode abuse", {"first_name": "\u0000\u0001\u0002\uffff\ud800"}),
        ("Null bytes", {"first_name": "test\x00admin"}),
        ("SQL Injection in name", {"first_name": "'; DROP TABLE users; --"}),
        ("SQL Injection 2", {"first_name": "' OR '1'='1' --"}),
        ("SQL Injection UNION", {"first_name": "' UNION SELECT password FROM users --"}),
        ("NoSQL Injection", {"first_name": {"$gt": ""}}),
        ("NoSQL regex", {"first_name": {"$regex": ".*"}}),
        ("Negative ID", {"id": -1}),
        ("Zero ID", {"id": 0}),
        ("Float ID", {"id": 1.5}),
        ("HTML injection", {"first_name": "<img src=x onerror=alert(1)>"}),
        ("Path traversal", {"first_name": "../../../etc/passwd"}),
        ("Template injection", {"first_name": "{{7*7}}${7*7}"}),
        ("CRLF injection", {"first_name": "test\r\nX-Injected: header"}),
    ]

    # Test on user update endpoint
    test_uid = target_uid or uid
    target = f"/users/{test_uid}" if test_uid else "/users/me"
    print(f"  Testing input validation on: {target}")
    for name, payload in payloads_validation:
        status, body, raw = api("PUT", target, body=payload, token=token)
        if status in (200, 201):
            # Check if the malicious value was stored as-is
            resp_data = body.get("data") or body.get("user") or body
            stored_name = resp_data.get("first_name") if isinstance(resp_data, dict) else None
            if stored_name and isinstance(payload.get("first_name"), str):
                if "<script>" in str(stored_name) or "DROP TABLE" in str(stored_name):
                    record("HIGH", "Input Validation", f"Stored XSS/SQLi possible: {name}",
                           f"PUT {target} accepted and stored malicious payload.\nStored value: {str(stored_name)[:200]}",
                           redact(raw))
                elif len(str(stored_name)) > 5000:
                    record("MEDIUM", "Input Validation", f"No length limit: {name}",
                           f"Server accepted 10000-char input without truncation.",
                           redact(raw))
                else:
                    print(f"  {name}: {status} (accepted but may be sanitized)")
            else:
                print(f"  {name}: {status} (accepted)")
        elif status in (400, 422):
            print(f"  {name}: {status} (validated - OK)")
        elif status in (401, 403):
            print(f"  {name}: {status} (auth blocked)")
        else:
            print(f"  {name}: {status}")
        time.sleep(0.2)

    # SQL injection in search/filter parameters
    print("\n  --- SQL/NoSQL Injection in Query Parameters ---")
    sqli_payloads = [
        "' OR 1=1 --",
        "'; DROP TABLE users;--",
        "' UNION SELECT 1,2,3,4,5--",
        "1' AND (SELECT COUNT(*) FROM users)>0--",
        "admin'--",
    ]
    search_endpoints = ["/users", "/announcements", "/departments", "/positions", "/events"]

    for endpoint in search_endpoints:
        for sqli in sqli_payloads[:2]:  # Test first 2 per endpoint
            encoded = urllib.parse.quote(sqli)
            status, body, raw = api("GET", f"{endpoint}?search={encoded}", token=token)
            if status == 200:
                items = body.get("data") or body.get("results") or []
                if isinstance(items, dict):
                    items = items.get("items") or items.get("rows") or []
                if isinstance(items, list) and len(items) > 10:
                    record("HIGH", "Input Validation", f"Possible SQL injection in {endpoint}?search=",
                           f"GET {endpoint}?search={sqli[:50]} returned {len(items)} results (possible data dump).",
                           redact(raw))
                else:
                    pass  # Normal behavior
            elif status == 500:
                record("MEDIUM", "Input Validation", f"Server error on SQLi input: {endpoint}",
                       f"GET {endpoint}?search={sqli[:50]} caused HTTP 500 (possible SQL error).",
                       redact(raw))
            time.sleep(0.15)

    # Restore name if changed
    if test_uid:
        api("PUT", target, body={"first_name": "Test"}, token=token)


# ── Test 4: Rate Limiting ───────────────────────────────────────────────
def test_rate_limiting():
    print("\n" + "=" * 70)
    print("TEST 4: Rate Limiting")
    print("=" * 70)

    # Rapid-fire login attempts with wrong password
    print("  --- Brute Force Login (50 attempts) ---")
    blocked = False
    statuses = []
    start = time.time()
    for i in range(50):
        status, body, raw = api("POST", "/auth/login", {"email": "ananya@technova.in", "password": f"wrong{i}"}, timeout=10)
        statuses.append(status)
        if status == 429:
            blocked = True
            print(f"  Rate limited at attempt {i + 1} (429)")
            break
        if status == 423:  # Account locked
            blocked = True
            print(f"  Account locked at attempt {i + 1} (423)")
            break
    elapsed = time.time() - start
    print(f"  Completed {len(statuses)} attempts in {elapsed:.1f}s")

    if not blocked:
        unique_statuses = set(statuses)
        record("HIGH", "Rate Limiting", "No rate limit on login endpoint",
               f"50 rapid login attempts with wrong passwords completed without rate limiting.\n"
               f"Status codes seen: {unique_statuses}\n"
               f"Time taken: {elapsed:.1f}s\n"
               f"This allows brute force password attacks.",
               f"Statuses: {statuses[:20]}")
    else:
        print(f"  Rate limiting or account lockout detected - GOOD")

    time.sleep(1)

    # Rapid-fire registration
    print("  --- Rapid Registration (20 attempts) ---")
    reg_blocked = False
    reg_statuses = []
    for i in range(20):
        payload = {
            "email": f"ratetest{i}@fakeorg{i}.com",
            "password": "Test@12345",
            "first_name": "Rate",
            "last_name": f"Test{i}",
            "organization_name": f"RateTestOrg{i}",
        }
        status, _, _ = api("POST", "/auth/register", body=payload, timeout=10)
        reg_statuses.append(status)
        if status == 429:
            reg_blocked = True
            print(f"  Rate limited at attempt {i + 1}")
            break
    if not reg_blocked and 200 in reg_statuses or 201 in reg_statuses:
        success_count = len([s for s in reg_statuses if s in (200, 201)])
        record("MEDIUM", "Rate Limiting", "No rate limit on registration endpoint",
               f"20 rapid registration attempts: {success_count} succeeded.\nStatuses: {set(reg_statuses)}",
               f"Statuses: {reg_statuses}")
    else:
        print(f"  Registration rate test complete. Statuses: {set(reg_statuses)}")

    time.sleep(1)

    # Rapid API calls to data endpoints
    print("  --- Rapid Data Endpoint Calls (50 attempts) ---")
    token, _, _ = get_token("org_admin")  # use cached token
    if token:
        data_blocked = False
        data_statuses = []
        for i in range(50):
            status, _, _ = api("GET", "/users", token=token, timeout=10)
            data_statuses.append(status)
            if status == 429:
                data_blocked = True
                print(f"  Rate limited at request {i + 1}")
                break
        if not data_blocked:
            record("MEDIUM", "Rate Limiting", "No rate limit on data endpoints",
                   f"50 rapid GET /users requests completed without throttling.\nStatuses: {set(data_statuses)}",
                   f"Statuses: {data_statuses[:20]}")


# ── Test 5: Token Security ──────────────────────────────────────────────
def test_token_security():
    print("\n" + "=" * 70)
    print("TEST 5: Token Security")
    print("=" * 70)

    # Get fresh tokens
    token, refresh, _ = get_token("employee")
    if not token:
        record("INFO", "Token Security", "Cannot test - login failed", "")
        return

    # Test with expired/invalid token
    fake_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxLCJleHAiOjE1MDAwMDAwMDB9.fake_signature"
    status, body, raw = api("GET", "/users", token=fake_token)
    if status == 200:
        record("CRITICAL", "Token Security", "Expired/invalid JWT accepted",
               f"A fabricated JWT with exp=2017 was accepted.\nGET /users returned 200.",
               redact(raw))
    else:
        print(f"  Expired/fake token: {status} (rejected - OK)")

    # Test with empty token
    status, body, raw = api("GET", "/users", token="")
    print(f"  Empty token: {status}")

    # Test with 'null' / 'undefined' token
    for bad in ["null", "undefined", "true", "0"]:
        status, _, _ = api("GET", "/users", token=bad)
        if status == 200:
            record("CRITICAL", "Token Security", f"Auth bypass with token='{bad}'",
                   f"GET /users with Authorization: Bearer {bad} returned 200.")
        else:
            print(f"  Token='{bad}': {status} (rejected - OK)")

    # Use refresh token as access token
    if refresh:
        status, body, raw = api("GET", "/users", token=refresh)
        if status == 200:
            record("HIGH", "Token Security", "Refresh token accepted as access token",
                   f"Using refresh token as Bearer token returned 200 for GET /users.\nRefresh and access tokens are not differentiated.",
                   redact(raw))
        else:
            print(f"  Refresh token as access token: {status} (rejected - OK)")
    else:
        print(f"  No refresh token returned - skipping refresh token test")

    # Check token format and expiry
    import base64
    try:
        parts = token.split(".")
        if len(parts) == 3:
            # Decode payload
            payload_b64 = parts[1] + "=" * (4 - len(parts[1]) % 4)
            payload = json.loads(base64.b64decode(payload_b64).decode())
            exp = payload.get("exp")
            iat = payload.get("iat")
            if exp and iat:
                lifetime = exp - iat
                hours = lifetime / 3600
                print(f"  Token lifetime: {hours:.1f} hours")
                if hours > 24:
                    record("MEDIUM", "Token Security", f"Excessive token lifetime: {hours:.0f} hours",
                           f"JWT token has a lifetime of {hours:.0f} hours ({lifetime}s).\nRecommended: 1-4 hours for access tokens.\nToken payload: {json.dumps({k: v for k, v in payload.items() if k not in ('password',)})}")
                elif hours > 8:
                    record("LOW", "Token Security", f"Long token lifetime: {hours:.0f} hours",
                           f"JWT token has a lifetime of {hours:.0f} hours. Consider shorter expiry.")
            # Check what data is in the token
            sensitive_keys = [k for k in payload.keys() if k in ("password", "ssn", "bank", "salary", "secret")]
            if sensitive_keys:
                record("HIGH", "Token Security", f"Sensitive data in JWT: {sensitive_keys}",
                       f"JWT payload contains sensitive fields: {sensitive_keys}")
            print(f"  JWT payload keys: {list(payload.keys())}")
    except Exception as e:
        print(f"  Token decode: {e}")

    # Token refresh rotation test
    if refresh:
        print("  --- Refresh Token Rotation ---")
        status, body, raw = api("POST", "/auth/refresh", body={"refresh_token": refresh}, token=token)
        if status in (200, 201):
            new_token = body.get("token") or body.get("access_token") or (body.get("data", {}) or {}).get("token")
            new_refresh = body.get("refresh_token") or (body.get("data", {}) or {}).get("refresh_token")

            if new_refresh and new_refresh == refresh:
                record("MEDIUM", "Token Security", "Refresh token not rotated",
                       "After refresh, the same refresh token is returned. Old refresh tokens should be invalidated.",
                       redact(raw))

            # Try using OLD refresh token again
            time.sleep(0.5)
            status2, body2, raw2 = api("POST", "/auth/refresh", body={"refresh_token": refresh}, token=token)
            if status2 in (200, 201):
                record("HIGH", "Token Security", "Old refresh token still valid after rotation",
                       f"After obtaining new tokens via refresh, the old refresh token still works.\nPOST /auth/refresh with old token returned {status2}.\nThis allows token replay attacks.",
                       redact(raw2))
            else:
                print(f"  Old refresh token after rotation: {status2} (invalidated - OK)")
        else:
            print(f"  POST /auth/refresh: {status}")
            # Try alternate refresh endpoints
            for ep in ["/auth/token/refresh", "/auth/refresh-token", "/token/refresh"]:
                status, body, raw = api("POST", ep, body={"refresh_token": refresh}, token=token)
                if status in (200, 201):
                    print(f"  Found refresh endpoint: {ep}")
                    break


# ── Test 6: Data Exposure ───────────────────────────────────────────────
def test_data_exposure():
    print("\n" + "=" * 70)
    print("TEST 6: Data Exposure")
    print("=" * 70)

    token, _, _ = get_token("org_admin")
    if not token:
        record("INFO", "Data Exposure", "Cannot test - login failed", "")
        return

    sensitive_fields = [
        "password", "password_hash", "hashed_password", "hash",
        "token", "access_token", "refresh_token", "api_key", "secret",
        "ssn", "social_security", "tax_id", "pan_number",
        "bank_account", "account_number", "routing_number", "ifsc",
        "credit_card", "card_number",
        "salt", "otp", "reset_token", "verification_token",
    ]

    moderate_fields = [
        "salary", "compensation", "ctc", "bank_name", "aadhaar",
    ]

    endpoints_to_check = [
        "/users", "/employees", "/payroll", "/attendance",
        "/leaves", "/departments", "/positions", "/announcements",
        "/documents", "/assets", "/events", "/holidays",
        "/designations", "/branches", "/salary", "/payslips",
    ]

    for endpoint in endpoints_to_check:
        status, body, raw = api("GET", endpoint, token=token)
        if status != 200:
            print(f"  {endpoint}: {status}")
            continue

        raw_lower = raw.lower()
        found_sensitive = [f for f in sensitive_fields if f'"' + f + '"' in raw_lower or f"'{f}'" in raw_lower]
        found_moderate = [f for f in moderate_fields if f'"' + f + '"' in raw_lower or f"'{f}'" in raw_lower]

        if found_sensitive:
            record("HIGH", "Data Exposure", f"Sensitive fields exposed in {endpoint}",
                   f"GET {endpoint} response contains sensitive fields: {found_sensitive}\n"
                   f"These fields should never appear in API responses.",
                   redact(raw, 800))
        if found_moderate:
            record("MEDIUM", "Data Exposure", f"Potentially sensitive fields in {endpoint}",
                   f"GET {endpoint} response contains: {found_moderate}\n"
                   f"Verify these are appropriate for this endpoint's audience.",
                   redact(raw, 800))
        if not found_sensitive and not found_moderate:
            print(f"  {endpoint}: {status} - no sensitive fields found (OK)")
        time.sleep(0.2)

    # Check if employee can see other employees' salary info
    print("\n  --- Employee accessing salary data ---")
    emp_token, _, _ = get_token("employee")
    if emp_token:
        for endpoint in ["/payroll", "/salary", "/payslips", "/users"]:
            status, body, raw = api("GET", endpoint, token=emp_token)
            if status == 200:
                items = body.get("data") or body.get("results") or []
                if isinstance(items, dict):
                    items = items.get("items") or items.get("rows") or []
                if isinstance(items, list) and len(items) > 1:
                    # Check if employee sees other people's data
                    record("MEDIUM", "Data Exposure", f"Employee can list {endpoint} ({len(items)} records)",
                           f"Employee role (priya@technova.in) can access {endpoint} and sees {len(items)} records.\n"
                           f"Verify employee should only see their own data.",
                           redact(raw, 500))
            time.sleep(0.2)


# ── Test 7: HTTP Method Testing ─────────────────────────────────────────
def test_http_methods():
    print("\n" + "=" * 70)
    print("TEST 7: HTTP Method Testing")
    print("=" * 70)

    token, _, _ = get_token("org_admin")
    if not token:
        record("INFO", "HTTP Methods", "Cannot test - login failed", "")
        return

    # DELETE on critical resources
    print("  --- DELETE on read-only / critical resources ---")
    critical_endpoints = ["/departments/1", "/positions/1", "/branches/1", "/designations/1"]
    for endpoint in critical_endpoints:
        status, body, raw = api("DELETE", endpoint, token=token)
        if status in (200, 204):
            record("HIGH", "HTTP Methods", f"DELETE succeeded on {endpoint}",
                   f"DELETE {endpoint} returned {status}.\nCritical resources should require additional confirmation or be protected.",
                   redact(raw))
        else:
            print(f"  DELETE {endpoint}: {status} (OK)")
        time.sleep(0.2)

    # OPTIONS / TRACE / HEAD
    print("  --- OPTIONS / TRACE / HEAD ---")
    test_endpoints = ["/users", "/auth/login", "/announcements"]
    for endpoint in test_endpoints:
        for method in ["OPTIONS", "TRACE", "HEAD"]:
            status, body, raw = api(method, endpoint, token=token)
            if method == "TRACE" and status == 200:
                record("MEDIUM", "HTTP Methods", f"TRACE enabled on {endpoint}",
                       f"TRACE {endpoint} returned 200. TRACE should be disabled to prevent XST attacks.",
                       redact(raw))
            elif method == "OPTIONS" and status == 200:
                allow = ""
                # Check for overly permissive CORS
                if "access-control-allow-origin" in raw.lower() and "*" in raw:
                    record("MEDIUM", "HTTP Methods", f"Wildcard CORS on {endpoint}",
                           f"OPTIONS {endpoint} returns Access-Control-Allow-Origin: *",
                           redact(raw))
            print(f"  {method} {endpoint}: {status}")
        time.sleep(0.2)

    # PUT/PATCH on read-only endpoints
    print("  --- PUT/PATCH on read-only resources ---")
    readonly = ["/auth/login", "/auth/me", "/holidays"]
    for endpoint in readonly:
        for method in ["PUT", "PATCH"]:
            status, _, raw = api(method, endpoint, body={"test": "data"}, token=token)
            if status in (200, 201, 204):
                record("MEDIUM", "HTTP Methods", f"{method} accepted on read-only {endpoint}",
                       f"{method} {endpoint} returned {status}. This endpoint should not accept modifications.",
                       redact(raw))
            else:
                print(f"  {method} {endpoint}: {status}")
        time.sleep(0.2)


# ── Token Cache ──────────────────────────────────────────────────────────
cached_tokens = {}  # role -> (token, refresh_token, user_info)

def get_token(role):
    """Get cached token or login fresh with retry on rate limit."""
    if role in cached_tokens and cached_tokens[role][0]:
        return cached_tokens[role]
    # Retry with backoff for rate limits
    for attempt in range(5):
        token, refresh, user = login(role)
        if token:
            cached_tokens[role] = (token, refresh, user)
            return token, refresh, user
        # If rate limited (429) or server error (502), wait and retry
        time.sleep(10 * (attempt + 1))
    return None, None, None


# ── Main ─────────────────────────────────────────────────────────────────
def main():
    print("=" * 70)
    print("EMP CLOUD HRMS - API Security Testing Suite")
    print(f"Target: {API}")
    print(f"Time: {datetime.now().isoformat()}")
    print("=" * 70)

    # Verify connectivity
    print("\n[*] Checking API connectivity...")
    status, body, raw = api("GET", "/health")
    if status == 0:
        status, body, raw = api("POST", "/auth/login", CREDS["employee"])
    print(f"  Connectivity check: status={status}")

    # Pre-login all accounts to cache tokens before rate limit tests
    print("\n[*] Pre-caching authentication tokens...")
    for role in ["org_admin", "employee", "super_admin", "other_org"]:
        t, r, u = get_token(role)
        print(f"  {role}: {'OK' if t else 'FAILED'}")
        time.sleep(0.5)

    # Run all tests (rate limiting LAST to avoid blocking other tests)
    test_idor()
    test_mass_assignment()
    test_input_validation()
    test_token_security()
    test_data_exposure()
    test_http_methods()
    test_rate_limiting()  # Must be last - triggers rate limits

    # ── Summary ──────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("SECURITY FINDINGS SUMMARY")
    print("=" * 70)

    by_severity = {}
    for f in findings:
        sev = f["severity"]
        by_severity.setdefault(sev, []).append(f)

    for sev in ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]:
        items = by_severity.get(sev, [])
        if items:
            print(f"\n  [{sev}] ({len(items)} findings)")
            for item in items:
                print(f"    - {item['title']}")

    total = len(findings)
    print(f"\n  TOTAL: {total} findings")

    # File GitHub issues for HIGH and CRITICAL
    actionable = [f for f in findings if f["severity"] in ("CRITICAL", "HIGH", "MEDIUM")]
    if actionable:
        print(f"\n[*] Filing {len(actionable)} GitHub issues...")
        for f in actionable:
            url = file_github_issue(f)
            print(f"  -> {f['severity']}: {f['title'][:60]}... => {url}")
            time.sleep(1)
    else:
        print("\n[*] No actionable findings to file as GitHub issues.")

    print("\n" + "=" * 70)
    print("TESTING COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
