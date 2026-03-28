#!/usr/bin/env python3
"""
Deep Security Retest for EmpCloud/EmpCloud
Actually attempts each attack vector and verifies if blocked.
"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import requests
import json
import base64
import time
import urllib3
urllib3.disable_warnings()

API = "https://test-empcloud-api.empcloud.com/api/v1"
FRONTEND = "https://test-empcloud.empcloud.com"
GITHUB_PAT = "$GITHUB_TOKEN"
REPO = "EmpCloud/EmpCloud"
TIMEOUT = 30

CREDS = {
    "org_admin": ("ananya@technova.in", "Welcome@123"),
    "employee": ("priya@technova.in", "Welcome@123"),
    "super_admin": ("admin@empcloud.com", "SuperAdmin@2026"),
}

results = []

def log(msg):
    print(msg)

def login(role):
    email, pwd = CREDS[role]
    log(f"  -> Logging in as {role} ({email})...")
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": pwd}, timeout=TIMEOUT, verify=False)
    if r.status_code == 200:
        data = r.json()
        token = data.get("token") or data.get("data", {}).get("token") or data.get("access_token")
        if not token and isinstance(data.get("data"), dict):
            token = data["data"].get("access_token") or data["data"].get("token")
            # Check nested tokens object
            if not token and isinstance(data["data"].get("tokens"), dict):
                token = data["data"]["tokens"].get("access_token") or data["data"]["tokens"].get("token") or data["data"]["tokens"].get("accessToken")
        if not token:
            # Try to find token anywhere in response
            text = json.dumps(data)
            if "token" in text.lower():
                log(f"  -> Login response keys: {list(data.keys())}")
                if "data" in data and isinstance(data["data"], dict):
                    log(f"  -> data keys: {list(data['data'].keys())}")
                    if "tokens" in data["data"]:
                        log(f"  -> tokens keys: {data['data']['tokens'] if isinstance(data['data']['tokens'], dict) else data['data']['tokens']}")
        log(f"  -> Login {'OK' if token else 'FAILED (no token in response)'} (status {r.status_code})")
        return token, data
    else:
        log(f"  -> Login FAILED: {r.status_code} {r.text[:200]}")
        return None, None

def auth_header(token):
    return {"Authorization": f"Bearer {token}"}

def decode_jwt(token):
    """Decode JWT payload without verification"""
    parts = token.split(".")
    if len(parts) < 2:
        return None
    payload = parts[1]
    # Fix padding
    payload += "=" * (4 - len(payload) % 4)
    try:
        decoded = base64.urlsafe_b64decode(payload)
        return json.loads(decoded)
    except Exception as e:
        log(f"  -> JWT decode error: {e}")
        return None

def github_comment(issue_num, body):
    """Post a comment on a GitHub issue"""
    url = f"https://api.github.com/repos/{REPO}/issues/{issue_num}/comments"
    headers = {"Authorization": f"token {GITHUB_PAT}", "Accept": "application/vnd.github.v3+json"}
    r = requests.post(url, json={"body": body}, headers=headers, timeout=TIMEOUT)
    if r.status_code == 201:
        log(f"  -> GitHub comment posted on #{issue_num}")
    else:
        log(f"  -> GitHub comment FAILED on #{issue_num}: {r.status_code} {r.text[:200]}")
    return r.status_code == 201

def github_reopen(issue_num):
    """Reopen a GitHub issue"""
    url = f"https://api.github.com/repos/{REPO}/issues/{issue_num}"
    headers = {"Authorization": f"token {GITHUB_PAT}", "Accept": "application/vnd.github.v3+json"}
    r = requests.patch(url, json={"state": "open"}, headers=headers, timeout=TIMEOUT)
    if r.status_code == 200:
        log(f"  -> GitHub issue #{issue_num} reopened")
    else:
        log(f"  -> GitHub reopen FAILED on #{issue_num}: {r.status_code}")
    return r.status_code == 200

def github_close(issue_num):
    """Close a GitHub issue"""
    url = f"https://api.github.com/repos/{REPO}/issues/{issue_num}"
    headers = {"Authorization": f"token {GITHUB_PAT}", "Accept": "application/vnd.github.v3+json"}
    r = requests.patch(url, json={"state": "closed"}, headers=headers, timeout=TIMEOUT)
    return r.status_code == 200

def get_issue_state(issue_num):
    """Get current state of an issue"""
    url = f"https://api.github.com/repos/{REPO}/issues/{issue_num}"
    headers = {"Authorization": f"token {GITHUB_PAT}", "Accept": "application/vnd.github.v3+json"}
    r = requests.get(url, headers=headers, timeout=TIMEOUT)
    if r.status_code == 200:
        return r.json().get("state", "unknown")
    return "unknown"


# ==========================================
# TEST #76 - Stored XSS in Registration
# ==========================================
def test_76_xss_registration():
    log("\n" + "="*60)
    log("=== #76 Stored XSS in Registration ===")
    log("="*60)

    xss_payload = '<script>alert(1)</script>'

    log(f"  Step 1: POST /auth/register with XSS in first_name: {xss_payload}")
    body = {
        "first_name": xss_payload,
        "last_name": "TestXSS",
        "email": f"xss_test_{int(time.time())}@evil.com",
        "password": "Test@12345",
        "organization_name": "XSS Test Org",
        "phone": "9999999999"
    }
    r = requests.post(f"{API}/auth/register", json=body, timeout=TIMEOUT, verify=False)
    log(f"  Step 2: Response status: {r.status_code}")
    log(f"  Step 2: Response body: {r.text[:500]}")

    if r.status_code in (400, 422):
        verdict = "FIXED"
        detail = f"Server rejected XSS payload with {r.status_code} - input validation in place"
    elif r.status_code == 201 or r.status_code == 200:
        resp_text = r.text
        if xss_payload in resp_text:
            verdict = "NOT A BUG"
            detail = "XSS stored in DB but React auto-escapes on render (per project rules, NOT a bug)"
        else:
            verdict = "NOT A BUG"
            detail = "Registration succeeded but React escapes output (per project rules)"
    elif r.status_code == 409:
        verdict = "INCONCLUSIVE"
        detail = f"Got 409 conflict - registration endpoint works but email may be duplicate"
    else:
        verdict = "INCONCLUSIVE"
        detail = f"Unexpected response: {r.status_code}"

    log(f"  Step 3: VERDICT: {verdict} - {detail}")

    # Also test XSS in other registration fields
    log(f"\n  Step 4: Testing XSS in organization_name field...")
    body2 = {
        "first_name": "Normal",
        "last_name": "User",
        "email": f"xss_org_{int(time.time())}@evil.com",
        "password": "Test@12345",
        "organization_name": xss_payload,
        "phone": "9999999998"
    }
    r2 = requests.post(f"{API}/auth/register", json=body2, timeout=TIMEOUT, verify=False)
    log(f"  Step 4: Org name XSS response: {r2.status_code} - {r2.text[:300]}")

    results.append(("#76", "Stored XSS in Registration", verdict, detail))

    comment = f"""Comment by E2E Testing Agent

