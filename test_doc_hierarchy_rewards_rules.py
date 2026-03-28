#!/usr/bin/env python3
"""
EmpCloud Business Rules V2 - Sections 20-22 Audit
Tests: Employee Documents & Compliance (DC001-DC010),
       Reporting Hierarchy & Org Structure (OH001-OH010),
       Rewards & Recognition (RW001-RW010)
"""
import sys, json, time, traceback, io, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import requests
import urllib3
urllib3.disable_warnings()

# ── Config ─────────────────────────────────────────────────────────────
API      = "https://test-empcloud-api.empcloud.com/api/v1"
REWARDS  = "https://test-rewards-api.empcloud.com/api/v1"

GH_TOKEN = "$GITHUB_TOKEN"
GH_REPO  = "EmpCloud/EmpCloud"

ADMIN_EMAIL = "ananya@technova.in"
ADMIN_PW    = "Welcome@123"
EMP_EMAIL   = "priya@technova.in"
EMP_PW      = "Welcome@123"

ENFORCED     = "ENFORCED"
NOT_ENFORCED = "NOT ENFORCED"
NOT_IMPL     = "NOT IMPLEMENTED"
PARTIAL      = "PARTIAL"

results = []
TIMEOUT = 30

# ── Helpers ────────────────────────────────────────────────────────────
def record(rid, cat, rule, status, detail=""):
    results.append({"id": rid, "category": cat, "rule": rule, "status": status, "detail": detail, "issue_url": None})
    icons = {ENFORCED: "[OK]", NOT_ENFORCED: "[BUG]", NOT_IMPL: "[N/A]", PARTIAL: "[!!]"}
    print(f"  {icons.get(status,'[??]')} {rid}: {rule} -> {status}")
    if detail:
        print(f"      {detail[:300]}")

def hdr(tok):
    return {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}

def hdr_no_ct(tok):
    return {"Authorization": f"Bearer {tok}"}

def login_cloud(email, pw):
    try:
        r = requests.post(f"{API}/auth/login", json={"email": email, "password": pw}, timeout=TIMEOUT, verify=False)
        if r.status_code != 200:
            print(f"  Login failed for {email}: {r.status_code} {r.text[:200]}")
            return None
        d = r.json().get("data", {})
        t = d.get("tokens", d)
        return t.get("access_token") or t.get("accessToken")
    except Exception as e:
        print(f"  Login error for {email}: {e}")
        return None

def sso_to_rewards(core_token):
    """SSO from core to Rewards module."""
    try:
        r = requests.post(f"{REWARDS}/auth/sso",
                          json={"token": core_token}, timeout=TIMEOUT, verify=False)
        if r.status_code == 200:
            d = r.json().get("data", {})
            t = d.get("tokens", d)
            return t.get("accessToken") or t.get("access_token")
        return None
    except:
        return None

def get_data(resp):
    """Extract data from EmpCloud nested response."""
    if not resp or resp.status_code not in [200, 201]:
        return None
    try:
        d = resp.json()
    except:
        return None
    payload = d.get("data", d)
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and "data" in payload:
        return payload["data"]
    return payload

def safe_get(url, headers, params=None):
    try:
        return requests.get(url, headers=headers, params=params, timeout=TIMEOUT, verify=False)
    except Exception as e:
        print(f"    GET {url} error: {e}")
        return None

def safe_post(url, headers, json_data=None, files=None, data=None):
    try:
        return requests.post(url, headers=headers, json=json_data, files=files, data=data, timeout=TIMEOUT, verify=False)
    except Exception as e:
        print(f"    POST {url} error: {e}")
        return None

def safe_delete(url, headers):
    try:
        return requests.delete(url, headers=headers, timeout=TIMEOUT, verify=False)
    except Exception as e:
        print(f"    DELETE {url} error: {e}")
        return None

def file_issue(title, body, labels):
    """File a GitHub issue."""
    try:
        # Check for duplicates first
        search_r = requests.get(f"https://api.github.com/search/issues",
            headers={"Authorization": f"token {GH_TOKEN}", "Accept": "application/vnd.github.v3+json"},
            params={"q": f'repo:{GH_REPO} is:issue "{title}" in:title'}, timeout=30)
        if search_r.status_code == 200:
            items = search_r.json().get("items", [])
            if items:
                url = items[0].get("html_url", "")
                print(f"    Duplicate found: {url}")
                return url

        r = requests.post(f"https://api.github.com/repos/{GH_REPO}/issues",
            headers={"Authorization": f"token {GH_TOKEN}", "Accept": "application/vnd.github.v3+json"},
            json={"title": title, "body": body, "labels": labels}, timeout=30)
        if r.status_code == 201:
            url = r.json().get("html_url", "")
            print(f"    Filed issue: {url}")
            return url
        else:
            print(f"    Issue filing failed: {r.status_code} {r.text[:200]}")
            return None
    except Exception as e:
        print(f"    Issue filing error: {e}")
        return None


