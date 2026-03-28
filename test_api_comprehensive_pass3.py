#!/usr/bin/env python3
"""
Pass 3: File remaining bugs and test additional edge cases.
"""
import sys, json, urllib.request, urllib.error, ssl, time

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

BASE = "https://test-empcloud-api.empcloud.com"
API = f"{BASE}/api/v1"
GITHUB_PAT = "$GITHUB_TOKEN"
GITHUB_REPO = "EmpCloud/EmpCloud"

HEADERS_BASE = {
    "User-Agent": "EmpCloud-API-Tester/3.0",
    "Origin": "https://test-empcloud.empcloud.com",
    "Accept": "application/json",
    "Content-Type": "application/json",
}

existing_issues = []
bugs_found = []


def api_call(method, url, data=None, token=None, timeout=20):
    headers = dict(HEADERS_BASE)
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        resp = urllib.request.urlopen(req, timeout=timeout, context=ctx)
        raw = resp.read().decode("utf-8", errors="replace")
        try:
            return resp.status, dict(resp.headers), json.loads(raw)
        except json.JSONDecodeError:
            return resp.status, dict(resp.headers), raw
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace") if e.fp else ""
        try:
            return e.code, {}, json.loads(raw)
        except json.JSONDecodeError:
            return e.code, {}, raw
    except Exception as e:
        return 0, {}, str(e)


def login(email, password):
    url = BASE + "/api/v1/auth/login"
    status, _, body = api_call("POST", url, {"email": email, "password": password})
    if status == 200 and isinstance(body, dict):
        data = body.get("data", {})
        if isinstance(data, dict):
            tkns = data.get("tokens", {})
            if isinstance(tkns, dict) and tkns.get("access_token"):
                return tkns["access_token"]
    return None


def fetch_existing_issues():
    global existing_issues
    url = f"https://api.github.com/repos/{GITHUB_REPO}/issues?state=all&per_page=100"
    headers = {"Authorization": f"token {GITHUB_PAT}", "Accept": "application/vnd.github.v3+json", "User-Agent": "test"}
    try:
        for page in range(1, 5):
            req = urllib.request.Request(f"{url}&page={page}", headers=headers)
            resp = urllib.request.urlopen(req, timeout=15, context=ctx)
            issues = json.loads(resp.read().decode())
            if not issues:
                break
            existing_issues.extend(issues)
        print(f"  Fetched {len(existing_issues)} existing issues")
    except Exception as e:
        print(f"  Warning: {e}")


def is_duplicate(title):
    title_lower = title.lower()
    for issue in existing_issues:
        existing = issue.get("title", "").lower()
        # Exact match
        if title_lower == existing:
            return issue["number"]
        # High word overlap
        words_new = set(title_lower.split())
        words_existing = set(existing.split())
        if len(words_new) > 3 and len(words_new & words_existing) / len(words_new) > 0.65:
            return issue["number"]
    return None


def file_bug(title, body_text, labels=None):
    if labels is None:
        labels = ["bug"]
    dup = is_duplicate(title)
    if dup:
        print(f"  [SKIP DUP] #{dup}: {title}")
        return None
    url = f"https://api.github.com/repos/{GITHUB_REPO}/issues"
    headers = {"Authorization": f"token {GITHUB_PAT}", "Accept": "application/vnd.github.v3+json",
               "User-Agent": "test", "Content-Type": "application/json"}
    payload = {"title": title, "body": body_text, "labels": labels}
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=headers, method="POST")
    try:
        resp = urllib.request.urlopen(req, timeout=15, context=ctx)
        result = json.loads(resp.read().decode())
        num = result.get("number")
        print(f"  [BUG FILED] #{num}: {title}")
        existing_issues.append({"number": num, "title": title})
        bugs_found.append({"number": num, "title": title})
        return num
    except Exception as e:
        print(f"  [FILE FAIL] {title}: {e}")
        return None


def count_items(body):
    if isinstance(body, dict):
        data = body.get("data", body)
        if isinstance(data, list):
            return len(data), data
        if isinstance(data, dict):
            for k in ["items", "rows", "records", "applications", "balances"]:
                if isinstance(data.get(k), list):
                    return len(data[k]), data[k]
    return 0, []


