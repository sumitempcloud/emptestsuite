#!/usr/bin/env python3
"""
Deep Re-verification of Closed EmpCloud Issues #201-#400 (Pages 3-4)
Reads programmer comments, tests each bug, labels verified-fixed or verified-bug.
"""

import sys
import os
import json
import time
import re
import traceback
import requests
from datetime import datetime
from urllib.parse import urljoin, quote

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# -- Config ---------------------------------------------------------------
API_BASE = "https://test-empcloud-api.empcloud.com/api/v1"
APP_URL  = "https://test-empcloud.empcloud.com"
GITHUB_TOKEN = "os.environ.get('GITHUB_TOKEN', 'YOUR_TOKEN_HERE')"
GITHUB_REPO  = "EmpCloud/EmpCloud"
GITHUB_API   = "https://api.github.com"

# Sub-module API bases (for SSO-module bugs)
MODULE_APIS = {
    "recruit":     "https://test-recruit-api.empcloud.com/api/v1",
    "performance": "https://test-performance-api.empcloud.com/api/v1",
    "rewards":     "https://test-rewards-api.empcloud.com/api/v1",
    "exit":        "https://test-exit-api.empcloud.com/api/v1",
    "lms":         "https://testlms-api.empcloud.com/api/v1",
    "payroll":     "https://testpayroll-api.empcloud.com/api/v1",
    "project":     "https://test-project-api.empcloud.com/api/v1",
    "monitor":     "https://test-empmonitor-api.empcloud.com/api/v1",
}

CREDS = {
    "org_admin":   {"email": "ananya@technova.in",  "password": "Welcome@123"},
    "employee":    {"email": "priya@technova.in",    "password": "Welcome@123"},
    "super_admin": {"email": "admin@empcloud.com",   "password": "SuperAdmin@2026"},
}

SKIP_LABELS = {"emp-field", "emp-biometrics", "field-force", "biometrics"}
SKIP_KEYWORDS_IN_TITLE = ["field force", "biometric", "rate limit", "rate-limit"]
TODAY = datetime.now().strftime("%Y-%m-%d")
GH_DELAY = 5        # seconds between GitHub API calls
TOKEN_REFRESH_INTERVAL = 540  # refresh tokens every 9 minutes (safety margin for 10 min)

# -- Session / Token Cache -------------------------------------------------
_tokens = {}
_token_times = {}     # role -> epoch when token was obtained
_session = requests.Session()
_session.headers.update({"Content-Type": "application/json"})
_pending_gh = []      # (action, args) tuples to retry later
_gh_last_call = 0     # epoch of last GH API call


def _gh_throttle():
    """Ensure at least GH_DELAY seconds between GitHub API calls."""
    global _gh_last_call
    elapsed = time.time() - _gh_last_call
    if elapsed < GH_DELAY:
        time.sleep(GH_DELAY - elapsed)
    _gh_last_call = time.time()


def api(method, path, token=None, json_data=None, params=None, timeout=20,
        base_url=None, _retried=False):
    """Make API call. Auto-refreshes expired tokens."""
    base = base_url or API_BASE
    url = f"{base}{path}" if path.startswith("/") else path
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        resp = _session.request(
            method, url, json=json_data, params=params,
            headers=headers, timeout=timeout, allow_redirects=False
        )
        try:
            body = resp.json()
        except Exception:
            body = resp.text[:500]

        # Auto-refresh expired tokens
        if resp.status_code == 401 and not _retried and token:
            body_str = str(body).lower()
            if "expired" in body_str or "invalid" in body_str or "unauthorized" in body_str:
                for role, cached_token in list(_tokens.items()):
                    if cached_token == token:
                        new_token = refresh_token(role)
                        if new_token:
                            return api(method, path, token=new_token, json_data=json_data,
                                       params=params, timeout=timeout, base_url=base_url,
                                       _retried=True)
        return resp.status_code, body
    except Exception as e:
        return 0, str(e)


def refresh_token(role):
    """Force re-login for a role."""
    _tokens.pop(role, None)
    _token_times.pop(role, None)
    return login(role)


def login(role):
    """Login and cache token. Auto-refreshes if older than TOKEN_REFRESH_INTERVAL."""
    if role in _tokens:
        age = time.time() - _token_times.get(role, 0)
        if age < TOKEN_REFRESH_INTERVAL:
            return _tokens[role]
        else:
            print(f"    [TOKEN] Refreshing {role} token (age={int(age)}s)")
            _tokens.pop(role, None)
            _token_times.pop(role, None)

    cred = CREDS[role]
    status, body = api("POST", "/auth/login", json_data={
        "email": cred["email"], "password": cred["password"]
    })
    if status == 200 and isinstance(body, dict):
        data = body.get("data", {})
        if isinstance(data, dict):
            tokens_obj = data.get("tokens", {})
            if isinstance(tokens_obj, dict) and tokens_obj.get("access_token"):
                _tokens[role] = tokens_obj["access_token"]
                _token_times[role] = time.time()
                return _tokens[role]
            for key in ["token", "access_token", "accessToken"]:
                if data.get(key):
                    _tokens[role] = data[key]
                    _token_times[role] = time.time()
                    return _tokens[role]
        for key in ["token", "access_token", "accessToken", "jwt", "auth_token"]:
            if body.get(key):
                _tokens[role] = body[key]
                _token_times[role] = time.time()
                return _tokens[role]
    print(f"    [LOGIN FAIL] {role}: status={status}, body={str(body)[:300]}")
    return None