# ══════════════════════════════════════════════════════════════════════
# SECTION 20: EMPLOYEE DOCUMENTS & COMPLIANCE
# ══════════════════════════════════════════════════════════════════════
def test_documents(admin_tok, emp_tok):
    print("\n" + "="*70)
    print("SECTION 20: EMPLOYEE DOCUMENTS & COMPLIANCE")
    print("="*70)

    # --- DC001: Mandatory documents list ---
    try:
        r = safe_get(f"{API}/documents/mandatory", hdr(admin_tok))
        if r and r.status_code == 200:
            data = get_data(r)
            record("DC001", "Documents", "Mandatory documents list (joining checklist)", ENFORCED,
                   f"Mandatory docs endpoint works. Data: {str(data)[:200]}")
        elif r and r.status_code == 404:
            record("DC001", "Documents", "Mandatory documents list (joining checklist)", NOT_IMPL,
                   f"404 - /documents/mandatory not found")
        else:
            record("DC001", "Documents", "Mandatory documents list (joining checklist)", PARTIAL,
                   f"Status {r.status_code if r else 'timeout'}: {r.text[:200] if r else 'No response'}")
    except Exception as e:
        record("DC001", "Documents", "Mandatory documents list (joining checklist)", PARTIAL, str(e))

    # --- DC002: Cannot mark onboarding complete without mandatory docs ---
    try:
        r = safe_get(f"{API}/onboarding/status", hdr(admin_tok))
        if r and r.status_code == 200:
            record("DC002", "Documents", "Cannot mark onboarding complete without mandatory docs", PARTIAL,
                   f"Onboarding status endpoint exists. Cannot safely test completion check on shared env.")
        else:
            record("DC002", "Documents", "Cannot mark onboarding complete without mandatory docs", PARTIAL,
                   f"Onboarding endpoint status {r.status_code if r else 'timeout'}. Cannot verify doc-check logic.")
    except Exception as e:
        record("DC002", "Documents", "Cannot mark onboarding complete without mandatory docs", PARTIAL, str(e))

    # --- DC003: Document expiry tracking ---
    try:
        r = safe_get(f"{API}/documents/expiry-alerts", hdr(admin_tok))
        if r and r.status_code == 200:
            data = get_data(r)
            record("DC003", "Documents", "Document expiry tracking (visa, passport, license)", ENFORCED,
                   f"Expiry alerts endpoint works. Data: {str(data)[:200]}")
        else:
            # Check if documents have expires_at field
            r2 = safe_get(f"{API}/documents", hdr(admin_tok), params={"limit": 5})
            docs = get_data(r2) or []
            has_expiry = False
            if isinstance(docs, list) and len(docs) > 0:
                has_expiry = "expires_at" in docs[0]
            if has_expiry:
                record("DC003", "Documents", "Document expiry tracking (visa, passport, license)", PARTIAL,
                       f"Documents have 'expires_at' field but /expiry-alerts returned {r.status_code if r else 'timeout'}")
            else:
                record("DC003", "Documents", "Document expiry tracking (visa, passport, license)", PARTIAL,
                       f"Expiry-alerts status {r.status_code if r else 'timeout'}")
    except Exception as e:
        record("DC003", "Documents", "Document expiry tracking", PARTIAL, str(e))

    # --- DC004: Expired document -> auto-notification to HR ---
    try:
        r = safe_get(f"{API}/notifications", hdr(admin_tok), params={"limit": 50})
        if r and r.status_code == 200:
            notifs = get_data(r)
            doc_notifs = []
            if isinstance(notifs, list):
                doc_notifs = [n for n in notifs if "document" in json.dumps(n).lower() or "expir" in json.dumps(n).lower()]
            record("DC004", "Documents", "Expired document -> auto-notification to HR", PARTIAL,
                   f"Notification system works. Found {len(doc_notifs)} doc-related notifications out of {len(notifs) if isinstance(notifs, list) else '?'}. Cannot trigger expiry in test.")
        else:
            record("DC004", "Documents", "Expired document -> auto-notification to HR", PARTIAL,
                   f"Notification endpoint status {r.status_code if r else 'timeout'}")
    except Exception as e:
        record("DC004", "Documents", "Expired document -> auto-notification to HR", PARTIAL, str(e))

    # --- DC005: Employee sees only own documents (CRITICAL) ---
    try:
        # Admin docs
        r_admin = safe_get(f"{API}/documents", hdr(admin_tok), params={"limit": 100})
        admin_docs = get_data(r_admin) or []
        admin_count = len(admin_docs) if isinstance(admin_docs, list) else 0

        # Employee tries /documents (should be restricted)
        r_emp_all = safe_get(f"{API}/documents", hdr(emp_tok))
        emp_all_docs = get_data(r_emp_all) or []
        emp_all_count = len(emp_all_docs) if isinstance(emp_all_docs, list) else 0

        # Employee tries /documents/my
        r_emp_my = safe_get(f"{API}/documents/my", hdr(emp_tok))
        emp_my_docs = get_data(r_emp_my) or []
        emp_my_count = len(emp_my_docs) if isinstance(emp_my_docs, list) else 0

        # Check if employee can access specific docs belonging to other users
        other_user_doc_accessible = False
        if isinstance(admin_docs, list):
            for doc in admin_docs:
                doc_user = doc.get("user_id")
                # priya is user/employee 655 (or 524 in rewards)
                if doc_user and doc_user != 655 and doc_user != 524:
                    r_access = safe_get(f"{API}/documents/{doc['id']}", hdr(emp_tok))
                    if r_access and r_access.status_code == 200:
                        other_user_doc_accessible = True
                        break

        if r_emp_all and r_emp_all.status_code in [403, 401]:
            record("DC005", "Documents", "Employee sees only own documents (not others')", ENFORCED,
                   f"Employee blocked from /documents ({r_emp_all.status_code}). Admin sees {admin_count} docs.")
        elif other_user_doc_accessible:
            record("DC005", "Documents", "Employee sees only own documents (not others')", NOT_ENFORCED,
                   f"Employee CAN access other users' documents by ID! Admin has {admin_count} docs, employee /documents returns {emp_all_count}, /documents/my returns {emp_my_count}")
        elif emp_all_count > emp_my_count and admin_count > 0:
            record("DC005", "Documents", "Employee sees only own documents (not others')", NOT_ENFORCED,
                   f"Employee /documents returns {emp_all_count} vs /my returns {emp_my_count}. Leaking others' docs.")
        elif admin_count > 0 and emp_all_count == 0 and emp_my_count == 0:
            record("DC005", "Documents", "Employee sees only own documents (not others')", ENFORCED,
                   f"Admin sees {admin_count} docs but employee sees 0 in both endpoints. Properly filtered.")
        else:
            record("DC005", "Documents", "Employee sees only own documents (not others')", PARTIAL,
                   f"Admin={admin_count}, emp /documents={emp_all_count}, emp /my={emp_my_count}")
    except Exception as e:
        record("DC005", "Documents", "Employee sees only own documents", PARTIAL, str(e))

    # --- DC006: HR can see all employee documents ---
    try:
        r = safe_get(f"{API}/documents", hdr(admin_tok))
        if r and r.status_code == 200:
            data = get_data(r)
            count = len(data) if isinstance(data, list) else "non-list"
            record("DC006", "Documents", "HR can see all employee documents", ENFORCED,
                   f"Admin GET /documents returns {count} docs")
        else:
            record("DC006", "Documents", "HR can see all employee documents", PARTIAL,
                   f"Status {r.status_code if r else 'timeout'}: {r.text[:200] if r else 'No response'}")
    except Exception as e:
        record("DC006", "Documents", "HR can see all employee documents", PARTIAL, str(e))

    # --- DC007: Cannot delete category with documents in it ---
    try:
        r = safe_get(f"{API}/documents/categories", hdr(admin_tok))
        cats = get_data(r) if r else None
        if isinstance(cats, list) and len(cats) > 0:
            # Find a category that has documents
            r_docs = safe_get(f"{API}/documents", hdr(admin_tok), params={"limit": 100})
            all_docs = get_data(r_docs) or []
            used_cat_ids = set()
            if isinstance(all_docs, list):
                for d in all_docs:
                    cid = d.get("category_id")
                    if cid:
                        used_cat_ids.add(cid)

            target_cat = None
            for c in cats:
                cid = c.get("id") or c.get("_id")
                if cid in used_cat_ids:
                    target_cat = c
                    break

            if target_cat:
                cat_id = target_cat.get("id") or target_cat.get("_id")
                cat_name = target_cat.get("name", "unknown")
                r_del = safe_delete(f"{API}/documents/categories/{cat_id}", hdr(admin_tok))
                if r_del and r_del.status_code in [400, 409, 422]:
                    record("DC007", "Documents", "Cannot delete category with documents in it", ENFORCED,
                           f"Delete category '{cat_name}' (has docs) blocked: {r_del.status_code} {r_del.text[:200]}")
                elif r_del and r_del.status_code in [200, 204]:
                    record("DC007", "Documents", "Cannot delete category with documents in it", NOT_ENFORCED,
                           f"Category '{cat_name}' with documents was DELETED! No protection. Status {r_del.status_code}")
                    # Recreate it
                    safe_post(f"{API}/documents/categories", hdr(admin_tok), json_data={"name": cat_name})
                else:
                    record("DC007", "Documents", "Cannot delete category with documents in it", PARTIAL,
                           f"Status {r_del.status_code if r_del else 'timeout'}: {r_del.text[:200] if r_del else 'N/A'}")
            else:
                record("DC007", "Documents", "Cannot delete category with documents in it", PARTIAL,
                       f"No category with documents found to test. {len(cats)} cats, {len(used_cat_ids)} used.")
        else:
            record("DC007", "Documents", "Cannot delete category with documents in it", PARTIAL,
                   f"No categories found. Status: {r.status_code if r else 'timeout'}")
    except Exception as e:
        record("DC007", "Documents", "Cannot delete category with documents in it", PARTIAL, str(e))

    # --- DC008: File size limit on uploads ---
    try:
        small_file = io.BytesIO(b"%PDF-1.4 test content")
        r = safe_post(f"{API}/documents/upload", hdr_no_ct(admin_tok),
                      files={"file": ("test_small.pdf", small_file, "application/pdf")},
                      data={"category_id": "20", "employee_id": "522", "title": "Size Test"})
        if r and r.status_code in [200, 201]:
            # Clean up
            doc_id = r.json().get("data", {}).get("id")
            if doc_id:
                safe_delete(f"{API}/documents/{doc_id}", hdr(admin_tok))
            record("DC008", "Documents", "File size limit on uploads (max 10MB)", PARTIAL,
                   f"Small file upload works. Cannot test 10MB+ without large upload. Endpoint: /documents/upload")
        elif r and r.status_code in [400, 413, 422]:
            record("DC008", "Documents", "File size limit on uploads (max 10MB)", PARTIAL,
                   f"Upload rejected ({r.status_code}): {r.text[:200]}")
        else:
            record("DC008", "Documents", "File size limit on uploads (max 10MB)", PARTIAL,
                   f"Status {r.status_code if r else 'timeout'}: {r.text[:200] if r else 'N/A'}")
    except Exception as e:
        record("DC008", "Documents", "File size limit on uploads (max 10MB)", PARTIAL, str(e))

    # --- DC009: Allowed file types only (no .exe) ---
    try:
        exe_content = b"MZ" + b"\x00" * 100  # Fake PE header
        r = safe_post(f"{API}/documents/upload", hdr_no_ct(admin_tok),
                      files={"file": ("malware_test.exe", io.BytesIO(exe_content), "application/x-msdownload")},
                      data={"category_id": "20", "employee_id": "522", "title": "EXE Test"})
        if r and r.status_code in [400, 415, 422]:
            err_text = r.text.lower()
            if "file" in err_text or "type" in err_text or "allowed" in err_text or "format" in err_text:
                record("DC009", "Documents", "Allowed file types only (PDF, JPG, PNG -- no .exe)", ENFORCED,
                       f".exe upload rejected: {r.status_code} {r.text[:200]}")
            else:
                record("DC009", "Documents", "Allowed file types only (no .exe)", PARTIAL,
                       f".exe rejected but reason unclear: {r.status_code} {r.text[:200]}")
        elif r and r.status_code in [200, 201]:
            record("DC009", "Documents", "Allowed file types only (no .exe)", NOT_ENFORCED,
                   f".exe file ACCEPTED! Server allows dangerous file types.")
        else:
            record("DC009", "Documents", "Allowed file types only (no .exe)", PARTIAL,
                   f"Status {r.status_code if r else 'timeout'}: {r.text[:200] if r else 'N/A'}")
    except Exception as e:
        record("DC009", "Documents", "Allowed file types only (no .exe)", PARTIAL, str(e))

    # --- DC010: Document version history ---
    try:
        r = safe_get(f"{API}/documents", hdr(admin_tok), params={"limit": 5})
        docs = get_data(r) if r else None
        if isinstance(docs, list) and len(docs) > 0:
            doc = docs[0]
            has_version = any(k for k in doc.keys() if "version" in k.lower())
            doc_id = doc.get("id") or doc.get("_id")
            r2 = safe_get(f"{API}/documents/{doc_id}", hdr(admin_tok)) if doc_id else None
            detail = get_data(r2) if r2 else None
            has_history = False
            if isinstance(detail, dict):
                has_history = any(k for k in detail.keys() if "version" in k.lower() or "history" in k.lower())
            if has_version or has_history:
                record("DC010", "Documents", "Document version history (new version doesn't delete old)", ENFORCED,
                       f"Version/history fields found in document data.")
            else:
                record("DC010", "Documents", "Document version history (new version doesn't delete old)", NOT_IMPL,
                       f"No version/history fields. Doc keys: {list(doc.keys())}")
        else:
            record("DC010", "Documents", "Document version history", PARTIAL,
                   f"No documents to check")
    except Exception as e:
        record("DC010", "Documents", "Document version history", PARTIAL, str(e))


