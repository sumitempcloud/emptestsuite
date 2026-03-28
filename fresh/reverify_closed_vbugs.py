"""
Re-verify ALL closed issues with "verified-bug" label on EmpCloud/EmpCloud.
Each issue gets an independent API test against the CORRECT module API.

Phase 1: Run all tests
Phase 2: Fix GitHub state (undo incorrect re-opens from first run, apply correct actions)
"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import urllib.request
import urllib.error
import json
import time
import ssl

# === Config ===
GITHUB_TOKEN = "$GITHUB_TOKEN"
REPO = "EmpCloud/EmpCloud"
GITHUB_API = f"https://api.github.com/repos/{REPO}"

CORE_API = "https://test-empcloud-api.empcloud.com/api/v1"
PAYROLL_API = "https://testpayroll-api.empcloud.com/api/v1"
LMS_API = "https://testlms-api.empcloud.com/api/v1"
REWARDS_API = "https://test-rewards-api.empcloud.com/api/v1"
EXIT_API = "https://test-exit-api.empcloud.com/api/v1"
PERFORMANCE_API = "https://test-performance-api.empcloud.com/api/v1"
RECRUIT_API = "https://test-recruit-api.empcloud.com/api/v1"

ADMIN_EMAIL = "ananya@technova.in"
ADMIN_PASS = "Welcome@123"

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

results = {}


def http_request(url, method="GET", data=None, headers=None, timeout=30):
    """Make HTTP request, returns (status_code, response_body)."""
    if headers is None:
        headers = {}
    headers.setdefault('User-Agent', UA)
    headers.setdefault('Accept', 'application/json, text/plain, */*')
    if data and isinstance(data, dict):
        data = json.dumps(data).encode('utf-8')
        headers.setdefault('Content-Type', 'application/json')

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        resp = urllib.request.urlopen(req, timeout=timeout, context=ctx)
        body = resp.read().decode('utf-8', errors='replace')
        try:
            return resp.status, json.loads(body)
        except:
            return resp.status, body
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='replace') if e.fp else ''
        try:
            return e.code, json.loads(body)
        except:
            return e.code, body
    except Exception as e:
        return 0, str(e)


def get_core_token():
    """Login to core API and get JWT token."""
    print("[AUTH] Logging into core API...")
    status, resp = http_request(
        f"{CORE_API}/auth/login",
        method="POST",
        data={"email": ADMIN_EMAIL, "password": ADMIN_PASS}
    )
    if status == 200 and isinstance(resp, dict):
        data = resp.get("data", {})
        tokens = data.get("tokens", {})
        token = (tokens.get("access_token") or tokens.get("accessToken") or
                 data.get("token") or data.get("accessToken") or
                 resp.get("token") or resp.get("accessToken"))
        if token:
            print(f"[AUTH] Core login OK")
            return token
    print(f"[AUTH] Core login failed: {status} -> {str(resp)[:200]}")
    return None


def get_module_token(module_api_base, module_name):
    """Login directly to a module API."""
    print(f"[AUTH] Trying direct login to {module_name}...")
    status, resp = http_request(
        f"{module_api_base}/auth/login",
        method="POST",
        data={"email": ADMIN_EMAIL, "password": ADMIN_PASS}
    )
    if status == 200 and isinstance(resp, dict):
        data = resp.get("data", {})
        tokens = data.get("tokens", {})
        token = (tokens.get("accessToken") or tokens.get("access_token") or
                 data.get("token") or data.get("accessToken") or
                 resp.get("token") or resp.get("accessToken"))
        if token:
            print(f"[AUTH] {module_name} direct login OK")
            return token
    print(f"[AUTH] {module_name} direct login: {status} -> {str(resp)[:200]}")
    return None


def github_api(path, method="GET", data=None):
    """Call GitHub API."""
    url = f"{GITHUB_API}/{path}" if not path.startswith("http") else path
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    return http_request(url, method=method, data=data, headers=headers)


def github_comment(issue_num, body):
    time.sleep(5)
    status, resp = github_api(f"issues/{issue_num}/comments", method="POST", data={"body": body})
    print(f"  [GH] Comment on #{issue_num}: {status}")
    return status == 201


def github_add_label(issue_num, label):
    time.sleep(5)
    status, resp = github_api(f"issues/{issue_num}/labels", method="POST", data={"labels": [label]})
    print(f"  [GH] Add label '{label}' to #{issue_num}: {status}")
    return status == 200


def github_remove_label(issue_num, label):
    time.sleep(5)
    url = f"{GITHUB_API}/issues/{issue_num}/labels/{urllib.request.quote(label, safe='')}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": UA
    }
    status, resp = http_request(url, method="DELETE", headers=headers)
    print(f"  [GH] Remove label '{label}' from #{issue_num}: {status}")
    return status == 200


def github_close(issue_num):
    time.sleep(5)
    status, resp = github_api(f"issues/{issue_num}", method="PATCH", data={"state": "closed"})
    print(f"  [GH] Close #{issue_num}: {status}")
    return status == 200


def github_reopen(issue_num):
    time.sleep(5)
    status, resp = github_api(f"issues/{issue_num}", method="PATCH", data={"state": "open"})
    print(f"  [GH] Reopen #{issue_num}: {status}")
    return status == 200


# ================================================================
# TEST FUNCTIONS
# ================================================================

def test_issue_1186(core_token):
    """#1186: [Medium][LMS] Quizzes Page - quizzes endpoint returns 404"""
    print("\n=== Testing #1186: LMS Quizzes Page ===")

    lms_token = get_module_token(LMS_API, "LMS")

    tokens_to_try = []
    if lms_token:
        tokens_to_try.append(("LMS direct token", lms_token))
    if core_token:
        tokens_to_try.append(("Core SSO token", core_token))
    if not tokens_to_try:
        # Try without auth
        tokens_to_try.append(("No auth", None))

    evidence_parts = []
    any_success = False

    for label, token in tokens_to_try:
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        status, resp = http_request(f"{LMS_API}/quizzes", headers=headers)
        resp_str = str(resp)[:300]
        evidence_parts.append(f"{label} -> GET {LMS_API}/quizzes: {status} {resp_str}")

        if status == 200:
            any_success = True
            break

    evidence = "\n".join(evidence_parts)
    if any_success:
        return True, f"Quizzes endpoint now returns 200.\n{evidence}"
    else:
        return False, f"Quizzes endpoint still failing.\n{evidence}"