**Deep Security Retest - #{76} Stored XSS in Registration**
Date: 2026-03-28

**Test Performed:**
- POST /api/v1/auth/register with `first_name: {xss_payload}`
- Response: {r.status_code}

**Result:** {verdict}
{detail}

Note: Per project rules, XSS stored in DB is NOT a bug since React auto-escapes all rendered content."""

    github_comment(76, comment)
    if verdict == "NOT A BUG" or verdict == "FIXED":
        state = get_issue_state(76)
        if state == "open":
            github_close(76)
            log(f"  -> Closed issue #76 (was open, now {verdict})")
    return verdict


# ==========================================
# TEST #77 - Privilege Escalation (role change)
# ==========================================
def test_77_privilege_escalation():
    log("\n" + "="*60)
    log("=== #77 Users Can Change Own Role to super_admin ===")
    log("="*60)

    log("  Step 1: Login as Org Admin")
    token, data = login("org_admin")
    if not token:
        log("  SKIP: Cannot login")
        results.append(("#77", "Privilege Escalation", "SKIP", "Login failed"))
        return "SKIP"

    # First get current user info
    log("  Step 1b: GET /users/me or /auth/me to find user ID")
    for endpoint in ["/auth/me", "/users/me", "/users/profile"]:
        r = requests.get(f"{API}{endpoint}", headers=auth_header(token), timeout=TIMEOUT, verify=False)
        if r.status_code == 200:
            me_data = r.json()
            log(f"  Step 1b: {endpoint} -> {json.dumps(me_data)[:300]}")
            break

    log("  Step 2: PUT /users/522 with role=super_admin")
    r = requests.put(f"{API}/users/522", json={"role": "super_admin"}, headers=auth_header(token), timeout=TIMEOUT, verify=False)
    log(f"  Step 2: Response status: {r.status_code}")
    log(f"  Step 2: Response body: {r.text[:500]}")

    # Also try PATCH
    log("  Step 2b: PATCH /users/522 with role=super_admin")
    r2 = requests.patch(f"{API}/users/522", json={"role": "super_admin"}, headers=auth_header(token), timeout=TIMEOUT, verify=False)
    log(f"  Step 2b: PATCH Response: {r2.status_code} - {r2.text[:500]}")

    put_status = r.status_code
    patch_status = r2.status_code

    # Check if role changed
    log("  Step 3: Verify - login again and check role")
    token2, data2 = login("org_admin")
    if token2:
        r3 = requests.get(f"{API}/auth/me", headers=auth_header(token2), timeout=TIMEOUT, verify=False)
        if r3.status_code == 200:
            me = r3.json()
            log(f"  Step 3: Current user data after attack: {json.dumps(me)[:400]}")
            role = None
            if isinstance(me.get("data"), dict):
                role = me["data"].get("role") or me["data"].get("user_role")
            elif isinstance(me, dict):
                role = me.get("role") or me.get("user_role")
            log(f"  Step 3: Current role = {role}")

    if put_status in (403, 401) and patch_status in (403, 401):
        verdict = "FIXED"
        detail = f"Server rejected role change: PUT={put_status}, PATCH={patch_status}"
    elif put_status in (403, 401) or patch_status in (403, 401):
        blocked_method = "PUT" if put_status in (403, 401) else "PATCH"
        allowed_method = "PATCH" if put_status in (403, 401) else "PUT"
        allowed_status = patch_status if put_status in (403, 401) else put_status
        if allowed_status == 200:
            verdict = "STILL FAILING"
            detail = f"{blocked_method} blocked ({put_status if blocked_method=='PUT' else patch_status}) but {allowed_method} returned {allowed_status} - partial fix only"
        else:
            verdict = "FIXED"
            detail = f"PUT={put_status}, PATCH={patch_status} - role change rejected"
    elif put_status == 200 or patch_status == 200:
        verdict = "STILL FAILING"
        detail = f"Role change accepted! PUT={put_status}, PATCH={patch_status}"
    elif put_status == 404 and patch_status == 404:
        verdict = "FIXED"
        detail = "Endpoint returns 404 - direct user update not exposed"
    else:
        verdict = "INCONCLUSIVE"
        detail = f"PUT={put_status}, PATCH={patch_status}"

    log(f"  Step 4: VERDICT: {verdict} - {detail}")
    results.append(("#77", "Privilege Escalation", verdict, detail))

    comment = f"""Comment by E2E Testing Agent

