#!/usr/bin/env python3
"""
EMP Cloud HRMS - Cross-Module Data Consistency Tests (v2)
Now with actual field names based on API discovery.
"""

import urllib.request
import urllib.error
import json
import ssl
import time
import sys
from datetime import datetime, date

API_BASE = "https://test-empcloud-api.empcloud.com"
FRONTEND = "https://test-empcloud.empcloud.com"
GITHUB_PAT = "$GITHUB_TOKEN"
GITHUB_REPO = "EmpCloud/EmpCloud"
ADMIN_EMAIL = "ananya@technova.in"
ADMIN_PASS = "Welcome@123"
EMP_EMAIL = "priya@technova.in"
EMP_PASS = "Welcome@123"

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

BUGS = []

def api(path, method="GET", data=None, token=None, timeout=30):
    url = API_BASE + path
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 EmpCloudTester/1.0",
        "Origin": FRONTEND,
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        resp = urllib.request.urlopen(req, context=ctx, timeout=timeout)
        raw = resp.read().decode("utf-8", errors="replace")
        try:
            return resp.status, json.loads(raw)
        except json.JSONDecodeError:
            return resp.status, raw
    except urllib.error.HTTPError as e:
        raw = ""
        try:
            raw = e.read().decode("utf-8", errors="replace")
        except Exception:
            pass
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, raw
    except Exception as ex:
        return 0, str(ex)


def login(email, password):
    code, body = api("/api/v1/auth/login", "POST", {"email": email, "password": password})
    if code == 429:
        print(f"  [429] Rate limited, waiting 90s...")
        time.sleep(90)
        code, body = api("/api/v1/auth/login", "POST", {"email": email, "password": password})
    if code == 429:
        print(f"  [429] Still rate limited, waiting 120s...")
        time.sleep(120)
        code, body = api("/api/v1/auth/login", "POST", {"email": email, "password": password})
    if code == 200 and isinstance(body, dict):
        token = body.get("data", {}).get("tokens", {}).get("access_token")
        user_data = body.get("data", {}).get("user", {})
        org_data = body.get("data", {}).get("org", {})
        if token:
            print(f"  [OK] Logged in as {email} (role={user_data.get('role')}, org={org_data.get('name')})")
            return token, user_data, org_data
    print(f"  [FAIL] Login failed: {code}")
    return None, None, None


def record_bug(title, body_text, labels=None):
    BUGS.append({"title": f"[DATA FLOW] {title}", "body": body_text, "labels": labels or ["bug", "data-consistency"]})


def file_github_issues():
    if not BUGS:
        print("\n=== No bugs to file ===")
        return
    print(f"\n{'='*60}")
    print(f"FILING {len(BUGS)} GITHUB ISSUES")
    print(f"{'='*60}")
    for bug in BUGS:
        body = bug["body"] + "\n\n---\n_Filed by cross-module data consistency test suite._"
        payload = {"title": bug["title"], "body": body, "labels": bug["labels"]}
        url = f"https://api.github.com/repos/{GITHUB_REPO}/issues"
        headers = {
            "Authorization": f"token {GITHUB_PAT}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "EmpCloudTester/1.0",
            "Content-Type": "application/json",
        }
        req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=headers, method="POST")
        try:
            resp = urllib.request.urlopen(req, context=ctx, timeout=30)
            result = json.loads(resp.read().decode())
            print(f"  [FILED] #{result.get('number')} - {bug['title']}")
            print(f"          {result.get('html_url')}")
        except Exception as ex:
            print(f"  [ERROR] Could not file: {bug['title']} -- {ex}")
        time.sleep(1)


def get_all_pages(path, token, key="data"):
    """Fetch all pages from a paginated endpoint."""
    all_items = []
    page = 1
    while True:
        sep = "&" if "?" in path else "?"
        code, body = api(f"{path}{sep}page={page}&limit=100", token=token)
        if code == 429:
            print(f"  [429] Rate limited, waiting 30s...")
            time.sleep(30)
            code, body = api(f"{path}{sep}page={page}&limit=100", token=token)
        if code != 200 or not isinstance(body, dict):
            break
        items = body.get(key, [])
        if isinstance(items, list):
            all_items.extend(items)
        else:
            break
        meta = body.get("meta", {})
        total_pages = meta.get("totalPages") or meta.get("total_pages") or 1
        if page >= total_pages:
            break
        page += 1
        time.sleep(0.3)
    return all_items