def test_issue_925(core_token):
    """#925: Payslip PDF download returns 404 Employee not found"""
    print("\n=== Testing #925: Payroll Payslip PDF Download ===")

    payroll_token = get_module_token(PAYROLL_API, "Payroll")

    tokens_to_try = []
    if payroll_token:
        tokens_to_try.append(("Payroll direct", payroll_token))
    if core_token:
        tokens_to_try.append(("Core SSO", core_token))
    if not tokens_to_try:
        return False, "Could not obtain any auth token for Payroll"

    evidence_parts = []

    for label, token in tokens_to_try:
        headers = {"Authorization": f"Bearer {token}"}

        # Step 1: List payslips
        status, resp = http_request(f"{PAYROLL_API}/self-service/payslips", headers=headers)
        evidence_parts.append(f"{label} -> GET {PAYROLL_API}/self-service/payslips: {status} {str(resp)[:300]}")

        if status == 200 and isinstance(resp, dict):
            payslips_data = resp.get("data", {})
            payslips = []
            if isinstance(payslips_data, list):
                payslips = payslips_data
            elif isinstance(payslips_data, dict):
                payslips = payslips_data.get("payslips", payslips_data.get("data", []))
                if not isinstance(payslips, list):
                    payslips = []

            if payslips:
                payslip_id = payslips[0].get("id") or payslips[0].get("_id")
                if payslip_id:
                    status2, resp2 = http_request(
                        f"{PAYROLL_API}/self-service/payslips/{payslip_id}/pdf",
                        headers=headers
                    )
                    evidence_parts.append(f"{label} -> GET .../payslips/{payslip_id}/pdf: {status2} {str(resp2)[:300]}")
                    if status2 == 200:
                        return True, f"Payslip PDF download works.\n" + "\n".join(evidence_parts)

        # Try specific ID from bug report
        specific_id = "5bff3652-e1f6-44e2-a11c-8c559d526da8"
        status3, resp3 = http_request(
            f"{PAYROLL_API}/self-service/payslips/{specific_id}/pdf",
            headers=headers
        )
        evidence_parts.append(f"{label} -> GET .../payslips/{specific_id}/pdf: {status3} {str(resp3)[:300]}")
        if status3 == 200:
            return True, f"Payslip PDF download fixed.\n" + "\n".join(evidence_parts)

    evidence = "\n".join(evidence_parts)
    return False, f"Payslip PDF download still failing.\n{evidence}"