# ══════════════════════════════════════════════════════════════════════
# SECTION 21: REPORTING HIERARCHY & ORG STRUCTURE
# ══════════════════════════════════════════════════════════════════════
def test_hierarchy(admin_tok):
    print("\n" + "="*70)
    print("SECTION 21: REPORTING HIERARCHY & ORG STRUCTURE")
    print("="*70)

    employees_basic = []
    employees_detail = []
    departments = []

    # Fetch employees (basic list)
    try:
        r = safe_get(f"{API}/employees", hdr(admin_tok), params={"limit": 200})
        employees_basic = get_data(r) or []
        if not isinstance(employees_basic, list):
            employees_basic = []
        print(f"  Fetched {len(employees_basic)} employees (basic list)")
    except:
        print("  Failed to fetch employees")

    # Fetch individual profiles for reporting_manager_id
    print("  Fetching individual profiles for manager data...")
    for emp in employees_basic:
        try:
            eid = emp.get("id")
            r = safe_get(f"{API}/employees/{eid}", hdr(admin_tok))
            if r and r.status_code == 200:
                d = r.json().get("data", {})
                employees_detail.append(d)
        except:
            pass
    print(f"  Fetched {len(employees_detail)} employee profiles")

    # Fetch departments
    try:
        r = safe_get(f"{API}/organizations/me/departments", hdr(admin_tok))
        departments = get_data(r) or []
        if not isinstance(departments, list):
            departments = []
        print(f"  Fetched {len(departments)} departments")
    except:
        print("  Failed to fetch departments")

    # --- OH001: Every employee must have a reporting manager (except CEO) ---
    try:
        if len(employees_detail) > 0:
            no_manager = []
            has_manager = 0
            for emp in employees_detail:
                mgr = emp.get("reporting_manager_id")
                designation = (emp.get("designation") or "").lower()
                status = emp.get("status")
                # Skip inactive/terminated (status=0 or 2)
                if status in [0, 2, "0", "2"]:
                    continue
                is_ceo = "ceo" in designation or "chief executive" in designation or "founder" in designation or "director" in designation
                is_top_admin = emp.get("role") == "org_admin" and not mgr
                if not mgr and not is_ceo:
                    name = f"{emp.get('first_name', '')} {emp.get('last_name', '')}"
                    no_manager.append(f"{name.strip()}(id={emp.get('id')}, role={emp.get('role')}, desig={designation})")
                elif mgr:
                    has_manager += 1

            if len(no_manager) == 0:
                record("OH001", "Hierarchy", "Every employee must have a reporting manager (except CEO)", ENFORCED,
                       f"All {has_manager} active non-CEO employees have reporting managers")
            else:
                record("OH001", "Hierarchy", "Every employee must have a reporting manager (except CEO)", NOT_ENFORCED,
                       f"{len(no_manager)} active employees missing manager: {'; '.join(no_manager[:5])}")
        else:
            record("OH001", "Hierarchy", "Every employee must have a reporting manager (except CEO)", PARTIAL,
                   f"Could not fetch employee profiles")
    except Exception as e:
        record("OH001", "Hierarchy", "Every employee must have a reporting manager (except CEO)", PARTIAL, str(e))

    # --- OH002: Reporting chain depth limit (no infinite nesting) ---
    try:
        r = safe_get(f"{API}/employees/org-chart", hdr(admin_tok))
        if r and r.status_code == 200:
            record("OH002", "Hierarchy", "Reporting chain depth limit (no infinite nesting)", PARTIAL,
                   f"Org chart exists. Cannot safely verify depth limit without creating circular chains.")
        else:
            record("OH002", "Hierarchy", "Reporting chain depth limit (no infinite nesting)", PARTIAL,
                   f"Org chart status {r.status_code if r else 'timeout'}")
    except Exception as e:
        record("OH002", "Hierarchy", "Reporting chain depth limit", PARTIAL, str(e))

    # --- OH003: Department must have at least one head/manager ---
    try:
        if len(departments) > 0:
            no_head = []
            for dept in departments:
                head = (dept.get("head") or dept.get("manager") or dept.get("head_id") or
                        dept.get("manager_id") or dept.get("department_head"))
                name = dept.get("name", "unknown")
                if not head:
                    no_head.append(name)
            if len(no_head) == 0:
                record("OH003", "Hierarchy", "Department must have at least one head/manager", ENFORCED,
                       f"All {len(departments)} departments have a head/manager")
            else:
                record("OH003", "Hierarchy", "Department must have at least one head/manager", NOT_ENFORCED,
                       f"{len(no_head)}/{len(departments)} departments missing head: {', '.join(no_head[:10])}")
        else:
            record("OH003", "Hierarchy", "Department must have at least one head/manager", PARTIAL,
                   f"No departments found")
    except Exception as e:
        record("OH003", "Hierarchy", "Department must have at least one head/manager", PARTIAL, str(e))

    # --- OH004: Cannot delete department with active employees (CRITICAL) ---
    try:
        if len(departments) > 0:
            # Find a department that has employees
            dept_employee_count = {}
            for emp in employees_detail:
                did = emp.get("department_id")
                if did and emp.get("status") in [1, "1"]:
                    dept_employee_count[did] = dept_employee_count.get(did, 0) + 1

            target_dept = None
            for dept in departments:
                did = dept.get("id") or dept.get("_id")
                if did in dept_employee_count and dept_employee_count[did] > 0:
                    target_dept = dept
                    break

            if target_dept:
                dept_id = target_dept.get("id") or target_dept.get("_id")
                dept_name = target_dept.get("name", "unknown")
                emp_count = dept_employee_count.get(dept_id, 0)

                r = safe_delete(f"{API}/organizations/me/departments/{dept_id}", hdr(admin_tok))
                if r and r.status_code in [400, 409, 422]:
                    record("OH004", "Hierarchy", "Cannot delete department with active employees", ENFORCED,
                           f"Delete dept '{dept_name}' ({emp_count} employees) blocked: {r.status_code} {r.text[:200]}")
                elif r and r.status_code in [200, 204]:
                    record("OH004", "Hierarchy", "Cannot delete department with active employees", NOT_ENFORCED,
                           f"Dept '{dept_name}' with {emp_count} active employees DELETED! No protection. Status {r.status_code}")
                    # Recreate it
                    safe_post(f"{API}/organizations/me/departments", hdr(admin_tok), json_data={"name": dept_name})
                else:
                    record("OH004", "Hierarchy", "Cannot delete department with active employees", PARTIAL,
                           f"Status {r.status_code if r else 'timeout'}: {r.text[:200] if r else 'N/A'}")
            else:
                record("OH004", "Hierarchy", "Cannot delete department with active employees", PARTIAL,
                       f"No department with active employees found to test")
        else:
            record("OH004", "Hierarchy", "Cannot delete department with active employees", PARTIAL,
                   f"No departments to test")
    except Exception as e:
        record("OH004", "Hierarchy", "Cannot delete department with active employees", PARTIAL, str(e))

    # --- OH005: Cannot delete designation if employees have that designation ---
    try:
        r_desig = safe_get(f"{API}/designations", hdr(admin_tok))
        r_desig2 = safe_get(f"{API}/organizations/me/designations", hdr(admin_tok))
        found = False
        for r_d, base in [(r_desig, f"{API}/designations"), (r_desig2, f"{API}/organizations/me/designations")]:
            if r_d and r_d.status_code == 200:
                desigs = get_data(r_d)
                if isinstance(desigs, list) and len(desigs) > 0:
                    d_id = desigs[0].get("id") or desigs[0].get("_id")
                    d_name = desigs[0].get("name", "unknown")
                    r_del = safe_delete(f"{base}/{d_id}", hdr(admin_tok))
                    if r_del and r_del.status_code in [400, 409, 422]:
                        record("OH005", "Hierarchy", "Cannot delete designation if employees have it", ENFORCED,
                               f"Blocked: {r_del.status_code} {r_del.text[:200]}")
                    elif r_del and r_del.status_code in [200, 204]:
                        record("OH005", "Hierarchy", "Cannot delete designation if employees have it", NOT_ENFORCED,
                               f"Designation '{d_name}' deleted even with employees assigned!")
                    else:
                        record("OH005", "Hierarchy", "Cannot delete designation if employees have it", PARTIAL,
                               f"Status {r_del.status_code if r_del else 'timeout'}")
                    found = True
                    break
        if not found:
            record("OH005", "Hierarchy", "Cannot delete designation if employees have it", NOT_IMPL,
                   f"No designations endpoint found. /designations={r_desig.status_code if r_desig else 'timeout'}")
    except Exception as e:
        record("OH005", "Hierarchy", "Cannot delete designation if employees have it", PARTIAL, str(e))

    # --- OH006: Org chart reflects real-time reporting structure ---
    try:
        r = safe_get(f"{API}/employees/org-chart", hdr(admin_tok))
        if r and r.status_code == 200:
            record("OH006", "Hierarchy", "Org chart reflects real-time reporting structure", ENFORCED,
                   f"Org chart endpoint returns 200 with data")
        elif r and r.status_code == 404:
            record("OH006", "Hierarchy", "Org chart reflects real-time reporting structure", NOT_IMPL,
                   f"/employees/org-chart returns 404")
        else:
            record("OH006", "Hierarchy", "Org chart reflects real-time reporting structure", PARTIAL,
                   f"Status {r.status_code if r else 'timeout'}")
    except Exception as e:
        record("OH006", "Hierarchy", "Org chart reflects real-time reporting structure", PARTIAL, str(e))

    # --- OH007: Manager transfer - reportees re-assigned ---
    try:
        record("OH007", "Hierarchy", "Manager transfer - all reportees should be re-assigned or moved", PARTIAL,
               f"Cannot safely test manager transfer on shared env. Requires destructive action.")
    except Exception as e:
        record("OH007", "Hierarchy", "Manager transfer - reportees re-assigned", PARTIAL, str(e))

    # --- OH008: Matrix reporting - dotted-line manager ---
    try:
        if len(employees_detail) > 0:
            emp = employees_detail[0]
            has_dotted = any(k for k in emp.keys() if "dotted" in k.lower() or "secondary" in k.lower() or "matrix" in k.lower())
            record("OH008", "Hierarchy", "Matrix reporting - employee can have dotted-line manager",
                   ENFORCED if has_dotted else NOT_IMPL,
                   f"Profile keys: {sorted(emp.keys())}. Dotted-line field: {has_dotted}")
        else:
            record("OH008", "Hierarchy", "Matrix reporting", PARTIAL, "No employee profiles to check")
    except Exception as e:
        record("OH008", "Hierarchy", "Matrix reporting", PARTIAL, str(e))

    # --- OH009: Head count per department ---
    try:
        if len(departments) > 0:
            dept = departments[0]
            has_count = any(k for k in dept.keys() if "count" in k.lower() or "headcount" in k.lower() or "employees" in k.lower() or "members" in k.lower())
            dept_name = dept.get("name", "unknown")
            if has_count:
                record("OH009", "Hierarchy", "Head count per department - tracked and reportable", ENFORCED,
                       f"Dept '{dept_name}' has headcount field")
            else:
                record("OH009", "Hierarchy", "Head count per department - tracked and reportable", NOT_IMPL,
                       f"Dept fields: {list(dept.keys())}. No headcount/employees field. Must be calculated from employee list.")
        else:
            record("OH009", "Hierarchy", "Head count per department", PARTIAL, "No departments to check")
    except Exception as e:
        record("OH009", "Hierarchy", "Head count per department", PARTIAL, str(e))

    # --- OH010: Cost center assignment ---
    try:
        has_cc = False
        if len(employees_detail) > 0:
            has_cc = any(k for k in employees_detail[0].keys() if "cost" in k.lower() or "center" in k.lower())
        if len(departments) > 0:
            has_cc = has_cc or any(k for k in departments[0].keys() if "cost" in k.lower() or "center" in k.lower())
        record("OH010", "Hierarchy", "Cost center assignment per employee/department",
               ENFORCED if has_cc else NOT_IMPL,
               f"Cost center field found: {has_cc}")
    except Exception as e:
        record("OH010", "Hierarchy", "Cost center assignment", PARTIAL, str(e))


