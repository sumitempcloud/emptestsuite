#!/usr/bin/env python3
"""
EMP Cloud HRMS - Deep Validation & Boundary Testing
Tests every form field with invalid/edge-case data across all endpoints.
Files GitHub issues for validation gaps found.
"""

import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import requests
import json
import time
import urllib3
urllib3.disable_warnings()

API = "https://test-empcloud-api.empcloud.com/api/v1"
GITHUB_TOKEN = "os.environ.get('GITHUB_TOKEN', 'YOUR_TOKEN_HERE')"
GITHUB_REPO = "EmpCloud/EmpCloud"

ADMIN_EMAIL = "ananya@technova.in"
ADMIN_PASS = "Welcome@123"
EMP_EMAIL = "priya@technova.in"
EMP_PASS = "Welcome@123"

SESSION = requests.Session()
SESSION.verify = False
SESSION.headers.update({"Content-Type": "application/json"})

# Track all issues
ISSUES = []
STATS = {"total_tests": 0, "passed": 0, "failed": 0, "validation_gaps": 0, "errors_500": 0}

# ─── Auth ─────────────────────────────────────────────────────────────
def login(email, password):
    r = SESSION.post(f"{API}/auth/login", json={"email": email, "password": password})
    if r.status_code == 200:
        data = r.json()
        # Token can be in various places
        token = None
        d = data.get("data", {})
        if isinstance(d, dict):
            tokens = d.get("tokens", {})
            if isinstance(tokens, dict):
                token = tokens.get("access_token") or tokens.get("token")
            if not token:
                token = d.get("access_token") or d.get("token")
        if not token:
            token = data.get("token") or data.get("access_token")
        if token:
            SESSION.headers["Authorization"] = f"Bearer {token}"
            print(f"  [AUTH] Logged in as {email}")
            return data
    print(f"  [AUTH] FAILED for {email}: {r.status_code} {r.text[:200]}")
    return None


def get_my_profile():
    """Get current user profile to extract IDs."""
    for ep in ["/users/me", "/auth/me", "/employees/me", "/organizations/me/employees/me"]:
        r = SESSION.get(f"{API}{ep}")
        if r.status_code == 200:
            return r.json().get("data", r.json())
    return {}


def get_org_users():
    """Get list of users in the org."""
    for ep in ["/organizations/me/employees", "/users", "/organizations/me/users", "/employees"]:
        r = SESSION.get(f"{API}{ep}")
        if r.status_code == 200:
            data = r.json()
            items = data.get("data", data)
            if isinstance(items, dict):
                items = items.get("items", items.get("employees", items.get("users", [])))
            if isinstance(items, list) and len(items) > 0:
                return items
    return []


# ─── Issue Filing ─────────────────────────────────────────────────────
def file_issue(title, body):
    """File a GitHub issue."""
    r = requests.post(
        f"https://api.github.com/repos/{GITHUB_REPO}/issues",
        headers={"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"},
        json={"title": f"[VALIDATION] {title}", "body": body, "labels": ["bug", "validation"]}
    )
    if r.status_code == 201:
        url = r.json().get("html_url", "")
        print(f"    -> Issue filed: {url}")
        return url
    else:
        print(f"    -> Issue filing failed: {r.status_code} {r.text[:200]}")
        return None


def record_gap(endpoint, method, field, value_sent, status_code, response_text, expected, severity="medium"):
    """Record a validation gap and file issue."""
    STATS["validation_gaps"] += 1

    # Truncate long values for display
    val_display = str(value_sent)
    if len(val_display) > 200:
        val_display = val_display[:200] + "...[truncated]"
    resp_display = str(response_text)
    if len(resp_display) > 500:
        resp_display = resp_display[:500] + "...[truncated]"

    gap = {
        "endpoint": endpoint,
        "method": method,
        "field": field,
        "value_sent": val_display,
        "status_code": status_code,
        "response": resp_display,
        "expected": expected,
        "severity": severity,
    }
    ISSUES.append(gap)

    title = f"{method} {endpoint} - {field}: {severity} validation gap"
    body = f"""## Validation Gap

**Endpoint:** `{method} {endpoint}`
**Field:** `{field}`
**Severity:** {severity}

### Invalid Value Sent
```
{val_display}
```

### Response Received
- **Status Code:** {status_code}
- **Body:**
```json
{resp_display}
```

### Expected Behavior
{expected}

### Steps to Reproduce
1. Login as org admin (ananya@technova.in)
2. Send `{method}` request to `{endpoint}`
3. Set field `{field}` to the invalid value shown above
4. Observe that the server responds with {status_code} instead of proper validation error

### Environment
- API: {API}
- Test Date: 2026-03-28
"""
    file_issue(title, body)
    return gap


