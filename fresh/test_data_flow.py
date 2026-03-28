"""
Cross-module data flow and consistency tests for EmpCloud HRMS.
Verifies data integrity across users, leave, attendance, announcements,
documents, departments, and organization modules.
"""

import requests
import json
import sys
import time
from datetime import datetime, timedelta
from decimal import Decimal

BASE = "https://test-empcloud-api.empcloud.com/api/v1"

# ---------- helpers ----------

class Stats:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.skipped = 0
        self.bugs = []

    def record(self, name, passed, detail=""):
        if passed:
            self.passed += 1
            print(f"  PASS  {name}")
        else:
            self.failed += 1
            print(f"  FAIL  {name}")
            if detail:
                print(f"        -> {detail}")
            self.bugs.append((name, detail))

    def skip(self, name, reason=""):
        self.skipped += 1
        print(f"  SKIP  {name} ({reason})")

    def summary(self):
        total = self.passed + self.failed + self.skipped
        print("\n" + "=" * 70)
        print(f"TOTAL: {total}  |  PASS: {self.passed}  |  FAIL: {self.failed}  |  SKIP: {self.skipped}")
        if self.bugs:
            print("\nBUGS FOUND:")
            for i, (name, detail) in enumerate(self.bugs, 1):
                print(f"  {i}. {name}")
                if detail:
                    print(f"     {detail}")
        print("=" * 70)
        return self.failed

stats = Stats()


def login(email, password):
    r = requests.post(f"{BASE}/auth/login", json={
        "email": email, "password": password
    }, timeout=15)
    data = r.json()
    assert data.get("success"), f"Login failed for {email}: {data}"
    return data["data"]["tokens"]["access_token"], data["data"]


def api(method, path, token, **kwargs):
    headers = {"Authorization": f"Bearer {token}"}
    kwargs.setdefault("timeout", 15)
    r = requests.request(method, f"{BASE}/{path}", headers=headers, **kwargs)
    return r.json()


def get(path, token, **kwargs):
    return api("GET", path, token, **kwargs)


def post(path, token, **kwargs):
    return api("POST", path, token, **kwargs)


def get_all_pages(path, token, max_pages=20):
    """Fetch all pages of a paginated endpoint."""
    all_items = []
    for page in range(1, max_pages + 1):
        sep = "&" if "?" in path else "?"
        resp = get(f"{path}{sep}page={page}&limit=100", token)
        if not resp.get("success"):
            break
        items = resp.get("data", [])
        if not items:
            break
        all_items.extend(items)
        meta = resp.get("meta", {})
        if page >= meta.get("total_pages", 1):
            break
    return all_items


# =====================================================================
# TESTS
# =====================================================================

def test_01_employee_visibility_across_modules(admin_token, admin_data):
    """Flow 1: Employee in /users -> visible in leave balances, announcements."""
    print("\n--- TEST 1: Employee cross-module visibility ---")

    # Pick a known employee: Priya (id=524)
    priya_id = 524

    # 1a. Verify Priya exists in /users
    resp = get(f"users/{priya_id}", admin_token)
    user_exists = resp.get("success") and resp["data"]["id"] == priya_id
    stats.record(
        "Priya (id=524) exists in /users",
        user_exists,
        "" if user_exists else f"Got: {resp}"
    )

    if not user_exists:
        return

    user = resp["data"]

    # 1b. Priya has leave balances
    resp = get(f"leave/balances?user_id={priya_id}", admin_token)
    has_balances = resp.get("success") and len(resp.get("data", [])) > 0
    stats.record(
        "Priya has leave balances",
        has_balances,
        "" if has_balances else "No leave balances found for user 524"
    )

    # 1c. Priya appears in leave applications
    all_apps = get_all_pages("leave/applications", admin_token)
    priya_apps = [a for a in all_apps if a["user_id"] == priya_id]
    stats.record(
        "Priya appears in leave applications",
        len(priya_apps) > 0,
        f"Found {len(priya_apps)} applications" if priya_apps else "No leave applications found"
    )

    # 1d. Priya can see announcements (target_type=all)
    emp_token, _ = login("priya@technova.in", "Welcome@123")
    resp = get("announcements", emp_token)
    can_see = resp.get("success") and len(resp.get("data", [])) > 0
    stats.record(
        "Priya (employee) can see announcements",
        can_see,
        "" if can_see else f"Got: {resp}"
    )