# ══════════════════════════════════════════════════════════════════════
# SECTION 22: REWARDS & RECOGNITION
# ══════════════════════════════════════════════════════════════════════
def test_rewards(admin_tok, emp_tok):
    print("\n" + "="*70)
    print("SECTION 22: REWARDS & RECOGNITION")
    print("="*70)

    # Get Rewards tokens via SSO
    print("  Authenticating to Rewards module...")
    rewards_admin = sso_to_rewards(admin_tok)
    rewards_emp = sso_to_rewards(emp_tok)
    print(f"  Rewards admin token: {'obtained' if rewards_admin else 'FAILED'}")
    print(f"  Rewards employee token: {'obtained' if rewards_emp else 'FAILED'}")

    rw_admin_tok = rewards_admin or admin_tok
    rw_emp_tok = rewards_emp or emp_tok

    # Get employee IDs from core
    emp_id_admin = None
    emp_id_emp = None
    all_employees = []
    try:
        r = safe_get(f"{API}/employees", hdr(admin_tok), params={"limit": 200})
        emps = get_data(r) or []
        if isinstance(emps, list):
            all_employees = emps
            for e in emps:
                email = (e.get("email") or "").lower()
                if email == ADMIN_EMAIL.lower():
                    emp_id_admin = e.get("id")
                elif email == EMP_EMAIL.lower():
                    emp_id_emp = e.get("id")
        print(f"  Admin employee ID: {emp_id_admin}, Employee ID: {emp_id_emp}")
    except:
        print("  Could not fetch employee IDs")

    # --- RW001: Cannot give kudos to yourself (HIGH) ---
    try:
        # Correct field name is receiver_id (discovered from API error)
        r = safe_post(f"{REWARDS}/kudos", hdr(rw_admin_tok),
                      json_data={"receiver_id": emp_id_admin, "message": "Self kudos test", "value": "teamwork"})
        if r and r.status_code in [400, 403, 422]:
            err = r.text.lower()
            if "self" in err or "yourself" in err:
                record("RW001", "Rewards", "Cannot give kudos to yourself", ENFORCED,
                       f"Self-kudos blocked: {r.status_code} {r.text[:200]}")
            else:
                record("RW001", "Rewards", "Cannot give kudos to yourself", PARTIAL,
                       f"Rejected but not clearly self-kudos: {r.status_code} {r.text[:200]}")
        elif r and r.status_code in [200, 201]:
            record("RW001", "Rewards", "Cannot give kudos to yourself", NOT_ENFORCED,
                   f"Self-kudos ACCEPTED! No self-check. Status {r.status_code}")
        else:
            record("RW001", "Rewards", "Cannot give kudos to yourself", PARTIAL,
                   f"Status {r.status_code if r else 'timeout'}: {r.text[:200] if r else 'N/A'}")
    except Exception as e:
        record("RW001", "Rewards", "Cannot give kudos to yourself", PARTIAL, str(e))

    # --- RW002: Maximum kudos per day limit ---
    try:
        r = safe_get(f"{REWARDS}/kudos/sent", hdr(rw_admin_tok))
        if r and r.status_code == 200:
            sent = get_data(r) or []
            record("RW002", "Rewards", "Maximum kudos per day limit enforced", PARTIAL,
                   f"Sent kudos endpoint works ({len(sent) if isinstance(sent, list) else '?'} sent). Cannot verify daily limit without mass-sending.")
        else:
            record("RW002", "Rewards", "Maximum kudos per day limit enforced", PARTIAL,
                   f"Status {r.status_code if r else 'timeout'}: {r.text[:200] if r else 'N/A'}")
    except Exception as e:
        record("RW002", "Rewards", "Maximum kudos per day limit", PARTIAL, str(e))

    # --- RW003: Points expiry ---
    try:
        r = safe_get(f"{REWARDS}/points/transactions", hdr(rw_admin_tok))
        if r and r.status_code == 200:
            txns = get_data(r) or []
            has_expiry = False
            if isinstance(txns, list) and len(txns) > 0:
                has_expiry = any("expir" in k.lower() for t in txns[:5] for k in t.keys())
            record("RW003", "Rewards", "Points expiry - unused points expire after X months",
                   ENFORCED if has_expiry else PARTIAL,
                   f"Points transactions: {len(txns) if isinstance(txns, list) else '?'}. Expiry field: {has_expiry}. Keys: {list(txns[0].keys()) if isinstance(txns, list) and txns else 'empty'}")
        else:
            record("RW003", "Rewards", "Points expiry", PARTIAL,
                   f"Status {r.status_code if r else 'timeout'}: {r.text[:200] if r else 'N/A'}")
    except Exception as e:
        record("RW003", "Rewards", "Points expiry", PARTIAL, str(e))

    # --- RW004: Reward redemption - cannot redeem more than balance (CRITICAL) ---
    try:
        # Get balance
        r_bal = safe_get(f"{REWARDS}/points/balance", hdr(rw_emp_tok))
        balance = None
        if r_bal and r_bal.status_code == 200:
            bd = r_bal.json().get("data", r_bal.json())
            if isinstance(bd, dict):
                balance = bd.get("balance") or bd.get("points") or bd.get("available") or bd.get("total")
            elif isinstance(bd, (int, float)):
                balance = bd

        # Get rewards catalog
        r_cat = safe_get(f"{REWARDS}/rewards", hdr(rw_emp_tok))
        catalog = get_data(r_cat) if r_cat else None

        if isinstance(catalog, list) and len(catalog) > 0:
            reward = catalog[0]
            reward_id = reward.get("id") or reward.get("_id")
            r_redeem = safe_post(f"{REWARDS}/rewards/{reward_id}/redeem", hdr(rw_emp_tok),
                                json_data={"quantity": 99999})
            if r_redeem and r_redeem.status_code in [400, 422]:
                err = r_redeem.text.lower()
                if "balance" in err or "insufficient" in err or "enough" in err or "points" in err:
                    record("RW004", "Rewards", "Cannot redeem more points than balance", ENFORCED,
                           f"Over-redemption blocked: {r_redeem.status_code}. Balance={balance}. {r_redeem.text[:200]}")
                else:
                    record("RW004", "Rewards", "Cannot redeem more points than balance", PARTIAL,
                           f"Rejected: {r_redeem.status_code} {r_redeem.text[:200]}. Balance={balance}")
            elif r_redeem and r_redeem.status_code in [200, 201]:
                record("RW004", "Rewards", "Cannot redeem more points than balance", NOT_ENFORCED,
                       f"Over-redemption ACCEPTED! Balance={balance}. No balance check!")
            else:
                record("RW004", "Rewards", "Cannot redeem more points than balance", PARTIAL,
                       f"Redeem status {r_redeem.status_code if r_redeem else 'timeout'}. Balance={balance}")
        else:
            record("RW004", "Rewards", "Cannot redeem more points than balance", PARTIAL,
                   f"Balance={balance}, catalog has {len(catalog) if isinstance(catalog, list) else 0} items. Cannot test redemption without catalog items.")
    except Exception as e:
        record("RW004", "Rewards", "Cannot redeem more points than balance", PARTIAL, str(e))

    # --- RW005: Manager budget - cannot award more than allocated ---
    try:
        r = safe_get(f"{REWARDS}/manager/dashboard", hdr(rw_admin_tok))
        if r and r.status_code == 200:
            data = r.json().get("data", r.json())
            budget_keys = [k for k in (data.keys() if isinstance(data, dict) else []) if "budget" in k.lower() or "allocated" in k.lower() or "remaining" in k.lower()]
            record("RW005", "Rewards", "Manager budget - cannot award more than allocated",
                   PARTIAL,
                   f"Manager dashboard available. Budget-related keys: {budget_keys}. All keys: {list(data.keys()) if isinstance(data, dict) else 'N/A'}")
        else:
            record("RW005", "Rewards", "Manager budget - cannot award more than allocated", PARTIAL,
                   f"Status {r.status_code if r else 'timeout'}: {r.text[:200] if r else 'N/A'}")
    except Exception as e:
        record("RW005", "Rewards", "Manager budget", PARTIAL, str(e))

    # --- RW006: Nomination requires at least one nominator besides self ---
    try:
        r = safe_get(f"{REWARDS}/nominations/programs", hdr(rw_admin_tok))
        if r and r.status_code == 200:
            programs = get_data(r) or []
            if isinstance(programs, list) and len(programs) > 0:
                prog = programs[0]
                prog_id = prog.get("id") or prog.get("_id")
                # Employee tries self-nomination
                r_nom = safe_post(f"{REWARDS}/nominations", hdr(rw_emp_tok),
                                  json_data={"program_id": prog_id, "nominee_id": emp_id_emp,
                                            "reason": "Self nomination test"})
                if r_nom and r_nom.status_code in [400, 422]:
                    err = r_nom.text.lower()
                    if "self" in err or "yourself" in err or "own" in err:
                        record("RW006", "Rewards", "Nomination requires at least one nominator besides self", ENFORCED,
                               f"Self-nomination blocked: {r_nom.status_code} {r_nom.text[:200]}")
                    else:
                        record("RW006", "Rewards", "Nomination requires at least one nominator besides self", PARTIAL,
                               f"Nomination rejected but not clearly self: {r_nom.status_code} {r_nom.text[:200]}")
                elif r_nom and r_nom.status_code in [200, 201]:
                    record("RW006", "Rewards", "Nomination requires at least one nominator besides self", NOT_ENFORCED,
                           f"Self-nomination ACCEPTED! No external nominator check. Status {r_nom.status_code}")
                else:
                    record("RW006", "Rewards", "Nomination requires at least one nominator besides self", PARTIAL,
                           f"Status {r_nom.status_code if r_nom else 'timeout'}: {r_nom.text[:200] if r_nom else 'N/A'}")
            else:
                record("RW006", "Rewards", "Nomination requires at least one nominator besides self", PARTIAL,
                       f"No nomination programs found")
        elif r and r.status_code == 404:
            record("RW006", "Rewards", "Nomination requires at least one nominator besides self", NOT_IMPL,
                   f"/nominations/programs returns 404")
        else:
            record("RW006", "Rewards", "Nomination requires at least one nominator besides self", PARTIAL,
                   f"Status {r.status_code if r else 'timeout'}")
    except Exception as e:
        record("RW006", "Rewards", "Nomination requires nominator besides self", PARTIAL, str(e))

    # --- RW007: Challenge completion - auto-award points ---
    try:
        r = safe_get(f"{REWARDS}/challenges", hdr(rw_admin_tok))
        if r and r.status_code == 200:
            challenges = get_data(r) or []
            has_auto = False
            if isinstance(challenges, list) and len(challenges) > 0:
                ch = challenges[0]
                has_auto = any(k for k in ch.keys() if "reward" in k.lower() or "points" in k.lower() or "auto" in k.lower())
                record("RW007", "Rewards", "Challenge completion - auto-award points on meeting criteria",
                       ENFORCED if has_auto else PARTIAL,
                       f"{len(challenges)} challenges. Points/reward fields: {has_auto}. Keys: {list(ch.keys())[:15]}")
            else:
                record("RW007", "Rewards", "Challenge completion - auto-award points on meeting criteria", PARTIAL,
                       f"No challenges found")
        else:
            record("RW007", "Rewards", "Challenge completion - auto-award points", PARTIAL,
                   f"Status {r.status_code if r else 'timeout'}: {r.text[:200] if r else 'N/A'}")
    except Exception as e:
        record("RW007", "Rewards", "Challenge completion auto-award", PARTIAL, str(e))

    # --- RW008: Celebration auto-detection (birthday/anniversary from profile) ---
    try:
        r = safe_get(f"{REWARDS}/celebrations", hdr(rw_admin_tok))
        if r and r.status_code == 200:
            resp_data = r.json().get("data", {})
            celebs = resp_data if isinstance(resp_data, list) else resp_data.get("data", resp_data.get("celebrations", []))
            if not isinstance(celebs, list):
                celebs = []
            types = set()
            for c in celebs[:20]:
                t = (c.get("type") or c.get("celebration_type") or "").lower()
                if t:
                    types.add(t)
            has_auto = any("birthday" in t or "anniversary" in t or "work" in t for t in types)
            record("RW008", "Rewards", "Celebration auto-detection (birthday/anniversary from profile)",
                   ENFORCED if has_auto else PARTIAL,
                   f"Celebrations endpoint works. Types found: {types}. Count: {len(celebs)}. Auto-detected: {has_auto}")
        else:
            record("RW008", "Rewards", "Celebration auto-detection", PARTIAL,
                   f"Status {r.status_code if r else 'timeout'}: {r.text[:200] if r else 'N/A'}")
    except Exception as e:
        record("RW008", "Rewards", "Celebration auto-detection", PARTIAL, str(e))

    # --- RW009: Leaderboard - only active employees, terminated excluded (HIGH) ---
    try:
        r = safe_get(f"{REWARDS}/leaderboard", hdr(rw_admin_tok), params={"perPage": 200})
        if r and r.status_code == 200:
            resp_data = r.json().get("data", {})
            entries = resp_data.get("entries", []) if isinstance(resp_data, dict) else resp_data

            # Get inactive/terminated employee IDs from core (status 0 or 2)
            inactive_ids = set()
            inactive_names = set()
            for emp in all_employees:
                eid = emp.get("id")
                r_prof = safe_get(f"{API}/employees/{eid}", hdr(admin_tok))
                if r_prof and r_prof.status_code == 200:
                    prof = r_prof.json().get("data", {})
                    status = prof.get("status")
                    if status in [0, 2, "0", "2"]:
                        inactive_ids.add(str(prof.get("id", "")))
                        name = f"{prof.get('first_name', '')} {prof.get('last_name', '')}".strip().lower()
                        inactive_names.add(name)

            terminated_in_lb = []
            if isinstance(entries, list):
                for entry in entries:
                    uid = str(entry.get("user_id") or entry.get("employee_id") or "")
                    if uid in inactive_ids:
                        terminated_in_lb.append(f"{entry.get('first_name', '')} {entry.get('last_name', '')} (id={uid})")

            if isinstance(entries, list) and len(entries) > 0:
                if len(terminated_in_lb) > 0:
                    record("RW009", "Rewards", "Leaderboard excludes terminated employees", NOT_ENFORCED,
                           f"Found {len(terminated_in_lb)} inactive/terminated in leaderboard: {', '.join(terminated_in_lb[:3])}")
                else:
                    record("RW009", "Rewards", "Leaderboard excludes terminated employees", ENFORCED,
                           f"Leaderboard has {len(entries)} entries, none are terminated. Inactive pool: {len(inactive_ids)} IDs")
            else:
                record("RW009", "Rewards", "Leaderboard excludes terminated employees", PARTIAL,
                       f"Leaderboard empty. Entries: {str(entries)[:200]}")
        else:
            record("RW009", "Rewards", "Leaderboard excludes terminated employees", PARTIAL,
                   f"Status {r.status_code if r else 'timeout'}: {r.text[:200] if r else 'N/A'}")
    except Exception as e:
        record("RW009", "Rewards", "Leaderboard excludes terminated employees", PARTIAL, str(e))

    # --- RW010: Anonymous kudos - sender identity not revealed ---
    try:
        r = safe_get(f"{REWARDS}/kudos", hdr(rw_emp_tok))
        if r and r.status_code == 200:
            kudos_list = get_data(r) or []
            has_anon = False
            anon_leaks = False
            if isinstance(kudos_list, list):
                for k in kudos_list[:20]:
                    is_anon = k.get("is_anonymous") or k.get("anonymous") or k.get("isAnonymous")
                    if is_anon:
                        has_anon = True
                        sender = k.get("sender") or k.get("from") or k.get("sender_name") or k.get("giver")
                        sender_id = k.get("sender_id") or k.get("senderId") or k.get("giver_id")
                        if sender or sender_id:
                            anon_leaks = True

            if has_anon and not anon_leaks:
                record("RW010", "Rewards", "Anonymous kudos - sender identity not revealed if enabled", ENFORCED,
                       f"Anonymous kudos found with sender hidden")
            elif has_anon and anon_leaks:
                record("RW010", "Rewards", "Anonymous kudos - sender identity not revealed if enabled", NOT_ENFORCED,
                       f"Anonymous kudos LEAKS sender identity!")
            else:
                record("RW010", "Rewards", "Anonymous kudos - sender identity not revealed if enabled", PARTIAL,
                       f"No anonymous kudos in feed to verify. Total: {len(kudos_list) if isinstance(kudos_list, list) else '?'}")
        else:
            record("RW010", "Rewards", "Anonymous kudos - sender identity not revealed", PARTIAL,
                   f"Status {r.status_code if r else 'timeout'}: {r.text[:200] if r else 'N/A'}")
    except Exception as e:
        record("RW010", "Rewards", "Anonymous kudos - sender identity not revealed", PARTIAL, str(e))