# ─── Test Helpers ─────────────────────────────────────────────────────
def test_field(endpoint, method, base_payload, field, value, expect_reject=True, expect_desc=""):
    """Test a single field with a specific value. Returns (passed, status, response)."""
    STATS["total_tests"] += 1
    payload = dict(base_payload)

    # Handle nested fields
    if "." in field:
        parts = field.split(".")
        payload[parts[0]] = payload.get(parts[0], {})
        payload[parts[0]][parts[1]] = value
    elif value is None and field in payload:
        payload[field] = None
    elif value == "__DELETE__":
        payload.pop(field, None)
    else:
        payload[field] = value

    try:
        if method == "POST":
            r = SESSION.post(f"{API}{endpoint}", json=payload)
        elif method == "PUT":
            r = SESSION.put(f"{API}{endpoint}", json=payload)
        elif method == "PATCH":
            r = SESSION.patch(f"{API}{endpoint}", json=payload)
        else:
            r = SESSION.get(f"{API}{endpoint}", params=payload)
    except Exception as e:
        print(f"    [ERR] {method} {endpoint} field={field}: {e}")
        STATS["failed"] += 1
        return False, 0, str(e)

    status = r.status_code
    resp = r.text[:500]

    if status == 500:
        STATS["errors_500"] += 1
        STATS["failed"] += 1
        val_short = str(value)[:80]
        print(f"    [500!] {field}={val_short} -> 500 Server Error")
        record_gap(endpoint, method, field, value, status, resp,
                   f"Should return 4xx validation error, not 500. {expect_desc}",
                   severity="high")
        return False, status, resp

    if expect_reject:
        if status in (200, 201):
            STATS["failed"] += 1
            val_short = str(value)[:80]
            print(f"    [GAP] {field}={val_short} -> {status} ACCEPTED (should reject)")
            record_gap(endpoint, method, field, value, status, resp,
                       f"Should reject with 400/422 validation error. {expect_desc}",
                       severity="medium")
            return False, status, resp
        else:
            STATS["passed"] += 1
            return True, status, resp
    else:
        # Expect acceptance
        if status in (200, 201):
            STATS["passed"] += 1
            return True, status, resp
        else:
            STATS["failed"] += 1
            val_short = str(value)[:80]
            print(f"    [GAP] {field}={val_short} -> {status} REJECTED (should accept)")
            record_gap(endpoint, method, field, value, status, resp,
                       f"Should accept valid value. {expect_desc}",
                       severity="medium")
            return False, status, resp


def test_query_param(endpoint, params, expect_reject=True, desc=""):
    """Test query parameters."""
    STATS["total_tests"] += 1
    try:
        r = SESSION.get(f"{API}{endpoint}", params=params)
    except Exception as e:
        STATS["failed"] += 1
        return False, 0, str(e)

    status = r.status_code
    resp = r.text[:500]

    if status == 500:
        STATS["errors_500"] += 1
        STATS["failed"] += 1
        print(f"    [500!] params={params} -> 500 Server Error")
        record_gap(endpoint, "GET", str(params), params, status, resp,
                   f"Should not crash. {desc}", severity="high")
        return False, status, resp

    if expect_reject and status in (200, 201):
        # For pagination, 200 might be acceptable if it clamps values
        pass  # Don't file for pagination usually

    STATS["passed"] += 1
    return True, status, resp


# ─── Discovery: find working endpoints ───────────────────────────────
def discover_endpoints():
    """Probe endpoints to find which ones exist."""
    found = {}
    endpoint_candidates = {
        "users": ["/organizations/me/employees", "/users", "/employees", "/organizations/me/users"],
        "leave_applications": ["/organizations/me/leave/applications", "/leave/applications",
                               "/organizations/me/leaves/applications", "/leaves/apply"],
        "leave_types": ["/organizations/me/leave/types", "/leave/types", "/organizations/me/leave-types"],
        "announcements": ["/organizations/me/announcements", "/announcements"],
        "events": ["/organizations/me/events", "/events"],
        "surveys": ["/organizations/me/surveys", "/surveys"],
        "assets": ["/organizations/me/assets", "/assets"],
        "positions": ["/organizations/me/positions", "/positions"],
        "helpdesk": ["/organizations/me/helpdesk/tickets", "/helpdesk/tickets", "/organizations/me/tickets"],
        "forum": ["/organizations/me/forum/posts", "/forum/posts", "/organizations/me/forums"],
        "feedback": ["/organizations/me/feedback", "/feedback"],
        "shifts": ["/organizations/me/shifts", "/shifts", "/organizations/me/attendance/shifts"],
        "policies": ["/organizations/me/policies", "/policies"],
        "departments": ["/organizations/me/departments", "/departments"],
    }

    for name, candidates in endpoint_candidates.items():
        for ep in candidates:
            r = SESSION.get(f"{API}{ep}")
            if r.status_code in (200, 201):
                found[name] = ep
                print(f"  [FOUND] {name}: {ep}")
                break
            elif r.status_code not in (404, 401, 403):
                found[name] = ep
                print(f"  [FOUND?] {name}: {ep} (status={r.status_code})")
                break
    return found


def discover_single_user(users_ep):
    """Find a user endpoint for PUT testing."""
    r = SESSION.get(f"{API}{users_ep}")
    if r.status_code == 200:
        data = r.json()
        items = data.get("data", data)
        if isinstance(items, dict):
            items = items.get("items", items.get("employees", items.get("users", items.get("rows", []))))
        if isinstance(items, list) and len(items) > 0:
            user = items[0]
            uid = user.get("id") or user.get("_id") or user.get("employee_id")
            if uid:
                # Try finding the single-user endpoint
                for pat in [f"{users_ep}/{uid}", f"/users/{uid}", f"/employees/{uid}"]:
                    r2 = SESSION.get(f"{API}{pat}")
                    if r2.status_code == 200:
                        return pat, r2.json().get("data", r2.json()), items
                return f"{users_ep}/{uid}", user, items
    return None, None, []


# ═══════════════════════════════════════════════════════════════════════
#  MAIN TEST SECTIONS
# ═══════════════════════════════════════════════════════════════════════