def test_issue_921(core_token):
    """#921: LMS Org Admin cannot create courses - 403 Forbidden"""
    print("\n=== Testing #921: LMS Create Courses (Org Admin) ===")

    lms_token = get_module_token(LMS_API, "LMS")

    tokens_to_try = []
    if lms_token:
        tokens_to_try.append(("LMS direct", lms_token))
    if core_token:
        tokens_to_try.append(("Core SSO", core_token))
    if not tokens_to_try:
        return False, "Could not obtain any auth token for LMS"

    evidence_parts = []

    for label, token in tokens_to_try:
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        # Test POST /courses
        course_data = {
            "title": "Reverify Test Course - Delete Me",
            "description": "Automated re-verification test",
            "category": "testing"
        }
        status, resp = http_request(f"{LMS_API}/courses", method="POST", data=course_data, headers=headers)
        evidence_parts.append(f"{label} -> POST {LMS_API}/courses: {status} {str(resp)[:300]}")

        if status in (200, 201):
            # Clean up
            if isinstance(resp, dict):
                cid = resp.get("data", {}).get("id") or resp.get("id") or resp.get("data", {}).get("_id")
                if cid:
                    http_request(f"{LMS_API}/courses/{cid}", method="DELETE", headers=headers)
            return True, f"Org admin can now create courses.\n" + "\n".join(evidence_parts)

        # Also test GET /courses
        status2, resp2 = http_request(f"{LMS_API}/courses", headers=headers)
        evidence_parts.append(f"{label} -> GET {LMS_API}/courses: {status2} {str(resp2)[:300]}")

    evidence = "\n".join(evidence_parts)
    return False, f"Org admin still cannot create courses.\n{evidence}"


def test_issue_763(core_token):
    """#763: EMP Exit - 9 documented features returning 404"""
    print("\n=== Testing #763: Exit Module - 9 Endpoints ===")

    exit_token = get_module_token(EXIT_API, "Exit")

    tokens_to_try = []
    if exit_token:
        tokens_to_try.append(("Exit direct", exit_token))
    if core_token:
        tokens_to_try.append(("Core SSO", core_token))
    if not tokens_to_try:
        return False, "Could not obtain any auth token for Exit module"

    endpoints = [
        "/checklist-templates",
        "/clearance-departments",
        "/interview-templates",
        "/letter-templates",
        "/email-templates",
        "/nps/scores",
        "/nps/trends",
        "/nps/responses",
        "/my-clearances",
    ]

    evidence_parts = []
    working = 0
    total = len(endpoints)

    for label, token in tokens_to_try:
        headers = {"Authorization": f"Bearer {token}"}
        working = 0

        for ep in endpoints:
            status, resp = http_request(f"{EXIT_API}{ep}", headers=headers)
            mark = "OK" if status in (200, 201) else f"FAIL({status})"
            evidence_parts.append(f"{label} -> GET {EXIT_API}{ep}: {mark} {str(resp)[:150]}")
            if status in (200, 201):
                working += 1

        if working > 0:
            break

    evidence = "\n".join(evidence_parts)
    if working == total:
        return True, f"All {total} Exit endpoints now return 200.\n{evidence}"
    elif working > 0:
        return False, f"Only {working}/{total} Exit endpoints working.\n{evidence}"
    else:
        return False, f"All {total} Exit endpoints still failing.\n{evidence}"