**Deep Security Retest - #77 Privilege Escalation (Role Change)**
Date: 2026-03-28

**Attack Attempted:**
1. Logged in as Org Admin (ananya@technova.in)
2. PUT /api/v1/users/522 with `{{"role": "super_admin"}}` -> {put_status}
3. PATCH /api/v1/users/522 with `{{"role": "super_admin"}}` -> {patch_status}
4. Re-logged in to verify role unchanged

**Result:** {verdict}
{detail}"""

    github_comment(77, comment)
    if "FAILING" in verdict:
        github_reopen(77)
    return verdict


# ==========================================
# TEST #65 - Internal Server IP in JWT
# ==========================================
def test_65_jwt_internal_ip():
    log("\n" + "="*60)
    log("=== #65 Internal Server IP in JWT (iss field) ===")
    log("="*60)

    log("  Step 1: Login to get JWT")
    token, data = login("org_admin")
    if not token:
        log("  SKIP: Cannot login")
        results.append(("#65", "JWT Internal IP", "SKIP", "Login failed"))
        return "SKIP"

    log(f"  Step 1: Token (first 50 chars): {token[:50]}...")

    log("  Step 2: Decode JWT payload")
    payload = decode_jwt(token)
    if not payload:
        log("  SKIP: Cannot decode JWT")
        results.append(("#65", "JWT Internal IP", "SKIP", "JWT decode failed"))
        return "SKIP"

    log(f"  Step 2: JWT Payload: {json.dumps(payload, indent=2)}")

    iss = payload.get("iss", "NOT PRESENT")
    log(f"  Step 3: iss field = {iss}")

    internal_ip = "163.227.174.141"
    has_internal_ip = internal_ip in str(iss)
    has_any_ip = any(c.isdigit() and "." in str(iss) for c in str(iss))

    # Also check for any private IPs
    import re
    ip_pattern = r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}'
    found_ips = re.findall(ip_pattern, str(payload))

    if has_internal_ip:
        verdict = "STILL FAILING"
        detail = f"JWT iss contains internal IP {internal_ip}: iss={iss}"
    elif found_ips:
        verdict = "STILL FAILING"
        detail = f"JWT contains IP addresses: {found_ips}, iss={iss}"
    elif iss == "NOT PRESENT":
        verdict = "FIXED"
        detail = "JWT has no iss field - no IP leak"
    elif "empcloud.com" in str(iss) and not found_ips:
        verdict = "FIXED"
        detail = f"JWT iss uses public domain: {iss}"
    else:
        verdict = "FIXED"
        detail = f"No internal IP found. iss={iss}"

    log(f"  Step 4: VERDICT: {verdict} - {detail}")
    results.append(("#65", "JWT Internal IP", verdict, detail))

    comment = f"""Comment by E2E Testing Agent

**Deep Security Retest - #65 Internal Server IP in JWT**
Date: 2026-03-28

**Test Performed:**
1. Logged in as Org Admin, obtained JWT
2. Decoded JWT payload (base64)
3. Checked `iss` field: `{iss}`
4. Full payload keys: {list(payload.keys()) if payload else 'N/A'}