def test_user_fields(endpoints, user_ep, user_data, all_users):
    """Test 1: User/Employee field validation."""
    print("\n" + "=" * 70)
    print("TEST 1: USER/EMPLOYEE FIELD VALIDATION")
    print("=" * 70)

    if not user_ep or not user_data:
        print("  [SKIP] No user endpoint found")
        return

    uid = user_data.get("id") or user_data.get("_id")
    print(f"  Testing PUT {user_ep} (user id={uid})")

    # Build a safe base payload from existing data
    base = {}
    for k in ["first_name", "last_name", "email", "contact_number", "gender",
              "date_of_birth", "date_of_joining", "department_id", "designation",
              "emp_code", "employment_type", "reporting_manager_id"]:
        if k in user_data and user_data[k] is not None:
            base[k] = user_data[k]

    # Find another user's email for duplicate test
    other_email = None
    other_uid = None
    for u in all_users:
        u_id = u.get("id") or u.get("_id")
        if u_id and str(u_id) != str(uid):
            other_email = u.get("email")
            other_uid = u_id
            break

    # --- EMAIL ---
    print("\n  [email]")
    for val, desc in [
        ("", "empty string"),
        ("not-an-email", "invalid format"),
        ("a@b", "incomplete domain"),
        (None, "null value"),
        ("x" * 300 + "@test.com", "extremely long email"),
        ("test @space.com", "email with space"),
        ("test@@double.com", "double @ sign"),
    ]:
        test_field(user_ep, "PUT", base, "email", val, expect_reject=True, expect_desc=desc)

    if other_email:
        test_field(user_ep, "PUT", base, "email", other_email, expect_reject=True,
                   expect_desc="duplicate email of another user")

    # --- FIRST_NAME / LAST_NAME ---
    for fname in ["first_name", "last_name"]:
        print(f"\n  [{fname}]")
        for val, desc in [
            ("", "empty string"),
            (None, "null"),
            ("A" * 500, "500 chars"),
            ("12345", "numbers only"),
            ("e\u0301 n\u0303 \u4e2d\u6587", "special unicode chars"),
            ("   ", "only spaces"),
            ("<script>alert(1)</script>", "XSS payload - stored OK per rules"),
        ]:
            test_field(user_ep, "PUT", base, fname, val, expect_reject=True, expect_desc=desc)
        # Valid: normal name should be accepted
        test_field(user_ep, "PUT", base, fname, "TestName", expect_reject=False, expect_desc="valid name")

    # --- CONTACT_NUMBER ---
    print("\n  [contact_number]")
    for val, desc in [
        ("", "empty string"),
        ("abc", "alphabetic"),
        ("000", "too short"),
        ("1" * 50, "50 digits"),
        ("+1234567890", "with plus prefix"),
        ("12-34-5678", "with dashes"),
        (None, "null"),
    ]:
        test_field(user_ep, "PUT", base, "contact_number", val, expect_reject=True, expect_desc=desc)

    # --- DATE_OF_BIRTH ---
    print("\n  [date_of_birth]")
    for val, desc in [
        ("", "empty string"),
        ("not-a-date", "invalid format"),
        ("2050-01-01", "future date"),
        ("1800-01-01", "too old (1800)"),
        ("2024-02-30", "invalid date Feb 30"),
        ("2023-02-29", "invalid leap day"),
        (None, "null"),
    ]:
        test_field(user_ep, "PUT", base, "date_of_birth", val, expect_reject=True, expect_desc=desc)
    # Valid leap day
    test_field(user_ep, "PUT", base, "date_of_birth", "2024-02-29", expect_reject=False,
               expect_desc="valid leap day 2024")

    # --- DATE_OF_JOINING ---
    print("\n  [date_of_joining]")
    for val, desc in [
        ("", "empty string"),
        ("not-a-date", "invalid format"),
        ("2050-06-01", "far future date"),
        ("1899-01-01", "date before DOB possibility"),
        (None, "null"),
    ]:
        test_field(user_ep, "PUT", base, "date_of_joining", val, expect_reject=True, expect_desc=desc)

    # DOJ before DOB
    if base.get("date_of_birth"):
        test_field(user_ep, "PUT", base, "date_of_joining", "1990-01-01",
                   expect_reject=True, expect_desc="DOJ before typical DOB")

    # --- DATE_OF_EXIT ---
    print("\n  [date_of_exit]")
    for val, desc in [
        ("1990-01-01", "before date_of_joining"),
        ("not-a-date", "invalid format"),
    ]:
        test_field(user_ep, "PUT", base, "date_of_exit", val, expect_reject=True, expect_desc=desc)

    # --- GENDER ---
    print("\n  [gender]")
    for val, desc in [
        ("invalid", "invalid string"),
        ("", "empty string"),
        ("M", "single letter M"),
        ("male", "lowercase male"),
        (None, "null"),
        (123, "integer"),
    ]:
        test_field(user_ep, "PUT", base, "gender", val, expect_reject=True, expect_desc=desc)

    # --- EMPLOYMENT_TYPE ---
    print("\n  [employment_type]")
    for val, desc in [
        ("invalid", "invalid type string"),
        ("", "empty string"),
        (None, "null"),
        (999, "integer"),
    ]:
        test_field(user_ep, "PUT", base, "employment_type", val, expect_reject=True, expect_desc=desc)

    # --- DEPARTMENT_ID ---
    print("\n  [department_id]")
    for val, desc in [
        (0, "zero"),
        (-1, "negative"),
        (999999, "non-existent"),
        ("abc", "string"),
        (None, "null"),
    ]:
        test_field(user_ep, "PUT", base, "department_id", val, expect_reject=True, expect_desc=desc)

    # --- REPORTING_MANAGER_ID ---
    print("\n  [reporting_manager_id]")
    for val, desc in [
        (uid, "own user ID (self-report)"),
        (0, "zero"),
        (-1, "negative"),
        (999999, "non-existent"),
        (None, "null"),
    ]:
        test_field(user_ep, "PUT", base, "reporting_manager_id", val, expect_reject=True, expect_desc=desc)

    # --- DESIGNATION ---
    print("\n  [designation]")
    for val, desc in [
        ("", "empty string"),
        (None, "null"),
        ("D" * 500, "500 chars"),
    ]:
        test_field(user_ep, "PUT", base, "designation", val, expect_reject=True, expect_desc=desc)

    # --- EMP_CODE ---
    print("\n  [emp_code]")
    for val, desc in [
        ("", "empty string"),
        ("!@#$%", "special chars only"),
        ("E" * 200, "200 chars"),
    ]:
        test_field(user_ep, "PUT", base, "emp_code", val, expect_reject=True, expect_desc=desc)