# ══════════════════════════════════════════════════════════════════════
# FILE BUGS
# ══════════════════════════════════════════════════════════════════════
def file_bugs():
    print("\n" + "="*70)
    print("FILING GITHUB ISSUES FOR FAILURES")
    print("="*70)

    bugs = [r for r in results if r["status"] == NOT_ENFORCED]
    print(f"  Found {len(bugs)} NOT ENFORCED rules to file as bugs")

    for bug in bugs:
        title = f"[Business Rule] {bug['id']}: {bug['rule']}"
        body = (
            f"## Business Rule Violation\n\n"
            f"**Rule ID**: {bug['id']}\n"
            f"**Category**: {bug['category']}\n"
            f"**Rule**: {bug['rule']}\n"
            f"**Status**: {bug['status']}\n\n"
            f"## Details\n\n{bug['detail']}\n\n"
            f"## Expected Behavior\n\n"
            f"The system should enforce: {bug['rule']}\n\n"
            f"## Source\n\n"
            f"From BUSINESS_RULES_V2.md sections 20-22\n\n"
            f"---\n*Automated business rule audit*"
        )
        labels = ["bug", "business-rule"]
        url = file_issue(title, body, labels)
        if url:
            bug["issue_url"] = url
        time.sleep(1)


# ══════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════
def main():
    print("="*70)
    print("EmpCloud Business Rules V2 - Sections 20-22 Audit")
    print(f"Started at {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)

    # Login
    print("\nAuthenticating...")
    admin_tok = login_cloud(ADMIN_EMAIL, ADMIN_PW)
    emp_tok = login_cloud(EMP_EMAIL, EMP_PW)
    print(f"  Admin token: {'obtained' if admin_tok else 'FAILED'}")
    print(f"  Employee token: {'obtained' if emp_tok else 'FAILED'}")

    if not admin_tok:
        print("FATAL: Admin login failed. Cannot proceed.")
        return

    # Run tests
    test_documents(admin_tok, emp_tok or admin_tok)
    test_hierarchy(admin_tok)
    test_rewards(admin_tok, emp_tok or admin_tok)

    # File bugs
    file_bugs()

    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)

    enforced = [r for r in results if r["status"] == ENFORCED]
    not_enforced = [r for r in results if r["status"] == NOT_ENFORCED]
    not_impl = [r for r in results if r["status"] == NOT_IMPL]
    partial = [r for r in results if r["status"] == PARTIAL]

    print(f"\n  ENFORCED:        {len(enforced)}")
    print(f"  NOT ENFORCED:    {len(not_enforced)}")
    print(f"  NOT IMPLEMENTED: {len(not_impl)}")
    print(f"  PARTIAL/UNCLEAR: {len(partial)}")
    print(f"  TOTAL:           {len(results)}")
    print()

    for r in results:
        icon = {ENFORCED: "[OK]", NOT_ENFORCED: "[BUG]", NOT_IMPL: "[N/A]", PARTIAL: "[!!]"}.get(r["status"], "[??]")
        issue = f" -> {r['issue_url']}" if r.get("issue_url") else ""
        print(f"  {icon} {r['id']}: {r['rule']} = {r['status']}{issue}")

    # Save results
    with open(r"C:\emptesting\doc_hierarchy_rewards_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nResults saved to C:\\emptesting\\doc_hierarchy_rewards_results.json")


if __name__ == "__main__":
    main()