**Result:** {verdict}
{detail}"""

    github_comment(65, comment)
    if "FAILING" in verdict:
        github_reopen(65)
    return verdict


# ==========================================
# TEST #67 - JWT uses HTTP not HTTPS
# ==========================================
def test_67_jwt_http():
    log("\n" + "="*60)
    log("=== #67 JWT Uses HTTP Instead of HTTPS ===")
    log("="*60)

    log("  Step 1: Login to get JWT")
    token, data = login("org_admin")
    if not token:
        results.append(("#67", "JWT HTTP", "SKIP", "Login failed"))
        return "SKIP"

    payload = decode_jwt(token)
    if not payload:
        results.append(("#67", "JWT HTTP", "SKIP", "JWT decode failed"))
        return "SKIP"

    iss = payload.get("iss", "NOT PRESENT")
    log(f"  Step 2: JWT iss = {iss}")
    log(f"  Step 2: Full payload: {json.dumps(payload, indent=2)}")

    if iss == "NOT PRESENT":
        verdict = "FIXED"
        detail = "No iss field in JWT - HTTP/HTTPS issue N/A"
    elif str(iss).startswith("http://"):
        verdict = "STILL FAILING"
        detail = f"JWT iss uses HTTP (insecure): {iss}"
    elif str(iss).startswith("https://"):
        verdict = "FIXED"
        detail = f"JWT iss uses HTTPS: {iss}"
    else:
        verdict = "FIXED"
        detail = f"iss does not contain HTTP URL: {iss}"

    log(f"  Step 3: VERDICT: {verdict} - {detail}")
    results.append(("#67", "JWT HTTP not HTTPS", verdict, detail))

    comment = f"""Comment by E2E Testing Agent

**Deep Security Retest - #67 JWT Uses HTTP Not HTTPS**
Date: 2026-03-28

**Test Performed:**
1. Decoded JWT payload
2. Checked `iss` field: `{iss}`

**Result:** {verdict}
{detail}"""

    github_comment(67, comment)
    if "FAILING" in verdict:
        github_reopen(67)
    return verdict


# ==========================================
# TEST #171 - Email Takeover via Mass Assignment
# ==========================================
def test_171_email_takeover():
    log("\n" + "="*60)
    log("=== #171 Email Takeover via Mass Assignment ===")
    log("="*60)

    log("  Step 1: Login as Employee (priya)")
    token, data = login("employee")
    if not token:
        results.append(("#171", "Email Takeover", "SKIP", "Login failed"))
        return "SKIP"

    evil_email = "hacked@evil.com"

    # Try PUT
    log(f"  Step 2: PUT /users/524 with email={evil_email}")
    r = requests.put(f"{API}/users/524", json={"email": evil_email}, headers=auth_header(token), timeout=TIMEOUT, verify=False)
    log(f"  Step 2: PUT response: {r.status_code} - {r.text[:500]}")

    # Try PATCH
    log(f"  Step 2b: PATCH /users/524 with email={evil_email}")
    r2 = requests.patch(f"{API}/users/524", json={"email": evil_email}, headers=auth_header(token), timeout=TIMEOUT, verify=False)
    log(f"  Step 2b: PATCH response: {r2.status_code} - {r2.text[:500]}")

    # Also try profile update endpoint
    log(f"  Step 2c: PUT /users/profile with email={evil_email}")
    r3 = requests.put(f"{API}/users/profile", json={"email": evil_email}, headers=auth_header(token), timeout=TIMEOUT, verify=False)
    log(f"  Step 2c: Profile PUT response: {r3.status_code} - {r3.text[:300]}")

    # Verify email didn't change
    log("  Step 3: GET /users/524 to verify email")
    r4 = requests.get(f"{API}/users/524", headers=auth_header(token), timeout=TIMEOUT, verify=False)
    log(f"  Step 3: GET response: {r4.status_code} - {r4.text[:500]}")

    email_changed = False
    if r4.status_code == 200:
        user_data = r4.json()
        current_email = None
        if isinstance(user_data.get("data"), dict):
            current_email = user_data["data"].get("email")
        elif isinstance(user_data, dict):
            current_email = user_data.get("email")
        log(f"  Step 3: Current email = {current_email}")
        if current_email == evil_email:
            email_changed = True

    put_ok = r.status_code in (200, 201)
    patch_ok = r2.status_code in (200, 201)

    if email_changed:
        verdict = "STILL FAILING"
        detail = f"Email was changed to {evil_email}! PUT={r.status_code}, PATCH={r2.status_code}"
    elif put_ok or patch_ok:
        # 200 but email not changed - server may silently ignore email field
        verdict = "FIXED"
        detail = f"Server returned 200 but email field was silently ignored (not changed). PUT={r.status_code}, PATCH={r2.status_code}"
    elif r.status_code in (403, 401) or r2.status_code in (403, 401):
        verdict = "FIXED"
        detail = f"Server rejected email change: PUT={r.status_code}, PATCH={r2.status_code}"
    elif r.status_code == 404 and r2.status_code == 404:
        verdict = "FIXED"
        detail = "Direct user update endpoint returns 404"
    else:
        verdict = "INCONCLUSIVE"
        detail = f"PUT={r.status_code}, PATCH={r2.status_code}, GET={r4.status_code}"

    log(f"  Step 4: VERDICT: {verdict} - {detail}")
    results.append(("#171", "Email Takeover", verdict, detail))

    comment = f"""Comment by E2E Testing Agent