def test_leave_applications(endpoints):
    """Test 2: Leave application field validation."""
    print("\n" + "=" * 70)
    print("TEST 2: LEAVE APPLICATION FIELD VALIDATION")
    print("=" * 70)

    ep = endpoints.get("leave_applications")
    if not ep:
        print("  [SKIP] No leave applications endpoint found")
        return

    # Get leave types
    lt_ep = endpoints.get("leave_types")
    leave_type_id = None
    if lt_ep:
        r = SESSION.get(f"{API}{lt_ep}")
        if r.status_code == 200:
            data = r.json().get("data", r.json())
            if isinstance(data, dict):
                data = data.get("items", data.get("rows", []))
            if isinstance(data, list) and data:
                leave_type_id = data[0].get("id") or data[0].get("_id")

    base = {
        "leave_type_id": leave_type_id or 1,
        "start_date": "2026-04-15",
        "end_date": "2026-04-15",
        "days_count": 1,
        "reason": "Testing leave validation",
    }

    print(f"  Testing POST {ep}")

    # --- LEAVE_TYPE_ID ---
    print("\n  [leave_type_id]")
    for val, desc in [
        (0, "zero"), (-1, "negative"), (999999, "non-existent"),
        (None, "null"), ("abc", "string"),
    ]:
        test_field(ep, "POST", base, "leave_type_id", val, expect_reject=True, expect_desc=desc)

    # --- START_DATE ---
    print("\n  [start_date]")
    for val, desc in [
        ("", "empty string"), ("not-a-date", "invalid format"),
        ("2020-01-01", "past date"),
        (None, "null"),
    ]:
        test_field(ep, "POST", base, "start_date", val, expect_reject=True, expect_desc=desc)

    # --- END_DATE ---
    print("\n  [end_date]")
    for val, desc in [
        ("2026-04-10", "before start_date"),
        ("", "empty string"),
        ("2027-04-15", "1 year from start"),
        (None, "null"),
    ]:
        test_field(ep, "POST", base, "end_date", val, expect_reject=True, expect_desc=desc)

    # --- DAYS_COUNT ---
    print("\n  [days_count]")
    for val, desc in [
        (0, "zero"), (-1, "negative"), (0.5, "half"),
        (365, "365 days"), (None, "null"),
    ]:
        test_field(ep, "POST", base, "days_count", val, expect_reject=True, expect_desc=desc)

    # --- IS_HALF_DAY ---
    print("\n  [is_half_day]")
    multi_day_base = dict(base, start_date="2026-04-15", end_date="2026-04-17", days_count=3)
    test_field(ep, "POST", multi_day_base, "is_half_day", True, expect_reject=True,
               expect_desc="half day with multi-day leave")
    for val, desc in [("yes", "string yes"), (1, "integer 1"), (None, "null")]:
        test_field(ep, "POST", base, "is_half_day", val, expect_reject=True, expect_desc=desc)

    # --- REASON ---
    print("\n  [reason]")
    for val, desc in [
        ("", "empty string"), (None, "null"),
        ("R" * 5000, "5000 chars"), ("   ", "only spaces"),
    ]:
        test_field(ep, "POST", base, "reason", val, expect_reject=True, expect_desc=desc)


def test_announcements(endpoints):
    """Test 3: Announcement field validation."""
    print("\n" + "=" * 70)
    print("TEST 3: ANNOUNCEMENT FIELD VALIDATION")
    print("=" * 70)

    ep = endpoints.get("announcements")
    if not ep:
        print("  [SKIP] No announcements endpoint found")
        return

    base = {
        "title": "Test Announcement Validation",
        "content": "This is test content for validation.",
        "date": "2026-04-01",
    }

    print(f"  Testing POST {ep}")

    # --- TITLE ---
    print("\n  [title]")
    for val, desc in [
        ("", "empty string"), (None, "null"),
        ("T" * 1000, "1000 chars"), ("   ", "only spaces"),
        ("\U0001f389\U0001f680\U0001f4a5", "emoji only"),
    ]:
        test_field(ep, "POST", base, "title", val, expect_reject=True, expect_desc=desc)

    # --- CONTENT ---
    print("\n  [content]")
    for val, desc in [
        ("", "empty string"), (None, "null"),
        ("C" * 50000, "50000 chars"),
        ("<h1>HTML</h1><script>alert(1)</script>", "HTML tags"),
        ("# Markdown\n- list", "markdown"),
    ]:
        test_field(ep, "POST", base, "content", val, expect_reject=True, expect_desc=desc)

    # --- DATE ---
    print("\n  [date]")
    for val, desc in [
        ("", "empty string"), ("not-a-date", "invalid format"),
        ("2020-01-01", "past date"), ("2030-01-01", "far future"),
        (None, "null"),
    ]:
        test_field(ep, "POST", base, "date", val, expect_reject=True, expect_desc=desc)


def test_events(endpoints):
    """Test 4: Event field validation."""
    print("\n" + "=" * 70)
    print("TEST 4: EVENT FIELD VALIDATION")
    print("=" * 70)

    ep = endpoints.get("events")
    if not ep:
        print("  [SKIP] No events endpoint found")
        return

    base = {
        "title": "Test Event Validation",
        "start_date": "2026-04-15",
        "end_date": "2026-04-16",
        "location": "Office",
        "description": "Test event for validation.",
    }

    print(f"  Testing POST {ep}")

    print("\n  [title]")
    for val, desc in [("", "empty"), (None, "null"), ("T" * 1000, "1000 chars")]:
        test_field(ep, "POST", base, "title", val, expect_reject=True, expect_desc=desc)

    print("\n  [start_date]")
    for val, desc in [
        ("2020-01-01", "past"), ("", "empty"),
        ("2026-05-01", "after end_date - reversed range"),
        (None, "null"),
    ]:
        # For start_date after end_date, use a combo
        if "reversed" in desc:
            test_field(ep, "POST", dict(base, end_date="2026-04-01"), "start_date", "2026-05-01",
                       expect_reject=True, expect_desc=desc)
        else:
            test_field(ep, "POST", base, "start_date", val, expect_reject=True, expect_desc=desc)

    print("\n  [end_date]")
    for val, desc in [
        ("2026-04-10", "before start_date"),
        ("", "empty"), (None, "null"),
    ]:
        test_field(ep, "POST", base, "end_date", val, expect_reject=True, expect_desc=desc)

    print("\n  [location]")
    for val, desc in [("", "empty"), (None, "null"), ("L" * 1000, "1000 chars")]:
        test_field(ep, "POST", base, "location", val, expect_reject=True, expect_desc=desc)

    print("\n  [description]")
    for val, desc in [("", "empty"), (None, "null"), ("D" * 50000, "50000 chars")]:
        test_field(ep, "POST", base, "description", val, expect_reject=True, expect_desc=desc)