def test_02_leave_balance_math(admin_token):
    """Flow 6: Leave balance math: allocated + carry_forward - used = balance."""
    print("\n--- TEST 2: Leave balance math (allocated + carry_forward - used = balance) ---")

    # Get all balances visible to admin (admin's own)
    resp = get("leave/balances", admin_token)
    assert resp.get("success"), f"Failed to get leave balances: {resp}"
    balances = resp["data"]

    all_correct = True
    for bal in balances:
        allocated = Decimal(str(bal["total_allocated"]))
        used = Decimal(str(bal["total_used"]))
        carry = Decimal(str(bal["total_carry_forward"]))
        actual_balance = Decimal(str(bal["balance"]))
        expected = allocated + carry - used

        name = bal.get("leave_type_name", f"type_{bal['leave_type_id']}")
        correct = actual_balance == expected
        if not correct:
            all_correct = False
        stats.record(
            f"Balance math for {name} (user {bal['user_id']}): "
            f"{allocated}+{carry}-{used}={expected}",
            correct,
            f"Expected {expected}, got {actual_balance}" if not correct else ""
        )

    # Also check Priya's balances
    resp = get("leave/balances?user_id=524", admin_token)
    if resp.get("success"):
        for bal in resp["data"]:
            allocated = Decimal(str(bal["total_allocated"]))
            used = Decimal(str(bal["total_used"]))
            carry = Decimal(str(bal["total_carry_forward"]))
            actual_balance = Decimal(str(bal["balance"]))
            expected = allocated + carry - used

            name = bal.get("leave_type_name", f"type_{bal['leave_type_id']}")
            correct = actual_balance == expected
            stats.record(
                f"Balance math for Priya - {name}: "
                f"{allocated}+{carry}-{used}={expected}",
                correct,
                f"Expected {expected}, got {actual_balance}" if not correct else ""
            )


def test_03_leave_approved_balance_deducted(admin_token):
    """Flow 2: Leave approved -> balance deducted.
    Verify that approved leave days are reflected in total_used."""
    print("\n--- TEST 3: Leave approved -> balance correctly deducted ---")

    # Get Priya's leave applications and balances
    all_apps = get_all_pages("leave/applications", admin_token)
    priya_apps = [a for a in all_apps if a["user_id"] == 524]

    resp = get("leave/balances?user_id=524", admin_token)
    assert resp.get("success"), f"Failed to get Priya balances: {resp}"
    balances = {b["leave_type_id"]: b for b in resp["data"]}

    # Sum approved days per leave type
    approved_days = {}
    for app in priya_apps:
        if app["status"] == "approved":
            lt = app["leave_type_id"]
            days = Decimal(str(app["days_count"]))
            approved_days[lt] = approved_days.get(lt, Decimal("0")) + days

    for lt_id, total_approved in approved_days.items():
        if lt_id in balances:
            bal = balances[lt_id]
            used = Decimal(str(bal["total_used"]))
            lt_name = bal.get("leave_type_name", f"type_{lt_id}")
            # used should be >= approved (could be more if some apps cancelled after counting)
            match = used >= total_approved
            stats.record(
                f"Priya {lt_name}: approved_days={total_approved}, total_used={used}",
                match,
                f"total_used ({used}) < sum of approved days ({total_approved})" if not match else ""
            )


def test_04_employee_count_consistency(admin_token, admin_data):
    """Flow 5: Employee count: /users total vs org.current_user_count."""
    print("\n--- TEST 4: Employee count consistency across sources ---")

    # Source 1: /users pagination meta.total
    resp = get("users?page=1&limit=1", admin_token)
    assert resp.get("success"), f"Users endpoint failed: {resp}"
    users_total = resp["meta"]["total"]

    # Source 2: org.current_user_count from login data
    org_user_count = admin_data["org"]["current_user_count"]

    # Compare
    stats.record(
        f"Users endpoint total ({users_total}) vs org.current_user_count ({org_user_count})",
        users_total == org_user_count,
        f"/users total={users_total}, org.current_user_count={org_user_count} -- MISMATCH"
        if users_total != org_user_count else ""
    )

    # Also verify by fetching all users and counting
    all_users = get_all_pages("users", admin_token)
    actual_count = len(all_users)
    stats.record(
        f"Fetched all users count ({actual_count}) matches meta.total ({users_total})",
        actual_count == users_total,
        f"Fetched {actual_count} users but meta says {users_total}"
        if actual_count != users_total else ""
    )

    # Active users (status=1) count
    active_users = [u for u in all_users if u.get("status") == 1]
    stats.record(
        f"Active users ({len(active_users)}) vs org.current_user_count ({org_user_count})",
        len(active_users) == org_user_count,
        f"Active users={len(active_users)}, org.current_user_count={org_user_count}"
        if len(active_users) != org_user_count else ""
    )

    return all_users


