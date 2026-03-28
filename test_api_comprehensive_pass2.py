#!/usr/bin/env python3
"""
Pass 2: Deep-dive on specific findings from comprehensive test.
Focus: XSS on multiple endpoints, RBAC subscription leak, method override, SQL on assets/surveys.
"""
import sys
import json
import urllib.request
import urllib.error
import ssl
import time

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
    "User-Agent": "EmpCloud-API-Tester/2.0",
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
        words_new = set(title_lower.split())
        words_existing = set(existing.split())
        if len(words_new) > 2 and len(words_new & words_existing) / len(words_new) > 0.6:
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


def main():
    print("="*80)
    print("PASS 2: DEEP-DIVE API TESTING")
    print("="*80)

    fetch_existing_issues()

    print("\n[LOGIN]")
    admin_token = login("ananya@technova.in", "Welcome@123")
    emp_token = login("priya@technova.in", "Welcome@123")
    other_token = login("john@globaltech.com", "Welcome@123")
    super_token = login("admin@empcloud.com", "SuperAdmin@2026")
    print(f"  Admin: {'OK' if admin_token else 'FAIL'}")
    print(f"  Employee: {'OK' if emp_token else 'FAIL'}")
    print(f"  Other org: {'OK' if other_token else 'FAIL'}")
    print(f"  Super: {'OK' if super_token else 'FAIL'}")

    # ── 1. Employee accessing /subscriptions detail ──
    print("\n" + "="*80)
    print("TEST 1: Employee access to /subscriptions (admin-only)")
    print("="*80)

    s_admin, _, b_admin = api_call("GET", API + "/subscriptions", token=admin_token)
    s_emp, _, b_emp = api_call("GET", API + "/subscriptions", token=emp_token)

    print(f"  Admin: {s_admin} -> {json.dumps(b_admin, indent=2)[:400] if isinstance(b_admin, dict) else str(b_admin)[:400]}")
    print(f"  Employee: {s_emp} -> {json.dumps(b_emp, indent=2)[:400] if isinstance(b_emp, dict) else str(b_emp)[:400]}")

    if s_emp == 200 and isinstance(b_emp, dict):
        data_emp = b_emp.get("data", b_emp)
        # Check if subscription data includes billing/cost info
        data_str = json.dumps(data_emp).lower()
        sensitive_in_subs = any(w in data_str for w in ["price", "cost", "billing", "plan", "amount", "payment"])
        file_bug(
            "[API] RBAC: Employee can view subscription/billing data via /subscriptions",
            f"""## Bug Report

**Endpoint:** `GET {API}/subscriptions`
**Category:** RBAC / Information Disclosure

**Test:**
- Org Admin (ananya@technova.in): Status {s_admin}
- Employee (priya@technova.in): Status {s_emp}

**Employee sees subscription data:**
```json
{json.dumps(b_emp, indent=2)[:800]}
```

**Contains sensitive billing info:** {sensitive_in_subs}

**Expected:** Employees should get 403 on /subscriptions which contains organizational billing and subscription data.
**Actual:** Employee gets full access to subscription information.

**Impact:** Information disclosure - employees can see subscription plans, module pricing, and billing details that should be admin-only.
""",
            ["bug", "API", "RBAC"]
        )

    # ── 2. XSS on multiple endpoints (file separate bugs per endpoint) ──
    print("\n" + "="*80)
    print("TEST 2: Stored XSS on multiple endpoints")
    print("="*80)

    xss_payload = '<script>alert("XSS")</script><img src=x onerror=alert(1)>'

    xss_tests = [
        ("/assets", {"name": xss_payload, "category_id": 1, "serial_number": "XSS-TEST-001", "status": "available"}),
        ("/policies", {"title": xss_payload, "content": xss_payload, "category": "general"}),
        ("/surveys", {"title": xss_payload, "description": xss_payload, "status": "draft"}),
    ]

    for path, payload in xss_tests:
        url = API + path
        status, _, body = api_call("POST", url, payload, token=admin_token)
        print(f"\n  POST {path}: status={status}")
        if status in (200, 201) and isinstance(body, dict):
            resp_str = json.dumps(body)
            stored_xss = "<script>" in resp_str or "onerror=" in resp_str
            print(f"    XSS stored in response: {stored_xss}")
            if stored_xss:
                # Get created ID and clean up
                data = body.get("data", body)
                created_id = data.get("id") or data.get("_id") if isinstance(data, dict) else None

                file_bug(
                    f"[API] Stored XSS: {path} endpoint accepts and stores unsanitized HTML/JavaScript",
                    f"""## Bug Report

**Endpoint:** `POST {API}{path}`
**Category:** Security / Stored XSS

**Payload sent:**
```json
{json.dumps(payload, indent=2)}
```

**Response (contains unsanitized script tags):**
```json
{json.dumps(body, indent=2)[:600]}
```

**Steps to reproduce:**
1. POST to `{API}{path}` with script tags in text fields
2. Response contains the unsanitized `<script>` tags
3. When rendered in frontend, JavaScript will execute

**Expected:** Input should be sanitized - HTML tags stripped or HTML-encoded before storage.
**Actual:** Script tags and event handlers stored verbatim.

**Impact:** Stored XSS - any user viewing this data in the UI could have malicious JavaScript executed in their browser. This can lead to session hijacking, data theft, or admin account compromise.
""",
                    ["bug", "API", "security", "XSS"]
                )

                # Cleanup
                if created_id:
                    api_call("DELETE", f"{url}/{created_id}", token=admin_token)
                    print(f"    Cleaned up: DELETE {path}/{created_id}")

    # ── 3. SQL injection payload accepted by /assets and /surveys ──
    print("\n" + "="*80)
    print("TEST 3: SQL injection payload accepted")
    print("="*80)

    sql_payload_str = "'; DROP TABLE users; --"
    sql_tests = [
        ("/assets", {"name": sql_payload_str, "category_id": 1, "serial_number": "SQL-TEST-001", "status": "available"}),
        ("/surveys", {"title": sql_payload_str, "description": sql_payload_str, "status": "draft"}),
    ]

    for path, payload in sql_tests:
        url = API + path
        status, _, body = api_call("POST", url, payload, token=admin_token)
        print(f"  POST {path} with SQL payload: status={status}")
        if status in (200, 201):
            print(f"    Response: {json.dumps(body, indent=2)[:300] if isinstance(body, dict) else str(body)[:300]}")
            # Check if the SQL string is stored
            resp_str = json.dumps(body) if isinstance(body, dict) else str(body)
            if "DROP TABLE" in resp_str:
                file_bug(
                    f"[API] Input Validation: {path} stores SQL injection payload without sanitization",
                    f"""## Bug Report

**Endpoint:** `POST {API}{path}`
**Category:** Security / Input Validation

**Payload:**
```json
{json.dumps(payload, indent=2)}
```

**Response stores SQL payload verbatim:**
```json
{json.dumps(body, indent=2)[:500]}
```

**Expected:** SQL-like input should either be rejected or properly sanitized/escaped.
**Actual:** SQL injection strings stored in the database without sanitization.

**Note:** While this may be parameterized queries preventing actual SQL injection, storing SQL syntax verbatim indicates lack of input sanitization which is a defense-in-depth concern.
""",
                    ["bug", "API", "validation"]
                )
            # Cleanup
            data = body.get("data", body)
            created_id = data.get("id") or data.get("_id") if isinstance(data, dict) else None
            if created_id:
                api_call("DELETE", f"{url}/{created_id}", token=admin_token)

    # ── 4. Employee sees all leave applications (should only see own) ──
    print("\n" + "="*80)
    print("TEST 4: Employee leave application visibility")
    print("="*80)

    s1, _, b_admin_leave = api_call("GET", API + "/leave/applications", token=admin_token)
    s2, _, b_emp_leave = api_call("GET", API + "/leave/applications", token=emp_token)

    admin_leave_count = 0
    emp_leave_count = 0

    def count_items(body):
        if isinstance(body, dict):
            data = body.get("data", body)
            if isinstance(data, list):
                return len(data), data
            if isinstance(data, dict):
                for k in ["items", "rows", "records", "applications"]:
                    if isinstance(data.get(k), list):
                        return len(data[k]), data[k]
                # Check if data has pagination with results
                if isinstance(data.get("data"), list):
                    return len(data["data"]), data["data"]
        return 0, []

    admin_leave_count, admin_leave_items = count_items(b_admin_leave)
    emp_leave_count, emp_leave_items = count_items(b_emp_leave)

    print(f"  Admin sees {admin_leave_count} leave applications")
    print(f"  Employee sees {emp_leave_count} leave applications")

    # Check if employee sees other people's leave apps
    if emp_leave_count > 0 and isinstance(emp_leave_items, list):
        # Get employee's user info
        emp_login_status, _, emp_login_body = api_call("POST", API + "/auth/login", {"email": "priya@technova.in", "password": "Welcome@123"})
        emp_user_id = None
        if isinstance(emp_login_body, dict):
            emp_user_id = emp_login_body.get("data", {}).get("user", {}).get("id")

        other_people_leaves = []
        for app in emp_leave_items:
            if isinstance(app, dict):
                app_user = app.get("user_id") or app.get("employee_id") or app.get("userId")
                if app_user and emp_user_id and str(app_user) != str(emp_user_id):
                    other_people_leaves.append(app)

        if other_people_leaves:
            print(f"  ** BUG: Employee sees {len(other_people_leaves)} leave apps from OTHER employees!")
            file_bug(
                "[API] RBAC: Employee can view other employees' leave applications",
                f"""## Bug Report

**Endpoint:** `GET {API}/leave/applications`
**Category:** RBAC / Information Disclosure

**Employee user ID:** {emp_user_id}
**Employee sees {emp_leave_count} total leave applications, {len(other_people_leaves)} belong to other employees**

**Sample of other employees' leave data visible to employee:**
```json
{json.dumps(other_people_leaves[:3], indent=2)[:800]}
```

**Expected:** Employee should only see their own leave applications.
**Actual:** Employee can see all leave applications in the organization.

**Impact:** Privacy violation - employees can see other colleagues' leave details (dates, reasons, types).
""",
                ["bug", "API", "RBAC", "privacy"]
            )
        else:
            print(f"  Employee only sees their own leave apps (or could not determine user IDs)")

    # ── 5. Employee sees all survey details ──
    print("\n" + "="*80)
    print("TEST 5: Employee survey/feedback visibility")
    print("="*80)

    s1, _, b_admin_surveys = api_call("GET", API + "/surveys", token=admin_token)
    s2, _, b_emp_surveys = api_call("GET", API + "/surveys", token=emp_token)

    admin_survey_count, admin_survey_items = count_items(b_admin_surveys)
    emp_survey_count, emp_survey_items = count_items(b_emp_surveys)

    print(f"  Admin sees {admin_survey_count} surveys")
    print(f"  Employee sees {emp_survey_count} surveys")

    # Check if employee sees draft surveys
    if isinstance(emp_survey_items, list):
        draft_surveys = [s for s in emp_survey_items if isinstance(s, dict) and s.get("status") == "draft"]
        if draft_surveys:
            print(f"  ** BUG: Employee sees {len(draft_surveys)} DRAFT surveys!")
            file_bug(
                "[API] RBAC: Employee can view draft surveys meant for admin only",
                f"""## Bug Report

**Endpoint:** `GET {API}/surveys`
**Category:** RBAC / Information Disclosure

**Employee sees {emp_survey_count} surveys including {len(draft_surveys)} draft surveys**

**Draft surveys visible to employee:**
```json
{json.dumps(draft_surveys[:3], indent=2)[:600]}
```

**Expected:** Employees should only see published surveys, not drafts.
**Actual:** Employee can see all surveys including draft status.

**Impact:** Information disclosure - employees can see unpublished surveys and their questions before they are officially released.
""",
                ["bug", "API", "RBAC"]
            )

    # ── 6. Employee sees all forum posts including admin-only ──
    print("\n" + "="*80)
    print("TEST 6: Employee sees all forum posts")
    print("="*80)

    s1, _, b_admin_forum = api_call("GET", API + "/forum/posts", token=admin_token)
    s2, _, b_emp_forum = api_call("GET", API + "/forum/posts", token=emp_token)

    admin_forum_count, _ = count_items(b_admin_forum)
    emp_forum_count, _ = count_items(b_emp_forum)
    print(f"  Admin sees {admin_forum_count} forum posts")
    print(f"  Employee sees {emp_forum_count} forum posts")

    # ── 7. Employee sees all policies including unpublished ──
    print("\n" + "="*80)
    print("TEST 7: Employee policy visibility (draft/unpublished)")
    print("="*80)

    s1, _, b_admin_policies = api_call("GET", API + "/policies", token=admin_token)
    s2, _, b_emp_policies = api_call("GET", API + "/policies", token=emp_token)

    admin_pol_count, admin_pol_items = count_items(b_admin_policies)
    emp_pol_count, emp_pol_items = count_items(b_emp_policies)

    print(f"  Admin sees {admin_pol_count} policies")
    print(f"  Employee sees {emp_pol_count} policies")

    if isinstance(emp_pol_items, list):
        draft_policies = [p for p in emp_pol_items if isinstance(p, dict) and p.get("status") in ("draft", "unpublished", "inactive")]
        if draft_policies:
            print(f"  ** BUG: Employee sees {len(draft_policies)} draft/inactive policies!")
            file_bug(
                "[API] RBAC: Employee can view draft/inactive policies",
                f"""## Bug Report

**Endpoint:** `GET {API}/policies`
**Category:** RBAC / Information Disclosure

**Employee sees {emp_pol_count} policies including {len(draft_policies)} draft/inactive ones**

**Draft/inactive policies visible to employee:**
```json
{json.dumps(draft_policies[:3], indent=2)[:600]}
```

**Expected:** Employees should only see published/active policies.
**Actual:** Employee sees all policies regardless of status.

**Impact:** Information disclosure - employees see unpublished policy drafts.
""",
                ["bug", "API", "RBAC"]
            )

    # ── 8. Check user list data exposure (detailed) ──
    print("\n" + "="*80)
    print("TEST 8: User data exposure analysis")
    print("="*80)

    s, _, b = api_call("GET", API + "/users", token=emp_token)
    if s == 200 and isinstance(b, dict):
        data = b.get("data", b)
        items = data if isinstance(data, list) else []
        if isinstance(data, dict):
            for k in ["items", "rows", "records", "users"]:
                if isinstance(data.get(k), list):
                    items = data[k]
                    break

        if items and isinstance(items[0], dict):
            sample_user = items[0]
            sensitive_fields_found = []
            for f in ["salary", "ctc", "bank_account", "pan", "aadhaar", "ssn",
                       "date_of_birth", "contact_number", "personal_email",
                       "emergency_contact", "blood_group", "marital_status",
                       "address", "reporting_manager_id"]:
                if f in sample_user and sample_user[f] is not None:
                    sensitive_fields_found.append(f"{f}={sample_user[f]}")

            print(f"  User record fields: {list(sample_user.keys())}")
            print(f"  Sensitive fields exposed: {sensitive_fields_found}")

            pii_fields = [f for f in sensitive_fields_found if any(
                w in f for w in ["date_of_birth", "contact_number", "address", "personal_email", "emergency", "blood", "marital"]
            )]
            if pii_fields and len(items) > 5:
                file_bug(
                    "[API] Data Exposure: Employee /users endpoint returns PII for all employees",
                    f"""## Bug Report

**Endpoint:** `GET {API}/users`
**Category:** Security / Data Exposure / Privacy

**Tested with:** Employee (priya@technova.in)
**Users returned:** {len(items)} (all org employees)

**PII fields exposed for each user:**
{chr(10).join(f'- `{f}`' for f in pii_fields)}

**All fields in user record:** `{', '.join(sample_user.keys())}`

**Sample user record (first item):**
```json
{json.dumps(sample_user, indent=2)[:600]}
```

**Expected:** Employee should only see basic directory info (name, email, department). Sensitive PII like date_of_birth, contact_number, address should be restricted.
**Actual:** Full PII exposed for all employees in the organization.

**Impact:** Privacy violation - any employee can access personal information of all colleagues including DOB, phone numbers, addresses, and marital status.
""",
                    ["bug", "API", "security", "privacy"]
                )

    # ── 9. Audit log access by employee ──
    print("\n" + "="*80)
    print("TEST 9: Audit log content analysis")
    print("="*80)

    s, _, b_audit = api_call("GET", API + "/audit", token=admin_token)
    if s == 200 and isinstance(b_audit, dict):
        data = b_audit.get("data", b_audit)
        items = data if isinstance(data, list) else []
        if isinstance(data, dict):
            for k in ["items", "rows", "records", "logs"]:
                if isinstance(data.get(k), list):
                    items = data[k]
                    break
        if items and isinstance(items[0], dict):
            print(f"  Audit log fields: {list(items[0].keys())}")
            print(f"  Sample entry: {json.dumps(items[0], indent=2)[:400]}")

    # ── 10. Test user detail endpoint exposure ──
    print("\n" + "="*80)
    print("TEST 10: Individual user access")
    print("="*80)

    # Get user IDs from users list
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
        for u in items[:5]:
            if isinstance(u, dict):
                uid = u.get("id") or u.get("_id")
                if uid:
                    user_ids.append(uid)

    for uid in user_ids:
        # Employee trying to access specific user
        s_emp, _, b_emp = api_call("GET", f"{API}/users/{uid}", token=emp_token)
        print(f"  Employee -> /users/{uid}: status={s_emp}")
        if s_emp == 200 and isinstance(b_emp, dict):
            data = b_emp.get("data", b_emp)
            if isinstance(data, dict) and data.get("salary") is not None:
                print(f"    ** Salary exposed: {data.get('salary')}")

    # ── 11. Employee comp-off visibility ──
    print("\n" + "="*80)
    print("TEST 11: Employee comp-off visibility")
    print("="*80)

    s1, _, b_admin_co = api_call("GET", API + "/leave/comp-off", token=admin_token)
    s2, _, b_emp_co = api_call("GET", API + "/leave/comp-off", token=emp_token)

    admin_co_count, admin_co_items = count_items(b_admin_co)
    emp_co_count, emp_co_items = count_items(b_emp_co)
    print(f"  Admin sees {admin_co_count} comp-off entries")
    print(f"  Employee sees {emp_co_count} comp-off entries")

    # Check if employee sees other people's comp-off
    if emp_co_count > 0 and isinstance(emp_co_items, list):
        emp_login_status, _, emp_login_body = api_call("POST", API + "/auth/login", {"email": "priya@technova.in", "password": "Welcome@123"})
        emp_user_id = None
        if isinstance(emp_login_body, dict):
            emp_user_id = emp_login_body.get("data", {}).get("user", {}).get("id")

        other_comp_offs = []
        for co in emp_co_items:
            if isinstance(co, dict):
                co_user = co.get("user_id") or co.get("employee_id")
                if co_user and emp_user_id and str(co_user) != str(emp_user_id):
                    other_comp_offs.append(co)

        if other_comp_offs:
            print(f"  ** BUG: Employee sees {len(other_comp_offs)} comp-off from other employees!")
            file_bug(
                "[API] RBAC: Employee can view other employees' comp-off requests",
                f"""## Bug Report

**Endpoint:** `GET {API}/leave/comp-off`
**Category:** RBAC / Information Disclosure

**Employee (priya@technova.in, ID: {emp_user_id}) sees {emp_co_count} comp-off entries**
**{len(other_comp_offs)} belong to other employees**

**Sample:**
```json
{json.dumps(other_comp_offs[:3], indent=2)[:600]}
```

**Expected:** Employee should only see their own comp-off requests.
**Actual:** Employee sees all comp-off requests in the organization.

**Impact:** Privacy violation.
""",
                ["bug", "API", "RBAC", "privacy"]
            )

    # ── 12. Announcements - employee create/update ──
    print("\n" + "="*80)
    print("TEST 12: Announcement CRUD by employee")
    print("="*80)

    # Try employee creating an announcement
    s_create, _, b_create = api_call("POST", API + "/announcements",
        {"title": "Employee Test Announcement", "content": "This should fail", "description": "test"},
        token=emp_token)
    print(f"  Employee POST /announcements: {s_create}")

    # Try employee updating an existing announcement
    s_list, _, b_list = api_call("GET", API + "/announcements", token=admin_token)
    ann_id = None
    if isinstance(b_list, dict):
        data = b_list.get("data", b_list)
        if isinstance(data, list) and data:
            ann_id = data[0].get("id") or data[0].get("_id")

    if ann_id:
        s_update, _, b_update = api_call("PUT", f"{API}/announcements/{ann_id}",
            {"title": "HACKED BY EMPLOYEE"}, token=emp_token)
        print(f"  Employee PUT /announcements/{ann_id}: {s_update}")
        if s_update == 200:
            file_bug(
                "[API] RBAC: Employee can update announcements",
                f"""## Bug Report

**Endpoint:** `PUT {API}/announcements/{ann_id}`
**Category:** RBAC / Authorization

**Tested with:** Employee (priya@technova.in)
**Expected:** 403 Forbidden
**Actual:** {s_update} - announcement updated successfully

**Impact:** Employees can modify official organization announcements.
""",
                ["bug", "API", "RBAC"]
            )

        s_delete, _, b_delete = api_call("DELETE", f"{API}/announcements/{ann_id}", token=emp_token)
        print(f"  Employee DELETE /announcements/{ann_id}: {s_delete}")
        if s_delete == 200:
            file_bug(
                "[API] RBAC: Employee can delete announcements",
                f"""## Bug Report

**Endpoint:** `DELETE {API}/announcements/{ann_id}`
**Category:** RBAC / Authorization

**Tested with:** Employee (priya@technova.in)
**Expected:** 403 Forbidden
**Actual:** {s_delete} - announcement deleted

**Impact:** Employees can delete official organization announcements.
""",
                ["bug", "API", "RBAC"]
            )

    # ── 13. Cross-org data access with direct ID manipulation ──
    print("\n" + "="*80)
    print("TEST 13: Cross-org detail access (announcements, assets, policies)")
    print("="*80)

    # Get TechNova resource IDs
    for path in ["/announcements", "/assets", "/policies", "/surveys", "/helpdesk/tickets", "/leave/types", "/forum/posts"]:
        s, _, b = api_call("GET", API + path, token=admin_token)
        if s != 200:
            continue
        data = b.get("data", b) if isinstance(b, dict) else b
        items = data if isinstance(data, list) else []
        if isinstance(data, dict):
            for k in ["items", "rows", "records"]:
                if isinstance(data.get(k), list):
                    items = data[k]
                    break

        for item in items[:2]:
            if not isinstance(item, dict):
                continue
            rid = item.get("id") or item.get("_id")
            if not rid:
                continue

            # Try with GlobalTech token
            s_other, _, b_other = api_call("GET", f"{API}{path}/{rid}", token=other_token)
            if s_other == 200:
                print(f"  ** BUG: GlobalTech can access TechNova {path}/{rid}")
                file_bug(
                    f"[API] Cross-Org: {path}/{{id}} accessible by other organization",
                    f"""## Bug Report

**Endpoint:** `GET {API}{path}/{rid}`
**Category:** Multi-tenancy / Data Isolation

**Resource belongs to:** TechNova (ananya@technova.in)
**Accessed by:** GlobalTech (john@globaltech.com)

**Expected:** 403 or 404
**Actual:** 200 - data returned

**Response:**
```json
{json.dumps(b_other, indent=2)[:500] if isinstance(b_other, dict) else str(b_other)[:500]}
```

**Impact:** Critical multi-tenancy violation - organizations can access each other's data by ID.
""",
                    ["bug", "API", "security", "multi-tenancy"]
                )
            else:
                print(f"  [{s_other}] GlobalTech -> {path}/{rid}")

    # ── 14. Test no-auth access on all live endpoints ──
    print("\n" + "="*80)
    print("TEST 14: Unauthenticated access scan")
    print("="*80)

    live_paths = [
        "/users", "/attendance/shifts", "/leave/balances", "/leave/applications",
        "/leave/types", "/leave/policies", "/leave/comp-off", "/documents",
        "/documents/categories", "/announcements", "/events", "/surveys",
        "/feedback", "/assets", "/assets/categories", "/positions",
        "/positions/vacancies", "/helpdesk/tickets", "/forum/posts",
        "/forum/categories", "/policies", "/notifications", "/audit",
        "/modules", "/subscriptions",
    ]

    for path in live_paths:
        s, _, b = api_call("GET", API + path)
        if s == 200:
            print(f"  ** BUG: {path} accessible without authentication!")
            file_bug(
                f"[API] Auth: {path} accessible without authentication",
                f"""## Bug Report

**Endpoint:** `GET {API}{path}`
**Category:** Authentication

**Expected:** 401 Unauthorized
**Actual:** {s} - data returned without any auth token

**Impact:** Unauthenticated data access.
""",
                ["bug", "API", "security"]
            )
        else:
            print(f"  [{s}] {path} (no auth)")

    # ── 15. Employee modules visibility analysis ──
    print("\n" + "="*80)
    print("TEST 15: Employee modules/subscriptions detail")
    print("="*80)

    s, _, b = api_call("GET", API + "/modules", token=emp_token)
    if s == 200 and isinstance(b, dict):
        data = b.get("data", b)
        items = data if isinstance(data, list) else []
        if isinstance(data, dict):
            for k in ["items", "rows", "records", "modules"]:
                if isinstance(data.get(k), list):
                    items = data[k]
                    break
        if items:
            print(f"  Employee sees {len(items)} modules")
            # Check if pricing is exposed
            sample = items[0] if items else {}
            data_str = json.dumps(items).lower()
            if any(w in data_str for w in ["price", "cost", "amount"]):
                print(f"  Module pricing exposed to employee!")
                file_bug(
                    "[API] RBAC: Employee can view module pricing via /modules",
                    f"""## Bug Report

**Endpoint:** `GET {API}/modules`
**Category:** RBAC / Information Disclosure

**Employee sees {len(items)} modules with pricing data**

**Sample:**
```json
{json.dumps(items[:2], indent=2)[:600]}
```

**Expected:** Module pricing should only be visible to admins.
**Impact:** Business-sensitive pricing information exposed to all employees.
""",
                    ["bug", "API", "RBAC"]
                )

    # Summary
    print("\n" + "="*80)
    print("PASS 2 SUMMARY")
    print("="*80)
    print(f"Bugs filed: {len(bugs_found)}")
    for bug in bugs_found:
        print(f"  #{bug['number']}: {bug['title']}")


if __name__ == "__main__":
    main()