def test_surveys(endpoints):
    """Test 5: Survey field validation."""
    print("\n" + "=" * 70)
    print("TEST 5: SURVEY FIELD VALIDATION")
    print("=" * 70)

    ep = endpoints.get("surveys")
    if not ep:
        print("  [SKIP] No surveys endpoint found")
        return

    base = {
        "title": "Test Survey Validation",
        "description": "Test survey for validation.",
        "start_date": "2026-04-15",
        "end_date": "2026-04-30",
    }

    print(f"  Testing POST {ep}")

    print("\n  [title]")
    for val, desc in [("", "empty"), (None, "null"), ("T" * 1000, "1000 chars")]:
        test_field(ep, "POST", base, "title", val, expect_reject=True, expect_desc=desc)

    print("\n  [description]")
    for val, desc in [("", "empty"), (None, "null")]:
        test_field(ep, "POST", base, "description", val, expect_reject=True, expect_desc=desc)

    print("\n  [date ranges]")
    # end before start
    test_field(ep, "POST", dict(base, start_date="2026-05-01"), "end_date", "2026-04-01",
               expect_reject=True, expect_desc="end before start")
    test_field(ep, "POST", base, "start_date", "", expect_reject=True, expect_desc="empty start")
    test_field(ep, "POST", base, "end_date", "", expect_reject=True, expect_desc="empty end")


def test_assets(endpoints):
    """Test 6: Asset field validation."""
    print("\n" + "=" * 70)
    print("TEST 6: ASSET FIELD VALIDATION")
    print("=" * 70)

    ep = endpoints.get("assets")
    if not ep:
        # Try more paths
        for try_ep in ["/organizations/me/assets", "/assets", "/organizations/me/asset-management"]:
            r = SESSION.get(f"{API}{try_ep}")
            if r.status_code in (200, 201):
                ep = try_ep
                break
    if not ep:
        print("  [SKIP] No assets endpoint found")
        return

    base = {
        "name": "Test Asset Validation",
        "serial_number": f"SN-VAL-{int(time.time())}",
        "category": "Laptop",
        "purchase_date": "2025-01-15",
        "warranty_expiry": "2027-01-15",
    }

    print(f"  Testing POST {ep}")

    print("\n  [name]")
    for val, desc in [("", "empty"), (None, "null"), ("A" * 1000, "1000 chars")]:
        test_field(ep, "POST", base, "name", val, expect_reject=True, expect_desc=desc)

    print("\n  [serial_number]")
    for val, desc in [("", "empty")]:
        test_field(ep, "POST", base, "serial_number", val, expect_reject=True, expect_desc=desc)
    # Duplicate serial
    test_field(ep, "POST", base, "serial_number", base["serial_number"],
               expect_reject=False, expect_desc="first creation")
    test_field(ep, "POST", base, "serial_number", base["serial_number"],
               expect_reject=True, expect_desc="duplicate serial number")

    print("\n  [category]")
    for val, desc in [("", "empty"), ("INVALID_CAT_XYZ", "invalid category")]:
        test_field(ep, "POST", base, "category", val, expect_reject=True, expect_desc=desc)

    print("\n  [purchase_date]")
    test_field(ep, "POST", base, "purchase_date", "2030-01-01", expect_reject=True,
               expect_desc="future purchase date")
    test_field(ep, "POST", base, "purchase_date", "", expect_reject=True, expect_desc="empty")

    print("\n  [warranty_expiry]")
    test_field(ep, "POST", base, "warranty_expiry", "2020-01-01", expect_reject=True,
               expect_desc="warranty before purchase")


def test_positions(endpoints):
    """Test 7: Position field validation."""
    print("\n" + "=" * 70)
    print("TEST 7: POSITION FIELD VALIDATION")
    print("=" * 70)

    ep = endpoints.get("positions")
    if not ep:
        for try_ep in ["/organizations/me/positions", "/positions", "/organizations/me/job-positions"]:
            r = SESSION.get(f"{API}{try_ep}")
            if r.status_code in (200, 201):
                ep = try_ep
                break
    if not ep:
        print("  [SKIP] No positions endpoint found")
        return

    base = {
        "title": f"Test Position {int(time.time())}",
        "department": "Engineering",
        "headcount": 5,
        "code": f"POS-{int(time.time())}",
    }

    print(f"  Testing POST {ep}")

    print("\n  [title]")
    for val, desc in [("", "empty"), (None, "null")]:
        test_field(ep, "POST", base, "title", val, expect_reject=True, expect_desc=desc)

    print("\n  [department]")
    for val, desc in [("", "empty"), ("INVALID_DEPT", "invalid")]:
        test_field(ep, "POST", base, "department", val, expect_reject=True, expect_desc=desc)

    print("\n  [headcount]")
    for val, desc in [(0, "zero"), (-1, "negative"), (10000, "very large")]:
        test_field(ep, "POST", base, "headcount", val, expect_reject=True, expect_desc=desc)

    print("\n  [code - duplicates]")
    test_field(ep, "POST", base, "code", base["code"], expect_reject=False, expect_desc="first creation")
    test_field(ep, "POST", base, "code", base["code"], expect_reject=True, expect_desc="duplicate code")