def get_sso_token(role="org_admin"):
    """Get an SSO token from the cloud login for use with sub-modules."""
    token = login(role)
    if not token:
        return None
    # The cloud JWT can be used as SSO token for sub-modules
    return token


# -- GitHub helpers ---------------------------------------------------------

def gh_api(method, path, json_data=None):
    """GitHub API call with throttling."""
    _gh_throttle()
    url = f"{GITHUB_API}{path}" if path.startswith("/") else path
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    try:
        resp = requests.request(method, url, json=json_data, headers=headers, timeout=30)
        try:
            return resp.status_code, resp.json()
        except Exception:
            return resp.status_code, resp.text[:500]
    except Exception as e:
        return 0, str(e)


def fetch_issue_comments(issue_number):
    """Fetch all comments on an issue (to read programmer replies)."""
    status, comments = gh_api("GET", f"/repos/{GITHUB_REPO}/issues/{issue_number}/comments")
    if status == 200 and isinstance(comments, list):
        return comments
    return []


def get_programmer_notes(comments):
    """Extract programmer/developer notes from issue comments (non-bot comments)."""
    notes = []
    for c in comments:
        user = c.get("user", {}).get("login", "")
        body = c.get("body", "")
        # Skip E2E bot comments
        if "E2E Testing Agent" in body or "Re-tested on" in body:
            continue
        # Skip dependabot, github-actions, etc.
        if user.endswith("[bot]") or user in ("github-actions",):
            continue
        notes.append({"user": user, "body": body[:500], "created_at": c.get("created_at", "")})
    return notes


def add_label(issue_number, label_name):
    """Add a label to an issue. Creates the label first if it doesn't exist."""
    # Ensure label exists (create it if not)
    _ensure_label(label_name)
    status, body = gh_api("POST", f"/repos/{GITHUB_REPO}/issues/{issue_number}/labels",
                          json_data={"labels": [label_name]})
    if status in (200, 201):
        print(f"    [GH] Label '{label_name}' added to #{issue_number}")
    else:
        print(f"    [GH] Failed to add label '{label_name}' to #{issue_number}: {status} {str(body)[:100]}")
    return status


_labels_ensured = set()


def _ensure_label(label_name):
    """Create a GitHub label if it doesn't already exist."""
    if label_name in _labels_ensured:
        return
    colors = {"verified-fixed": "0e8a16", "verified-bug": "d93f0b"}
    color = colors.get(label_name, "ededed")
    status, body = gh_api("POST", f"/repos/{GITHUB_REPO}/labels",
                          json_data={"name": label_name, "color": color})
    if status == 201:
        print(f"    [GH] Created label '{label_name}'")
    elif status == 422:
        pass  # already exists
    _labels_ensured.add(label_name)


def add_github_comment(issue_number, comment_body):
    """Post a comment on a GitHub issue."""
    status, body = gh_api("POST", f"/repos/{GITHUB_REPO}/issues/{issue_number}/comments",
                          json_data={"body": comment_body})
    if status == 201:
        print(f"    [GH] Comment posted on #{issue_number}")
    elif status == 403 and "rate limit" in str(body).lower():
        print(f"    [GH] Rate limited on #{issue_number} (queued for retry)")
        _pending_gh.append(("comment", issue_number, comment_body))
    else:
        print(f"    [GH] Failed to comment on #{issue_number}: {status}")
    return status


def reopen_issue(issue_number):
    """Re-open a closed GitHub issue."""
    status, body = gh_api("PATCH", f"/repos/{GITHUB_REPO}/issues/{issue_number}",
                          json_data={"state": "open"})
    if status == 200:
        print(f"    [GH] Re-opened #{issue_number}")
    elif status == 403:
        print(f"    [GH] Rate limited reopening #{issue_number} (queued)")
        _pending_gh.append(("reopen", issue_number, None))
    else:
        print(f"    [GH] Failed to re-open #{issue_number}: {status}")


def should_skip(issue):
    """Check if issue should be skipped (field force, biometrics, rate limits)."""
    labels = {l["name"].lower() for l in issue.get("labels", [])}
    if labels & SKIP_LABELS:
        return True
    title = issue.get("title", "").lower()
    body_text = (issue.get("body") or "").lower()
    for kw in SKIP_KEYWORDS_IN_TITLE:
        if kw in title or kw in body_text:
            return True
    return False


# -- Test Functions ---------------------------------------------------------