def test_05_department_counts_consistent(admin_token, all_users):
    """Flow 4: Department counts consistent across modules."""
    print("\n--- TEST 5: Department distribution consistency ---")

    # Count users per department from /users data
    dept_counts = {}
    for u in all_users:
        dept_id = u.get("department_id")
        if dept_id:
            dept_counts[dept_id] = dept_counts.get(dept_id, 0) + 1

    # Each user with a department_id should be a valid department
    # Check a few specific users
    users_with_dept = [u for u in all_users if u.get("department_id")]
    users_without_dept = [u for u in all_users if not u.get("department_id")]

    stats.record(
        f"Users with department assigned: {len(users_with_dept)}/{len(all_users)}",
        len(users_with_dept) > 0,
        "No users have department_id set" if not users_with_dept else ""
    )

    # Verify no orphan department references (department_id should be consistent)
    dept_ids = set(dept_counts.keys())
    stats.record(
        f"Found {len(dept_ids)} unique departments across users",
        len(dept_ids) > 0,
        ""
    )

    # Verify Priya and Ananya are in the same department (both dept_id=20)
    priya = next((u for u in all_users if u["id"] == 524), None)
    ananya = next((u for u in all_users if u["id"] == 522), None)
    if priya and ananya:
        same_dept = priya["department_id"] == ananya["department_id"]
        stats.record(
            f"Priya (dept={priya['department_id']}) and Ananya (dept={ananya['department_id']}) in same dept",
            same_dept,
            "Department mismatch" if not same_dept else ""
        )

    # Verify reporting_manager_id references valid user IDs
    # Note: managers may be inactive (status=0) but still exist in DB
    user_ids = {u["id"] for u in all_users}
    orphan_managers = []
    inactive_managers = []
    for u in all_users:
        mgr = u.get("reporting_manager_id")
        if mgr and mgr not in user_ids:
            # Check if the manager exists but is inactive
            mgr_resp = get(f"users/{mgr}", admin_token)
            if mgr_resp.get("success"):
                mgr_data = mgr_resp["data"]
                if mgr_data.get("status") == 0 or mgr_data.get("date_of_exit"):
                    inactive_managers.append(
                        (u["id"], u.get("email"), mgr,
                         f"{mgr_data['first_name']} {mgr_data['last_name']} (exited)"))
                else:
                    orphan_managers.append((u["id"], u.get("email"), mgr))
            else:
                orphan_managers.append((u["id"], u.get("email"), mgr))

    stats.record(
        "No reporting_manager_id points to truly non-existent users",
        len(orphan_managers) == 0,
        f"Orphan manager refs: {orphan_managers[:5]}" if orphan_managers else ""
    )

    if inactive_managers:
        stats.record(
            "BUG: Active employees report to exited/inactive managers",
            False,
            f"{len(inactive_managers)} employees reference exited managers, "
            f"e.g. {inactive_managers[0]}"
        )


def test_06_announcement_created_visible_to_employee(admin_token):
    """Flow 7: Announcement created -> visible to employee."""
    print("\n--- TEST 6: Announcement creation -> employee visibility ---")

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    title = f"DataFlow Test Announcement {timestamp}"
    content = "This announcement tests cross-module data flow visibility."

    # Admin creates announcement (valid priorities: low, normal, high, urgent)
    resp = post("announcements", admin_token, json={
        "title": title,
        "content": content,
    })

    created = resp.get("success", False)
    stats.record(
        "Admin can create announcement",
        created,
        f"Failed: {resp}" if not created else ""
    )

    if not created:
        return

    announcement_id = resp["data"]["id"]

    # Employee (Priya) should see it -- search all pages
    emp_token, _ = login("priya@technova.in", "Welcome@123")
    all_announcements = get_all_pages("announcements", emp_token)
    found = any(a["id"] == announcement_id for a in all_announcements)
    stats.record(
        f"Employee sees newly created announcement (id={announcement_id}) "
        f"among {len(all_announcements)} total",
        found,
        "Announcement not visible to employee across all pages" if not found else ""
    )

    # Cleanup: we don't delete to avoid side effects, just note
    return announcement_id