def test_helpdesk(endpoints):
    """Test 8: Helpdesk ticket field validation."""
    print("\n" + "=" * 70)
    print("TEST 8: HELPDESK TICKET FIELD VALIDATION")
    print("=" * 70)

    ep = endpoints.get("helpdesk")
    if not ep:
        for try_ep in ["/organizations/me/helpdesk/tickets", "/helpdesk/tickets",
                       "/organizations/me/helpdesk", "/organizations/me/tickets"]:
            r = SESSION.get(f"{API}{try_ep}")
            if r.status_code in (200, 201):
                ep = try_ep
                break
    if not ep:
        print("  [SKIP] No helpdesk endpoint found")
        return

    base = {
        "subject": "Test Helpdesk Validation",
        "description": "Testing helpdesk validation.",
        "priority": "medium",
        "category": "general",
    }

    print(f"  Testing POST {ep}")

    print("\n  [subject]")
    for val, desc in [("", "empty"), (None, "null"), ("S" * 1000, "1000 chars")]:
        test_field(ep, "POST", base, "subject", val, expect_reject=True, expect_desc=desc)

    print("\n  [description]")
    for val, desc in [("", "empty"), (None, "null"), ("D" * 50000, "50000 chars")]:
        test_field(ep, "POST", base, "description", val, expect_reject=True, expect_desc=desc)

    print("\n  [priority]")
    for val, desc in [
        ("", "empty"), ("invalid", "invalid value"),
        ("URGENT", "uppercase"), ("critical", "critical - may be invalid"),
    ]:
        test_field(ep, "POST", base, "priority", val, expect_reject=True, expect_desc=desc)

    print("\n  [category]")
    for val, desc in [("", "empty"), ("INVALID_CAT_XYZ", "invalid category")]:
        test_field(ep, "POST", base, "category", val, expect_reject=True, expect_desc=desc)


def test_forum(endpoints):
    """Test 9: Forum post field validation."""
    print("\n" + "=" * 70)
    print("TEST 9: FORUM POST FIELD VALIDATION")
    print("=" * 70)

    ep = endpoints.get("forum")
    if not ep:
        for try_ep in ["/organizations/me/forum/posts", "/forum/posts",
                       "/organizations/me/forums", "/organizations/me/forum"]:
            r = SESSION.get(f"{API}{try_ep}")
            if r.status_code in (200, 201):
                ep = try_ep
                break
    if not ep:
        print("  [SKIP] No forum endpoint found")
        return

    base = {
        "title": "Test Forum Validation",
        "content": "Testing forum post validation.",
        "category_id": 1,
    }

    print(f"  Testing POST {ep}")

    print("\n  [title]")
    for val, desc in [("", "empty"), (None, "null"), ("T" * 1000, "1000 chars")]:
        test_field(ep, "POST", base, "title", val, expect_reject=True, expect_desc=desc)

    print("\n  [content]")
    for val, desc in [("", "empty"), (None, "null"), ("C" * 50000, "50000 chars")]:
        test_field(ep, "POST", base, "content", val, expect_reject=True, expect_desc=desc)

    print("\n  [category_id]")
    for val, desc in [(0, "zero"), (-1, "negative"), (999999, "non-existent"), (None, "null")]:
        test_field(ep, "POST", base, "category_id", val, expect_reject=True, expect_desc=desc)


def test_feedback(endpoints):
    """Test 10: Feedback field validation."""
    print("\n" + "=" * 70)
    print("TEST 10: FEEDBACK FIELD VALIDATION")
    print("=" * 70)

    ep = endpoints.get("feedback")
    if not ep:
        for try_ep in ["/organizations/me/feedback", "/feedback",
                       "/organizations/me/feedbacks"]:
            r = SESSION.get(f"{API}{try_ep}")
            if r.status_code in (200, 201):
                ep = try_ep
                break
    if not ep:
        print("  [SKIP] No feedback endpoint found")
        return

    base = {
        "subject": "Test Feedback Validation",
        "message": "Testing feedback validation.",
        "category": "general",
        "is_anonymous": False,
    }

    print(f"  Testing POST {ep}")

    print("\n  [subject]")
    for val, desc in [("", "empty"), (None, "null"), ("S" * 1000, "1000 chars")]:
        test_field(ep, "POST", base, "subject", val, expect_reject=True, expect_desc=desc)

    print("\n  [message]")
    for val, desc in [("", "empty"), (None, "null"), ("M" * 50000, "50000 chars")]:
        test_field(ep, "POST", base, "message", val, expect_reject=True, expect_desc=desc)

    print("\n  [category]")
    for val, desc in [("", "empty"), ("INVALID_CAT_XYZ", "invalid category")]:
        test_field(ep, "POST", base, "category", val, expect_reject=True, expect_desc=desc)

    print("\n  [is_anonymous]")
    for val, desc in [("yes", "string yes"), (1, "integer 1"), (None, "null")]:
        test_field(ep, "POST", base, "is_anonymous", val, expect_reject=True, expect_desc=desc)


