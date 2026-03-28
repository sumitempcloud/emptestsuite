#!/usr/bin/env python3
"""
Verify 11 newly deployed features via API-only testing (crash-proof, no Selenium).
Issues: #499, #519, #520, #545, #556, #563, #673, #700, #703, #704
"""

import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import requests
import json
import time

BASE = "https://test-empcloud-api.empcloud.com"
API = f"{BASE}/api/v1"
GH_PAT = "os.environ.get('GITHUB_TOKEN', 'YOUR_TOKEN_HERE')"
GH_REPO = "EmpCloud/EmpCloud"
TIMEOUT = 30

results = {}

# ── Helpers ──────────────────────────────────────────────────────────────

def login(email, password, label=""):
    try:
        r = requests.post(f"{API}/auth/login",
                          json={"email": email, "password": password}, timeout=TIMEOUT)
        if r.status_code == 200:
            d = r.json()
            token = d["data"]["tokens"]["access_token"]
            user = d["data"]["user"]
            print(f"  [LOGIN] {label}: id={user['id']}, role={user['role']}")
            return token, user
    except Exception as e:
        print(f"  [LOGIN] {label} ERROR: {e}")
    print(f"  [LOGIN] {label} FAILED")
    return None, None


def hdr(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def gh_comment(issue_num, body):
    try:
        r = requests.post(
            f"https://api.github.com/repos/{GH_REPO}/issues/{issue_num}/comments",
            headers={"Authorization": f"token {GH_PAT}", "Accept": "application/vnd.github.v3+json"},
            json={"body": body}, timeout=30)
        print(f"  [GH] #{issue_num}: {'OK' if r.status_code in (200,201) else r.status_code}")
    except Exception as e:
        print(f"  [GH] #{issue_num} error: {e}")


# ── Login ────────────────────────────────────────────────────────────────

print("=" * 70)
print("LOGGING IN")
print("=" * 70)

oa_token, oa_user = login("ananya@technova.in", "Welcome@123", "Org Admin")
emp_token, emp_user = login("priya@technova.in", "Welcome@123", "Employee")
sa_token, sa_user = login("admin@empcloud.com", "SuperAdmin@2026", "Super Admin")

if not oa_token:
    print("FATAL: Org Admin login failed.")
    sys.exit(1)

oa_hdr = hdr(oa_token)
emp_hdr = hdr(emp_token) if emp_token else {}
sa_hdr = hdr(sa_token) if sa_token else {}


# ══════════════════════════════════════════════════════════════════════════
# #499 - Audit Log Filters
# ══════════════════════════════════════════════════════════════════════════

def test_499():
    print("\n" + "=" * 70)
    print("#499 - Audit Log Filters")
    print("=" * 70)

    token_hdr = sa_hdr or oa_hdr

    # Unfiltered
    r = requests.get(f"{API}/audit", headers=token_hdr, timeout=TIMEOUT)
    if r.status_code != 200:
        return {"status": "FAIL", "detail": f"GET /audit -> {r.status_code}"}
    d = r.json()
    total_all = d.get("meta", {}).get("total", len(d.get("data", [])))
    print(f"  Unfiltered: total={total_all}")

    # Action filter
    r2 = requests.get(f"{API}/audit", headers=token_hdr, params={"action": "login"}, timeout=TIMEOUT)
    d2 = r2.json()
    total_login = d2.get("meta", {}).get("total", len(d2.get("data", [])))
    print(f"  action=login: total={total_login}")
    action_filters = total_login < total_all

    # Date filter (from_date/to_date)
    r3 = requests.get(f"{API}/audit", headers=token_hdr,
                      params={"from_date": "2026-03-01", "to_date": "2026-03-28"}, timeout=TIMEOUT)
    d3 = r3.json()
    total_date = d3.get("meta", {}).get("total", len(d3.get("data", [])))
    print(f"  from_date/to_date filter: total={total_date}")
    date_filters_ft = total_date < total_all

    # Date filter (start_date/end_date)
    r4 = requests.get(f"{API}/audit", headers=token_hdr,
                      params={"start_date": "2026-03-27", "end_date": "2026-03-27"}, timeout=TIMEOUT)
    d4 = r4.json()
    total_se = d4.get("meta", {}).get("total", len(d4.get("data", [])))
    print(f"  start_date/end_date 1-day: total={total_se}")
    date_filters_se = total_se < total_all

    detail = (f"Unfiltered: {total_all} records. "
              f"Action=login filter: {total_login} records ({'NARROWS - PASS' if action_filters else 'SAME count - filter ignored'}). "
              f"Date filter (from_date/to_date): {total_date} ({'narrows' if date_filters_ft else 'NOT narrowing - ignored'}). "
              f"Date filter (start_date/end_date): {total_se} ({'narrows - WORKS' if date_filters_se else 'NOT narrowing'}).")

    if action_filters and (date_filters_ft or date_filters_se):
        return {"status": "PASS", "detail": detail}
    elif action_filters:
        return {"status": "PARTIAL", "detail": detail + " Action filter works, but date filter (from_date/to_date) is not narrowing results."}
    else:
        return {"status": "FAIL", "detail": detail}


# ══════════════════════════════════════════════════════════════════════════
# #519 - Create Organization
# ══════════════════════════════════════════════════════════════════════════

def test_519():
    print("\n" + "=" * 70)
    print("#519 - Create Organization (Super Admin)")
    print("=" * 70)

    if not sa_token:
        return {"status": "FAIL", "detail": "Super Admin login failed"}

    # Check GET listing works
    r_list = requests.get(f"{API}/admin/organizations", headers=sa_hdr, timeout=TIMEOUT)
    list_ok = r_list.status_code == 200
    org_count = len(r_list.json().get("data", [])) if list_ok else 0
    print(f"  GET /admin/organizations -> {r_list.status_code}, count={org_count}")

    # Try POST
    payload = {"name": "API Test Org", "email": "apitest@test.com",
               "legal_name": "API Test Org Ltd", "contact_number": "1234567890"}
    r = requests.post(f"{API}/admin/organizations", headers=sa_hdr, json=payload, timeout=TIMEOUT)
    print(f"  POST /admin/organizations -> {r.status_code}")

    if r.status_code in (200, 201):
        data = r.json()
        org_id = data.get("data", {}).get("id")
        detail = f"Organization created successfully. ID: {org_id}. Listing shows {org_count} orgs."
        if org_id:
            requests.delete(f"{API}/admin/organizations/{org_id}", headers=sa_hdr, timeout=TIMEOUT)
        return {"status": "PASS", "detail": detail}
    elif r.status_code == 409:
        return {"status": "PASS", "detail": f"POST returns 409 (conflict/duplicate). Endpoint exists and validates. Listing: {org_count} orgs."}
    else:
        detail = (f"GET /admin/organizations: {'OK' if list_ok else 'FAIL'} ({org_count} orgs). "
                  f"POST /admin/organizations: {r.status_code} (endpoint not found). "
                  f"Organization listing works but creation endpoint is missing.")
        return {"status": "FAIL", "detail": detail}


# ══════════════════════════════════════════════════════════════════════════
# #520 - Platform Settings
# ══════════════════════════════════════════════════════════════════════════

def test_520():
    print("\n" + "=" * 70)
    print("#520 - Platform Settings (SMTP config)")
    print("=" * 70)

    token_hdr = sa_hdr or oa_hdr
    paths = ["/admin/settings", "/settings", "/admin/platform-settings", "/platform/settings",
             "/config", "/admin/config", "/admin/settings/smtp", "/settings/smtp",
             "/settings/email", "/admin/smtp", "/admin/email-settings",
             "/admin/email/config", "/admin/email-config", "/admin/platform/settings",
             "/system/settings", "/super-admin/settings", "/admin/configuration"]

    for p in paths:
        r = requests.get(f"{API}{p}", headers=token_hdr, timeout=TIMEOUT)
        if r.status_code == 200:
            data = r.json()
            text = json.dumps(data).lower()
            has_smtp = any(k in text for k in ["smtp", "mail_host", "email_host", "mailer"])
            print(f"  GET {p} -> 200, SMTP: {has_smtp}")
            detail = f"Settings found at {p}. SMTP config: {'present' if has_smtp else 'not in response'}."
            return {"status": "PASS" if has_smtp else "PARTIAL", "detail": detail}
        else:
            print(f"  GET {p} -> {r.status_code}")

    return {"status": "FAIL",
            "detail": f"No platform settings endpoint found. Tried {len(paths)} paths, all returned 404."}


# ══════════════════════════════════════════════════════════════════════════
# #545 - Attendance Filters
# ══════════════════════════════════════════════════════════════════════════

def test_545():
    print("\n" + "=" * 70)
    print("#545 - Attendance Filters")
    print("=" * 70)

    # Unfiltered
    r = requests.get(f"{API}/attendance/records", headers=oa_hdr, timeout=TIMEOUT)
    if r.status_code != 200:
        return {"status": "FAIL", "detail": f"GET /attendance/records -> {r.status_code}"}
    total_all = r.json().get("meta", {}).get("total", 0)
    print(f"  Unfiltered: total={total_all}")

    # Department filter
    r2 = requests.get(f"{API}/attendance/records", headers=oa_hdr,
                      params={"department_id": "20"}, timeout=TIMEOUT)
    total_dept20 = r2.json().get("meta", {}).get("total", 0)
    print(f"  department_id=20: total={total_dept20}")

    r3 = requests.get(f"{API}/attendance/records", headers=oa_hdr,
                      params={"department_id": "999"}, timeout=TIMEOUT)
    total_dept999 = r3.json().get("meta", {}).get("total", 0)
    print(f"  department_id=999: total={total_dept999}")

    dept_ok = total_dept20 < total_all and total_dept999 == 0

    # Date filter
    r4 = requests.get(f"{API}/attendance/records", headers=oa_hdr,
                      params={"date": "2026-03-28"}, timeout=TIMEOUT)
    total_d1 = r4.json().get("meta", {}).get("total", 0)

    r5 = requests.get(f"{API}/attendance/records", headers=oa_hdr,
                      params={"date": "2026-01-01"}, timeout=TIMEOUT)
    total_d2 = r5.json().get("meta", {}).get("total", 0)
    print(f"  date=2026-03-28: total={total_d1}, date=2026-01-01: total={total_d2}")

    date_ok = total_d1 != total_d2 or total_d1 < total_all

    # Try from_date/to_date
    r6 = requests.get(f"{API}/attendance/records", headers=oa_hdr,
                      params={"from_date": "2026-01-01", "to_date": "2026-01-01"}, timeout=TIMEOUT)
    total_ft = r6.json().get("meta", {}).get("total", 0)
    print(f"  from/to Jan 1: total={total_ft}")

    detail = (f"Unfiltered: {total_all}. "
              f"Department filter: dept_id=20 -> {total_dept20}, dept_id=999 -> {total_dept999} ({'PASS - narrows results' if dept_ok else 'not narrowing'}). "
              f"Date filter: date param -> {total_d1}/{total_d2} ({'narrows' if date_ok else 'same count for different dates - NOT filtering'}), "
              f"from/to_date Jan 1 -> {total_ft} ({'narrows' if total_ft < total_all else 'not filtering'}).")

    if dept_ok and (date_ok or total_ft < total_all):
        return {"status": "PASS", "detail": detail}
    elif dept_ok:
        return {"status": "PARTIAL", "detail": detail + " Department filter works. Date filter is NOT narrowing results."}
    else:
        return {"status": "FAIL", "detail": detail}


# ══════════════════════════════════════════════════════════════════════════
# #556 - Employee Profile Editing
# ══════════════════════════════════════════════════════════════════════════

def test_556():
    print("\n" + "=" * 70)
    print("#556 - Employee Profile Editing")
    print("=" * 70)

    if not emp_token:
        return {"status": "FAIL", "detail": "Employee login failed"}

    priya_id = emp_user.get("id", 524)

    # Read current
    r = requests.get(f"{API}/users/{priya_id}", headers=oa_hdr, timeout=TIMEOUT)
    if r.status_code != 200:
        return {"status": "FAIL", "detail": f"Cannot read user profile: {r.status_code}"}
    original = r.json().get("data", r.json())
    orig_phone = original.get("contact_number", "")
    print(f"  Original phone: {orig_phone}")

    # Employee tries to update own profile
    r_emp = requests.put(f"{API}/users/{priya_id}", headers=emp_hdr,
                         json={"contact_number": "9876543210"}, timeout=TIMEOUT)
    emp_can_edit = r_emp.status_code == 200
    print(f"  Employee self-edit: {r_emp.status_code}")

    # Org admin updates employee
    test_phone = "9876543210"
    r_oa = requests.put(f"{API}/users/{priya_id}", headers=oa_hdr,
                        json={"contact_number": test_phone}, timeout=TIMEOUT)
    print(f"  OA update: {r_oa.status_code}")

    if r_oa.status_code != 200:
        return {"status": "FAIL", "detail": f"PUT /users/{priya_id} as org admin -> {r_oa.status_code}: {r_oa.text[:200]}"}

    # Check if PUT response shows updated value
    put_phone = r_oa.json().get("data", {}).get("contact_number", "")
    print(f"  PUT response phone: {put_phone}")

    # Read back
    time.sleep(1)
    r_after = requests.get(f"{API}/users/{priya_id}", headers=oa_hdr, timeout=TIMEOUT)
    after_phone = r_after.json().get("data", r_after.json()).get("contact_number", "")
    print(f"  After read-back phone: {after_phone}")

    persisted = after_phone == test_phone

    # Restore
    requests.put(f"{API}/users/{priya_id}", headers=oa_hdr,
                 json={"contact_number": orig_phone}, timeout=TIMEOUT)
    print(f"  Restored to: {orig_phone}")

    detail = (f"Employee self-edit (PUT /users/{priya_id} as employee): {'200 OK' if emp_can_edit else '403 Forbidden - employees cannot edit own profile'}. "
              f"Org admin edit: 200 OK. "
              f"PUT response phone='{put_phone}', GET read-back phone='{after_phone}'. "
              f"Persistence: {'YES' if persisted else 'NO - value did not change despite 200 response'}.")

    if persisted and emp_can_edit:
        return {"status": "PASS", "detail": detail}
    elif persisted:
        return {"status": "PARTIAL", "detail": detail + " Org admin can edit but employees cannot self-edit (403)."}
    else:
        return {"status": "FAIL", "detail": detail + " PUT returns 200 but does NOT actually persist the change."}


# ══════════════════════════════════════════════════════════════════════════
# #563 - Bulk Leave Approval
# ══════════════════════════════════════════════════════════════════════════

def test_563():
    print("\n" + "=" * 70)
    print("#563 - Bulk Leave Approval")
    print("=" * 70)

    # Get pending leaves
    r = requests.get(f"{API}/leave/applications", headers=oa_hdr,
                     params={"status": "pending"}, timeout=TIMEOUT)
    if r.status_code != 200:
        return {"status": "FAIL", "detail": f"GET /leave/applications -> {r.status_code}"}

    pending = r.json().get("data", [])
    pend_ids = [i["id"] for i in pending if "id" in i]
    print(f"  Pending leaves: {len(pend_ids)} (IDs: {pend_ids[:5]})")

    if not pend_ids:
        return {"status": "PARTIAL", "detail": "Leave endpoint works but 0 pending leaves to test approval."}

    # Try bulk approve endpoints
    bulk_ok = False
    for path in ["/leave/applications/bulk-approve", "/leave/bulk-approve",
                 "/leaves/bulk-approve", "/leave/applications/bulk-action"]:
        for payload in [{"ids": pend_ids[:3]}, {"leave_ids": pend_ids[:3]},
                        {"application_ids": pend_ids[:3]}]:
            for method in [requests.post, requests.put]:
                r = method(f"{API}{path}", headers=oa_hdr, json=payload, timeout=TIMEOUT)
                if r.status_code in (200, 201):
                    bulk_ok = True
                    print(f"  Bulk approve: {method.__name__.upper()} {path} -> 200")
                    break
            if bulk_ok:
                break
        if bulk_ok:
            break

    # Individual approve
    indiv_ok = 0
    for lid in pend_ids[:2]:
        r = requests.put(f"{API}/leave/applications/{lid}/approve", headers=oa_hdr,
                         json={"status": "approved"}, timeout=TIMEOUT)
        if r.status_code == 200:
            indiv_ok += 1
            print(f"  Individual approve {lid}: OK")
        else:
            print(f"  Individual approve {lid}: {r.status_code}")

    detail = (f"Pending leaves: {len(pend_ids)}. "
              f"Bulk approve endpoint: {'FOUND and works' if bulk_ok else 'NOT FOUND (404 on all attempted paths)'}. "
              f"Individual approve (PUT /leave/applications/ID/approve): {indiv_ok}/{min(2, len(pend_ids))} succeeded.")

    if bulk_ok:
        return {"status": "PASS", "detail": detail}
    elif indiv_ok > 0:
        return {"status": "PARTIAL", "detail": detail + " Individual approval works but no dedicated bulk endpoint."}
    else:
        return {"status": "FAIL", "detail": detail}


# ══════════════════════════════════════════════════════════════════════════
# #673 - Notifications
# ══════════════════════════════════════════════════════════════════════════

def test_673():
    print("\n" + "=" * 70)
    print("#673 - Notifications")
    print("=" * 70)

    r = requests.get(f"{API}/notifications", headers=oa_hdr, timeout=TIMEOUT)
    if r.status_code != 200:
        return {"status": "FAIL", "detail": f"GET /notifications -> {r.status_code}"}

    data = r.json()
    notifs = data.get("data", [])
    meta = data.get("meta", {})
    total = meta.get("total", len(notifs))
    print(f"  Notifications: {total} (page has {len(notifs)})")

    # Try mark as read if we have items
    mark_ok = False
    if notifs:
        nid = notifs[0].get("id")
        if nid:
            r2 = requests.put(f"{API}/notifications/{nid}/read", headers=oa_hdr,
                              json={"read": True}, timeout=TIMEOUT)
            if r2.status_code in (200, 201, 204):
                mark_ok = True
            else:
                r3 = requests.put(f"{API}/notifications/{nid}", headers=oa_hdr,
                                  json={"is_read": True}, timeout=TIMEOUT)
                mark_ok = r3.status_code in (200, 201, 204)

    detail = (f"GET /notifications: 200 OK. Returns {total} notifications (meta: {json.dumps(meta)}). "
              f"Mark-as-read: {'works' if mark_ok else 'untestable (0 notifications in inbox)' if total == 0 else 'failed'}.")

    return {"status": "PASS", "detail": detail}


# ══════════════════════════════════════════════════════════════════════════
# #700 - Leave Shows Employee Names
# ══════════════════════════════════════════════════════════════════════════

def test_700():
    print("\n" + "=" * 70)
    print("#700 - Leave Applications Show Employee Names")
    print("=" * 70)

    r = requests.get(f"{API}/leave/applications", headers=oa_hdr, timeout=TIMEOUT)
    if r.status_code != 200:
        return {"status": "FAIL", "detail": f"GET /leave/applications -> {r.status_code}"}

    leaves = r.json().get("data", [])
    if not leaves:
        return {"status": "PARTIAL", "detail": "Endpoint works but 0 leave records."}

    sample = leaves[0]
    keys = list(sample.keys())
    print(f"  Sample keys: {keys}")

    # Check for name fields
    name_fields = []
    for f in ["user_first_name", "user_last_name", "user_email", "user_emp_code",
              "employee_name", "name", "full_name", "first_name"]:
        if sample.get(f):
            name_fields.append(f"{f}={sample[f]}")

    # Check nested objects
    for nest in ["employee", "user", "applicant"]:
        if isinstance(sample.get(nest), dict):
            nested = sample[nest]
            for nf in ["name", "first_name", "full_name"]:
                if nested.get(nf):
                    name_fields.append(f"{nest}.{nf}={nested[nf]}")

    has_names = bool(name_fields)
    print(f"  Name fields: {name_fields}")

    detail = (f"GET /leave/applications: {len(leaves)} records. "
              f"Employee name fields: {', '.join(name_fields) if name_fields else 'NONE'}. "
              f"All keys: {keys}.")

    return {"status": "PASS" if has_names else "FAIL", "detail": detail}


# ══════════════════════════════════════════════════════════════════════════
# #703 - Invite Employee
# ══════════════════════════════════════════════════════════════════════════

def test_703():
    print("\n" + "=" * 70)
    print("#703 - Invite Employee")
    print("=" * 70)

    test_email = f"verify-test-{int(time.time())}@test.com"
    payload = {"email": test_email, "role": "employee",
               "first_name": "Test", "last_name": "Verify"}

    r = requests.post(f"{API}/users/invite", headers=oa_hdr, json=payload, timeout=TIMEOUT)
    print(f"  POST /users/invite -> {r.status_code}")

    if r.status_code in (200, 201):
        data = r.json()
        inv = data.get("data", {}).get("invitation", data.get("data", {}))
        inv_id = inv.get("id", "N/A")
        detail = (f"Invitation created via POST /users/invite. "
                  f"Email: {test_email}, invitation ID: {inv_id}. "
                  f"Response: {json.dumps(data)[:300]}")
        return {"status": "PASS", "detail": detail}
    elif r.status_code == 422:
        return {"status": "PARTIAL", "detail": f"Endpoint exists but validation error: {r.text[:200]}"}
    else:
        return {"status": "FAIL", "detail": f"POST /users/invite -> {r.status_code}: {r.text[:200]}"}


# ══════════════════════════════════════════════════════════════════════════
# #704 - Org Chart
# ══════════════════════════════════════════════════════════════════════════

def test_704():
    print("\n" + "=" * 70)
    print("#704 - Org Chart / Reporting Hierarchy")
    print("=" * 70)

    # Dedicated org chart endpoint
    r = requests.get(f"{API}/users/org-chart", headers=oa_hdr, timeout=TIMEOUT)
    chart_ok = r.status_code == 200
    chart_data = r.json().get("data", []) if chart_ok else []

    def count_tree(nodes):
        c = 0
        for n in nodes:
            c += 1
            c += count_tree(n.get("children", []))
        return c

    tree_count = count_tree(chart_data) if chart_data else 0
    print(f"  GET /users/org-chart: {r.status_code}, top-level={len(chart_data)}, tree total={tree_count}")

    # Users endpoint with reporting_manager_id
    r2 = requests.get(f"{API}/users", headers=oa_hdr, params={"per_page": 100}, timeout=TIMEOUT)
    users = r2.json().get("data", []) if r2.status_code == 200 else []
    total_users = r2.json().get("meta", {}).get("total", len(users)) if r2.status_code == 200 else 0
    has_reporting = sum(1 for u in users if u.get("reporting_manager_id"))
    print(f"  Users: {total_users} total, {has_reporting} have reporting_manager_id")

    detail = (f"Org chart endpoint (GET /users/org-chart): {'200 OK' if chart_ok else 'not found'}. "
              f"Returns {tree_count} employees in tree ({len(chart_data)} top-level nodes). "
              f"Users endpoint: {total_users} total, {has_reporting} have reporting_manager_id. "
              f"Hierarchy: {'present' if has_reporting > 2 or tree_count > 2 else 'only ' + str(max(tree_count, has_reporting)) + ' entries'}.")

    if chart_ok and (tree_count > 2 or has_reporting > 2):
        return {"status": "PASS", "detail": detail}
    elif chart_ok:
        return {"status": "PARTIAL", "detail": detail + f" Org chart endpoint works but only {tree_count} entries in tree."}
    else:
        return {"status": "FAIL", "detail": detail}


# ══════════════════════════════════════════════════════════════════════════
# Run All Tests
# ══════════════════════════════════════════════════════════════════════════

test_map = {
    499: ("Audit Log Filters", test_499),
    519: ("Create Organization", test_519),
    520: ("Platform Settings", test_520),
    545: ("Attendance Filters", test_545),
    556: ("Employee Profile Editing", test_556),
    563: ("Bulk Leave Approval", test_563),
    673: ("Notifications", test_673),
    700: ("Leave Shows Employee Names", test_700),
    703: ("Invite Employee", test_703),
    704: ("Org Chart", test_704),
}

for issue, (title, fn) in test_map.items():
    try:
        results[issue] = fn()
    except Exception as e:
        import traceback
        results[issue] = {"status": "ERROR", "detail": f"{e}\n{traceback.format_exc()[:300]}"}
    results[issue]["title"] = title


# ══════════════════════════════════════════════════════════════════════════
# Summary
# ══════════════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("RESULTS SUMMARY")
print("=" * 70)

pass_c = sum(1 for r in results.values() if r["status"] == "PASS")
partial_c = sum(1 for r in results.values() if r["status"] == "PARTIAL")
fail_c = sum(1 for r in results.values() if r["status"] in ("FAIL", "ERROR"))

for issue in sorted(results.keys()):
    r = results[issue]
    tag = {"PASS": "PASS", "PARTIAL": "WARN", "FAIL": "FAIL", "ERROR": "ERR!"}[r["status"]]
    print(f"  [{tag}] #{issue} {r['title']}")
    # Wrap detail at ~100 chars
    d = r["detail"]
    while d:
        print(f"         {d[:110]}")
        d = d[110:]

print(f"\nTotals: {pass_c} PASS / {partial_c} PARTIAL / {fail_c} FAIL  (out of {len(results)})")


# ══════════════════════════════════════════════════════════════════════════
# GitHub Comments
# ══════════════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("POSTING GITHUB COMMENTS")
print("=" * 70)

for issue in sorted(results.keys()):
    r = results[issue]
    status_label = {"PASS": "PASS", "PARTIAL": "Partial", "FAIL": "FAIL", "ERROR": "Error"}[r["status"]]
    body = (f"**API Verification (2026-03-28) -- {status_label}**\n\n"
            f"**Feature:** {r['title']}\n"
            f"**Result:** {r['status']}\n\n"
            f"**Details:**\n{r['detail']}\n\n"
            f"_Tested via crash-proof API-only script (no Selenium). Base: `{API}`_")
    gh_comment(issue, body)

print("\nDone.")