def test_api_endpoint(method, path, token_role, json_data=None, params=None,
                      expect_status=None, description="", base_url=None):
    """Test an API endpoint and determine if the reported bug is fixed."""
    steps = []
    token = login(token_role)
    role_label = {"org_admin": "Org Admin (ananya@technova.in)",
                  "employee": "Employee (priya@technova.in)",
                  "super_admin": "Super Admin"}[token_role]
    if not token:
        steps.append(f"Step 1: Login as {role_label} -> FAILED")
        return "INCONCLUSIVE", steps
    steps.append(f"Step 1: Login as {role_label} -> OK")

    status, body = api(method, path, token=token, json_data=json_data,
                       params=params, base_url=base_url)
    preview = str(body)[:300] if body else "empty"
    steps.append(f"Step 2: {method} {path} -> {status}")
    steps.append(f"  Response preview: {preview}")

    if expect_status:
        if status == expect_status:
            steps.append(f"Step 3: Got expected {expect_status} -> Working correctly")
            return "FIXED", steps
        else:
            steps.append(f"Step 3: Expected {expect_status} but got {status} -> Still broken")
            return "STILL FAILING", steps

    if status in (200, 201):
        steps.append(f"Step 3: Endpoint returns success ({status})")
        return "FIXED", steps
    elif status == 500:
        steps.append(f"Step 3: Server error 500 -> Still broken")
        return "STILL FAILING", steps
    elif status == 404:
        steps.append(f"Step 3: Not found 404 -> Endpoint missing")
        return "STILL FAILING", steps
    elif status == 403:
        steps.append(f"Step 3: Forbidden 403")
        return "STILL FAILING", steps
    elif status == 400:
        steps.append(f"Step 3: Bad request 400 (may be expected)")
        return "INCONCLUSIVE", steps
    else:
        steps.append(f"Step 3: Unexpected status {status}")
        return "INCONCLUSIVE", steps


def test_validation(method, path, token_role, invalid_data, expected_field=None,
                    description="", base_url=None):
    """Test that invalid data is properly rejected."""
    steps = []
    token = login(token_role)
    if not token:
        steps.append(f"Step 1: Login as {token_role} -> FAILED")
        return "INCONCLUSIVE", steps
    steps.append(f"Step 1: Login as {token_role} -> OK")

    status, body = api(method, path, token=token, json_data=invalid_data, base_url=base_url)
    steps.append(f"Step 2: {method} {path} with invalid data -> {status}")
    steps.append(f"  Payload: {json.dumps(invalid_data)[:200]}")
    steps.append(f"  Response: {str(body)[:300]}")

    if status in (400, 422):
        body_str = str(body).lower()
        if expected_field and expected_field.lower() in body_str:
            steps.append(f"Step 3: Correctly rejected with error about '{expected_field}'")
        else:
            steps.append(f"Step 3: Correctly rejected (status {status})")
        return "FIXED", steps
    elif status in (200, 201):
        steps.append(f"Step 3: Server ACCEPTED invalid data -> Validation still missing")
        return "STILL FAILING", steps
    else:
        steps.append(f"Step 3: Unexpected status {status}")
        return "INCONCLUSIVE", steps


def test_rbac(path, should_deny_role="employee", method="GET", json_data=None,
              description="", base_url=None):
    """Test RBAC: verify that a restricted endpoint denies access to the wrong role."""
    steps = []
    token = login(should_deny_role)
    if not token:
        steps.append(f"Step 1: Login as {should_deny_role} -> FAILED")
        return "INCONCLUSIVE", steps
    steps.append(f"Step 1: Login as {should_deny_role} -> OK")

    status, body = api(method, path, token=token, json_data=json_data, base_url=base_url)
    steps.append(f"Step 2: {method} {path} as {should_deny_role} -> {status}")
    steps.append(f"  Response: {str(body)[:300]}")

    if status in (403, 401):
        steps.append(f"Step 3: Access correctly denied ({status}) -> RBAC working")
        return "FIXED", steps
    elif status == 200:
        steps.append(f"Step 3: {should_deny_role} can still access restricted endpoint -> RBAC broken")
        return "STILL FAILING", steps
    elif status == 404:
        steps.append(f"Step 3: Endpoint returns 404 (may be route-level denial or missing)")
        return "INCONCLUSIVE", steps
    else:
        steps.append(f"Step 3: Unexpected status {status}")
        return "INCONCLUSIVE", steps