# ---------------------------------------------------------------------------
def main():
    print("=" * 60)
    print("EMP Cloud HRMS - Cross-Module Data Consistency Tests v2")
    print(f"Date: {datetime.now().isoformat()}")
    print("=" * 60)

    # === LOGIN ===
    print("\n--- Login ---")
    admin_token, admin_user, org_data = login(ADMIN_EMAIL, ADMIN_PASS)
    if not admin_token:
        print("[FATAL] Cannot proceed")
        sys.exit(1)
    time.sleep(1)
    emp_token, emp_user, _ = login(EMP_EMAIL, EMP_PASS)

    # =========================================================================
    # TEST 1: FULL API ENDPOINT DISCOVERY
    # =========================================================================
    print(f"\n{'='*60}")
    print("TEST 1: API ENDPOINT DISCOVERY")
    print(f"{'='*60}")

    endpoints = [
        "/api/v1/users", "/api/v1/departments", "/api/v1/locations",
        "/api/v1/designations", "/api/v1/attendance", "/api/v1/leaves",
        "/api/v1/leave-applications", "/api/v1/leave-balances",
        "/api/v1/leave/applications", "/api/v1/leave/balances", "/api/v1/leave/types",
        "/api/v1/documents", "/api/v1/announcements", "/api/v1/events",
        "/api/v1/surveys", "/api/v1/feedback", "/api/v1/assets",
        "/api/v1/positions", "/api/v1/tickets", "/api/v1/knowledge-base",
        "/api/v1/wellness", "/api/v1/forum", "/api/v1/audit",
        "/api/v1/modules", "/api/v1/organizations", "/api/v1/billing",
        "/api/v1/subscriptions", "/api/v1/onboarding", "/api/v1/shifts",
        "/api/v1/holidays", "/api/v1/payroll", "/api/v1/reports",
        "/api/v1/notifications", "/api/v1/settings", "/api/v1/custom-fields",
        "/api/v1/biometric", "/api/v1/device-management", "/api/v1/daily-check-in",
        "/api/v1/headcount", "/api/v1/org-chart", "/api/v1/invite",
        "/api/v1/dashboard", "/api/v1/dashboard/stats", "/api/v1/dashboard/headcount",
        "/api/v1/employees", "/api/v1/roles", "/api/v1/permissions",
        "/api/v1/teams", "/api/v1/projects", "/api/v1/tasks",
        "/api/v1/attendance/summary", "/api/v1/attendance/today",
        "/api/v1/attendance/list", "/api/v1/check-in", "/api/v1/checkin",
        "/api/v1/me", "/api/v1/profile", "/api/v1/organization",
    ]

    api_map = {}
    for ep in endpoints:
        code, body = api(ep, token=admin_token)
        if code == 429:
            time.sleep(30)
            code, body = api(ep, token=admin_token)
        if code == 200:
            structure = "?"
            if isinstance(body, dict):
                structure = f"keys={list(body.keys())[:8]}"
                # Show data shape
                d = body.get("data")
                if isinstance(d, list):
                    structure += f" data=[{len(d)} items]"
                elif isinstance(d, dict):
                    structure += f" data.keys={list(d.keys())[:6]}"
            elif isinstance(body, list):
                structure = f"array[{len(body)}]"
            api_map[ep] = structure
            print(f"  [200] {ep:50s} {structure}")
        elif code in (401, 403):
            print(f"  [{code}] {ep}")
        # Skip 404s silently
        time.sleep(0.2)

    print(f"\n  Live endpoints: {len(api_map)}")

    # =========================================================================
    # TEST 2: EMPLOYEE COUNT CONSISTENCY
    # =========================================================================
    print(f"\n{'='*60}")
    print("TEST 2: EMPLOYEE COUNT CONSISTENCY")
    print(f"{'='*60}")

    # Get all users with pagination
    users = get_all_pages("/api/v1/users", admin_token)
    print(f"  /api/v1/users: {len(users)} total users (all pages)")

    # Also check single page meta for total count
    code, body = api("/api/v1/users?page=1&limit=100", token=admin_token)
    meta = body.get("meta", {}) if isinstance(body, dict) else {}
    meta_total = meta.get("total") or meta.get("totalCount")
    if meta_total:
        print(f"  /api/v1/users meta.total: {meta_total}")
        if int(meta_total) != len(users):
            print(f"  [WARN] meta.total={meta_total} but fetched {len(users)} users")

    # Org data from login says current_user_count
    org_user_count = org_data.get("current_user_count") if org_data else None
    print(f"  Org.current_user_count (from login): {org_user_count}")

    if org_user_count and int(org_user_count) != len(users):
        mismatch = f"org.current_user_count={org_user_count} but /api/v1/users returns {len(users)} users"
        print(f"  [BUG] {mismatch}")
        record_bug(
            "Employee headcount mismatch between org data and users API",
            f"## Description\n"
            f"The organization's `current_user_count` field ({org_user_count}) does not match "
            f"the actual number of users returned by `/api/v1/users` ({len(users)}).\n\n"
            f"## Steps to Reproduce\n"
            f"1. Login as org admin -> response `data.org.current_user_count` = {org_user_count}\n"
            f"2. GET `/api/v1/users` -> returns {len(users)} user records\n\n"
            f"## Expected\nBoth counts should be identical.\n\n"
            f"## Environment\n- API: {API_BASE}\n- Org: {org_data.get('name')}\n- Date: {date.today()}"
        )
    else:
        print(f"  [INFO] org count vs users API comparison done")

    # Print first user to see field structure
    if users:
        print(f"\n  Sample user keys: {list(users[0].keys())}")
        print(f"  Sample user: {json.dumps(users[0], indent=2, default=str)[:600]}")

    # =========================================================================
    # TEST 3: DEPARTMENT CONSISTENCY
    # =========================================================================
    print(f"\n{'='*60}")
    print("TEST 3: DEPARTMENT CONSISTENCY")
    print(f"{'='*60}")

    # Collect all unique department_ids from users
    dept_ids_in_use = set()
    for u in users:
        did = u.get("department_id")
        if did is not None:
            dept_ids_in_use.add(did)
    print(f"  Unique department_ids referenced by users: {dept_ids_in_use}")

    # Try to get departments -- multiple patterns
    departments = {}
    for ep in ["/api/v1/departments", "/api/v1/department",
               "/api/v1/settings/departments", "/api/v1/organization/departments"]:
        code, body = api(ep, token=admin_token)
        if code == 200 and isinstance(body, dict):
            d = body.get("data", [])
            if isinstance(d, list) and d:
                for dept in d:
                    did = dept.get("id") or dept.get("_id")
                    if did:
                        departments[did] = dept.get("name", "unnamed")
                print(f"  {ep}: {len(departments)} departments found")
                break

    if not departments:
        print("  [WARN] No departments endpoint found -- checking if department is a string field")
        # Maybe department_id references a name or is embedded
        dept_field_types = set()
        for u in users:
            d = u.get("department_id")
            dept_field_types.add(type(d).__name__)
        print(f"  department_id field types: {dept_field_types}")

    # Check for null departments
    null_dept_users = []
    for u in users:
        did = u.get("department_id")
        uname = f"{u.get('first_name', '')} {u.get('last_name', '')} ({u.get('email', '')})"
        status = u.get("status")
        if did is None and status == 1:  # active user with no dept
            null_dept_users.append(uname)

    if null_dept_users:
        print(f"  [BUG] {len(null_dept_users)} active users have null department_id:")
        for u in null_dept_users:
            print(f"    - {u}")
        record_bug(
            f"{len(null_dept_users)} active employees have no department assigned",
            f"## Description\n"
            f"{len(null_dept_users)} active employees (status=1) have `department_id` set to null.\n\n"
            f"## Affected Users\n" + "\n".join(f"- {u}" for u in null_dept_users) + "\n\n"
            f"## Expected\nEvery active employee should have a valid department.\n\n"
            f"## Environment\n- API: {API_BASE}\n- Date: {date.today()}"
        )
    else:
        print(f"  [PASS] All active users have department_id set")

    # Check orphaned dept refs (if we have dept list)
    if departments:
        orphaned = []
        for u in users:
            did = u.get("department_id")
            if did and did not in departments:
                orphaned.append(f"{u.get('email')} -> dept_id={did}")
        if orphaned:
            print(f"  [BUG] {len(orphaned)} orphaned department references")
            record_bug(
                f"{len(orphaned)} employees reference non-existent departments",
                f"## Description\nThese employees have department_id values not found in departments list.\n\n"
                f"## Details\n" + "\n".join(f"- {o}" for o in orphaned[:20]) + "\n\n"
                f"## Environment\n- API: {API_BASE}\n- Date: {date.today()}"
            )

    # =========================================================================
    # TEST 4: REPORTING MANAGER CONSISTENCY
    # =========================================================================
    print(f"\n{'='*60}")
    print("TEST 4: REPORTING MANAGER CONSISTENCY")
    print(f"{'='*60}")

    user_ids = set()
    for u in users:
        uid = u.get("id")
        if uid:
            user_ids.add(uid)

    invalid_mgr = []
    null_mgr = []
    self_mgr = []
    valid_mgr = 0

    for u in users:
        uid = u.get("id")
        mgr_id = u.get("reporting_manager_id")
        uname = f"{u.get('first_name', '')} {u.get('last_name', '')} ({u.get('email', '')})"
        status = u.get("status")

        if mgr_id is None:
            null_mgr.append(uname)
        elif mgr_id == uid:
            self_mgr.append(uname)
        elif mgr_id not in user_ids:
            invalid_mgr.append(f"{uname} -> manager_id={mgr_id}")
        else:
            valid_mgr += 1

    print(f"  Valid manager refs: {valid_mgr}")
    print(f"  Null manager: {len(null_mgr)} -> {null_mgr}")
    print(f"  Self-referencing: {len(self_mgr)} -> {self_mgr}")
    print(f"  Invalid (orphaned): {len(invalid_mgr)} -> {invalid_mgr}")

    if invalid_mgr:
        record_bug(
            f"{len(invalid_mgr)} employees reference non-existent reporting managers",
            f"## Description\n"
            f"These employees have `reporting_manager_id` that does not match any user ID.\n\n"
            f"## Affected\n" + "\n".join(f"- {m}" for m in invalid_mgr) + "\n\n"
            f"## Valid user IDs\n{sorted(user_ids)}\n\n"
            f"## Environment\n- API: {API_BASE}\n- Date: {date.today()}"
        )

    if self_mgr:
        record_bug(
            f"{len(self_mgr)} employees are their own reporting manager",
            f"## Description\nCircular reference: employee's reporting_manager_id equals their own ID.\n\n"
            f"## Affected\n" + "\n".join(f"- {m}" for m in self_mgr) + "\n\n"
            f"## Environment\n- API: {API_BASE}\n- Date: {date.today()}"
        )

    # Check org chart
    for ep in ["/api/v1/org-chart", "/api/v1/orgchart"]:
        code, body = api(ep, token=admin_token)
        if code == 200:
            print(f"  Org chart data available at {ep}: {json.dumps(body, default=str)[:500]}")

    if not invalid_mgr and not self_mgr:
        print(f"  [PASS] All manager references are valid")

    # =========================================================================
    # TEST 5: LEAVE BALANCE CROSS-CHECK
    # =========================================================================
    print(f"\n{'='*60}")
    print("TEST 5: LEAVE BALANCE CROSS-CHECK")
    print(f"{'='*60}")

    # Get leave types
    code, body = api("/api/v1/leave/types", token=admin_token)
    leave_types = body.get("data", []) if isinstance(body, dict) else []
    print(f"  Leave types: {len(leave_types)}")
    for lt in leave_types:
        print(f"    - id={lt.get('id')} name={lt.get('name')} code={lt.get('code')}")

    # Get leave balances
    code, body = api("/api/v1/leave/balances", token=admin_token)
    leave_balances = body.get("data", []) if isinstance(body, dict) else []
    print(f"  Leave balances: {len(leave_balances)} records")
    if leave_balances:
        print(f"    Sample: {json.dumps(leave_balances[0], default=str)}")

    # Get ALL leave applications with pagination
    leave_apps = get_all_pages("/api/v1/leave/applications", admin_token)
    print(f"  Leave applications: {len(leave_apps)} total")
    if leave_apps:
        print(f"    Sample: {json.dumps(leave_apps[0], default=str)[:500]}")
        statuses = {}
        for app in leave_apps:
            s = app.get("status", "unknown")
            statuses[s] = statuses.get(s, 0) + 1
        print(f"    Status distribution: {statuses}")

    # Cross-check balances: total_allocated - total_used should = balance
    balance_issues = []
    for bal in leave_balances:
        total = bal.get("total_allocated", 0) or 0
        used = bal.get("total_used", 0) or 0
        carry = bal.get("total_carry_forward", 0) or 0
        remaining = bal.get("balance", 0) or 0

        try:
            total = float(total)
            used = float(used)
            carry = float(carry)
            remaining = float(remaining)
        except (ValueError, TypeError):
            continue

        expected = total + carry - used
        if abs(expected - remaining) > 0.01:
            balance_issues.append({
                "user_id": bal.get("user_id"),
                "leave_type_id": bal.get("leave_type_id"),
                "total_allocated": total,
                "carry_forward": carry,
                "total_used": used,
                "balance": remaining,
                "expected_balance": expected,
                "diff": round(expected - remaining, 2),
            })

    if balance_issues:
        print(f"  [BUG] {len(balance_issues)} balance arithmetic errors:")
        for bi in balance_issues:
            print(f"    user_id={bi['user_id']} type={bi['leave_type_id']}: "
                  f"alloc={bi['total_allocated']}+cf={bi['carry_forward']}-used={bi['total_used']}="
                  f"{bi['expected_balance']} but balance={bi['balance']} (diff={bi['diff']})")
        record_bug(
            f"Leave balance arithmetic error in {len(balance_issues)} records",
            f"## Description\n"
            f"`total_allocated + total_carry_forward - total_used != balance` for {len(balance_issues)} records.\n\n"
            f"## Details\n" + "\n".join(
                f"- user_id={bi['user_id']}, leave_type={bi['leave_type_id']}: "
                f"{bi['total_allocated']}+{bi['carry_forward']}-{bi['total_used']}="
                f"{bi['expected_balance']} but balance={bi['balance']}"
                for bi in balance_issues
            ) + "\n\n"
            f"## Expected\n`balance = total_allocated + total_carry_forward - total_used`\n\n"
            f"## Environment\n- API: {API_BASE}\n- Date: {date.today()}"
        )
    else:
        print(f"  [PASS] Leave balance arithmetic is correct")

    # Cross-check: total_used in balance vs sum of approved leave applications
    if leave_balances and leave_apps:
        # Sum approved days by (user_id, leave_type_id)
        approved_days = {}
        for app in leave_apps:
            if app.get("status") == "approved":
                key = (app.get("user_id"), app.get("leave_type_id"))
                days = float(app.get("days_count", 0) or 0)
                approved_days[key] = approved_days.get(key, 0) + days

        used_mismatch = []
        for bal in leave_balances:
            key = (bal.get("user_id"), bal.get("leave_type_id"))
            balance_used = float(bal.get("total_used", 0) or 0)
            app_used = approved_days.get(key, 0)
            if abs(balance_used - app_used) > 0.01:
                used_mismatch.append({
                    "user_id": key[0],
                    "leave_type_id": key[1],
                    "balance_total_used": balance_used,
                    "approved_app_days": app_used,
                    "diff": round(balance_used - app_used, 2),
                })

        if used_mismatch:
            print(f"  [BUG] {len(used_mismatch)} mismatches between balance.total_used and sum of approved applications:")
            for m in used_mismatch:
                print(f"    user={m['user_id']} type={m['leave_type_id']}: "
                      f"balance.total_used={m['balance_total_used']} vs approved_days={m['approved_app_days']} "
                      f"(diff={m['diff']})")
            record_bug(
                f"Leave used count mismatch: balance.total_used != sum of approved leaves ({len(used_mismatch)} records)",
                f"## Description\n"
                f"For {len(used_mismatch)} user-leave-type combinations, `total_used` in leave balance "
                f"does not match the sum of `days_count` from approved leave applications.\n\n"
                f"## Details\n" + "\n".join(
                    f"- user_id={m['user_id']}, leave_type={m['leave_type_id']}: "
                    f"balance says used={m['balance_total_used']}, approved apps sum={m['approved_app_days']}"
                    for m in used_mismatch
                ) + "\n\n"
                f"## Expected\n`leave_balance.total_used` should equal sum of approved leave applications' `days_count`\n\n"
                f"## Environment\n- API: {API_BASE}\n- Date: {date.today()}"
            )
        else:
            print(f"  [PASS] Leave used counts match approved applications")

    # =========================================================================
    # TEST 6: DATA INTEGRITY CHECKS
    # =========================================================================
    print(f"\n{'='*60}")
    print("TEST 6: DATA INTEGRITY CHECKS")
    print(f"{'='*60}")

    # Get locations for reference validation
    locations = {}
    code, body = api("/api/v1/locations", token=admin_token)
    if code == 200 and isinstance(body, dict):
        for loc in (body.get("data", []) if isinstance(body.get("data"), list) else []):
            lid = loc.get("id")
            if lid:
                locations[lid] = loc.get("name", "?")
        print(f"  Locations: {len(locations)}")

    # Get designations
    designations = {}
    code, body = api("/api/v1/designations", token=admin_token)
    if code == 200 and isinstance(body, dict):
        for des in (body.get("data", []) if isinstance(body.get("data"), list) else []):
            did = des.get("id")
            if did:
                designations[did] = des.get("name", "?")
        print(f"  Designations: {len(designations)}")

    today_d = date.today()
    missing_email = []
    missing_name = []
    future_join = []
    exit_before_join = []
    orphaned_loc = []
    orphaned_des = []
    inactive_with_issues = []

    for u in users:
        uid = u.get("id")
        email = u.get("email", "")
        fname = u.get("first_name", "")
        lname = u.get("last_name", "")
        label = email or f"id={uid}"
        status = u.get("status")

        # Missing required fields
        if not email or not email.strip():
            missing_email.append(f"id={uid} first_name={fname}")
        if not fname or not fname.strip():
            missing_name.append(label)

        # Date checks
        def parse_date(ds):
            if not ds:
                return None
            for fmt in ["%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"]:
                try:
                    return datetime.strptime(str(ds)[:26], fmt).date()
                except ValueError:
                    continue
            return None

        join_dt = parse_date(u.get("date_of_joining"))
        exit_dt = parse_date(u.get("date_of_exit"))

        if join_dt and join_dt > today_d:
            future_join.append(f"{label} joined {join_dt}")

        if join_dt and exit_dt and exit_dt < join_dt:
            exit_before_join.append(f"{label} joined={join_dt} exited={exit_dt}")

        # Location reference
        loc_id = u.get("location_id")
        if loc_id and locations and loc_id not in locations:
            orphaned_loc.append(f"{label} -> location_id={loc_id}")

        # Designation field (it's a string in this API, not an ID)
        des = u.get("designation")
        # designation is a string field here, not an FK -- skip orphan check

    print(f"\n  --- Field Completeness ---")
    print(f"  Missing email: {len(missing_email)}")
    print(f"  Missing first_name: {len(missing_name)}")

    print(f"\n  --- Date Consistency ---")
    print(f"  Future join dates: {len(future_join)}")
    for f in future_join:
        print(f"    - {f}")
    print(f"  Exit before join: {len(exit_before_join)}")
    for e in exit_before_join:
        print(f"    - {e}")

    print(f"\n  --- Reference Integrity ---")
    print(f"  Orphaned location refs: {len(orphaned_loc)}")
    for o in orphaned_loc:
        print(f"    - {o}")

    # File bugs
    if missing_email:
        record_bug(
            f"{len(missing_email)} users have missing email",
            f"## Description\nUsers with null/empty email:\n" + "\n".join(f"- {e}" for e in missing_email) +
            f"\n\n## Environment\n- API: {API_BASE}\n- Date: {date.today()}"
        )

    if missing_name:
        record_bug(
            f"{len(missing_name)} users have missing first_name",
            f"## Description\nUsers with null/empty first_name:\n" + "\n".join(f"- {n}" for n in missing_name) +
            f"\n\n## Environment\n- API: {API_BASE}\n- Date: {date.today()}"
        )

    if future_join:
        record_bug(
            f"{len(future_join)} employees have joining date in the future",
            f"## Description\nEmployees with date_of_joining after today ({today_d}):\n" +
            "\n".join(f"- {f}" for f in future_join) +
            f"\n\n## Expected\nActive employees should not have future join dates.\n\n"
            f"## Environment\n- API: {API_BASE}\n- Date: {date.today()}"
        )

    if exit_before_join:
        record_bug(
            f"{len(exit_before_join)} employees have exit date before join date",
            f"## Description\n" + "\n".join(f"- {e}" for e in exit_before_join) +
            f"\n\n## Expected\nExit date must be after join date.\n\n"
            f"## Environment\n- API: {API_BASE}\n- Date: {date.today()}"
        )

    if orphaned_loc:
        record_bug(
            f"{len(orphaned_loc)} employees reference non-existent locations",
            f"## Description\n" + "\n".join(f"- {o}" for o in orphaned_loc) +
            f"\n\n## Available locations: {locations}\n\n"
            f"## Environment\n- API: {API_BASE}\n- Date: {date.today()}"
        )

    # Check: location_id is null for how many active users?
    null_loc = [u.get("email") for u in users if u.get("location_id") is None and u.get("status") == 1]
    if null_loc:
        print(f"\n  [INFO] {len(null_loc)} active users have null location_id: {null_loc}")
        if len(null_loc) == len([u for u in users if u.get("status") == 1]):
            print(f"  [NOTE] ALL active users have null location -- likely not configured")
        else:
            record_bug(
                f"{len(null_loc)} active employees have no location assigned",
                f"## Description\n{len(null_loc)} active users have null `location_id`.\n\n"
                f"## Affected\n" + "\n".join(f"- {e}" for e in null_loc) +
                f"\n\n## Environment\n- API: {API_BASE}\n- Date: {date.today()}"
            )

    # =========================================================================
    # EMPLOYEE vs EMPLOYEE VISIBILITY CHECK
    # =========================================================================
    print(f"\n{'='*60}")
    print("TEST 7: CROSS-ROLE DATA VISIBILITY")
    print(f"{'='*60}")
    if emp_token:
        code, body = api("/api/v1/users", token=emp_token)
        if code == 200 and isinstance(body, dict):
            emp_users = body.get("data", [])
            print(f"  Employee sees {len(emp_users)} users (admin sees {len(users)})")
            if len(emp_users) != len(users):
                print(f"  [INFO] Different visibility is expected (RBAC)")
        elif code in (401, 403):
            print(f"  [INFO] Employee cannot access /api/v1/users ({code}) -- proper RBAC")
        else:
            print(f"  [{code}] Employee /api/v1/users response")

        # Employee leave balance
        code, body = api("/api/v1/leave/balances", token=emp_token)
        if code == 200 and isinstance(body, dict):
            emp_bal = body.get("data", [])
            print(f"  Employee sees {len(emp_bal)} leave balances")
            if emp_bal:
                print(f"    Sample: {json.dumps(emp_bal[0], default=str)[:300]}")

    # =========================================================================
    # SUMMARY
    # =========================================================================
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"  Total bugs found: {len(BUGS)}")
    for i, bug in enumerate(BUGS, 1):
        print(f"    {i}. {bug['title']}")

    file_github_issues()

    print(f"\n{'='*60}")
    print("ALL TESTS COMPLETE")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