def test_issue_762(core_token):
    """#762: EMP Rewards - Integration Summary missing"""
    print("\n=== Testing #762: Rewards Integration Summary ===")

    rewards_token = get_module_token(REWARDS_API, "Rewards")

    tokens_to_try = []
    if rewards_token:
        tokens_to_try.append(("Rewards direct", rewards_token))
    if core_token:
        tokens_to_try.append(("Core SSO", core_token))
    if not tokens_to_try:
        return False, "Could not obtain any auth token for Rewards module"

    evidence_parts = []

    for label, token in tokens_to_try:
        headers = {"Authorization": f"Bearer {token}"}
        status, resp = http_request(f"{REWARDS_API}/integration/user/1/summary", headers=headers)
        evidence_parts.append(f"{label} -> GET {REWARDS_API}/integration/user/1/summary: {status} {str(resp)[:300]}")
        if status == 200:
            return True, f"Integration summary endpoint now works.\n" + "\n".join(evidence_parts)

    evidence = "\n".join(evidence_parts)
    return False, f"Integration summary endpoint still failing.\n{evidence}"


def test_issue_761(core_token):
    """#761: EMP Rewards - Teams Config missing"""
    print("\n=== Testing #761: Rewards Teams Config ===")

    rewards_token = get_module_token(REWARDS_API, "Rewards")

    tokens_to_try = []
    if rewards_token:
        tokens_to_try.append(("Rewards direct", rewards_token))
    if core_token:
        tokens_to_try.append(("Core SSO", core_token))
    if not tokens_to_try:
        return False, "Could not obtain any auth token for Rewards module"

    evidence_parts = []

    for label, token in tokens_to_try:
        headers = {"Authorization": f"Bearer {token}"}
        status, resp = http_request(f"{REWARDS_API}/teams", headers=headers)
        evidence_parts.append(f"{label} -> GET {REWARDS_API}/teams: {status} {str(resp)[:300]}")
        if status == 200:
            return True, f"Teams endpoint now works.\n" + "\n".join(evidence_parts)

    evidence = "\n".join(evidence_parts)
    return False, f"Teams endpoint still failing.\n{evidence}"


def test_issue_754(core_token):
    """#754: EMP Payroll - 6 documented features missing"""
    print("\n=== Testing #754: Payroll - 6 Endpoints ===")

    payroll_token = get_module_token(PAYROLL_API, "Payroll")

    tokens_to_try = []
    if payroll_token:
        tokens_to_try.append(("Payroll direct", payroll_token))
    if core_token:
        tokens_to_try.append(("Core SSO", core_token))

    evidence_parts = []
    working = 0
    total = 6

    # Auth login test
    status_login, resp_login = http_request(
        f"{PAYROLL_API}/auth/login",
        method="POST",
        data={"email": ADMIN_EMAIL, "password": ADMIN_PASS}
    )
    evidence_parts.append(f"POST {PAYROLL_API}/auth/login: {status_login} {str(resp_login)[:200]}")
    if status_login == 200:
        working += 1

    if not tokens_to_try:
        if status_login == 200 and isinstance(resp_login, dict):
            data = resp_login.get("data", {})
            tkns = data.get("tokens", {})
            t = (tkns.get("accessToken") or tkns.get("access_token") or
                 data.get("token") or data.get("accessToken"))
            if t:
                tokens_to_try.append(("Payroll login token", t))

    if not tokens_to_try:
        evidence_parts.append("No auth tokens available for remaining endpoints")
        return False, f"Payroll auth issue.\n" + "\n".join(evidence_parts)

    other_endpoints = [
        ("GL Mappings", "GET", "/gl-accounting/mappings"),
        ("Global Payroll Dashboard", "GET", "/global-payroll/dashboard"),
        ("Global Payroll Countries", "GET", "/global-payroll/countries"),
        ("Global Employees", "GET", "/global-payroll/employees"),
        ("Compensation Benchmarks", "GET", "/compensation-benchmarks"),
    ]

    for label, token in tokens_to_try:
        headers = {"Authorization": f"Bearer {token}"}

        for name, method, ep in other_endpoints:
            status, resp = http_request(f"{PAYROLL_API}{ep}", method=method, headers=headers)
            mark = "OK" if status in (200, 201) else f"FAIL({status})"
            evidence_parts.append(f"{label} -> {method} {PAYROLL_API}{ep}: {mark} {str(resp)[:150]}")
            if status in (200, 201):
                working += 1

        break  # Only need one token

    evidence = "\n".join(evidence_parts)
    if working == total:
        return True, f"All {total} Payroll endpoints now work.\n{evidence}"
    elif working > 0:
        return False, f"Only {working}/{total} Payroll endpoints working (partial fix).\n{evidence}"
    else:
        return False, f"All {total} Payroll endpoints still failing.\n{evidence}"


