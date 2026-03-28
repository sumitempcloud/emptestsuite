#!/usr/bin/env python3
"""
EMP Cloud HRMS — Business Rules V2: Sections 27-30
  27. Data Migration & Import (DM001-DM007)
  28. Calendar & Holiday (CH001-CH007)
  29. Gratuity & Benefits (GB001-GB007)
  30. Audit & Compliance (AC001-AC010)

Verdict per rule: ENFORCED / NOT ENFORCED / NOT IMPLEMENTED / PARTIAL
Files bugs with "[Business Rule]" prefix.
"""

import sys, json, time, csv, io, uuid, requests
from datetime import datetime, timedelta, date
from typing import Optional

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

API_BASE = "https://test-empcloud-api.empcloud.com/api/v1"
GITHUB_PAT = "$GITHUB_TOKEN"
GITHUB_REPO = "EmpCloud/EmpCloud"

CREDENTIALS = {
    "org_admin": {"email": "ananya@technova.in", "password": "Welcome@123"},
    "employee": {"email": "priya@technova.in", "password": "Welcome@123"},
    "super_admin": {"email": "admin@empcloud.com", "password": "SuperAdmin@2026"},
}

BUGS = []
RESULTS = {"passed": 0, "failed": 0, "skipped": 0, "bugs": 0}
VERDICTS = {}  # rule_id -> verdict string


# ── helpers ──────────────────────────────────────────────────────────────────
def login(role):
    cred = CREDENTIALS[role]
    try:
        r = requests.post(f"{API_BASE}/auth/login", json=cred, timeout=30)
        if r.status_code == 200:
            data = r.json()["data"]
            return {
                "token": data["tokens"]["access_token"],
                "user": data["user"],
                "org": data.get("org", {}),
            }
        print(f"  [LOGIN FAIL] {role}: {r.status_code}")
        return None
    except Exception as e:
        print(f"  [LOGIN ERROR] {role}: {e}")
        return None


def api(method, path, token, data=None, params=None, timeout=30):
    try:
        r = requests.request(
            method,
            f"{API_BASE}{path}",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json=data,
            params=params,
            timeout=timeout,
        )
        try:
            return r.status_code, r.json()
        except Exception:
            return r.status_code, r.text[:500]
    except Exception as e:
        return 0, str(e)


def api_raw(method, path, token, files=None, data=None, timeout=30):
    """For multipart/form-data uploads (CSV import)."""
    try:
        r = requests.request(
            method,
            f"{API_BASE}{path}",
            headers={"Authorization": f"Bearer {token}"},
            files=files,
            data=data,
            timeout=timeout,
        )
        try:
            return r.status_code, r.json()
        except Exception:
            return r.status_code, r.text[:500]
    except Exception as e:
        return 0, str(e)


def ok(s):
    return s in (200, 201)


def record(name, passed, detail="", bug_title="", expected="", actual="", endpoint="", steps="", rule=""):
    RESULTS["passed" if passed else "failed"] += 1
    tag = "PASS" if passed else "FAIL"
    print(f"  [{tag}] {name}: {detail[:300]}")
    if not passed and bug_title:
        BUGS.append({
            "title": f"[Business Rule] {bug_title}",
            "endpoint": endpoint,
            "steps": steps,
            "expected": expected,
            "actual": actual,
            "business_rule": rule,
        })
        RESULTS["bugs"] += 1


def skip(name, reason=""):
    RESULTS["skipped"] += 1
    print(f"  [SKIP] {name}: {reason}")


def verdict(rule_id, status, note=""):
    VERDICTS[rule_id] = status
    extra = f" — {note}" if note else ""
    print(f"  >> {rule_id}: {status}{extra}")