def test_07_document_upload_visible_in_profile(admin_token):
    """Flow 8: Document uploaded -> visible in employee profile."""
    print("\n--- TEST 7: Document upload -> visible in profile ---")

    # Get document categories first
    resp = get("documents/categories", admin_token)
    if not resp.get("success") or not resp["data"]:
        stats.skip("Document upload test", "No document categories available")
        return

    category_id = resp["data"][0]["id"]
    category_name = resp["data"][0]["name"]

    # Upload a document for user 524 (Priya) via /documents/upload
    import io

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    doc_name = f"DataFlow Test Doc {timestamp}"

    fake_pdf = io.BytesIO(b"%PDF-1.4 fake test content for data flow test")

    resp = post("documents/upload", admin_token, data={
        "user_id": "524",
        "category_id": str(category_id),
        "name": doc_name
    }, files={
        "file": ("dataflow_test.pdf", fake_pdf, "application/pdf")
    })

    uploaded = resp.get("success", False)
    stats.record(
        f"Upload document for Priya (category={category_name})",
        uploaded,
        f"Failed: {resp}" if not uploaded else ""
    )

    if not uploaded:
        return

    doc_id = resp["data"]["id"]

    # Verify visible in documents list for that user
    resp = get("documents?user_id=524", admin_token)
    if resp.get("success"):
        found = any(d["id"] == doc_id for d in resp.get("data", []))
        stats.record(
            f"Uploaded document (id={doc_id}) visible in Priya's documents",
            found,
            "Document not found in user's document list" if not found else ""
        )
    else:
        stats.record(
            "Can query documents for user",
            False,
            f"Failed: {resp}"
        )

    # Also check from employee perspective
    emp_token, _ = login("priya@technova.in", "Welcome@123")
    resp = get("documents", emp_token)
    if resp.get("success"):
        found = any(d["id"] == doc_id for d in resp.get("data", []))
        stats.record(
            f"Priya (employee) sees her own uploaded document (id={doc_id})",
            found,
            "Document not visible to employee" if not found else ""
        )
    else:
        stats.record(
            "Employee can access own documents",
            False,
            f"Failed: {resp}"
        )


def test_08_leave_types_consistent(admin_token):
    """Leave types in /leave/types match those referenced in balances."""
    print("\n--- TEST 8: Leave types consistency ---")

    resp = get("leave/types", admin_token)
    assert resp.get("success"), f"Failed to get leave types: {resp}"
    leave_types = {lt["id"]: lt for lt in resp["data"]}

    # Get balances and check references
    resp = get("leave/balances", admin_token)
    assert resp.get("success"), f"Failed to get balances: {resp}"

    for bal in resp["data"]:
        lt_id = bal["leave_type_id"]
        lt_name_in_bal = bal.get("leave_type_name", "")
        if lt_id in leave_types:
            lt_name_in_types = leave_types[lt_id]["name"]
            match = lt_name_in_bal == lt_name_in_types
            stats.record(
                f"Leave type name consistent: balance says '{lt_name_in_bal}', "
                f"types says '{lt_name_in_types}'",
                match,
                f"Name mismatch for type {lt_id}" if not match else ""
            )
        else:
            stats.record(
                f"Leave type {lt_id} in balances exists in /leave/types",
                False,
                f"Type {lt_id} ({lt_name_in_bal}) not found in leave types list"
            )


def test_09_user_self_data_matches_admin_view(admin_token):
    """Employee's own profile data matches what admin sees."""
    print("\n--- TEST 9: Self-service data matches admin view ---")

    # Admin view of Priya
    resp = get("users/524", admin_token)
    assert resp.get("success"), f"Failed: {resp}"
    admin_view = resp["data"]

    # Employee view
    emp_token, emp_data = login("priya@technova.in", "Welcome@123")
    emp_view = emp_data["user"]

    # Compare key fields
    for field in ["id", "email", "first_name", "last_name", "department_id",
                  "designation", "employment_type", "role", "emp_code"]:
        admin_val = admin_view.get(field)
        emp_val = emp_view.get(field)
        stats.record(
            f"Priya self-view matches admin for '{field}': {emp_val}",
            admin_val == emp_val,
            f"Admin sees {field}={admin_val}, employee sees {field}={emp_val}"
            if admin_val != emp_val else ""
        )