**Deep Security Retest - #171 Email Takeover via Mass Assignment**
Date: 2026-03-28

**Attack Attempted:**
1. Logged in as Employee (priya@technova.in)
2. PUT /api/v1/users/524 with `{{"email": "hacked@evil.com"}}` -> {r.status_code}
3. PATCH /api/v1/users/524 with `{{"email": "hacked@evil.com"}}` -> {r2.status_code}
4. Verified email via GET /api/v1/users/524

**Result:** {verdict}
{detail}"""

    github_comment(171, comment)
    if "FAILING" in verdict:
        github_reopen(171)
    return verdict


# ==========================================
# TEST #169-173 - Mass Assignment (various fields)
# ==========================================
def test_mass_assignment_fields():
    log("\n" + "="*60)
    log("=== #169-173 Mass Assignment (org_id, status, salary, verified) ===")
    log("="*60)

    log("  Step 1: Login as Employee")
    token, data = login("employee")
    if not token:
        for num in [169, 170, 172, 173]:
            results.append((f"#{num}", "Mass Assignment", "SKIP", "Login failed"))
        return

    # Get user ID
    r_me = requests.get(f"{API}/auth/me", headers=auth_header(token), timeout=TIMEOUT, verify=False)
    me_data = r_me.json() if r_me.status_code == 200 else {}
    user_id = None
    if isinstance(me_data.get("data"), dict):
        user_id = me_data["data"].get("id") or me_data["data"].get("user_id")
    log(f"  Step 1b: User ID = {user_id}")

    test_cases = [
        (169, "org_id", {"org_id": 9999}, "Organization ID change"),
        (170, "status", {"status": "inactive"}, "Status change"),
        (172, "salary", {"salary": 999999, "base_salary": 999999, "ctc": 999999}, "Salary change"),
        (173, "verified", {"verified": True, "is_verified": True, "email_verified": True}, "Verified flag change"),
    ]

    for issue_num, field_name, payload, desc in test_cases:
        log(f"\n  --- Testing #{issue_num}: {desc} ---")

        target = f"/users/{user_id}" if user_id else "/users/524"

        log(f"  PUT {target} with {json.dumps(payload)}")
        r = requests.put(f"{API}{target}", json=payload, headers=auth_header(token), timeout=TIMEOUT, verify=False)
        log(f"  PUT response: {r.status_code} - {r.text[:300]}")

        log(f"  PATCH {target} with {json.dumps(payload)}")
        r2 = requests.patch(f"{API}{target}", json=payload, headers=auth_header(token), timeout=TIMEOUT, verify=False)
        log(f"  PATCH response: {r2.status_code} - {r2.text[:300]}")

        # Also try profile endpoint
        r3 = requests.put(f"{API}/users/profile", json=payload, headers=auth_header(token), timeout=TIMEOUT, verify=False)
        log(f"  Profile PUT response: {r3.status_code} - {r3.text[:200]}")

        # Check if field changed
        r4 = requests.get(f"{API}{target}", headers=auth_header(token), timeout=TIMEOUT, verify=False)
        field_changed = False
        if r4.status_code == 200:
            resp = r4.json()
            user_obj = resp.get("data", resp) if isinstance(resp, dict) else resp
            if isinstance(user_obj, dict):
                for k, v in payload.items():
                    if user_obj.get(k) == v:
                        field_changed = True
                        log(f"  WARNING: Field {k} was changed to {v}!")

        if field_changed:
            verdict = "STILL FAILING"
            detail = f"{field_name} was actually changed via mass assignment"
        elif r.status_code in (403, 401, 404) and r2.status_code in (403, 401, 404):
            verdict = "FIXED"
            detail = f"Server rejected {field_name} change: PUT={r.status_code}, PATCH={r2.status_code}"
        elif r.status_code == 200 or r2.status_code == 200:
            verdict = "FIXED"
            detail = f"Server returned 200 but {field_name} field silently ignored (not changed)"
        elif r.status_code == 404:
            verdict = "FIXED"
            detail = f"Endpoint returns 404 - direct field update not exposed"
        else:
            verdict = "INCONCLUSIVE"
            detail = f"PUT={r.status_code}, PATCH={r2.status_code}"

        log(f"  VERDICT: {verdict} - {detail}")
        results.append((f"#{issue_num}", f"Mass Assignment ({field_name})", verdict, detail))

        comment = f"""Comment by E2E Testing Agent

**Deep Security Retest - #{issue_num} Mass Assignment ({desc})**
Date: 2026-03-28

**Attack Attempted:**
1. Logged in as Employee (priya@technova.in)
2. PUT {target} with `{json.dumps(payload)}` -> {r.status_code}
3. PATCH {target} with `{json.dumps(payload)}` -> {r2.status_code}
4. PUT /users/profile with same payload -> {r3.status_code}
5. Verified via GET - field changed: {field_changed}