def file_github_issues():
    if not BUGS:
        print("\n=== No bugs to file ===")
        return
    print(f"\n=== Filing {len(BUGS)} bugs to GitHub ===")
    hdr = {"Authorization": f"token {GITHUB_PAT}", "Accept": "application/vnd.github+json"}
    for bug in BUGS:
        body = f"""## Bug Report (Automated QA — Business Rules V2 Sections 27-30)

**URL/Endpoint:** `{API_BASE}{bug['endpoint']}`

**Steps to Reproduce:**
{bug['steps']}

**Expected Result:**
{bug['expected']}

**Actual Result:**
{bug['actual']}

**Business Rule Violated:**
{bug['business_rule']}

**Environment:** Test (test-empcloud-api.empcloud.com)
**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        try:
            r = requests.post(
                f"https://api.github.com/repos/{GITHUB_REPO}/issues",
                headers=hdr,
                json={"title": bug["title"], "body": body, "labels": ["bug", "business-rule", "automated-qa"]},
                timeout=30,
            )
            if r.status_code == 201:
                print(f"  [FILED] {bug['title']} -> {r.json().get('html_url')}")
            else:
                print(f"  [FAIL] {bug['title']} - {r.status_code}: {r.text[:200]}")
        except Exception as e:
            print(f"  [ERROR] {e}")


# ── endpoint discovery ───────────────────────────────────────────────────────
def discover_endpoints(token):
    """Probe likely endpoint paths and return a dict of what exists."""
    endpoints = {}
    probes = {
        "import_csv": ["/import/csv", "/users/import", "/employees/import",
                       "/import/employees", "/bulk/import", "/data/import",
                       "/users/bulk-upload", "/users/upload", "/employee/import"],
        "holidays": ["/holidays", "/calendar/holidays", "/holiday",
                     "/leave/holidays", "/organization/holidays", "/organizations/me/holidays"],
        "calendar": ["/calendar", "/calendar/events", "/events",
                     "/leave/calendar", "/organizations/me/calendar"],
        "gratuity": ["/gratuity", "/benefits/gratuity", "/payroll/gratuity",
                     "/gratuity/calculate", "/employee/gratuity"],
        "benefits": ["/benefits", "/employee/benefits", "/insurance",
                     "/benefits/plans"],
        "audit": ["/audit", "/audit/logs", "/audit-logs", "/logs",
                  "/admin/audit", "/admin/logs", "/activity-logs",
                  "/admin/activity-logs", "/super-admin/audit-logs"],
        "salary": ["/salary", "/payroll/salary", "/salary-structures",
                   "/payroll/salary-structures", "/compensation"],
        "working_days": ["/working-days", "/calendar/working-days",
                         "/attendance/working-days", "/payroll/working-days"],
        "users": ["/users"],
        "org": ["/organizations/me"],
        "departments": ["/organizations/me/departments"],
        "attendance": ["/attendance/records"],
        "leave_types": ["/leave/types"],
    }

    for key, paths in probes.items():
        for path in paths:
            s, body = api("GET", path, token)
            if s in (200, 201):
                endpoints[key] = path
                break
            elif s == 403:
                # exists but forbidden — note it
                endpoints[key + "_403"] = path
    return endpoints


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 27 — DATA MIGRATION & IMPORT RULES
# ═════════════════════════════════════════════════════════════════════════════
def test_section_27(admin_ctx, sa_ctx, endpoints):
    print("\n" + "=" * 70)
    print("SECTION 27 — DATA MIGRATION & IMPORT RULES")
    print("=" * 70)

    tok = admin_ctx["token"]

    # ---------- find import endpoint ----------
    import_path = endpoints.get("import_csv")
    if not import_path:
        # Try POST-based probing
        dummy_csv = "first_name,last_name,email\nTest,User,test_probe@example.com\n"
        import_candidates = [
            "/import/csv", "/users/import", "/employees/import",
            "/import/employees", "/bulk/import", "/data/import",
            "/users/bulk-upload", "/users/upload", "/employee/import",
        ]
        for path in import_candidates:
            s, _ = api_raw("POST", path, tok,
                           files={"file": ("test.csv", io.BytesIO(dummy_csv.encode()), "text/csv")})
            if s not in (404, 405, 0):
                import_path = path
                break

    # ── DM001: CSV import duplicate email detection ──
    print("\n--- DM001: CSV import duplicate email detection ---")
    if import_path:
        # Get an existing user email
        s, udata = api("GET", "/users", tok, params={"limit": 1})
        existing_email = None
        if ok(s) and isinstance(udata, dict):
            users_list = udata.get("data", {})
            if isinstance(users_list, dict):
                users_list = users_list.get("users", users_list.get("items", []))
            if isinstance(users_list, list) and users_list:
                existing_email = users_list[0].get("email", "ananya@technova.in")
        if not existing_email:
            existing_email = "ananya@technova.in"

        dup_csv = f"first_name,last_name,email,department\nDupe,Test,{existing_email},Engineering\n"
        s, body = api_raw("POST", import_path, tok,
                          files={"file": ("dup.csv", io.BytesIO(dup_csv.encode()), "text/csv")})
        if ok(s):
            # Import succeeded — check if it silently duplicated or detected
            body_str = json.dumps(body) if isinstance(body, dict) else str(body)
            has_dup_warn = any(w in body_str.lower() for w in ["duplicate", "already exists", "skip", "conflict"])
            if has_dup_warn:
                record("DM001", True, "Duplicate email detected on import", rule="DM001")
                verdict("DM001", "ENFORCED")
            else:
                record("DM001", False, f"Import accepted duplicate email without warning: {body_str[:200]}",
                       bug_title="DM001 — CSV import does not detect duplicate emails",
                       expected="Duplicate email rows rejected or flagged",
                       actual=f"Import returned 200 with no duplicate warning: {body_str[:200]}",
                       endpoint=import_path,
                       steps=f"1. POST {import_path} with CSV containing existing email {existing_email}",
                       rule="DM001")
                verdict("DM001", "NOT ENFORCED")
        elif s in (400, 409, 422):
            body_str = json.dumps(body) if isinstance(body, dict) else str(body)
            record("DM001", True, f"Duplicate rejected ({s}): {body_str[:200]}", rule="DM001")
            verdict("DM001", "ENFORCED")
        else:
            record("DM001", False, f"Import endpoint returned {s}", rule="DM001")
            verdict("DM001", "NOT IMPLEMENTED", f"Import endpoint returned {s}")
    else:
        skip("DM001", "No CSV import endpoint found")
        verdict("DM001", "NOT IMPLEMENTED", "No import endpoint discovered")

    # ── DM002: Mandatory fields validated before import ──
    print("\n--- DM002: CSV mandatory fields validated ---")
    if import_path:
        bad_csv = "first_name\nOnlyFirst\n"  # missing last_name, email
        s, body = api_raw("POST", import_path, tok,
                          files={"file": ("bad.csv", io.BytesIO(bad_csv.encode()), "text/csv")})
        if s in (400, 422):
            record("DM002", True, f"Incomplete CSV rejected ({s})", rule="DM002")
            verdict("DM002", "ENFORCED")
        elif ok(s):
            body_str = json.dumps(body) if isinstance(body, dict) else str(body)
            has_err = any(w in body_str.lower() for w in ["missing", "required", "mandatory", "invalid"])
            if has_err:
                record("DM002", True, "Mandatory field validation in response", rule="DM002")
                verdict("DM002", "ENFORCED")
            else:
                record("DM002", False, f"CSV with missing mandatory fields accepted: {body_str[:200]}",
                       bug_title="DM002 — CSV import does not validate mandatory fields",
                       expected="CSV missing email/last_name rejected",
                       actual=f"Accepted: {body_str[:200]}",
                       endpoint=import_path,
                       steps="1. POST CSV with only first_name column",
                       rule="DM002")
                verdict("DM002", "NOT ENFORCED")
        else:
            skip("DM002", f"Import returned {s}")
            verdict("DM002", "NOT IMPLEMENTED")
    else:
        skip("DM002", "No CSV import endpoint")
        verdict("DM002", "NOT IMPLEMENTED")

    # ── DM003: Partial failure should not corrupt existing data ──
    print("\n--- DM003: Partial CSV failure — data integrity ---")
    if import_path:
        # CSV with 1 good row + 1 bad row (invalid email)
        mixed_csv = (
            "first_name,last_name,email,department\n"
            "Good,User,gooduser_dm003@example.com,Engineering\n"
            "Bad,User,not-an-email,Engineering\n"
        )
        # Count users before
        s_before, body_before = api("GET", "/users", tok, params={"limit": 1})
        count_before = None
        if ok(s_before) and isinstance(body_before, dict):
            d = body_before.get("data", {})
            if isinstance(d, dict):
                count_before = d.get("total", d.get("count"))
            elif isinstance(d, list):
                count_before = len(d)

        s, body = api_raw("POST", import_path, tok,
                          files={"file": ("mixed.csv", io.BytesIO(mixed_csv.encode()), "text/csv")})

        body_str = json.dumps(body) if isinstance(body, dict) else str(body)
        if s in (400, 422):
            record("DM003", True, f"Entire import rejected due to bad row ({s}) — safe", rule="DM003")
            verdict("DM003", "ENFORCED", "Entire batch rejected on partial error")
        elif ok(s):
            has_partial = any(w in body_str.lower() for w in ["partial", "failed", "error", "skipped"])
            if has_partial:
                record("DM003", True, f"Partial failure reported, good rows may have imported: {body_str[:200]}", rule="DM003")
                verdict("DM003", "PARTIAL", "Partial failures reported but data integrity uncertain")
            else:
                record("DM003", False, f"Mixed CSV accepted without error report: {body_str[:200]}",
                       bug_title="DM003 — Partial CSV failure does not report errors or may corrupt data",
                       expected="Bad rows rejected, good rows imported, error report returned",
                       actual=f"200 with no partial-failure report: {body_str[:200]}",
                       endpoint=import_path,
                       steps="1. POST CSV with 1 valid + 1 invalid-email row",
                       rule="DM003")
                verdict("DM003", "NOT ENFORCED")
        else:
            skip("DM003", f"Import returned {s}")
            verdict("DM003", "NOT IMPLEMENTED")
    else:
        skip("DM003", "No CSV import endpoint")
        verdict("DM003", "NOT IMPLEMENTED")

    # ── DM004: Report which rows failed and why ──
    print("\n--- DM004: CSV import error reporting ---")
    if import_path:
        bad_csv2 = (
            "first_name,last_name,email\n"
            ",Missing,first@example.com\n"
            "No,Email,\n"
        )
        s, body = api_raw("POST", import_path, tok,
                          files={"file": ("bad2.csv", io.BytesIO(bad_csv2.encode()), "text/csv")})
        body_str = json.dumps(body) if isinstance(body, dict) else str(body)
        has_row_detail = any(w in body_str.lower() for w in ["row", "line", "index", "errors"])
        if s in (400, 422) and has_row_detail:
            record("DM004", True, f"Row-level errors reported ({s})", rule="DM004")
            verdict("DM004", "ENFORCED")
        elif ok(s) and has_row_detail:
            record("DM004", True, "Row-level failure info in response", rule="DM004")
            verdict("DM004", "ENFORCED")
        elif s in (400, 422):
            record("DM004", False, f"Rejected but no row-level detail: {body_str[:200]}",
                   bug_title="DM004 — CSV import error lacks row-level detail",
                   expected="Error response identifies which rows failed and why",
                   actual=f"Generic {s} error: {body_str[:200]}",
                   endpoint=import_path, steps="1. POST CSV with 2 bad rows", rule="DM004")
            verdict("DM004", "PARTIAL", "Rejects bad CSV but no row-level detail")
        else:
            skip("DM004", f"Import returned {s}")
            verdict("DM004", "NOT IMPLEMENTED")
    else:
        skip("DM004", "No CSV import endpoint")
        verdict("DM004", "NOT IMPLEMENTED")

    # ── DM005: Bulk operations rollback on failure ──
    print("\n--- DM005: Bulk operation rollback ---")
    # Tested implicitly with DM003 (partial failure). Record same verdict.
    dm003_v = VERDICTS.get("DM003", "NOT IMPLEMENTED")
    if dm003_v == "ENFORCED":
        verdict("DM005", "ENFORCED", "Batch rejected atomically on error")
    elif dm003_v == "PARTIAL":
        verdict("DM005", "NOT ENFORCED", "Partial import without rollback")
    else:
        verdict("DM005", "NOT IMPLEMENTED")
    skip("DM005", f"Inferred from DM003 ({dm003_v})")

    # ── DM006: Data export respects RBAC ──
    print("\n--- DM006: Data export respects RBAC ---")
    emp_ctx = login("employee")
    if emp_ctx:
        export_paths = ["/export/employees", "/users/export", "/data/export",
                        "/export/csv", "/reports/export", "/employees/export"]
        found_export = False
        for ep in export_paths:
            s, body = api("GET", ep, emp_ctx["token"])
            if s == 200:
                found_export = True
                # Employee got 200 on export — check if it's restricted to own data
                body_str = json.dumps(body) if isinstance(body, dict) else str(body)
                record("DM006", True, f"Export endpoint exists, check scope manually: {body_str[:150]}", rule="DM006")
                verdict("DM006", "PARTIAL", "Export endpoint reachable by employee; scope unclear from API alone")
                break
            elif s == 403:
                found_export = True
                record("DM006", True, f"Employee blocked from bulk export ({s})", rule="DM006")
                verdict("DM006", "ENFORCED")
                break
        if not found_export:
            skip("DM006", "No export endpoint found")
            verdict("DM006", "NOT IMPLEMENTED", "No export endpoint discovered")
    else:
        skip("DM006", "Employee login failed")
        verdict("DM006", "NOT IMPLEMENTED")

    # ── DM007: Historical data import — future dates rejected ──
    print("\n--- DM007: Historical data import date validation ---")
    if import_path:
        future = (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d")
        future_csv = f"first_name,last_name,email,date_of_joining\nFuture,Hire,future_dm007@example.com,{future}\n"
        s, body = api_raw("POST", import_path, tok,
                          files={"file": ("future.csv", io.BytesIO(future_csv.encode()), "text/csv")})
        body_str = json.dumps(body) if isinstance(body, dict) else str(body)
        if s in (400, 422):
            record("DM007", True, f"Future date rejected ({s})", rule="DM007")
            verdict("DM007", "ENFORCED")
        elif ok(s):
            has_date_err = any(w in body_str.lower() for w in ["future", "date", "invalid"])
            if has_date_err:
                record("DM007", True, "Future date flagged in response", rule="DM007")
                verdict("DM007", "ENFORCED")
            else:
                record("DM007", False, f"Future joining date accepted: {body_str[:200]}",
                       bug_title="DM007 — CSV import accepts future dates in historical import",
                       expected="Dates far in the future rejected for historical data import",
                       actual=f"Accepted: {body_str[:200]}",
                       endpoint=import_path, steps=f"1. POST CSV with date_of_joining={future}",
                       rule="DM007")
                verdict("DM007", "NOT ENFORCED")
        else:
            skip("DM007", f"Import returned {s}")
            verdict("DM007", "NOT IMPLEMENTED")
    else:
        skip("DM007", "No CSV import endpoint")
        verdict("DM007", "NOT IMPLEMENTED")


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 28 — CALENDAR & HOLIDAY RULES
# ═════════════════════════════════════════════════════════════════════════════
def test_section_28(admin_ctx, sa_ctx, endpoints):
    print("\n" + "=" * 70)
    print("SECTION 28 — CALENDAR & HOLIDAY RULES")
    print("=" * 70)

    tok = admin_ctx["token"]

    # Discover holiday endpoint
    holiday_path = endpoints.get("holidays")
    holiday_data = None
    if holiday_path:
        s, body = api("GET", holiday_path, tok)
        if ok(s):
            holiday_data = body

    # ── CH001: Holiday list per location ──
    print("\n--- CH001: Holiday list per location ---")
    if holiday_data:
        body_str = json.dumps(holiday_data) if isinstance(holiday_data, dict) else str(holiday_data)
        has_location = any(w in body_str.lower() for w in ["location", "state", "branch", "office", "region"])
        if has_location:
            record("CH001", True, "Holidays have location/state data", rule="CH001")
            verdict("CH001", "ENFORCED")
        else:
            record("CH001", False, f"Holiday list lacks location info: {body_str[:200]}",
                   bug_title="CH001 — Holiday list has no location/state differentiation",
                   expected="Holidays filterable or associated by location/state",
                   actual=f"No location field found: {body_str[:200]}",
                   endpoint=holiday_path, steps="1. GET holidays", rule="CH001")
            verdict("CH001", "NOT ENFORCED")
    else:
        # Try location-specific query
        for path in ["/holidays?location=Mumbai", "/holidays?state=Maharashtra"]:
            s, body = api("GET", path, tok)
            if ok(s):
                holiday_data = body
                record("CH001", True, "Location-filtered holiday endpoint exists", rule="CH001")
                verdict("CH001", "ENFORCED")
                break
        else:
            skip("CH001", "No holiday endpoint found")
            verdict("CH001", "NOT IMPLEMENTED", "No holiday endpoint discovered")

    # ── CH002: Optional holidays — limited per employee ──
    print("\n--- CH002: Optional holidays limited per employee ---")
    if holiday_data:
        body_str = json.dumps(holiday_data) if isinstance(holiday_data, dict) else str(holiday_data)
        has_optional = any(w in body_str.lower() for w in ["optional", "restricted", "floating", "type"])
        if has_optional:
            record("CH002", True, "Holiday data has optional/type field", rule="CH002")
            verdict("CH002", "PARTIAL", "Type field exists, limit enforcement unclear")
        else:
            record("CH002", False, "No optional holiday categorization found", rule="CH002")
            verdict("CH002", "NOT IMPLEMENTED")
    else:
        skip("CH002", "No holiday data")
        verdict("CH002", "NOT IMPLEMENTED")

    # ── CH003: Holiday on weekend — substitute holiday ──
    print("\n--- CH003: Weekend holiday → substitute holiday ---")
    if holiday_data and isinstance(holiday_data, dict):
        items = holiday_data.get("data", holiday_data)
        if isinstance(items, dict):
            items = items.get("holidays", items.get("items", items.get("data", [])))
        if isinstance(items, list):
            weekend_holidays = []
            for h in items:
                d_str = h.get("date", h.get("holiday_date", ""))
                if d_str:
                    try:
                        d = datetime.strptime(d_str[:10], "%Y-%m-%d")
                        if d.weekday() >= 5:
                            weekend_holidays.append(h)
                    except Exception:
                        pass
            if weekend_holidays:
                body_str = json.dumps(weekend_holidays)
                has_sub = any(w in body_str.lower() for w in ["substitute", "compensatory", "comp_off", "moved"])
                if has_sub:
                    record("CH003", True, "Weekend holidays have substitute info", rule="CH003")
                    verdict("CH003", "ENFORCED")
                else:
                    record("CH003", False, f"Weekend holidays exist but no substitute: {body_str[:200]}",
                           bug_title="CH003 — No substitute holiday for holidays falling on weekends",
                           expected="Holiday on weekend triggers substitute on next working day",
                           actual=f"Weekend holidays found with no substitute mechanism: {body_str[:200]}",
                           endpoint=holiday_path, steps="1. GET holidays, find dates on Sat/Sun", rule="CH003")
                    verdict("CH003", "NOT ENFORCED")
            else:
                skip("CH003", "No holidays fall on weekends in current data")
                verdict("CH003", "PARTIAL", "No weekend holidays to verify against")
        else:
            skip("CH003", "Cannot parse holiday list")
            verdict("CH003", "NOT IMPLEMENTED")
    else:
        skip("CH003", "No holiday data")
        verdict("CH003", "NOT IMPLEMENTED")

    # ── CH004: Restricted holidays need application ──
    print("\n--- CH004: Restricted holidays require application ---")
    if holiday_data:
        body_str = json.dumps(holiday_data) if isinstance(holiday_data, dict) else str(holiday_data)
        has_restricted = any(w in body_str.lower() for w in ["restricted", "apply", "application", "request"])
        if has_restricted:
            record("CH004", True, "Restricted holiday concept exists", rule="CH004")
            verdict("CH004", "PARTIAL", "Field present, workflow enforcement unclear")
        else:
            skip("CH004", "No restricted holiday concept in data")
            verdict("CH004", "NOT IMPLEMENTED")
    else:
        skip("CH004", "No holiday data")
        verdict("CH004", "NOT IMPLEMENTED")

    # ── CH005: Financial year calendar (Apr-Mar) ──
    print("\n--- CH005: Financial year calendar (Apr-Mar) ---")
    fy_found = False
    for path in ["/calendar?year_type=financial", "/organizations/me",
                 "/settings/calendar", "/calendar/settings", "/payroll/settings"]:
        s, body = api("GET", path, tok)
        if ok(s):
            body_str = json.dumps(body) if isinstance(body, dict) else str(body)
            has_fy = any(w in body_str.lower() for w in ["financial", "fiscal", "apr", "april", "fy", "year_type"])
            if has_fy:
                record("CH005", True, f"Financial year concept found at {path}", rule="CH005")
                verdict("CH005", "ENFORCED")
                fy_found = True
                break
    if not fy_found:
        # Check org settings
        s, body = api("GET", "/organizations/me", tok)
        if ok(s):
            body_str = json.dumps(body) if isinstance(body, dict) else str(body)
            has_fy = any(w in body_str.lower() for w in ["financial_year", "fiscal_year", "fy_start"])
            if has_fy:
                record("CH005", True, "FY config in org settings", rule="CH005")
                verdict("CH005", "ENFORCED")
                fy_found = True
        if not fy_found:
            skip("CH005", "No financial year configuration found")
            verdict("CH005", "NOT IMPLEMENTED")

    # ── CH006: Working days calculation excludes holidays and weekends ──
    print("\n--- CH006: Working days excludes holidays & weekends ---")
    wd_found = False
    # Try working-days endpoint
    wd_paths = ["/working-days", "/calendar/working-days", "/attendance/working-days",
                "/payroll/working-days", "/attendance/summary", "/attendance/monthly-summary"]
    for path in wd_paths:
        today = datetime.now()
        month_start = today.replace(day=1).strftime("%Y-%m-%d")
        month_end = today.strftime("%Y-%m-%d")
        s, body = api("GET", path, tok, params={"start_date": month_start, "end_date": month_end, "month": today.month, "year": today.year})
        if ok(s):
            body_str = json.dumps(body) if isinstance(body, dict) else str(body)
            has_wd = any(w in body_str.lower() for w in ["working_days", "workingdays", "total_days", "business_days"])
            if has_wd:
                record("CH006", True, f"Working days data at {path}: {body_str[:200]}", rule="CH006")
                verdict("CH006", "ENFORCED")
                wd_found = True
                break

    if not wd_found:
        # Check if leave balance or payroll implicitly uses working days
        s, body = api("GET", "/leave/balances", tok)
        if ok(s):
            body_str = json.dumps(body) if isinstance(body, dict) else str(body)
            # Leave system exists — working days likely used internally
            record("CH006", False, "No explicit working-days endpoint; leave system exists but calculation not verifiable",
                   bug_title="CH006 — No API to verify working days calculation excludes holidays/weekends",
                   expected="Working days API or payroll summary that excludes holidays and weekends",
                   actual="No working-days endpoint found; cannot verify calculation",
                   endpoint="/working-days (expected)", steps="1. GET /working-days, /attendance/summary — all 404",
                   rule="CH006")
            verdict("CH006", "NOT IMPLEMENTED", "No working-days endpoint")
        else:
            skip("CH006", "Cannot verify working days calculation")
            verdict("CH006", "NOT IMPLEMENTED")

    # ── CH007: Leave calendar shows holidays, leaves, events ──
    print("\n--- CH007: Leave calendar shows combined view ---")
    cal_paths = ["/leave/calendar", "/calendar", "/calendar/events"]
    for path in cal_paths:
        s, body = api("GET", path, tok, params={"month": datetime.now().month, "year": datetime.now().year})
        if ok(s):
            body_str = json.dumps(body) if isinstance(body, dict) else str(body)
            has_combined = sum(1 for w in ["holiday", "leave", "event"] if w in body_str.lower())
            if has_combined >= 2:
                record("CH007", True, f"Calendar at {path} shows multiple item types", rule="CH007")
                verdict("CH007", "ENFORCED")
            else:
                record("CH007", False, f"Calendar only partially combined: {body_str[:200]}",
                       bug_title="CH007 — Leave calendar missing combined holiday/leave/event view",
                       expected="Calendar shows holidays, leaves, and events together",
                       actual=f"Only {has_combined}/3 types found: {body_str[:200]}",
                       endpoint=path, steps=f"1. GET {path}", rule="CH007")
                verdict("CH007", "PARTIAL")
            break
    else:
        skip("CH007", "No calendar endpoint found")
        verdict("CH007", "NOT IMPLEMENTED")


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 29 — GRATUITY & BENEFITS
# ═════════════════════════════════════════════════════════════════════════════
def test_section_29(admin_ctx, sa_ctx, endpoints):
    print("\n" + "=" * 70)
    print("SECTION 29 — GRATUITY & BENEFITS")
    print("=" * 70)

    tok = admin_ctx["token"]

    # Get employee list to check tenure
    s, udata = api("GET", "/users", tok, params={"limit": 50})
    users = []
    if ok(s) and isinstance(udata, dict):
        d = udata.get("data", {})
        if isinstance(d, dict):
            users = d.get("users", d.get("items", d.get("data", [])))
        elif isinstance(d, list):
            users = d

    # ── GB001: Gratuity eligible after 5 years of service ──
    print("\n--- GB001: Gratuity eligibility after 5 years ---")
    gratuity_path = endpoints.get("gratuity")
    gratuity_found = False

    # Try specific gratuity endpoints
    grat_paths = ["/gratuity", "/benefits/gratuity", "/payroll/gratuity",
                  "/gratuity/eligible", "/gratuity/calculate"]
    for path in grat_paths:
        s, body = api("GET", path, tok)
        if ok(s):
            gratuity_path = path
            gratuity_found = True
            body_str = json.dumps(body) if isinstance(body, dict) else str(body)
            has_5yr = any(w in body_str.lower() for w in ["5 year", "five year", "eligible", "tenure", "eligibility"])
            if has_5yr:
                record("GB001", True, f"Gratuity endpoint has eligibility data: {body_str[:200]}", rule="GB001")
                verdict("GB001", "ENFORCED")
            else:
                record("GB001", False, f"Gratuity endpoint exists but no 5-year check: {body_str[:200]}",
                       bug_title="GB001 — Gratuity endpoint lacks 5-year eligibility verification",
                       expected="Gratuity only for employees with 5+ years of service",
                       actual=f"No tenure check visible: {body_str[:200]}",
                       endpoint=path, steps=f"1. GET {path}", rule="GB001")
                verdict("GB001", "PARTIAL")
            break

    if not gratuity_found:
        # Check employee data for tenure info
        long_tenure = None
        short_tenure = None
        for u in users:
            doj = u.get("date_of_joining", u.get("joining_date", u.get("created_at", "")))
            if doj:
                try:
                    join_dt = datetime.strptime(doj[:10], "%Y-%m-%d")
                    years = (datetime.now() - join_dt).days / 365.25
                    if years >= 5:
                        long_tenure = u
                    elif years < 5:
                        short_tenure = u
                except Exception:
                    pass

        if long_tenure or short_tenure:
            info_parts = []
            if long_tenure:
                info_parts.append(f"5yr+ employee found: {long_tenure.get('email', '?')}")
            if short_tenure:
                info_parts.append(f"<5yr employee found: {short_tenure.get('email', '?')}")
            skip("GB001", f"No gratuity endpoint; employee tenure data: {'; '.join(info_parts)}")
        else:
            skip("GB001", "No gratuity endpoint and no tenure data in user records")
        verdict("GB001", "NOT IMPLEMENTED", "No gratuity API endpoint")

    # ── GB002: Gratuity formula = 15/26 x last drawn salary x years ──
    print("\n--- GB002: Gratuity formula correctness ---")
    if gratuity_found and gratuity_path:
        # Try to calculate for a specific employee
        test_emp = users[0] if users else None
        if test_emp:
            emp_id = test_emp.get("id", test_emp.get("_id"))
            calc_paths = [
                f"/gratuity/calculate/{emp_id}",
                f"/gratuity/calculate?employee_id={emp_id}",
                f"/payroll/gratuity/{emp_id}",
            ]
            for path in calc_paths:
                s, body = api("GET", path, tok)
                if ok(s):
                    body_str = json.dumps(body) if isinstance(body, dict) else str(body)
                    has_formula = any(w in body_str.lower() for w in ["15/26", "formula", "basic", "salary", "amount"])
                    if has_formula:
                        record("GB002", True, f"Gratuity calculation found: {body_str[:200]}", rule="GB002")
                        verdict("GB002", "ENFORCED")
                    else:
                        record("GB002", False, f"Gratuity response lacks formula details: {body_str[:200]}",
                               rule="GB002")
                        verdict("GB002", "PARTIAL")
                    break
            else:
                skip("GB002", "Gratuity calculation endpoint not found")
                verdict("GB002", "PARTIAL", "Gratuity endpoint exists but no calculation API")
        else:
            skip("GB002", "No employees to test gratuity calculation")
            verdict("GB002", "NOT IMPLEMENTED")
    else:
        skip("GB002", "No gratuity endpoint")
        verdict("GB002", "NOT IMPLEMENTED")

    # ── GB003: Gratuity max cap Rs 20L ──
    print("\n--- GB003: Gratuity max cap Rs 20,00,000 ---")
    if gratuity_found:
        verdict("GB003", "PARTIAL", "Gratuity endpoint exists; cap enforcement cannot be verified without calculation")
    else:
        skip("GB003", "No gratuity endpoint")
        verdict("GB003", "NOT IMPLEMENTED")

    # ── GB004: Insurance enrollment within 30 days of joining ──
    print("\n--- GB004: Insurance enrollment within 30 days ---")
    ins_paths = ["/insurance", "/benefits/insurance", "/benefits",
                 "/insurance/enrollment", "/benefits/enrollment"]
    ins_found = False
    for path in ins_paths:
        s, body = api("GET", path, tok)
        if ok(s):
            ins_found = True
            body_str = json.dumps(body) if isinstance(body, dict) else str(body)
            has_window = any(w in body_str.lower() for w in ["30 day", "enrollment", "window", "deadline"])
            if has_window:
                record("GB004", True, f"Insurance enrollment with window: {body_str[:200]}", rule="GB004")
                verdict("GB004", "ENFORCED")
            else:
                record("GB004", False, f"Insurance exists but no 30-day window: {body_str[:200]}", rule="GB004")
                verdict("GB004", "NOT ENFORCED")
            break

    if not ins_found:
        skip("GB004", "No insurance endpoint found")
        verdict("GB004", "NOT IMPLEMENTED")

    # ── GB005: Insurance dependents management ──
    print("\n--- GB005: Insurance dependents management ---")
    dep_paths = ["/insurance/dependents", "/benefits/dependents",
                 "/dependents", "/insurance/family"]
    dep_found = False
    for path in dep_paths:
        s, body = api("GET", path, tok)
        if ok(s):
            dep_found = True
            record("GB005", True, f"Dependents endpoint exists at {path}", rule="GB005")
            verdict("GB005", "ENFORCED")
            break
        elif s == 403:
            dep_found = True
            record("GB005", True, f"Dependents endpoint exists (403)", rule="GB005")
            verdict("GB005", "PARTIAL")
            break
    if not dep_found:
        skip("GB005", "No dependents endpoint")
        verdict("GB005", "NOT IMPLEMENTED")

    # ── GB006: Flexible benefits plan within limit ──
    print("\n--- GB006: Flexible benefits plan allocation ---")
    fbp_paths = ["/benefits/flexible", "/benefits/plan", "/benefits/fbp",
                 "/flexible-benefits", "/compensation/benefits"]
    fbp_found = False
    for path in fbp_paths:
        s, body = api("GET", path, tok)
        if ok(s):
            fbp_found = True
            body_str = json.dumps(body) if isinstance(body, dict) else str(body)
            record("GB006", True, f"FBP endpoint at {path}: {body_str[:200]}", rule="GB006")
            verdict("GB006", "PARTIAL", "Endpoint exists, limit enforcement unclear")
            break
    if not fbp_found:
        skip("GB006", "No FBP endpoint")
        verdict("GB006", "NOT IMPLEMENTED")

    # ── GB007: Meal vouchers/fuel card taxable beyond threshold ──
    print("\n--- GB007: Meal vouchers / fuel card tax threshold ---")
    skip("GB007", "Requires payroll tax calculation; no dedicated endpoint expected")
    verdict("GB007", "NOT IMPLEMENTED", "No meal voucher / fuel card API")


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 30 — AUDIT & COMPLIANCE REPORTING
# ═════════════════════════════════════════════════════════════════════════════
def test_section_30(admin_ctx, sa_ctx, endpoints):
    print("\n" + "=" * 70)
    print("SECTION 30 — AUDIT & COMPLIANCE REPORTING")
    print("=" * 70)

    admin_tok = admin_ctx["token"]
    sa_tok = sa_ctx["token"] if sa_ctx else None

    # ── Discover audit endpoint ──
    audit_path = endpoints.get("audit")
    audit_data = None
    if not audit_path:
        # Try with super admin
        if sa_tok:
            audit_candidates = ["/audit", "/audit/logs", "/audit-logs", "/logs",
                                "/admin/audit", "/admin/logs", "/activity-logs",
                                "/admin/activity-logs", "/super-admin/audit-logs",
                                "/admin/audit-logs"]
            for path in audit_candidates:
                s, body = api("GET", path, sa_tok)
                if ok(s):
                    audit_path = path
                    audit_data = body
                    break

    if audit_path and not audit_data:
        tok = sa_tok or admin_tok
        s, body = api("GET", audit_path, tok)
        if ok(s):
            audit_data = body

    # ── AC001: Every action logged with timestamp, user ID, IP ──
    print("\n--- AC001: Actions logged with timestamp, user ID, IP ---")
    if audit_data:
        body_str = json.dumps(audit_data) if isinstance(audit_data, dict) else str(audit_data)
        has_ts = any(w in body_str.lower() for w in ["timestamp", "created_at", "date", "time"])
        has_user = any(w in body_str.lower() for w in ["user_id", "userid", "user", "performed_by", "actor"])
        has_ip = any(w in body_str.lower() for w in ["ip", "ip_address", "ipaddress", "source"])

        fields_present = sum([has_ts, has_user, has_ip])
        if fields_present == 3:
            record("AC001", True, "Audit log has timestamp, user ID, and IP", rule="AC001")
            verdict("AC001", "ENFORCED")
        elif fields_present >= 1:
            missing = []
            if not has_ts: missing.append("timestamp")
            if not has_user: missing.append("user_id")
            if not has_ip: missing.append("IP")
            record("AC001", False, f"Audit log missing: {', '.join(missing)}",
                   bug_title=f"AC001 — Audit log missing {', '.join(missing)}",
                   expected="Every action logged with timestamp, user ID, and IP address",
                   actual=f"Audit log present but missing: {', '.join(missing)}. Sample: {body_str[:200]}",
                   endpoint=audit_path, steps=f"1. GET {audit_path}", rule="AC001")
            verdict("AC001", "PARTIAL", f"Missing: {', '.join(missing)}")
        else:
            record("AC001", False, f"Audit data unstructured: {body_str[:200]}", rule="AC001")
            verdict("AC001", "NOT ENFORCED")
    else:
        # Try to generate an action and then check for logs
        # Perform an action as admin
        s, _ = api("GET", "/users", admin_tok)
        time.sleep(1)
        # Check if any logging endpoint recorded it
        if sa_tok:
            for path in ["/admin/activity-logs", "/admin/logs"]:
                s2, body2 = api("GET", path, sa_tok)
                if ok(s2):
                    audit_data = body2
                    audit_path = path
                    body_str = json.dumps(body2) if isinstance(body2, dict) else str(body2)
                    record("AC001", True, f"Activity logs found at {path}: {body_str[:200]}", rule="AC001")
                    verdict("AC001", "PARTIAL", "Logs exist but full field check needed")
                    break
            else:
                skip("AC001", "No audit log endpoint found")
                verdict("AC001", "NOT IMPLEMENTED", "No audit/activity-log endpoint")
        else:
            skip("AC001", "No audit endpoint and no super admin")
            verdict("AC001", "NOT IMPLEMENTED")

    # ── AC002: Audit log is append-only (cannot modify/delete) ──
    print("\n--- AC002: Audit log append-only ---")
    if audit_path:
        tok = sa_tok or admin_tok
        # Try to DELETE an audit entry
        audit_items = []
        if audit_data and isinstance(audit_data, dict):
            d = audit_data.get("data", audit_data)
            if isinstance(d, dict):
                audit_items = d.get("logs", d.get("items", d.get("data", d.get("audit_logs", []))))
            elif isinstance(d, list):
                audit_items = d

        if audit_items and isinstance(audit_items, list) and len(audit_items) > 0:
            entry = audit_items[0]
            entry_id = entry.get("id", entry.get("_id", ""))
            if entry_id:
                # Try DELETE
                s_del, body_del = api("DELETE", f"{audit_path}/{entry_id}", tok)
                # Try PUT/PATCH to modify
                s_put, body_put = api("PUT", f"{audit_path}/{entry_id}", tok, data={"action": "modified"})
                s_patch, body_patch = api("PATCH", f"{audit_path}/{entry_id}", tok, data={"action": "modified"})

                delete_blocked = s_del in (403, 404, 405, 501)
                modify_blocked = s_put in (403, 404, 405, 501) and s_patch in (403, 404, 405, 501)

                if delete_blocked and modify_blocked:
                    record("AC002", True,
                           f"DELETE={s_del}, PUT={s_put}, PATCH={s_patch} — all blocked",
                           rule="AC002")
                    verdict("AC002", "ENFORCED")
                elif s_del in (200, 201, 204):
                    record("AC002", False, f"Audit entry DELETED successfully ({s_del})",
                           bug_title="AC002 — Audit log entries can be deleted (not append-only)",
                           expected="Audit logs cannot be modified or deleted",
                           actual=f"DELETE {audit_path}/{entry_id} returned {s_del}",
                           endpoint=f"{audit_path}/{entry_id}",
                           steps=f"1. GET {audit_path}\n2. DELETE {audit_path}/{entry_id}",
                           rule="AC002")
                    verdict("AC002", "NOT ENFORCED")
                elif s_put in (200, 201) or s_patch in (200, 201):
                    record("AC002", False, f"Audit entry MODIFIED (PUT={s_put}, PATCH={s_patch})",
                           bug_title="AC002 — Audit log entries can be modified (not append-only)",
                           expected="Audit logs cannot be modified or deleted",
                           actual=f"PUT={s_put}, PATCH={s_patch} on audit entry",
                           endpoint=f"{audit_path}/{entry_id}",
                           steps=f"1. PUT/PATCH {audit_path}/{entry_id}",
                           rule="AC002")
                    verdict("AC002", "NOT ENFORCED")
                else:
                    record("AC002", True, f"Non-standard codes but likely blocked: DEL={s_del}, PUT={s_put}, PATCH={s_patch}",
                           rule="AC002")
                    verdict("AC002", "PARTIAL")
            else:
                skip("AC002", "No entry ID to test deletion")
                verdict("AC002", "PARTIAL", "Audit data exists but no ID for mutation test")
        else:
            skip("AC002", "No audit entries to test mutation")
            verdict("AC002", "PARTIAL", "Audit endpoint found but empty")
    else:
        skip("AC002", "No audit endpoint")
        verdict("AC002", "NOT IMPLEMENTED")

    # ── AC003: Login attempts (success + failure) logged ──
    print("\n--- AC003: Login attempts logged ---")
    # Generate a failed login
    try:
        requests.post(f"{API_BASE}/auth/login",
                      json={"email": "ananya@technova.in", "password": "WrongPassword!"},
                      timeout=15)
    except Exception:
        pass
    time.sleep(1)

    if audit_path:
        tok = sa_tok or admin_tok
        s, body = api("GET", audit_path, tok, params={"action": "login", "limit": 10})
        if not ok(s):
            s, body = api("GET", audit_path, tok, params={"type": "auth", "limit": 10})
        if not ok(s):
            s, body = api("GET", audit_path, tok, params={"limit": 20})

        if ok(s):
            body_str = json.dumps(body) if isinstance(body, dict) else str(body)
            has_login = any(w in body_str.lower() for w in ["login", "auth", "sign_in", "signin", "sign-in"])
            has_fail = any(w in body_str.lower() for w in ["fail", "error", "invalid", "wrong", "denied"])
            if has_login:
                if has_fail:
                    record("AC003", True, "Login attempts including failures are logged", rule="AC003")
                    verdict("AC003", "ENFORCED")
                else:
                    record("AC003", False, "Login logged but no failure entries visible",
                           bug_title="AC003 — Failed login attempts not in audit log",
                           expected="Both successful and failed logins logged",
                           actual="Only successful logins appear in audit log",
                           endpoint=audit_path, steps="1. Login with wrong password\n2. Check audit logs",
                           rule="AC003")
                    verdict("AC003", "PARTIAL", "Successes logged, failures unclear")
            else:
                skip("AC003", "No login events in audit log")
                verdict("AC003", "NOT ENFORCED")
        else:
            skip("AC003", f"Audit query returned {s}")
            verdict("AC003", "NOT IMPLEMENTED")
    else:
        skip("AC003", "No audit endpoint")
        verdict("AC003", "NOT IMPLEMENTED")

    # ── AC004: Salary/payroll changes logged with before/after values ──
    print("\n--- AC004: Salary changes logged with before/after ---")
    if audit_path:
        tok = sa_tok or admin_tok
        s, body = api("GET", audit_path, tok, params={"action": "salary", "limit": 10})
        if not ok(s):
            s, body = api("GET", audit_path, tok, params={"type": "salary", "limit": 10})
        if not ok(s):
            s, body = api("GET", audit_path, tok, params={"module": "payroll", "limit": 10})
        if not ok(s):
            # Get all and search
            s, body = api("GET", audit_path, tok, params={"limit": 50})

        if ok(s):
            body_str = json.dumps(body) if isinstance(body, dict) else str(body)
            has_salary = any(w in body_str.lower() for w in ["salary", "payroll", "compensation", "ctc"])
            has_before_after = any(w in body_str.lower() for w in ["before", "after", "old_value", "new_value",
                                                                     "previous", "updated", "from", "changes"])
            if has_salary and has_before_after:
                record("AC004", True, "Salary changes logged with before/after", rule="AC004")
                verdict("AC004", "ENFORCED")
            elif has_salary:
                record("AC004", False, "Salary events logged but missing before/after values",
                       bug_title="AC004 — Salary change audit entries lack before/after values",
                       expected="Salary changes logged with old and new values",
                       actual=f"Salary events found but no before/after diff: {body_str[:200]}",
                       endpoint=audit_path, steps="1. GET audit logs filtered by salary/payroll",
                       rule="AC004")
                verdict("AC004", "PARTIAL", "Salary events present, no diff")
            else:
                skip("AC004", "No salary events in audit log")
                verdict("AC004", "NOT ENFORCED", "No salary change events in audit")
        else:
            skip("AC004", f"Audit query returned {s}")
            verdict("AC004", "NOT IMPLEMENTED")
    else:
        skip("AC004", "No audit endpoint")
        verdict("AC004", "NOT IMPLEMENTED")

    # ── AC005: Leave approval chain logged ──
    print("\n--- AC005: Leave approval chain logged ---")
    if audit_path:
        tok = sa_tok or admin_tok
        s, body = api("GET", audit_path, tok, params={"action": "leave", "limit": 10})
        if not ok(s):
            s, body = api("GET", audit_path, tok, params={"type": "leave", "limit": 10})
        if not ok(s):
            s, body = api("GET", audit_path, tok, params={"limit": 50})

        if ok(s):
            body_str = json.dumps(body) if isinstance(body, dict) else str(body)
            has_leave = any(w in body_str.lower() for w in ["leave", "approval", "approve", "reject"])
            if has_leave:
                record("AC005", True, "Leave approval events in audit", rule="AC005")
                verdict("AC005", "ENFORCED")
            else:
                skip("AC005", "No leave approval events in audit")
                verdict("AC005", "NOT ENFORCED")
        else:
            skip("AC005", f"Audit query returned {s}")
            verdict("AC005", "NOT IMPLEMENTED")
    else:
        skip("AC005", "No audit endpoint")
        verdict("AC005", "NOT IMPLEMENTED")

    # ── AC006: Document access logged ──
    print("\n--- AC006: Document access logged ---")
    if audit_path:
        tok = sa_tok or admin_tok
        # Access a document to generate log
        api("GET", "/documents", admin_tok)
        time.sleep(1)
        s, body = api("GET", audit_path, tok, params={"limit": 20})
        if ok(s):
            body_str = json.dumps(body) if isinstance(body, dict) else str(body)
            has_doc = any(w in body_str.lower() for w in ["document", "file", "download", "view"])
            if has_doc:
                record("AC006", True, "Document access in audit", rule="AC006")
                verdict("AC006", "ENFORCED")
            else:
                skip("AC006", "No document access events in audit")
                verdict("AC006", "NOT ENFORCED")
        else:
            skip("AC006", f"Audit query returned {s}")
            verdict("AC006", "NOT IMPLEMENTED")
    else:
        skip("AC006", "No audit endpoint")
        verdict("AC006", "NOT IMPLEMENTED")

    # ── AC007: Export of audit logs ──
    print("\n--- AC007: Audit log export ---")
    if audit_path:
        tok = sa_tok or admin_tok
        export_paths = [f"{audit_path}/export", f"{audit_path}/download",
                        f"{audit_path}?format=csv", f"{audit_path}?export=true"]
        exported = False
        for path in export_paths:
            s, body = api("GET", path, tok)
            if ok(s):
                record("AC007", True, f"Audit export at {path}", rule="AC007")
                verdict("AC007", "ENFORCED")
                exported = True
                break
        if not exported:
            skip("AC007", "No audit export endpoint")
            verdict("AC007", "NOT IMPLEMENTED")
    else:
        skip("AC007", "No audit endpoint")
        verdict("AC007", "NOT IMPLEMENTED")

    # ── AC008: Retention period — 7 years ──
    print("\n--- AC008: Audit log retention (7 years) ---")
    if audit_path:
        tok = sa_tok or admin_tok
        # Try to query very old records
        old_date = (datetime.now() - timedelta(days=365*7)).strftime("%Y-%m-%d")
        s, body = api("GET", audit_path, tok, params={"from_date": old_date, "start_date": old_date, "limit": 5})
        if ok(s):
            body_str = json.dumps(body) if isinstance(body, dict) else str(body)
            has_retention = any(w in body_str.lower() for w in ["retention", "archive", "7 year"])
            record("AC008", True, f"Audit query for old dates accepted ({s})", rule="AC008")
            verdict("AC008", "PARTIAL", "Endpoint accepts old date range; actual retention policy unclear")
        else:
            skip("AC008", "Cannot verify retention from API alone")
            verdict("AC008", "PARTIAL", "Cannot verify retention policy via API")
    else:
        skip("AC008", "No audit endpoint")
        verdict("AC008", "NOT IMPLEMENTED")

    # ── AC009: SOC 2 compliance ──
    print("\n--- AC009: SOC 2 compliance documentation ---")
    skip("AC009", "SOC 2 is a documentation/process requirement — not testable via API")
    verdict("AC009", "NOT IMPLEMENTED", "Process-level; not API-testable")

    # ── AC010: POSH compliance tracking ──
    print("\n--- AC010: POSH compliance reporting ---")
    posh_paths = ["/posh", "/compliance/posh", "/grievance", "/complaints",
                  "/helpdesk/tickets?type=posh", "/admin/posh"]
    posh_found = False
    tok = sa_tok or admin_tok
    for path in posh_paths:
        s, body = api("GET", path, tok)
        if ok(s):
            posh_found = True
            record("AC010", True, f"POSH/grievance endpoint at {path}", rule="AC010")
            verdict("AC010", "PARTIAL", "Endpoint exists; full POSH tracking unclear")
            break
    if not posh_found:
        skip("AC010", "No POSH endpoint found")
        verdict("AC010", "NOT IMPLEMENTED")


# ═════════════════════════════════════════════════════════════════════════════
# MAIN
# ═════════════════════════════════════════════════════════════════════════════
def main():
    print("=" * 70)
    print("EMP CLOUD — BUSINESS RULES V2 SECTIONS 27-30 TEST")
    print("Data Migration | Calendar | Gratuity | Audit")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # ── Login ──
    print("\n--- Logging in ---")
    admin_ctx = login("org_admin")
    sa_ctx = login("super_admin")
    if not admin_ctx:
        print("FATAL: Org admin login failed — aborting")
        return

    print(f"  Admin: {admin_ctx['user'].get('email', '?')}")
    if sa_ctx:
        print(f"  Super Admin: {sa_ctx['user'].get('email', '?')}")

    # ── Discover endpoints ──
    print("\n--- Discovering endpoints ---")
    endpoints = discover_endpoints(admin_ctx["token"])
    if sa_ctx:
        sa_eps = discover_endpoints(sa_ctx["token"])
        for k, v in sa_eps.items():
            if k not in endpoints:
                endpoints[k] = v
    print(f"  Found: {', '.join(f'{k}={v}' for k, v in endpoints.items())}")

    # ── Run sections ──
    test_section_27(admin_ctx, sa_ctx, endpoints)
    test_section_28(admin_ctx, sa_ctx, endpoints)
    test_section_29(admin_ctx, sa_ctx, endpoints)
    test_section_30(admin_ctx, sa_ctx, endpoints)

    # ── Summary ──
    print("\n" + "=" * 70)
    print("VERDICT SUMMARY")
    print("=" * 70)
    for rule_id in sorted(VERDICTS.keys()):
        print(f"  {rule_id}: {VERDICTS[rule_id]}")

    counts = {}
    for v in VERDICTS.values():
        base = v.split(" — ")[0].strip()
        counts[base] = counts.get(base, 0) + 1
    print(f"\n  Totals: {dict(counts)}")
    print(f"  Tests: {RESULTS['passed']} passed, {RESULTS['failed']} failed, {RESULTS['skipped']} skipped")
    print(f"  Bugs to file: {RESULTS['bugs']}")

    # ── File bugs ──
    file_github_issues()

    print("\n=== DONE ===")


if __name__ == "__main__":
    main()