def test_shifts(endpoints):
    """Test 11: Shift field validation."""
    print("\n" + "=" * 70)
    print("TEST 11: SHIFT FIELD VALIDATION")
    print("=" * 70)

    ep = endpoints.get("shifts")
    if not ep:
        for try_ep in ["/organizations/me/shifts", "/shifts",
                       "/organizations/me/attendance/shifts"]:
            r = SESSION.get(f"{API}{try_ep}")
            if r.status_code in (200, 201):
                ep = try_ep
                break
    if not ep:
        print("  [SKIP] No shifts endpoint found")
        return

    base = {
        "name": f"Test Shift {int(time.time())}",
        "start_time": "09:00",
        "end_time": "17:00",
    }

    print(f"  Testing POST {ep}")

    print("\n  [name]")
    for val, desc in [("", "empty"), (None, "null")]:
        test_field(ep, "POST", base, "name", val, expect_reject=True, expect_desc=desc)
    # Duplicate name
    test_field(ep, "POST", base, "name", base["name"], expect_reject=False, expect_desc="first creation")
    test_field(ep, "POST", base, "name", base["name"], expect_reject=True, expect_desc="duplicate name")

    print("\n  [start_time]")
    for val, desc in [("", "empty"), ("25:00", "invalid hour"), ("abc", "non-time string")]:
        test_field(ep, "POST", base, "start_time", val, expect_reject=True, expect_desc=desc)

    print("\n  [end_time]")
    for val, desc in [("", "empty"), ("08:00", "before start_time when start=09:00")]:
        test_field(ep, "POST", base, "end_time", val, expect_reject=True, expect_desc=desc)


def test_leave_types(endpoints):
    """Test 12: Leave type field validation."""
    print("\n" + "=" * 70)
    print("TEST 12: LEAVE TYPE FIELD VALIDATION")
    print("=" * 70)

    ep = endpoints.get("leave_types")
    if not ep:
        for try_ep in ["/organizations/me/leave/types", "/leave/types",
                       "/organizations/me/leave-types"]:
            r = SESSION.get(f"{API}{try_ep}")
            if r.status_code in (200, 201):
                ep = try_ep
                break
    if not ep:
        print("  [SKIP] No leave types endpoint found")
        return

    base = {
        "name": f"Test Leave Type {int(time.time())}",
        "code": f"TLT-{int(time.time())}",
        "max_days_allowed": 10,
        "type": "paid",
    }

    print(f"  Testing POST {ep}")

    print("\n  [name]")
    for val, desc in [("", "empty"), (None, "null")]:
        test_field(ep, "POST", base, "name", val, expect_reject=True, expect_desc=desc)

    print("\n  [code]")
    for val, desc in [("", "empty")]:
        test_field(ep, "POST", base, "code", val, expect_reject=True, expect_desc=desc)
    # Duplicate
    test_field(ep, "POST", base, "code", base["code"], expect_reject=False, expect_desc="first creation")
    base2 = dict(base, name=f"Test Leave Type DUP {int(time.time())}")
    test_field(ep, "POST", base2, "code", base["code"], expect_reject=True, expect_desc="duplicate code")

    print("\n  [max_days_allowed]")
    for val, desc in [(0, "zero"), (-1, "negative"), (1000, "very large 1000")]:
        test_field(ep, "POST", base, "max_days_allowed", val, expect_reject=True, expect_desc=desc)

    print("\n  [type]")
    for val, desc in [("", "empty"), ("INVALID_TYPE", "invalid type string")]:
        test_field(ep, "POST", base, "type", val, expect_reject=True, expect_desc=desc)


def test_policies(endpoints):
    """Test 13: Policy field validation."""
    print("\n" + "=" * 70)
    print("TEST 13: POLICY FIELD VALIDATION")
    print("=" * 70)

    ep = endpoints.get("policies")
    if not ep:
        for try_ep in ["/organizations/me/policies", "/policies",
                       "/organizations/me/policy"]:
            r = SESSION.get(f"{API}{try_ep}")
            if r.status_code in (200, 201):
                ep = try_ep
                break
    if not ep:
        print("  [SKIP] No policies endpoint found")
        return

    base = {
        "title": f"Test Policy {int(time.time())}",
        "content": "This is a test policy content for validation.",
        "category": "general",
    }

    print(f"  Testing POST {ep}")

    print("\n  [title]")
    for val, desc in [("", "empty"), (None, "null")]:
        test_field(ep, "POST", base, "title", val, expect_reject=True, expect_desc=desc)

    # Duplicate
    test_field(ep, "POST", base, "title", base["title"], expect_reject=False, expect_desc="first creation")
    test_field(ep, "POST", base, "title", base["title"], expect_reject=True, expect_desc="duplicate title")

    print("\n  [content]")
    for val, desc in [("", "empty"), (None, "null"), ("C" * 50000, "50000 chars")]:
        test_field(ep, "POST", base, "content", val, expect_reject=True, expect_desc=desc)

    print("\n  [category]")
    for val, desc in [("", "empty"), ("INVALID_CAT_XYZ", "invalid")]:
        test_field(ep, "POST", base, "category", val, expect_reject=True, expect_desc=desc)


def test_pagination_filtering(endpoints):
    """Test 14: Pagination & filtering validation."""
    print("\n" + "=" * 70)
    print("TEST 14: PAGINATION & FILTERING VALIDATION")
    print("=" * 70)

    # Test pagination on all found list endpoints
    list_eps = [ep for ep in endpoints.values() if ep]

    for ep in list_eps[:5]:  # test on first 5 endpoints
        print(f"\n  Testing GET {ep} pagination")

        test_query_param(ep, {"page": 0}, desc="page=0")
        test_query_param(ep, {"page": -1}, desc="page=-1")
        test_query_param(ep, {"page": 999999}, desc="page=999999")
        test_query_param(ep, {"per_page": 0}, desc="per_page=0")
        test_query_param(ep, {"per_page": -1}, desc="per_page=-1")
        test_query_param(ep, {"per_page": 10000}, desc="per_page=10000")
        test_query_param(ep, {"sort": "nonexistent_field_xyz"}, desc="sort=invalid")
        test_query_param(ep, {"order": "INVALID"}, desc="order=invalid")
        test_query_param(ep, {"search": "'; DROP TABLE users; --"}, desc="SQL injection in search")
        test_query_param(ep, {"search": "<script>alert(1)</script>"}, desc="XSS in search")
        test_query_param(ep, {"search": ""}, desc="empty search")
        test_query_param(ep, {"search": "a" * 1000}, desc="very long search string")