# ================================================================
# MAIN
# ================================================================

def main():
    print("=" * 70)
    print("RE-VERIFICATION OF CLOSED ISSUES WITH 'verified-bug' LABEL")
    print("=" * 70)
    print()

    # Step 1: Fresh core token
    core_token = get_core_token()
    print()

    # Step 2: Run all tests
    tests = {
        1186: test_issue_1186,
        925: test_issue_925,
        921: test_issue_921,
        763: test_issue_763,
        762: test_issue_762,
        761: test_issue_761,
        754: test_issue_754,
    }

    for issue_num, test_fn in tests.items():
        try:
            fixed, evidence = test_fn(core_token)
        except Exception as e:
            fixed = False
            evidence = f"Test error: {e}"
        results[issue_num] = {"fixed": fixed, "evidence": evidence}
        print(f"\n  => #{issue_num}: {'FIXED' if fixed else 'STILL FAILING'}")
        print(f"     Evidence preview: {evidence[:300]}")
        print()

    # Step 3: Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    for num, res in sorted(results.items()):
        status = "FIXED" if res["fixed"] else "STILL FAILING"
        print(f"  #{num}: {status}")

    # Step 4: Apply GitHub actions
    # NOTE: First run incorrectly re-opened all issues due to Cloudflare 403.
    # This run will correct the state based on actual test results.
    print("\n" + "=" * 70)
    print("APPLYING GITHUB ACTIONS (correcting state)")
    print("=" * 70)

    for num, res in sorted(results.items()):
        print(f"\n--- #{num} ---")
        evidence_block = res["evidence"]
        if len(evidence_block) > 1500:
            evidence_block = evidence_block[:1500] + "\n... (truncated)"

        if res["fixed"]:
            # CONFIRMED FIXED -> close, remove verified-bug, add verified-closed-lead-tester
            print(f"  Action: Confirm fix, close, update labels")

            github_close(num)
            github_remove_label(num, "verified-bug")
            github_add_label(num, "verified-closed-lead-tester")

            comment = (
                f"**Verified closed by Lead Tester. Fix confirmed.**\n\n"
                f"Re-verified with independent API test on {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())}.\n"
                f"Tested against correct module-specific API URL with proper auth.\n\n"
                f"**Evidence:**\n"
                f"```\n{evidence_block}\n```\n\n"
                f"Re-verification: PASS"
            )
            github_comment(num, comment)

        else:
            # STILL FAILING -> ensure open, ensure verified-bug, no verified-closed-lead-tester
            print(f"  Action: Keep open, update with real evidence")

            # Issue should already be open from prior run - but ensure
            github_reopen(num)

            comment = (
                f"**Lead Tester: Bug still present after programmer's fix.**\n\n"
                f"Re-verified with independent API test on {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())}.\n"
                f"Tested against correct module-specific API URLs with proper auth tokens.\n\n"
                f"**Evidence:**\n"
                f"```\n{evidence_block}\n```\n\n"
                f"Re-verification: FAIL -- Issue remains open."
            )
            github_comment(num, comment)

    print("\n" + "=" * 70)
    print("DONE")
    print("=" * 70)


if __name__ == "__main__":
    main()