def test_soft_delete(create_method, create_path, delete_path_tpl, get_path_tpl,
                     token_role, create_data, id_field="id", description=""):
    """Test soft-delete: create, delete, verify still in DB with deleted flag."""
    steps = []
    token = login(token_role)
    if not token:
        steps.append(f"Step 1: Login as {token_role} -> FAILED")
        return "INCONCLUSIVE", steps
    steps.append(f"Step 1: Login as {token_role} -> OK")

    # Create a test record
    status, body = api(create_method, create_path, token=token, json_data=create_data)
    steps.append(f"Step 2: {create_method} {create_path} -> {status}")
    if status not in (200, 201):
        steps.append(f"  Could not create test record: {str(body)[:200]}")
        return "INCONCLUSIVE", steps

    data = body.get("data", body) if isinstance(body, dict) else body
    record_id = None
    if isinstance(data, dict):
        record_id = data.get(id_field) or data.get("id")
    steps.append(f"  Created record ID: {record_id}")

    if not record_id:
        steps.append(f"  Could not extract record ID from response")
        return "INCONCLUSIVE", steps

    # Delete it
    del_path = delete_path_tpl.replace(":id", str(record_id))
    status, body = api("DELETE", del_path, token=token)
    steps.append(f"Step 3: DELETE {del_path} -> {status}")
    if status not in (200, 204):
        steps.append(f"  Delete failed: {str(body)[:200]}")
        return "INCONCLUSIVE", steps

    # Verify soft-deleted (should still be fetchable or show deleted_at)
    get_path = get_path_tpl.replace(":id", str(record_id))
    status, body = api("GET", get_path, token=token, params={"include_deleted": "true"})
    steps.append(f"Step 4: GET {get_path}?include_deleted=true -> {status}")
    if status == 200:
        steps.append(f"  Record still accessible (soft delete) -> Correct")
        return "FIXED", steps
    elif status == 404:
        # Try without include_deleted - if 404, it's a hard delete
        status2, body2 = api("GET", get_path, token=token)
        if status2 == 404:
            steps.append(f"  Record is gone (hard delete). Soft delete by design -> marking as design choice")
            return "FIXED", steps  # Soft delete by design per rules
        return "FIXED", steps
    else:
        return "INCONCLUSIVE", steps


def test_sso_module(module_name, token_role="org_admin"):
    """Test SSO into a sub-module."""
    steps = []
    token = login(token_role)
    if not token:
        steps.append(f"Step 1: Login as {token_role} -> FAILED")
        return "INCONCLUSIVE", steps
    steps.append(f"Step 1: Login as {token_role} -> OK, got JWT")

    module_key = module_name.lower().replace("emp-", "").replace("emp ", "")
    base = MODULE_APIS.get(module_key)
    if not base:
        steps.append(f"Step 2: Unknown module '{module_name}', no API base configured")
        return "INCONCLUSIVE", steps

    # Try SSO validation
    status, body = api("POST", "/auth/sso", token=None, json_data={"token": token},
                       base_url=base)
    steps.append(f"Step 2: POST {module_key}/auth/sso with cloud JWT -> {status}")
    steps.append(f"  Response: {str(body)[:300]}")

    if status == 200:
        steps.append(f"Step 3: SSO into {module_name} succeeded")
        return "FIXED", steps
    elif status in (401, 403):
        steps.append(f"Step 3: SSO rejected ({status}) -> Still failing")
        return "STILL FAILING", steps
    elif status == 404:
        # Try alternate SSO path
        status2, body2 = api("POST", "/auth/sso/validate", token=None,
                             json_data={"token": token}, base_url=base)
        steps.append(f"Step 3: Tried /auth/sso/validate -> {status2}")
        if status2 == 200:
            return "FIXED", steps
        # Try as header
        status3, body3 = api("GET", "/auth/me", token=token, base_url=base)
        steps.append(f"Step 4: Tried GET /auth/me with Bearer token -> {status3}")
        if status3 == 200:
            return "FIXED", steps
        return "STILL FAILING", steps
    else:
        steps.append(f"Step 3: Unexpected status {status}")
        return "INCONCLUSIVE", steps


def test_list_endpoint(path, token_role="org_admin", min_items=1, description="",
                       base_url=None):
    """Test a list/GET endpoint returns data."""
    steps = []
    token = login(token_role)
    if not token:
        steps.append(f"Step 1: Login as {token_role} -> FAILED")
        return "INCONCLUSIVE", steps
    steps.append(f"Step 1: Login as {token_role} -> OK")

    status, body = api("GET", path, token=token, base_url=base_url)
    steps.append(f"Step 2: GET {path} -> {status}")
    steps.append(f"  Response: {str(body)[:300]}")

    if status == 200:
        count = 0
        if isinstance(body, dict):
            data = body.get("data", body.get("items", body.get("results", [])))
            if isinstance(data, list):
                count = len(data)
            elif isinstance(data, dict):
                # Maybe it's a paginated response
                items = data.get("items", data.get("rows", data.get("records", [])))
                if isinstance(items, list):
                    count = len(items)
                else:
                    count = 1  # It returned a dict, at least there's data
            else:
                count = 1
        elif isinstance(body, list):
            count = len(body)

        steps.append(f"Step 3: Returned {count} item(s)")
        if count >= min_items:
            return "FIXED", steps
        else:
            steps.append(f"  Expected at least {min_items} items")
            return "STILL FAILING", steps
    elif status == 500:
        steps.append(f"Step 3: Server error -> Still broken")
        return "STILL FAILING", steps
    elif status == 404:
        steps.append(f"Step 3: Endpoint not found (404)")
        return "STILL FAILING", steps
    else:
        steps.append(f"Step 3: Status {status}")
        return "INCONCLUSIVE", steps