def main():
    print("="*80)
    print("PASS 3: ADDITIONAL EDGE CASES")
    print("="*80)

    fetch_existing_issues()

    admin_token = login("ananya@technova.in", "Welcome@123")
    emp_token = login("priya@technova.in", "Welcome@123")
    other_token = login("john@globaltech.com", "Welcome@123")
    super_token = login("admin@empcloud.com", "SuperAdmin@2026")
    print(f"  All logins: {'OK' if all([admin_token, emp_token, other_token, super_token]) else 'SOME FAILED'}")

    # Get employee user ID
    s, _, b = api_call("POST", API + "/auth/login", {"email": "priya@technova.in", "password": "Welcome@123"})
    emp_user_id = b.get("data", {}).get("user", {}).get("id") if isinstance(b, dict) else None
    print(f"  Employee user ID: {emp_user_id}")

    # ── 1. Stored XSS on /policies and /surveys (separate bugs) ──
    print("\n" + "="*80)
    print("TEST 1: File separate XSS bugs for policies and surveys")
    print("="*80)

    xss_payload = '<script>alert("XSS")</script><img src=x onerror=alert(1)>'

    for path, payload, endpoint_name in [
        ("/policies", {"title": xss_payload, "content": xss_payload, "category": "general"}, "policies"),
        ("/surveys", {"title": xss_payload, "description": xss_payload, "status": "draft"}, "surveys"),
        ("/announcements", {"title": xss_payload, "content": xss_payload, "description": xss_payload}, "announcements"),
    ]:
        url = API + path
        status, _, body = api_call("POST", url, payload, token=admin_token)
        if status in (200, 201) and isinstance(body, dict):
            resp_str = json.dumps(body)
            if "<script>" in resp_str or "onerror=" in resp_str:
                created_id = body.get("data", {}).get("id") if isinstance(body.get("data"), dict) else None

                file_bug(
                    f"[API] Stored XSS vulnerability in /{endpoint_name} - unsanitized HTML/JS accepted",
                    f"""## Bug Report

**Endpoint:** `POST {API}{path}`
**Category:** Security / Stored XSS

**Payload:**
```json
{json.dumps(payload, indent=2)}
```

**Response confirms script tags stored verbatim:**
```json
{json.dumps(body, indent=2)[:600]}
```

**Steps to reproduce:**
1. Send POST to `{API}{path}` with `<script>` tags in text fields
2. Response contains unsanitized `<script>` and `onerror=` handlers
3. When data is viewed in the UI, the JavaScript executes

**Expected:** HTML/JS should be stripped or HTML-entity encoded.
**Actual:** Stored as-is, creating a persistent XSS attack vector.

**Impact:** Stored XSS - any user viewing this {endpoint_name[:-1]} in the UI will execute attacker's JavaScript. Can lead to session hijacking, data exfiltration, or admin account takeover.
""",
                    ["bug", "API", "security", "XSS"]
                )

                if created_id:
                    api_call("DELETE", f"{url}/{created_id}", token=admin_token)
        print(f"  {path}: status={status}")

    # ── 2. Employee comp-off visibility (file as distinct bug) ──
    print("\n" + "="*80)
    print("TEST 2: Employee sees all comp-off requests")
    print("="*80)

    s1, _, b1 = api_call("GET", API + "/leave/comp-off", token=admin_token)
    s2, _, b2 = api_call("GET", API + "/leave/comp-off", token=emp_token)
    admin_count, admin_items = count_items(b1)
    emp_count, emp_items = count_items(b2)

    other_comp = []
    for co in emp_items:
        if isinstance(co, dict):
            uid = co.get("user_id") or co.get("employee_id")
            if uid and str(uid) != str(emp_user_id):
                other_comp.append(co)

    if other_comp:
        file_bug(
            "[API] RBAC: Employee can view all comp-off requests in the organization",
            f"""## Bug Report

**Endpoint:** `GET {API}/leave/comp-off`
**Category:** RBAC / Privacy

**Employee (priya@technova.in, ID: {emp_user_id}) sees {emp_count} comp-off entries**
**{len(other_comp)} belong to other employees**

**Other employees' comp-off visible to employee:**
```json
{json.dumps(other_comp[:3], indent=2)[:600]}
```

**Expected:** Employee should only see their own comp-off requests.
**Actual:** All organization comp-off requests returned regardless of user.

**Impact:** Privacy violation - employees can see colleagues' comp-off details.
""",
            ["bug", "API", "RBAC", "privacy"]
        )

    # ── 3. SQL injection stored in surveys ──
    print("\n" + "="*80)
    print("TEST 3: SQL injection payload stored in surveys")
    print("="*80)

    sql_payload = "'; DROP TABLE users; --"
    s, _, b = api_call("POST", API + "/surveys",
        {"title": sql_payload, "description": sql_payload, "status": "draft"},
        token=admin_token)
    if s in (200, 201) and isinstance(b, dict):
        resp_str = json.dumps(b)
        if "DROP TABLE" in resp_str:
            created_id = b.get("data", {}).get("id") if isinstance(b.get("data"), dict) else None
            file_bug(
                "[API] Input Validation: /surveys stores SQL injection payload without sanitization",
                f"""## Bug Report

**Endpoint:** `POST {API}/surveys`
**Category:** Security / Input Validation

**Payload:**
```json
{{"title": "{sql_payload}", "description": "{sql_payload}", "status": "draft"}}
```

**Response stores SQL verbatim:**
```json
{json.dumps(b, indent=2)[:500]}
```

**Expected:** SQL-like syntax should be sanitized or rejected.
**Actual:** Stored as-is. While parameterized queries likely prevent execution, storing raw SQL payloads is a defense-in-depth failure.

**Impact:** If any downstream system processes this data in a non-parameterized way, SQL injection could occur.
""",
                ["bug", "API", "validation", "security"]
            )
            if created_id:
                api_call("DELETE", f"{API}/surveys/{created_id}", token=admin_token)

    # ── 4. Employee can see all helpdesk ticket details ──
    print("\n" + "="*80)
    print("TEST 4: Employee helpdesk ticket data exposure")
    print("="*80)

    s1, _, b1 = api_call("GET", API + "/helpdesk/tickets", token=admin_token)
    s2, _, b2 = api_call("GET", API + "/helpdesk/tickets", token=emp_token)
    admin_count, admin_items = count_items(b1)
    emp_count, emp_items = count_items(b2)

    print(f"  Admin sees {admin_count} tickets")
    print(f"  Employee sees {emp_count} tickets")

    # Check if employee can see tickets created by others
    other_tickets = []
    for t in emp_items:
        if isinstance(t, dict):
            creator = t.get("created_by") or t.get("user_id") or t.get("requester_id")
            if creator and str(creator) != str(emp_user_id):
                other_tickets.append(t)

    if other_tickets:
        print(f"  Employee sees {len(other_tickets)} tickets from other users")

    # ── 5. Employee individual user detail access ──
    print("\n" + "="*80)
    print("TEST 5: Employee can access individual user profiles")
    print("="*80)

    s, _, b = api_call("GET", API + "/users", token=admin_token)
    user_ids = []
    if s == 200 and isinstance(b, dict):
        data = b.get("data", b)
        items = data if isinstance(data, list) else []
        if isinstance(data, dict):
            for k in ["items", "rows", "records", "users"]:
                if isinstance(data.get(k), list):
                    items = data[k]
                    break
        for u in items:
            if isinstance(u, dict):
                uid = u.get("id") or u.get("_id")
                if uid and str(uid) != str(emp_user_id):
                    user_ids.append(uid)

    accessible_profiles = []
    for uid in user_ids[:5]:
        s, _, b = api_call("GET", f"{API}/users/{uid}", token=emp_token)
        if s == 200:
            accessible_profiles.append({"uid": uid, "body": b})
            print(f"  Employee -> /users/{uid}: 200 (accessible)")
        else:
            print(f"  Employee -> /users/{uid}: {s}")

    if accessible_profiles:
        sample = accessible_profiles[0]["body"]
        data = sample.get("data", sample) if isinstance(sample, dict) else sample
        fields = list(data.keys()) if isinstance(data, dict) else "unknown"

        file_bug(
            "[API] RBAC: Employee can access individual user profiles via /users/{id}",
            f"""## Bug Report

**Endpoint:** `GET {API}/users/{{id}}`
**Category:** RBAC / Information Disclosure

**Tested with:** Employee (priya@technova.in)
**Accessible profiles:** {len(accessible_profiles)} out of {len(user_ids[:5])} tested

**Fields exposed in individual user profile:**
`{fields}`

**Sample response for /users/{accessible_profiles[0]['uid']}:**
```json
{json.dumps(sample, indent=2)[:600]}
```

**Expected:** Employee should only access their own profile via /users/{{id}}, or get limited fields for colleagues (name, email, department only).
**Actual:** Full profile data accessible for any user in the organization.

**Impact:** Information disclosure - employees can enumerate and view detailed profiles of all colleagues.
""",
            ["bug", "API", "RBAC"]
        )

    # ── 6. Token does not expire / refresh handling ──
    print("\n" + "="*80)
    print("TEST 6: Token refresh and session management")
    print("="*80)

    # Check refresh token endpoint
    s_login, _, b_login = api_call("POST", API + "/auth/login", {"email": "ananya@technova.in", "password": "Welcome@123"})
    refresh_token = None
    if isinstance(b_login, dict):
        refresh_token = b_login.get("data", {}).get("tokens", {}).get("refresh_token")

    if refresh_token:
        # Try refresh
        for path in ["/auth/refresh", "/auth/token/refresh", "/auth/refresh-token"]:
            s_ref, _, b_ref = api_call("POST", API + path, {"refresh_token": refresh_token})
            print(f"  POST {path}: {s_ref}")
            if s_ref == 200:
                print(f"    Refresh response: {json.dumps(b_ref, indent=2)[:300] if isinstance(b_ref, dict) else str(b_ref)[:300]}")

        # Try using refresh token as access token
        s_abuse, _, b_abuse = api_call("GET", API + "/users", token=refresh_token)
        print(f"  Using refresh_token as access_token on /users: {s_abuse}")
        if s_abuse == 200:
            file_bug(
                "[API] Auth: Refresh token accepted as access token on /users",
                f"""## Bug Report

**Category:** Authentication / Token Management
**Test:** Used refresh_token value as Bearer token on `GET {API}/users`
**Expected:** 401 - refresh tokens should not be usable as access tokens
**Actual:** 200 - data returned

**Impact:** Token confusion vulnerability - refresh tokens (which have longer lifetimes) can be used as access tokens, defeating the purpose of short-lived access tokens.
""",
                ["bug", "API", "security"]
            )

    # ── 7. Logout / Token invalidation ──
    print("\n" + "="*80)
    print("TEST 7: Logout and token invalidation")
    print("="*80)

    # Get a fresh token
    fresh_token = login("ananya@technova.in", "Welcome@123")

    # Verify it works
    s_before, _, _ = api_call("GET", API + "/users", token=fresh_token)
    print(f"  Before logout: /users status={s_before}")

    # Logout
    for path in ["/auth/logout", "/logout", "/auth/signout"]:
        s_logout, _, b_logout = api_call("POST", API + path, token=fresh_token)
        print(f"  POST {path}: {s_logout}")
        if s_logout == 200:
            break

    # Try using the token again
    time.sleep(1)
    s_after, _, _ = api_call("GET", API + "/users", token=fresh_token)
    print(f"  After logout: /users status={s_after}")

    if s_after == 200:
        file_bug(
            "[API] Auth: Token remains valid after logout - session not invalidated",
            f"""## Bug Report

**Category:** Authentication / Session Management
**Endpoint:** `POST {API}/auth/logout` then `GET {API}/users`

**Steps:**
1. Login and get access token
2. Verify token works (GET /users -> {s_before})
3. Call logout endpoint
4. Use same token again (GET /users -> {s_after})

**Expected:** Token should be invalidated after logout, subsequent requests should get 401.
**Actual:** Token still works after logout.

**Impact:** Session fixation risk - logged-out tokens remain valid, meaning stolen tokens cannot be revoked.
""",
            ["bug", "API", "security"]
        )

    # ── 8. Password brute force / account lockout ──
    print("\n" + "="*80)
    print("TEST 8: Account lockout after failed logins")
    print("="*80)

    # Try 10 wrong passwords (skip rate limit check per instructions)
    for i in range(10):
        s, _, b = api_call("POST", API + "/auth/login", {"email": "ananya@technova.in", "password": f"WrongPass{i}"})
        if i == 9:
            print(f"  After 10 wrong passwords: status={s}")

    # Now try correct password
    s_correct, _, b_correct = api_call("POST", API + "/auth/login", {"email": "ananya@technova.in", "password": "Welcome@123"})
    print(f"  Correct password after 10 failures: status={s_correct}")

    if s_correct == 200:
        print("  Account not locked after 10 failed attempts - potential brute force vulnerability")
        # Note: we skip rate limiting bugs per instructions

    # ── 9. Employee can modify helpdesk tickets of others ──
    print("\n" + "="*80)
    print("TEST 9: Employee modifying other users' helpdesk tickets")
    print("="*80)

    s, _, b = api_call("GET", API + "/helpdesk/tickets", token=admin_token)
    _, ticket_items = count_items(b)

    for t in ticket_items[:3]:
        if not isinstance(t, dict):
            continue
        tid = t.get("id") or t.get("_id")
        creator = t.get("created_by") or t.get("user_id")
        if tid and creator and str(creator) != str(emp_user_id):
            # Try to update someone else's ticket
            s_update, _, b_update = api_call("PUT", f"{API}/helpdesk/tickets/{tid}",
                {"subject": "MODIFIED BY EMPLOYEE", "priority": "urgent"}, token=emp_token)
            print(f"  Employee PUT /helpdesk/tickets/{tid} (owned by {creator}): {s_update}")
            if s_update == 200:
                file_bug(
                    "[API] RBAC: Employee can modify other users' helpdesk tickets",
                    f"""## Bug Report

**Endpoint:** `PUT {API}/helpdesk/tickets/{tid}`
**Category:** RBAC / Authorization

**Ticket ID:** {tid} (created by user {creator})
**Modified by:** Employee (priya@technova.in, ID: {emp_user_id})

**Expected:** 403 - employees should only modify their own tickets.
**Actual:** 200 - ticket modified successfully.

**Impact:** Authorization bypass - employees can modify or escalate other users' support tickets.
""",
                    ["bug", "API", "RBAC"]
                )
            break

    # ── 10. Super admin token accessing org data ──
    print("\n" + "="*80)
    print("TEST 10: Super admin cross-org access")
    print("="*80)

    # Super admin should not auto-see org-specific data without context
    s, _, b = api_call("GET", API + "/users", token=super_token)
    su_count, su_items = count_items(b)
    print(f"  Super admin -> /users: status={s}, count={su_count}")

    if su_count > 0:
        # Check if super admin sees users from multiple orgs
        org_ids = set()
        for u in su_items:
            if isinstance(u, dict) and u.get("organization_id"):
                org_ids.add(u["organization_id"])
        print(f"  Organization IDs in super admin user list: {org_ids}")
        if len(org_ids) > 1:
            print("  Super admin sees users from multiple orgs in /users (expected for super admin)")

    # ── 11. Employee accessing individual assets/announcements ──
    print("\n" + "="*80)
    print("TEST 11: Employee accessing individual resource details")
    print("="*80)

    for path in ["/announcements", "/policies", "/surveys", "/events"]:
        s, _, b = api_call("GET", API + path, token=admin_token)
        _, items = count_items(b)
        for item in items[:2]:
            if not isinstance(item, dict):
                continue
            rid = item.get("id") or item.get("_id")
            if not rid:
                continue
            s_emp, _, b_emp = api_call("GET", f"{API}{path}/{rid}", token=emp_token)
            print(f"  Employee -> {path}/{rid}: {s_emp}")

    # ── 12. Check if employee can create helpdesk tickets as other users ──
    print("\n" + "="*80)
    print("TEST 12: Employee creating tickets impersonating other users")
    print("="*80)

    # Try creating a ticket with a different user_id
    for uid in user_ids[:2]:
        s, _, b = api_call("POST", API + "/helpdesk/tickets",
            {"subject": "Impersonation Test", "description": "Testing", "priority": "low",
             "user_id": uid, "created_by": uid},
            token=emp_token)
        print(f"  Employee POST /helpdesk/tickets (user_id={uid}): {s}")
        if s in (200, 201) and isinstance(b, dict):
            data = b.get("data", {})
            actual_creator = data.get("created_by") or data.get("user_id")
            if actual_creator and str(actual_creator) == str(uid) and str(uid) != str(emp_user_id):
                print(f"  ** BUG: Ticket created as user {uid} instead of {emp_user_id}!")
                file_bug(
                    "[API] RBAC: Employee can create helpdesk tickets impersonating other users",
                    f"""## Bug Report

**Endpoint:** `POST {API}/helpdesk/tickets`
**Category:** RBAC / Impersonation

**Employee (ID: {emp_user_id}) created ticket with user_id={uid}**
**Ticket created_by field shows:** {actual_creator}

**Expected:** The created_by/user_id should always be set to the authenticated user, ignoring any user_id in the payload.
**Actual:** Server accepts the user_id from the request body.

**Impact:** Identity spoofing - employees can create tickets that appear to come from other users.
""",
                    ["bug", "API", "security", "RBAC"]
                )
            # Cleanup
            created_id = data.get("id") if isinstance(data, dict) else None
            if created_id:
                api_call("DELETE", f"{API}/helpdesk/tickets/{created_id}", token=admin_token)

    # ── 13. Employee updating own role via user update ──
    print("\n" + "="*80)
    print("TEST 13: Employee self-privilege escalation via /users/{id}")
    print("="*80)

    if emp_user_id:
        for payload in [
            {"role": "org_admin"},
            {"role": "admin"},
            {"status": 1, "role": "org_admin", "is_admin": True},
        ]:
            s, _, b = api_call("PUT", f"{API}/users/{emp_user_id}", payload, token=emp_token)
            print(f"  Employee PUT /users/{emp_user_id} with {payload}: {s}")
            if s == 200 and isinstance(b, dict):
                data = b.get("data", b)
                if isinstance(data, dict) and data.get("role") in ["org_admin", "admin", "super_admin"]:
                    file_bug(
                        "[API] Critical: Employee can escalate own role to admin via PUT /users/{id}",
                        f"""## Bug Report

**Endpoint:** `PUT {API}/users/{emp_user_id}`
**Category:** Security / Privilege Escalation

**Employee (priya@technova.in) sent:** `{json.dumps(payload)}`
**Response shows role:** {data.get('role')}

**Expected:** 403 or role field ignored for self-update.
**Actual:** Role escalated to admin.

**Impact:** CRITICAL privilege escalation - any employee can make themselves an admin.
""",
                        ["bug", "API", "security", "critical"]
                    )

    # ── 14. Test leave application manipulation ──
    print("\n" + "="*80)
    print("TEST 14: Leave application manipulation")
    print("="*80)

    s, _, b = api_call("GET", API + "/leave/applications", token=emp_token)
    _, leave_items = count_items(b)

    for la in leave_items[:3]:
        if not isinstance(la, dict):
            continue
        la_id = la.get("id") or la.get("_id")
        la_owner = la.get("user_id") or la.get("employee_id")
        la_status = la.get("status")

        if la_id and la_owner and str(la_owner) != str(emp_user_id):
            # Try approving someone else's leave
            s_approve, _, b_approve = api_call("PUT", f"{API}/leave/applications/{la_id}",
                {"status": "approved"}, token=emp_token)
            print(f"  Employee approve leave #{la_id} (owner={la_owner}): {s_approve}")
            if s_approve == 200:
                file_bug(
                    "[API] RBAC: Employee can approve/modify other employees' leave applications",
                    f"""## Bug Report

**Endpoint:** `PUT {API}/leave/applications/{la_id}`
**Category:** RBAC / Authorization

**Leave application ID:** {la_id} (belongs to user {la_owner})
**Modified by:** Employee (priya@technova.in, ID: {emp_user_id})
**Action:** Changed status to "approved"

**Expected:** 403 - only managers/admins should approve leave.
**Actual:** 200 - leave application modified.

**Impact:** Authorization bypass - any employee can approve leave requests.
""",
                    ["bug", "API", "RBAC"]
                )
            break

    # ── 15. Employee accessing leave policies (should be read-only) ──
    print("\n" + "="*80)
    print("TEST 15: Employee modifying leave policies")
    print("="*80)

    s, _, b = api_call("GET", API + "/leave/policies", token=admin_token)
    _, policy_items = count_items(b)

    for p in policy_items[:2]:
        if not isinstance(p, dict):
            continue
        pid = p.get("id") or p.get("_id")
        if pid:
            s_update, _, _ = api_call("PUT", f"{API}/leave/policies/{pid}",
                {"name": "HACKED BY EMPLOYEE", "days": 999}, token=emp_token)
            print(f"  Employee PUT /leave/policies/{pid}: {s_update}")
            if s_update == 200:
                file_bug(
                    "[API] RBAC: Employee can modify leave policies",
                    f"""## Bug Report

**Endpoint:** `PUT {API}/leave/policies/{pid}`
**Category:** RBAC / Authorization

**Expected:** 403 - only admins should modify leave policies.
**Actual:** 200 - policy modified by employee.

**Impact:** Employees can modify organization leave policies.
""",
                    ["bug", "API", "RBAC"]
                )
            break

    # Summary
    print("\n" + "="*80)
    print("PASS 3 SUMMARY")
    print("="*80)
    print(f"Bugs filed this pass: {len(bugs_found)}")
    for bug in bugs_found:
        print(f"  #{bug['number']}: {bug['title']}")


if __name__ == "__main__":
    main()