def test_10_leave_balances_per_user_from_admin(admin_token, all_users):
    """Spot-check: multiple users have leave balances if they are active."""
    print("\n--- TEST 10: Spot-check leave balances for multiple users ---")

    # Pick up to 5 original active employees (with emp_code, excluding admin)
    candidates = [u for u in all_users
                  if u.get("status") == 1 and u.get("department_id")
                  and u.get("emp_code")
                  and u["id"] not in (522,)]
    # Sort by ID to get the original seed employees first
    candidates.sort(key=lambda u: u["id"])
    candidates = candidates[:5]

    for user in candidates:
        uid = user["id"]
        name = f"{user['first_name']} {user['last_name']}"
        resp = get(f"leave/balances?user_id={uid}", admin_token)
        has_bal = resp.get("success") and len(resp.get("data", [])) > 0
        stats.record(
            f"User {name} (id={uid}) has leave balances",
            has_bal,
            f"No balances for active user {uid}" if not has_bal else ""
        )

        # Verify math on each
        if has_bal:
            for bal in resp["data"]:
                allocated = Decimal(str(bal["total_allocated"]))
                used = Decimal(str(bal["total_used"]))
                carry = Decimal(str(bal["total_carry_forward"]))
                actual = Decimal(str(bal["balance"]))
                expected = allocated + carry - used
                if actual != expected:
                    stats.record(
                        f"  Balance math for {name} - {bal['leave_type_name']}",
                        False,
                        f"Expected {expected}, got {actual}"
                    )


def test_11_cross_role_data_isolation(admin_token):
    """Employee should not see other employees' leave or documents."""
    print("\n--- TEST 11: Cross-role data isolation ---")

    emp_token, _ = login("priya@technova.in", "Welcome@123")

    # Employee should only see own leave balances
    resp = get("leave/balances", emp_token)
    if resp.get("success"):
        user_ids = set(b["user_id"] for b in resp["data"])
        only_own = user_ids == {524} or len(user_ids) == 0
        stats.record(
            "Employee leave balances only show own data",
            only_own,
            f"Saw balances for user_ids: {user_ids}" if not only_own else ""
        )

    # Employee should only see own documents
    resp = get("documents", emp_token)
    if resp.get("success"):
        doc_user_ids = set(d.get("user_id") for d in resp.get("data", []))
        only_own_docs = doc_user_ids <= {524}  # subset of {524} or empty
        stats.record(
            "Employee documents only show own data",
            only_own_docs,
            f"Saw docs for user_ids: {doc_user_ids}" if not only_own_docs else ""
        )


def test_12_org_data_consistency_across_logins():
    """Org data from different user logins should be consistent."""
    print("\n--- TEST 12: Org data consistent across different logins ---")

    _, admin_data = login("ananya@technova.in", "Welcome@123")
    _, emp_data = login("priya@technova.in", "Welcome@123")

    admin_org = admin_data["org"]
    emp_org = emp_data["org"]

    for field in ["id", "name", "legal_name", "email", "timezone",
                  "current_user_count", "is_active"]:
        a_val = admin_org.get(field)
        e_val = emp_org.get(field)
        stats.record(
            f"Org.{field} consistent: admin={a_val}, emp={e_val}",
            a_val == e_val,
            f"Mismatch: admin={a_val}, employee={e_val}" if a_val != e_val else ""
        )


# =====================================================================
# MAIN
# =====================================================================

def main():
    print("=" * 70)
    print("EmpCloud Cross-Module Data Flow & Consistency Tests")
    print(f"Target: {BASE}")
    print(f"Time:   {datetime.now().isoformat()}")
    print("=" * 70)

    # Login
    print("\n--- Authentication ---")
    try:
        admin_token, admin_data = login("ananya@technova.in", "Welcome@123")
        print(f"  Logged in as Org Admin: {admin_data['user']['email']}")
    except Exception as e:
        print(f"  FATAL: Admin login failed: {e}")
        sys.exit(1)

    # Run tests
    test_01_employee_visibility_across_modules(admin_token, admin_data)
    test_02_leave_balance_math(admin_token)
    test_03_leave_approved_balance_deducted(admin_token)
    all_users = test_04_employee_count_consistency(admin_token, admin_data)
    test_05_department_counts_consistent(admin_token, all_users)
    test_06_announcement_created_visible_to_employee(admin_token)
    test_07_document_upload_visible_in_profile(admin_token)
    test_08_leave_types_consistent(admin_token)
    test_09_user_self_data_matches_admin_view(admin_token)
    test_10_leave_balances_per_user_from_admin(admin_token, all_users)
    test_11_cross_role_data_isolation(admin_token)
    test_12_org_data_consistency_across_logins()

    # Summary
    failures = stats.summary()
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