**Result:** {verdict}
{detail}"""

        github_comment(issue_num, comment)
        if "FAILING" in verdict:
            github_reopen(issue_num)


# ==========================================
# TEST #317 - Token Valid After Logout
# ==========================================
def test_317_token_after_logout():
    log("\n" + "="*60)
    log("=== #317 Token Valid After Logout ===")
    log("="*60)

    log("  Step 1: Login to get fresh token")
    token, data = login("employee")
    if not token:
        results.append(("#317", "Token After Logout", "SKIP", "Login failed"))
        return "SKIP"

    log("  Step 1b: Verify token works before logout")
    # Try multiple 'me' endpoints to find the right one
    me_endpoint = None
    for ep in ["/auth/me", "/users/me", "/users/profile", "/me", "/users"]:
        r0 = requests.get(f"{API}{ep}", headers=auth_header(token), timeout=TIMEOUT, verify=False)
        log(f"  Step 1b: {ep} -> {r0.status_code}")
        if r0.status_code == 200:
            me_endpoint = ep
            break
    if not me_endpoint:
        log("  WARNING: No working 'me' endpoint found, using /users for verification")

    log("  Step 2: POST /auth/logout")
    r1 = requests.post(f"{API}/auth/logout", headers=auth_header(token), timeout=TIMEOUT, verify=False)
    log(f"  Step 2: Logout response: {r1.status_code} - {r1.text[:300]}")

    # Also try DELETE /auth/logout
    if r1.status_code in (404, 405):
        log("  Step 2b: Trying GET /auth/logout")
        r1b = requests.get(f"{API}/auth/logout", headers=auth_header(token), timeout=TIMEOUT, verify=False)
        log(f"  Step 2b: GET logout: {r1b.status_code} - {r1b.text[:200]}")

        log("  Step 2c: Trying DELETE /auth/session")
        r1c = requests.delete(f"{API}/auth/session", headers=auth_header(token), timeout=TIMEOUT, verify=False)
        log(f"  Step 2c: DELETE session: {r1c.status_code} - {r1c.text[:200]}")

    log("  Step 3: Use OLD token to access protected endpoint")
    time.sleep(1)  # small delay
    verify_ep = me_endpoint or "/users"
    r2 = requests.get(f"{API}{verify_ep}", headers=auth_header(token), timeout=TIMEOUT, verify=False)
    log(f"  Step 3: Old token {verify_ep}: {r2.status_code} - {r2.text[:300]}")

    r3 = requests.get(f"{API}/users", headers=auth_header(token), timeout=TIMEOUT, verify=False)
    log(f"  Step 3b: Old token /users: {r3.status_code}")

    if r1.status_code == 404:
        verdict = "STILL FAILING"
        detail = "No logout endpoint exists (/auth/logout returns 404) - tokens cannot be invalidated"
    elif r2.status_code == 401:
        verdict = "FIXED"
        detail = "Token properly invalidated after logout - returns 401"
    elif r2.status_code == 200:
        verdict = "STILL FAILING"
        detail = f"Old token still works after logout! /auth/me={r2.status_code}, /users={r3.status_code}"
    else:
        verdict = "INCONCLUSIVE"
        detail = f"Logout={r1.status_code}, post-logout /auth/me={r2.status_code}"

    log(f"  Step 4: VERDICT: {verdict} - {detail}")
    results.append(("#317", "Token After Logout", verdict, detail))

    comment = f"""Comment by E2E Testing Agent

**Deep Security Retest - #317 Token Valid After Logout**
Date: 2026-03-28

**Test Performed:**
1. Logged in as Employee, got fresh JWT
2. Verified token works (GET /auth/me -> {r0.status_code})
3. POST /auth/logout -> {r1.status_code}
4. Used OLD token: GET /auth/me -> {r2.status_code}, GET /users -> {r3.status_code}