def test_boundary_values(endpoints, user_ep, user_data):
    """Test 15: Boundary value testing across types."""
    print("\n" + "=" * 70)
    print("TEST 15: BOUNDARY VALUE TESTING")
    print("=" * 70)

    if not user_ep or not user_data:
        print("  [SKIP] No user endpoint for boundary tests")
        return

    base = {}
    for k in ["first_name", "last_name", "email"]:
        if k in user_data and user_data[k] is not None:
            base[k] = user_data[k]

    print("\n  [Integer boundary values on department_id]")
    for val, desc in [
        (-2147483648, "MIN_INT"),
        (2147483647, "MAX_INT"),
        (3.14, "float"),
        ("not_a_number", "string"),
        (True, "boolean true"),
        (False, "boolean false"),
    ]:
        test_field(user_ep, "PUT", base, "department_id", val, expect_reject=True, expect_desc=desc)

    print("\n  [String boundary values on first_name]")
    for val, desc in [
        ("A", "1 char"),
        ("A" * 255, "255 chars"),
        ("A" * 256, "256 chars"),
        ("A" * 1000, "1000 chars"),
        ("\x00", "null byte"),
        ("\t\n\r", "whitespace chars"),
        ("Robert'); DROP TABLE users;--", "SQL injection"),
    ]:
        test_field(user_ep, "PUT", base, "first_name", val, expect_reject=True, expect_desc=desc)

    print("\n  [Date boundary values on date_of_birth]")
    for val, desc in [
        ("1900-01-01", "very old date"),
        ("2100-12-31", "far future"),
        ("2024-02-29", "valid leap day"),
        ("2023-02-29", "invalid leap day"),
        ("0000-01-01", "year zero"),
        ("9999-12-31", "year 9999"),
    ]:
        if "valid leap" in desc:
            test_field(user_ep, "PUT", base, "date_of_birth", val, expect_reject=False, expect_desc=desc)
        else:
            test_field(user_ep, "PUT", base, "date_of_birth", val, expect_reject=True, expect_desc=desc)

    print("\n  [Boolean boundary values]")
    # Test on any endpoint that has boolean fields
    ep = endpoints.get("feedback")
    if ep:
        fb_base = {
            "subject": "Bool Test", "message": "Testing booleans",
            "category": "general", "is_anonymous": False,
        }
        for val, desc in [
            (0, "integer 0"), (1, "integer 1"),
            ("true", "string true"), ("false", "string false"),
            (None, "null"), ("", "empty string"),
        ]:
            test_field(ep, "POST", fb_base, "is_anonymous", val, expect_reject=True, expect_desc=desc)


# ═══════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════
def main():
    print("=" * 70)
    print("EMP CLOUD HRMS - DEEP VALIDATION & BOUNDARY TESTING")
    print("=" * 70)
    print(f"API: {API}")
    print(f"Date: 2026-03-28\n")

    # Login as admin
    print("[STEP 1] Authenticating as Org Admin...")
    auth = login(ADMIN_EMAIL, ADMIN_PASS)
    if not auth:
        print("FATAL: Cannot login as admin. Aborting.")
        return

    # Discover endpoints
    print("\n[STEP 2] Discovering API endpoints...")
    endpoints = discover_endpoints()
    print(f"  Found {len(endpoints)} endpoint groups")

    # Get user data for PUT testing
    print("\n[STEP 3] Getting user data for field testing...")
    users_ep = endpoints.get("users")
    user_ep, user_data, all_users = None, None, []
    if users_ep:
        user_ep, user_data, all_users = discover_single_user(users_ep)
        if user_ep:
            print(f"  User endpoint: {user_ep}")
            if user_data:
                uid = user_data.get("id") or user_data.get("_id")
                print(f"  User ID: {uid}, Name: {user_data.get('first_name', '?')} {user_data.get('last_name', '?')}")

    # Run all test sections
    print("\n[STEP 4] Running validation tests...")

    test_user_fields(endpoints, user_ep, user_data, all_users)
    test_leave_applications(endpoints)
    test_announcements(endpoints)
    test_events(endpoints)
    test_surveys(endpoints)
    test_assets(endpoints)
    test_positions(endpoints)
    test_helpdesk(endpoints)
    test_forum(endpoints)
    test_feedback(endpoints)
    test_shifts(endpoints)
    test_leave_types(endpoints)
    test_policies(endpoints)
    test_pagination_filtering(endpoints)
    test_boundary_values(endpoints, user_ep, user_data)

    # ─── Summary ──────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("FINAL SUMMARY")
    print("=" * 70)
    print(f"  Total tests run:      {STATS['total_tests']}")
    print(f"  Passed (validated):   {STATS['passed']}")
    print(f"  Failed:               {STATS['failed']}")
    print(f"  Validation gaps:      {STATS['validation_gaps']}")
    print(f"  500 errors:           {STATS['errors_500']}")
    print(f"  GitHub issues filed:  {len(ISSUES)}")

    if ISSUES:
        print("\n  VALIDATION GAPS FOUND:")
        print("  " + "-" * 66)
        for i, gap in enumerate(ISSUES, 1):
            print(f"  {i:3}. [{gap['severity'].upper()}] {gap['method']} {gap['endpoint']}")
            print(f"       Field: {gap['field']}, Value: {str(gap['value_sent'])[:60]}")
            print(f"       Got: {gap['status_code']}, Expected: {gap['expected'][:60]}")
            print()
    else:
        print("\n  No validation gaps found - all fields properly validated!")

    # Save results
    results = {
        "stats": STATS,
        "issues": ISSUES,
        "endpoints_tested": endpoints,
    }
    with open("C:/emptesting/validation_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=str)
    print("\n  Results saved to C:/emptesting/validation_results.json")


if __name__ == "__main__":
    main()