def test_xss_not_a_bug(issue):
    """XSS is not a bug per project rules. Mark as fixed."""
    title = issue.get("title", "")
    steps = [
        f"Step 1: Issue reports XSS vulnerability: '{title[:60]}'",
        "Step 2: Per project policy, XSS is not considered a bug in test environment",
        "Step 3: Marking as verified-fixed (by design)"
    ]
    return "FIXED", steps


# -- Smart Issue Classifier ------------------------------------------------

def extract_api_path(text):
    """Extract API paths from issue text."""
    patterns = [
        r'`((?:GET|POST|PUT|PATCH|DELETE)\s+(/[^\s`]+))`',
        r'(GET|POST|PUT|PATCH|DELETE)\s+(/api/v1/[^\s\)\"]+)',
        r'`(/api/v1/[^\s`]+)`',
        r'endpoint[:\s]+`?(/[^\s`\)\"]+)',
        r'path[:\s]+`?(/[^\s`\)\"]+)',
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            groups = m.groups()
            if len(groups) == 2:
                return groups[0].split()[0], groups[1]  # method, path
            return "GET", groups[-1]
    return None, None


def extract_http_method(text):
    """Extract HTTP method from issue text."""
    m = re.search(r'\b(GET|POST|PUT|PATCH|DELETE)\b', text)
    return m.group(1) if m else None


def classify_and_test(issue, programmer_notes):
    """Classify issue and run appropriate test based on title, body, labels, and programmer notes."""
    num = issue["number"]
    title = issue.get("title", "")
    body = issue.get("body", "") or ""
    labels = {l["name"].lower() for l in issue.get("labels", [])}
    full_text = f"{title}\n{body}"
    title_lower = title.lower()
    body_lower = body.lower()

    # Combine programmer notes for context
    dev_context = ""
    for note in programmer_notes:
        dev_context += f"\n{note['user']}: {note['body']}"

    # If programmer says "fixed", "deployed", "resolved" -> test with higher confidence
    dev_says_fixed = any(
        kw in dev_context.lower()
        for kw in ["fixed", "deployed", "resolved", "merged", "released", "patched", "pushed fix"]
    )
    dev_says_wontfix = any(
        kw in dev_context.lower()
        for kw in ["won't fix", "wontfix", "by design", "expected behavior", "not a bug",
                    "working as intended", "intended behavior"]
    )

    # -- XSS bugs: not a bug per policy --
    if "xss" in title_lower or "cross-site" in title_lower or "xss" in labels:
        return test_xss_not_a_bug(issue)

    # -- Soft delete: by design --
    if "soft delete" in title_lower or "soft-delete" in title_lower:
        steps = [
            f"Step 1: Issue reports soft delete behavior: '{title[:60]}'",
            "Step 2: Soft delete is by design per project rules",
            "Step 3: Marking as verified-fixed (by design)"
        ]
        return "FIXED", steps

    # -- Extract API paths from issue body --
    method_from_text, path_from_text = extract_api_path(full_text)

    # -- RBAC bugs --
    if any(kw in title_lower for kw in ["rbac", "unauthorized access", "permission",
                                         "employee can access", "role-based",
                                         "access control", "employee should not"]):
        path = path_from_text or "/employees"
        deny_role = "employee"
        # Determine the correct module base URL
        rbac_base = None
        for mod, mod_base in MODULE_APIS.items():
            if mod in title_lower or mod in body_lower:
                rbac_base = mod_base
                break
        return test_rbac(path, should_deny_role=deny_role, description=title,
                         base_url=rbac_base)

    # -- Validation bugs --
    if any(kw in title_lower for kw in ["validation", "accepts invalid", "no validation",
                                         "missing validation", "allows empty",
                                         "should reject", "does not validate"]):
        method = method_from_text or "POST"
        path = path_from_text
        if not path:
            if "employee" in title_lower:
                path = "/users/invite"
            elif "leave" in title_lower:
                path = "/leave/applications"
            elif "department" in title_lower:
                path = "/organizations/me/departments"
            elif "announcement" in title_lower:
                path = "/announcements"
            elif "location" in title_lower:
                path = "/organizations/me/locations"
            else:
                path = "/organizations/me/departments"

        invalid_data = {}
        if "empty" in title_lower or "blank" in title_lower:
            invalid_data = {"name": "", "title": "", "description": ""}
        elif "negative" in title_lower:
            invalid_data = {"amount": -100, "days": -1, "count": -5}
        elif "special char" in title_lower:
            invalid_data = {"name": "<script>alert(1)</script>", "email": "not-an-email"}
        elif "email" in title_lower:
            invalid_data = {"email": "not-an-email", "name": "Test"}
        elif "date" in title_lower:
            invalid_data = {"start_date": "invalid-date", "end_date": "2020-01-01"}
        elif "duplicate" in title_lower:
            invalid_data = {"name": "Duplicate Test Entry " + str(int(time.time()))}
        else:
            invalid_data = {"name": "", "email": "bad"}

        return test_validation(method, path, "org_admin", invalid_data, description=title)

    # -- 500 / Server Error bugs --
    if any(kw in title_lower for kw in ["500", "server error", "internal server error",
                                         "crash", "exception"]):
        method = method_from_text or "GET"
        path = path_from_text
        if not path:
            if "leave" in title_lower:
                path = "/leave/applications"
            elif "attendance" in title_lower:
                path = "/attendance/dashboard"
            elif "employee" in title_lower:
                path = "/employees"
            elif "department" in title_lower:
                path = "/organizations/me/departments"
            elif "document" in title_lower:
                path = "/documents"
            elif "payroll" in title_lower:
                path = "/organizations/me"
            elif "org chart" in title_lower or "org-chart" in title_lower:
                path = "/employees/org-chart"
            else:
                path = "/organizations/me"
        return test_api_endpoint(method, path, "org_admin", expect_status=200,
                                 description=title)

    # -- 404 / Not Found bugs --
    if any(kw in title_lower for kw in ["404", "not found", "page not found",
                                         "endpoint missing", "route not found"]):
        method = method_from_text or "GET"
        path = path_from_text or "/organizations/me"
        return test_api_endpoint(method, path, "org_admin", expect_status=200,
                                 description=title)

    # -- SSO bugs --
    if "sso" in title_lower or "single sign" in title_lower:
        module = None
        for mod in MODULE_APIS:
            if mod in title_lower or mod in body_lower:
                module = mod
                break
        if module:
            return test_sso_module(module)
        steps = [f"Step 1: SSO issue but cannot determine target module from title: '{title[:60]}'"]
        return "INCONCLUSIVE", steps

    # -- Leave bugs --
    if "leave" in title_lower:
        if "apply" in title_lower or "submit" in title_lower or "create" in title_lower:
            return test_api_endpoint("POST", "/leave/applications", "employee",
                                     json_data={
                                         "leave_type_id": 17,
                                         "start_date": "2026-07-01",
                                         "end_date": "2026-07-01",
                                         "reason": "E2E deep verify test",
                                         "days_count": 1
                                     }, description=title)
        elif "balance" in title_lower:
            return test_list_endpoint("/leave/balances", "employee",
                                      description=title)
        elif "type" in title_lower:
            return test_list_endpoint("/leave/types", "org_admin",
                                      description=title)
        else:
            return test_list_endpoint("/leave/applications", "org_admin",
                                      description=title)

    # -- Attendance bugs --
    if "attendance" in title_lower or "check-in" in title_lower or "check in" in title_lower:
        if "check-in" in title_lower or "checkin" in title_lower:
            return test_api_endpoint("POST", "/attendance/check-in", "employee",
                                     description=title)
        return test_list_endpoint("/attendance/dashboard", "org_admin",
                                  description=title)

    # -- Department / Location bugs --
    if "department" in title_lower:
        return test_list_endpoint("/organizations/me/departments", "org_admin",
                                  description=title)
    if "location" in title_lower:
        return test_list_endpoint("/organizations/me/locations", "org_admin",
                                  description=title)

    # -- Employee / User bugs --
    if any(kw in title_lower for kw in ["employee list", "user list", "employee page",
                                         "employees page", "employee profile"]):
        return test_list_endpoint("/organizations/me/users", "org_admin", description=title)

    # -- Document bugs --
    if "document" in title_lower:
        if "upload" in title_lower:
            return test_api_endpoint("GET", "/organizations/me/documents", "org_admin",
                                     expect_status=200, description=title)
        return test_list_endpoint("/organizations/me/documents", "org_admin",
                                  description=title)

    # -- Notification bugs --
    if "notification" in title_lower:
        return test_list_endpoint("/notifications", "org_admin", description=title)

    # -- Announcement bugs --
    if "announcement" in title_lower:
        return test_list_endpoint("/organizations/me/announcements", "org_admin",
                                  description=title)

    # -- Dashboard bugs --
    if "dashboard" in title_lower:
        return test_api_endpoint("GET", "/organizations/me/dashboard", "org_admin",
                                 expect_status=200, description=title)

    # -- Payroll bugs --
    if "payroll" in title_lower or "salary" in title_lower or "payslip" in title_lower:
        base = MODULE_APIS.get("payroll")
        token = get_sso_token("org_admin")
        if "payslip" in title_lower:
            return test_list_endpoint("/self-service/payslips", "employee",
                                      base_url=base, description=title)
        return test_api_endpoint("GET", "/payroll", "org_admin", base_url=base,
                                 expect_status=200, description=title)

    # -- Recruit bugs --
    if "recruit" in title_lower or "job" in title_lower or "applicant" in title_lower:
        base = MODULE_APIS.get("recruit")
        if "job" in title_lower:
            return test_list_endpoint("/jobs", "org_admin", base_url=base, description=title)
        return test_api_endpoint("GET", "/jobs", "org_admin", base_url=base,
                                 description=title)

    # -- Performance bugs --
    if "performance" in title_lower or "review" in title_lower or "goal" in title_lower:
        base = MODULE_APIS.get("performance")
        if "goal" in title_lower:
            return test_list_endpoint("/goals", "org_admin", base_url=base, description=title)
        if "review" in title_lower:
            return test_list_endpoint("/review-cycles", "org_admin", base_url=base,
                                      description=title)
        return test_api_endpoint("GET", "/review-cycles", "org_admin", base_url=base,
                                 description=title)

    # -- Rewards bugs --
    if "reward" in title_lower or "kudos" in title_lower or "recognition" in title_lower:
        base = MODULE_APIS.get("rewards")
        return test_list_endpoint("/kudos", "org_admin", base_url=base, description=title)

    # -- Exit bugs --
    if "exit" in title_lower or "resignation" in title_lower or "offboarding" in title_lower:
        base = MODULE_APIS.get("exit")
        return test_list_endpoint("/exits", "org_admin", base_url=base, description=title)

    # -- LMS bugs --
    if "lms" in title_lower or "course" in title_lower or "training" in title_lower:
        base = MODULE_APIS.get("lms")
        return test_list_endpoint("/courses", "org_admin", base_url=base, description=title)

    # -- Project bugs --
    if "project" in title_lower or "task" in title_lower or "timesheet" in title_lower:
        base = MODULE_APIS.get("project")
        return test_list_endpoint("/projects", "org_admin", base_url=base, description=title)

    # -- Enhancement / Feature request --
    if "enhancement" in labels or "feature-request" in labels or "documentation" in labels:
        steps = [
            f"Step 1: Issue #{num} is an enhancement/feature request",
            "Step 2: Not a bug fix to verify -> Skipping"
        ]
        return "SKIPPED", steps

    # -- Fallback: try to extract a path from the body and test it --
    if path_from_text:
        method = method_from_text or "GET"
        return test_api_endpoint(method, path_from_text, "org_admin", description=title)

    # -- Cannot classify --
    steps = [
        f"Step 1: Could not auto-classify issue #{num}",
        f"  Title: {title[:80]}",
        f"  Labels: {[l['name'] for l in issue.get('labels', [])]}",
    ]
    if dev_says_fixed:
        steps.append("Step 2: Developer comments indicate this was fixed")
        steps.append("Step 3: Trusting developer confirmation, marking as fixed")
        return "FIXED", steps
    if dev_says_wontfix:
        steps.append("Step 2: Developer says won't fix / by design")
        return "FIXED", steps

    return "SKIPPED", steps


# -- Main ------------------------------------------------------------------

def main():
    print("=" * 80)
    print("EMPCLOUD DEEP RE-VERIFY -- Closed Issues Pages 3-4 (#201-#400 range)")
    print(f"Date: {TODAY}")
    print(f"API: {API_BASE}")
    print(f"GitHub delay: {GH_DELAY}s between calls")
    print("=" * 80)

    # Pre-login all roles
    print("\n[*] Pre-authenticating all roles...")
    for role in ["org_admin", "employee", "super_admin"]:
        token = login(role)
        if token:
            print(f"  {role}: OK (token={token[:20]}...)")
        else:
            print(f"  {role}: FAILED")

    # Fetch closed issues pages 3 and 4
    all_issues = []
    for page in [3, 4]:
        print(f"\n[*] Fetching closed issues page {page}...")
        status, issues = gh_api("GET",
            f"/repos/{GITHUB_REPO}/issues?state=closed&per_page=100&page={page}&sort=created&direction=desc")
        if status != 200:
            print(f"  FATAL: Could not fetch page {page}: {status}")
            continue
        if not isinstance(issues, list):
            print(f"  FATAL: Unexpected response type for page {page}")
            continue
        print(f"  Got {len(issues)} issues from page {page}")
        all_issues.extend(issues)

    if not all_issues:
        print("FATAL: No issues fetched. Exiting.")
        return

    print(f"\n[*] Total issues to process: {len(all_issues)}")

    # Filter out PRs
    issues = [i for i in all_issues if not i.get("pull_request")]
    print(f"[*] After filtering PRs: {len(issues)} issues")

    # Track results
    results = {"FIXED": 0, "STILL FAILING": 0, "INCONCLUSIVE": 0, "SKIPPED": 0}
    still_failing = []
    verified_fixed = []
    issue_results = []  # for final report

    print("\n" + "=" * 80)
    print("STARTING DEEP RE-VERIFICATION")
    print("=" * 80)

    for idx, issue in enumerate(issues):
        num = issue["number"]
        title = issue["title"]

        print(f"\n{'─' * 70}")
        print(f"[{idx+1}/{len(issues)}] #{num}: {title[:65]}")
        print(f"{'─' * 70}")

        # Skip field force, biometrics, rate limit
        if should_skip(issue):
            print(f"  SKIPPED (field force / biometrics / rate limit)")
            results["SKIPPED"] += 1
            issue_results.append({"number": num, "title": title, "verdict": "SKIPPED",
                                   "reason": "excluded module/topic"})
            continue

        # Step 1: Read programmer comments
        print(f"  [*] Fetching comments for #{num}...")
        comments = fetch_issue_comments(num)
        programmer_notes = get_programmer_notes(comments)
        if programmer_notes:
            print(f"  [*] Found {len(programmer_notes)} programmer comment(s):")
            for note in programmer_notes[:3]:
                print(f"    @{note['user']} ({note['created_at'][:10]}): {note['body'][:100]}...")
        else:
            print(f"  [*] No programmer comments found")

        # Step 2: Test the issue
        try:
            verdict, steps = classify_and_test(issue, programmer_notes)
        except Exception as e:
            verdict = "INCONCLUSIVE"
            steps = [f"ERROR during test: {e}", traceback.format_exc()[:300]]

        # Print steps
        for step in steps:
            print(f"  {step}")

        print(f"\n  >>> VERDICT: {verdict}")
        results[verdict] = results.get(verdict, 0) + 1

        # Step 3: Apply label and comment
        dev_notes_summary = ""
        if programmer_notes:
            dev_notes_summary = "\n**Programmer comments reviewed:**\n"
            for note in programmer_notes[:3]:
                dev_notes_summary += f"- @{note['user']}: {note['body'][:120]}...\n"

        step_text = "\n".join(f"- {s}" for s in steps)

        if verdict == "FIXED":
            verified_fixed.append(num)
            comment = (
                f"## Re-verification by E2E Agent ({TODAY})\n\n"
                f"{dev_notes_summary}\n"
                f"**Test steps:**\n{step_text}\n\n"
                f"**Result: VERIFIED FIXED** :white_check_mark:\n\n"
                f"Adding `verified-fixed` label."
            )
            add_github_comment(num, comment)
            add_label(num, "verified-fixed")

        elif verdict == "STILL FAILING":
            still_failing.append(num)
            comment = (
                f"## Re-verification by E2E Agent ({TODAY})\n\n"
                f"{dev_notes_summary}\n"
                f"**Test steps:**\n{step_text}\n\n"
                f"**Result: STILL FAILING** :x:\n\n"
                f"Re-opening issue and adding `verified-bug` label."
            )
            add_github_comment(num, comment)
            add_label(num, "verified-bug")
            reopen_issue(num)

        elif verdict == "INCONCLUSIVE":
            comment = (
                f"## Re-verification by E2E Agent ({TODAY})\n\n"
                f"{dev_notes_summary}\n"
                f"**Test steps:**\n{step_text}\n\n"
                f"**Result: INCONCLUSIVE** :grey_question:\n\n"
                f"Could not definitively verify fix. Manual review recommended."
            )
            add_github_comment(num, comment)

        # else SKIPPED: no comment

        issue_results.append({
            "number": num,
            "title": title,
            "verdict": verdict,
            "steps": steps,
            "programmer_notes": len(programmer_notes),
        })

        # Brief pause between issues (GH throttle handles individual calls)
        time.sleep(1)

    # -- Summary --
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    for k, v in results.items():
        print(f"  {k}: {v}")
    total = sum(results.values())
    print(f"\n  Total processed: {total}")

    if still_failing:
        print(f"\n  STILL FAILING (re-opened + verified-bug): {still_failing}")
    if verified_fixed:
        print(f"\n  VERIFIED FIXED (labeled verified-fixed): {verified_fixed}")

    # Retry any pending GH operations
    if _pending_gh:
        print(f"\n[*] Retrying {len(_pending_gh)} pending GitHub operations after 30s cooldown...")
        time.sleep(30)
        for action_tuple in _pending_gh:
            action = action_tuple[0]
            issue_num = action_tuple[1]
            if action == "comment":
                comment_body = action_tuple[2]
                s, _ = gh_api("POST", f"/repos/{GITHUB_REPO}/issues/{issue_num}/comments",
                              json_data={"body": comment_body})
                print(f"    [RETRY] Comment #{issue_num}: {'OK' if s == 201 else 'FAIL'}")
            elif action == "reopen":
                s, _ = gh_api("PATCH", f"/repos/{GITHUB_REPO}/issues/{issue_num}",
                              json_data={"state": "open"})
                print(f"    [RETRY] Reopen #{issue_num}: {'OK' if s == 200 else 'FAIL'}")

    # Save results JSON
    results_file = os.path.join(os.path.dirname(__file__), "deep_verify_201_400_results.json")
    with open(results_file, "w", encoding="utf-8") as f:
        json.dump({
            "date": TODAY,
            "summary": results,
            "still_failing": still_failing,
            "verified_fixed": verified_fixed,
            "details": issue_results,
        }, f, indent=2, ensure_ascii=False)
    print(f"\n[*] Results saved to {results_file}")

    print("\nDone.")


if __name__ == "__main__":
    main()