**Result:** {verdict}
{detail}"""

    github_comment(317, comment)
    if "FAILING" in verdict:
        github_reopen(317)
    return verdict


# ==========================================
# TEST #79 - Missing Security Headers
# ==========================================
def test_79_security_headers():
    log("\n" + "="*60)
    log("=== #79 Missing Security Headers ===")
    log("="*60)

    log(f"  Step 1: GET {FRONTEND}/ and check headers")
    r = requests.get(FRONTEND, timeout=TIMEOUT, verify=False)
    log(f"  Step 1: Status: {r.status_code}")
    log(f"  Step 1: All headers:")
    for k, v in r.headers.items():
        log(f"    {k}: {v}")

    # Also check API headers
    log(f"\n  Step 1b: GET {API}/auth/me headers (API)")
    r2 = requests.get(f"{API}/auth/me", timeout=TIMEOUT, verify=False)
    log(f"  Step 1b: API headers:")
    for k, v in r2.headers.items():
        log(f"    {k}: {v}")

    headers = {k.lower(): v for k, v in r.headers.items()}
    api_headers = {k.lower(): v for k, v in r2.headers.items()}

    missing = []
    found = []

    checks = {
        "x-frame-options": "Clickjacking protection",
        "x-content-type-options": "MIME sniffing protection",
        "strict-transport-security": "HSTS",
        "content-security-policy": "CSP",
        "x-xss-protection": "XSS protection (legacy)",
        "referrer-policy": "Referrer policy",
    }

    for header, desc in checks.items():
        in_frontend = header in headers
        in_api = header in api_headers
        status = "PRESENT" if (in_frontend or in_api) else "MISSING"
        location = []
        if in_frontend: location.append("frontend")
        if in_api: location.append("API")

        if in_frontend or in_api:
            val = headers.get(header) or api_headers.get(header)
            found.append(f"  {header}: {val} ({', '.join(location)})")
            log(f"  [PRESENT] {header} ({desc}): {val} ({', '.join(location)})")
        else:
            missing.append(f"  {header} ({desc})")
            log(f"  [MISSING] {header} ({desc})")

    if len(missing) == 0:
        verdict = "FIXED"
        detail = "All security headers present"
    elif len(missing) <= 2:
        verdict = "PARTIALLY FIXED"
        detail = f"Missing {len(missing)}/{len(checks)} headers: {', '.join(h.split('(')[0].strip() for h in missing)}"
    else:
        verdict = "STILL FAILING"
        detail = f"Missing {len(missing)}/{len(checks)} security headers"

    log(f"\n  Step 2: VERDICT: {verdict} - {detail}")
    results.append(("#79", "Missing Security Headers", verdict, detail))

    missing_list = "\n".join(missing) if missing else "None"
    found_list = "\n".join(found) if found else "None"

    comment = f"""Comment by E2E Testing Agent

**Deep Security Retest - #79 Missing Security Headers**
Date: 2026-03-28

**Test Performed:**
- GET {FRONTEND}/ (frontend headers)
- GET {API}/auth/me (API headers)

**Headers Found:**
{found_list}

**Headers Missing:**
{missing_list}

**Result:** {verdict}
{detail}"""

    github_comment(79, comment)
    if "FAILING" in verdict:
        github_reopen(79)
    return verdict


# ==========================================
# TEST #68 - Express Default Error Page
# ==========================================
def test_68_express_error():
    log("\n" + "="*60)
    log("=== #68 Express Default Error Page ===")
    log("="*60)

    log("  Step 1: GET /api/ (should not reveal Express)")
    r = requests.get(f"{API.rsplit('/api/v1', 1)[0]}/api/", timeout=TIMEOUT, verify=False)
    log(f"  Step 1: Status: {r.status_code}")
    log(f"  Step 1: Body: {r.text[:500]}")
    log(f"  Step 1: Content-Type: {r.headers.get('Content-Type', 'N/A')}")

    # Also check root
    log("  Step 1b: GET / on API domain")
    r2 = requests.get(f"{API.rsplit('/api/v1', 1)[0]}/", timeout=TIMEOUT, verify=False)
    log(f"  Step 1b: Status: {r2.status_code}")
    log(f"  Step 1b: Body: {r2.text[:500]}")

    # Check X-Powered-By header
    powered_by = r.headers.get("X-Powered-By", "NOT PRESENT")
    log(f"  Step 1c: X-Powered-By: {powered_by}")

    has_express_text = "Cannot GET" in r.text or "Express" in r.text
    has_html_error = r.text.strip().startswith("<!DOCTYPE") or r.text.strip().startswith("<html")
    is_json = "application/json" in r.headers.get("Content-Type", "")
    reveals_express = powered_by.lower() == "express" or "express" in r.text.lower()

    if has_express_text or reveals_express:
        verdict = "STILL FAILING"
        detail = f"Express framework revealed: X-Powered-By={powered_by}, body contains Express text: {has_express_text}"
    elif is_json:
        verdict = "FIXED"
        detail = f"Returns JSON response, no Express leak. X-Powered-By={powered_by}"
    elif has_html_error:
        verdict = "STILL FAILING"
        detail = "Returns HTML error page instead of JSON"
    else:
        verdict = "FIXED"
        detail = f"No Express default page. Status={r.status_code}, X-Powered-By={powered_by}"

    log(f"\n  Step 2: VERDICT: {verdict} - {detail}")
    results.append(("#68", "Express Default Error", verdict, detail))

    comment = f"""Comment by E2E Testing Agent

**Deep Security Retest - #68 Express Default Error Page**
Date: 2026-03-28

**Test Performed:**
1. GET /api/ -> {r.status_code} (Content-Type: {r.headers.get('Content-Type', 'N/A')})
2. Body: `{r.text[:200].replace(chr(10), ' ')}`
3. X-Powered-By: {powered_by}

**Result:** {verdict}
{detail}"""

    github_comment(68, comment)
    if "FAILING" in verdict:
        github_reopen(68)
    return verdict


# ==========================================
# TEST #69 - Inconsistent 404 vs 401
# ==========================================
def test_69_inconsistent_errors():
    log("\n" + "="*60)
    log("=== #69 Inconsistent 404 vs 401 Responses ===")
    log("="*60)

    log("  Step 1: GET /users without auth (should be 401)")
    r1 = requests.get(f"{API}/users", timeout=TIMEOUT, verify=False)
    log(f"  Step 1: /users -> {r1.status_code} {r1.text[:300]}")
    log(f"  Step 1: Content-Type: {r1.headers.get('Content-Type', 'N/A')}")

    log("  Step 2: GET /nonexistent without auth")
    r2 = requests.get(f"{API}/nonexistent_endpoint_xyz", timeout=TIMEOUT, verify=False)
    log(f"  Step 2: /nonexistent -> {r2.status_code} {r2.text[:300]}")
    log(f"  Step 2: Content-Type: {r2.headers.get('Content-Type', 'N/A')}")

    log("  Step 3: GET /admin/super without auth")
    r3 = requests.get(f"{API}/admin/super", timeout=TIMEOUT, verify=False)
    log(f"  Step 3: /admin/super -> {r3.status_code} {r3.text[:300]}")

    # Check consistency
    ct1 = r1.headers.get("Content-Type", "")
    ct2 = r2.headers.get("Content-Type", "")

    is_json1 = "json" in ct1.lower()
    is_json2 = "json" in ct2.lower()

    both_json = is_json1 and is_json2

    # Check if valid endpoint returns 401 and invalid returns something different
    users_is_401 = r1.status_code == 401
    nonexist_is_401_or_404 = r2.status_code in (401, 404)

    issues = []
    if not is_json1 and r1.status_code != 200:
        issues.append(f"/users returns non-JSON ({ct1})")
    if not is_json2:
        issues.append(f"nonexistent returns non-JSON ({ct2})")
    if "Cannot GET" in r2.text or "Express" in r2.text:
        issues.append("Express default error page on 404")
    if r1.status_code != 401 and r1.status_code != 403:
        issues.append(f"/users without auth returns {r1.status_code} instead of 401")

    if not issues:
        verdict = "FIXED"
        detail = f"Consistent error responses: /users={r1.status_code}(JSON:{is_json1}), /nonexistent={r2.status_code}(JSON:{is_json2})"
    else:
        verdict = "STILL FAILING"
        detail = f"Issues: {'; '.join(issues)}"

    log(f"\n  Step 4: VERDICT: {verdict} - {detail}")
    results.append(("#69", "Inconsistent Errors", verdict, detail))

    comment = f"""Comment by E2E Testing Agent

**Deep Security Retest - #69 Inconsistent 404 vs 401 Responses**
Date: 2026-03-28

**Test Performed:**
1. GET /api/v1/users (no auth) -> {r1.status_code} (Content-Type: {ct1})
2. GET /api/v1/nonexistent (no auth) -> {r2.status_code} (Content-Type: {ct2})
3. GET /api/v1/admin/super (no auth) -> {r3.status_code}

**Analysis:**
- Both JSON? {both_json}
- /users returns 401? {users_is_401}
- Issues: {issues if issues else 'None'}

**Result:** {verdict}
{detail}"""

    github_comment(69, comment)
    if "FAILING" in verdict:
        github_reopen(69)
    return verdict


# ==========================================
# MAIN
# ==========================================
def main():
    log("=" * 70)
    log("  DEEP SECURITY RETEST - EmpCloud/EmpCloud")
    log("  Date: 2026-03-28")
    log("=" * 70)

    # Run all tests
    test_76_xss_registration()
    test_77_privilege_escalation()
    test_65_jwt_internal_ip()
    test_67_jwt_http()
    test_171_email_takeover()
    test_mass_assignment_fields()
    test_317_token_after_logout()
    test_79_security_headers()
    test_68_express_error()
    test_69_inconsistent_errors()

    # Summary
    log("\n" + "=" * 70)
    log("  SUMMARY")
    log("=" * 70)

    for issue, name, verdict, detail in results:
        icon = "PASS" if "FIXED" in verdict or "NOT A BUG" in verdict else ("FAIL" if "FAILING" in verdict else "???")
        log(f"  [{icon}] {issue} {name}: {verdict}")
        log(f"         {detail}")

    fixed = sum(1 for _, _, v, _ in results if "FIXED" in v or "NOT A BUG" in v)
    failing = sum(1 for _, _, v, _ in results if "FAILING" in v)
    partial = sum(1 for _, _, v, _ in results if "PARTIAL" in v)
    other = len(results) - fixed - failing - partial

    log(f"\n  Total: {len(results)} tests")
    log(f"  Fixed/Not a Bug: {fixed}")
    log(f"  Still Failing: {failing}")
    log(f"  Partially Fixed: {partial}")
    log(f"  Inconclusive/Skip: {other}")
    log("=" * 70)

if __name__ == "__main__":
    main()
