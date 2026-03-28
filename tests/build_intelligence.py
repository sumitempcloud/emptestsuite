#!/usr/bin/env python3
"""
EmpCloud Intelligence Builder
Fetches all issues + comments from EmpCloud/EmpCloud and builds a comprehensive analysis.
"""

import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import json
import re
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from collections import defaultdict, Counter
from datetime import datetime

# Create a session with retry logic
session = requests.Session()
retries = Retry(total=5, backoff_factor=1.0, status_forcelist=[429, 500, 502, 503, 504],
                allowed_methods=["GET"])
adapter = HTTPAdapter(max_retries=retries)
session.mount("https://", adapter)
session.mount("http://", adapter)

GITHUB_TOKEN = "os.environ.get('GITHUB_TOKEN', 'YOUR_TOKEN_HERE')"
REPO = "EmpCloud/EmpCloud"
HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

def api_get(url):
    """Make a GET request with retry and rate limit handling."""
    for attempt in range(5):
        try:
            resp = session.get(url, headers=HEADERS, timeout=30)
            # Check for rate limiting
            remaining = resp.headers.get("X-RateLimit-Remaining", "?")
            if resp.status_code == 403 and "rate limit" in resp.text.lower():
                reset_time = int(resp.headers.get("X-RateLimit-Reset", 0))
                wait = max(reset_time - int(time.time()), 60)
                print(f"    Rate limited! Waiting {wait}s...")
                time.sleep(wait)
                continue
            return resp
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            wait = 2 ** attempt
            print(f"    Connection error (attempt {attempt+1}/5), retrying in {wait}s...")
            time.sleep(wait)
    return None

def fetch_all_issues():
    """Fetch all issues (open + closed), pages 1-10."""
    all_issues = []
    for state in ["open", "closed"]:
        for page in range(1, 11):
            url = f"https://api.github.com/repos/{REPO}/issues?state={state}&per_page=100&page={page}"
            print(f"  Fetching {state} issues page {page}...")
            resp = api_get(url)
            if resp is None or resp.status_code != 200:
                print(f"    Error fetching page, stopping.")
                break
            data = resp.json()
            if not data:
                print(f"    No more {state} issues.")
                break
            # Filter out pull requests
            issues = [i for i in data if "pull_request" not in i]
            all_issues.extend(issues)
            print(f"    Got {len(issues)} issues (total so far: {len(all_issues)})")
            time.sleep(0.5)
    return all_issues

def fetch_all_comments_bulk():
    """Fetch ALL issue comments for the repo using the bulk endpoint."""
    all_comments = []
    for page in range(1, 200):  # up to 20k comments
        url = f"https://api.github.com/repos/{REPO}/issues/comments?per_page=100&page={page}&sort=created&direction=asc"
        print(f"  Fetching comments page {page}...")
        resp = api_get(url)
        if resp is None or resp.status_code != 200:
            print(f"    Error or rate limit, stopping at page {page}.")
            break
        data = resp.json()
        if not data:
            print(f"    No more comments (total: {len(all_comments)}).")
            break
        # Extract issue number from the issue_url
        for c in data:
            issue_url = c.get("issue_url", "")
            # issue_url looks like https://api.github.com/repos/EmpCloud/EmpCloud/issues/123
            parts = issue_url.rstrip("/").split("/")
            try:
                c["issue_number"] = int(parts[-1])
            except (ValueError, IndexError):
                c["issue_number"] = 0
        all_comments.extend(data)
        print(f"    Got {len(data)} comments (total: {len(all_comments)})")
        time.sleep(0.3)
    return all_comments

def fetch_comments(issue_number):
    """Fetch all comments for a given issue (fallback, not used in bulk mode)."""
    comments = []
    for page in range(1, 5):
        url = f"https://api.github.com/repos/{REPO}/issues/{issue_number}/comments?per_page=100&page={page}"
        resp = api_get(url)
        if resp is None or resp.status_code != 200:
            break
        data = resp.json()
        if not data:
            break
        comments.extend(data)
    return comments

def classify_module(title, body, labels):
    """Classify which module an issue belongs to."""
    text = (title + " " + (body or "")).lower()
    label_names = [l["name"].lower() for l in labels] if labels else []

    module_keywords = {
        "emp-attendance": ["attendance", "check-in", "check-out", "checkin", "checkout", "emp-attendance"],
        "emp-leave": ["leave", "emp-leave", "leave balance", "leave request", "leave type"],
        "emp-payroll": ["payroll", "emp-payroll", "salary", "payslip", "ctc"],
        "emp-core": ["emp-core", "employee", "department", "designation", "organization"],
        "emp-auth": ["auth", "login", "sso", "token", "jwt", "emp-auth", "authentication"],
        "emp-engage": ["engage", "emp-engage", "announcement", "survey", "poll"],
        "emp-performance": ["performance", "emp-performance", "kpi", "appraisal", "goal"],
        "emp-recruit": ["recruit", "emp-recruit", "job", "candidate", "hiring", "applicant"],
        "emp-field": ["field", "emp-field", "field force", "tracking"],
        "emp-biometrics": ["biometric", "emp-biometric", "fingerprint", "face"],
        "emp-helpdesk": ["helpdesk", "emp-helpdesk", "ticket", "support"],
        "emp-expense": ["expense", "emp-expense", "reimbursement", "claim"],
        "emp-documents": ["document", "emp-document", "doc management"],
        "emp-training": ["training", "emp-training", "course", "lms"],
        "frontend/dashboard": ["dashboard", "frontend", "ui", "sidebar", "navigation", "menu"],
    }

    # Check labels first
    for module, keywords in module_keywords.items():
        for kw in keywords:
            if any(kw in ln for ln in label_names):
                return module

    # Check title/body
    for module, keywords in module_keywords.items():
        for kw in keywords:
            if kw in text:
                return module

    return "unknown"

def classify_bug_type(title, body):
    """Classify the type of bug."""
    text = (title + " " + (body or "")).lower()
    types = []

    type_keywords = {
        "RBAC": ["rbac", "role", "permission", "access control", "unauthorized", "forbidden", "admin ui to employee"],
        "Routing/404": ["404", "not found", "route", "routing", "endpoint not found", "page not found"],
        "SSO": ["sso", "single sign", "token", "jwt", "rs256"],
        "Validation": ["validation", "required field", "invalid", "missing field", "400"],
        "Server Error (500)": ["500", "internal server", "server error", "crash"],
        "UI/Frontend": ["ui", "frontend", "display", "render", "css", "layout", "sidebar", "button"],
        "Data Integrity": ["count", "mismatch", "calculation", "balance", "orphan", "inconsist"],
        "API Response": ["response", "api", "endpoint", "payload", "json"],
        "Authentication": ["auth", "login", "logout", "session", "expire"],
        "Rate Limiting": ["rate limit", "429", "throttl"],
        "CORS": ["cors", "cross-origin", "access-control"],
        "Performance": ["slow", "timeout", "performance", "latency"],
        "Missing Feature": ["missing", "not implemented", "todo", "placeholder"],
    }

    for bug_type, keywords in type_keywords.items():
        for kw in keywords:
            if kw in text:
                types.append(bug_type)
                break

    return types if types else ["Other"]

def extract_endpoints(text):
    """Extract API endpoints from issue text."""
    if not text:
        return []
    patterns = [
        r'(?:GET|POST|PUT|DELETE|PATCH)\s+(/[a-zA-Z0-9/_\-{}:]+)',
        r'(?:https?://[^/\s]+)(/api/[a-zA-Z0-9/_\-{}:]+)',
        r'(/api/[a-zA-Z0-9/_\-{}:]+)',
        r'`(/[a-zA-Z0-9/_\-{}:]+)`',
    ]
    endpoints = []
    for p in patterns:
        endpoints.extend(re.findall(p, text))
    return list(set(endpoints))

def extract_status_codes(text):
    """Extract HTTP status codes from text."""
    if not text:
        return []
    codes = re.findall(r'\b(2\d{2}|3\d{2}|4\d{2}|5\d{2})\b', text)
    return codes

def analyze_programmer_comments(comments, issues):
    """Analyze comments from the developer (sumitempcloud)."""
    dev_comments = []
    patterns = {
        "by_design": [],
        "not_a_bug": [],
        "fixed": [],
        "wont_fix": [],
        "explanations": [],
        "commit_refs": [],
    }

    for c in comments:
        user = c.get("user", {}).get("login", "")
        body = c.get("body", "") or ""
        issue_num = c.get("issue_number", "?")

        if user.lower() in ["sumitempcloud", "sumit"]:
            dev_comments.append(c)
            lower_body = body.lower()

            if "by design" in lower_body or "intended" in lower_body or "expected behavior" in lower_body:
                patterns["by_design"].append({"issue": issue_num, "comment": body[:300]})
            if "not a bug" in lower_body or "not bug" in lower_body or "working as expected" in lower_body:
                patterns["not_a_bug"].append({"issue": issue_num, "comment": body[:300]})
            if "fixed" in lower_body or "resolved" in lower_body or "deployed" in lower_body:
                patterns["fixed"].append({"issue": issue_num, "comment": body[:300]})
            if "won't fix" in lower_body or "wontfix" in lower_body or "not planned" in lower_body:
                patterns["wont_fix"].append({"issue": issue_num, "comment": body[:300]})

            # Extract commit references
            commits = re.findall(r'[a-f0-9]{7,40}', body)
            if commits:
                patterns["commit_refs"].extend([{"issue": issue_num, "commit": c_hash} for c_hash in commits])

            if len(body.strip()) > 20:
                patterns["explanations"].append({"issue": issue_num, "comment": body[:500]})

    return dev_comments, patterns

def build_intelligence(issues, all_comments):
    """Build the comprehensive intelligence document."""

    # === MODULE ANALYSIS ===
    module_stats = defaultdict(lambda: {"total": 0, "open": 0, "closed": 0, "bugs": [], "bug_types": Counter()})
    bug_type_counter = Counter()
    endpoint_status = defaultdict(list)  # endpoint -> list of status codes
    endpoints_200 = set()
    endpoints_404 = set()
    endpoints_500 = set()
    all_endpoints = set()
    sso_info = []
    rbac_info = []
    data_integrity = []
    false_positives = []
    not_a_bug_issues = []
    by_design_issues = []

    for issue in issues:
        title = issue.get("title", "")
        body = issue.get("body", "") or ""
        state = issue.get("state", "")
        labels = issue.get("labels", [])
        number = issue.get("number", 0)
        label_names = [l["name"].lower() for l in labels] if labels else []
        full_text = title + " " + body

        module = classify_module(title, body, labels)
        bug_types = classify_bug_type(title, body)

        module_stats[module]["total"] += 1
        if state == "open":
            module_stats[module]["open"] += 1
        else:
            module_stats[module]["closed"] += 1

        module_stats[module]["bugs"].append({
            "number": number,
            "title": title,
            "state": state,
            "types": bug_types
        })

        for bt in bug_types:
            module_stats[module]["bug_types"][bt] += 1
            bug_type_counter[bt] += 1

        # Extract endpoints
        eps = extract_endpoints(full_text)
        all_endpoints.update(eps)

        codes = extract_status_codes(full_text)
        for ep in eps:
            endpoint_status[ep].extend(codes)
            if "200" in codes:
                endpoints_200.add(ep)
            if "404" in codes:
                endpoints_404.add(ep)
            if "500" in codes:
                endpoints_500.add(ep)

        # SSO related
        if any(kw in full_text.lower() for kw in ["sso", "token", "jwt", "rs256", "single sign"]):
            sso_info.append({"number": number, "title": title, "body": body[:500], "state": state})

        # RBAC related
        if any(kw in full_text.lower() for kw in ["rbac", "role", "permission", "access control", "admin", "employee role"]):
            rbac_info.append({"number": number, "title": title, "body": body[:500], "state": state})

        # Data integrity
        if any(kw in full_text.lower() for kw in ["count", "mismatch", "calculation", "balance", "orphan", "integrity"]):
            data_integrity.append({"number": number, "title": title, "body": body[:500], "state": state})

        # False positives / not-a-bug
        if any(ln in ["not a bug", "by design", "wontfix", "invalid", "duplicate"] for ln in label_names):
            false_positives.append({"number": number, "title": title, "state": state, "labels": label_names})

        # Check comments for not-a-bug / by-design
        issue_comments = [c for c in all_comments if c.get("issue_number") == number]
        for c in issue_comments:
            cbody = (c.get("body", "") or "").lower()
            if "not a bug" in cbody or "working as expected" in cbody:
                not_a_bug_issues.append({"number": number, "title": title, "comment": c.get("body", "")[:300]})
            if "by design" in cbody or "intended" in cbody:
                by_design_issues.append({"number": number, "title": title, "comment": c.get("body", "")[:300]})

    # Programmer analysis
    dev_comments, dev_patterns = analyze_programmer_comments(all_comments, issues)

    return {
        "module_stats": {k: {"total": v["total"], "open": v["open"], "closed": v["closed"],
                             "bug_types": dict(v["bug_types"]),
                             "bugs": v["bugs"]} for k, v in module_stats.items()},
        "bug_type_counter": dict(bug_type_counter),
        "endpoints_200": sorted(endpoints_200),
        "endpoints_404": sorted(endpoints_404),
        "endpoints_500": sorted(endpoints_500),
        "all_endpoints": sorted(all_endpoints),
        "endpoint_status": {k: v for k, v in endpoint_status.items()},
        "sso_info": sso_info,
        "rbac_info": rbac_info,
        "data_integrity": data_integrity,
        "false_positives": false_positives,
        "not_a_bug_issues": not_a_bug_issues,
        "by_design_issues": by_design_issues,
        "dev_comments_count": len(dev_comments),
        "dev_patterns": {k: v for k, v in dev_patterns.items()},
        "total_issues": len(issues),
        "open_issues": sum(1 for i in issues if i["state"] == "open"),
        "closed_issues": sum(1 for i in issues if i["state"] == "closed"),
    }

def generate_markdown(intel, issues, all_comments):
    """Generate the INTELLIGENCE.md document."""

    lines = []
    lines.append("# EmpCloud HRMS - Comprehensive Test Intelligence Document")
    lines.append(f"\n**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"**Source:** {REPO} GitHub Issues (all open + closed)")
    lines.append(f"**Total Issues Analyzed:** {intel['total_issues']}")
    lines.append(f"**Open Issues:** {intel['open_issues']}")
    lines.append(f"**Closed Issues:** {intel['closed_issues']}")
    lines.append(f"**Developer Comments Analyzed:** {intel['dev_comments_count']}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # === A. BUG PATTERNS ===
    lines.append("## A. BUG PATTERNS - What Breaks Most Often?")
    lines.append("")

    lines.append("### Bug Type Frequency")
    lines.append("")
    lines.append("| Bug Type | Count |")
    lines.append("|----------|-------|")
    for bt, count in sorted(intel["bug_type_counter"].items(), key=lambda x: -x[1]):
        lines.append(f"| {bt} | {count} |")
    lines.append("")

    lines.append("### Modules With Most Bugs")
    lines.append("")
    lines.append("| Module | Total | Open | Closed | Top Bug Types |")
    lines.append("|--------|-------|------|--------|---------------|")
    sorted_modules = sorted(intel["module_stats"].items(), key=lambda x: -x[1]["total"])
    for mod, stats in sorted_modules:
        top_types = ", ".join(f"{k}({v})" for k, v in sorted(stats["bug_types"].items(), key=lambda x: -x[1])[:3])
        lines.append(f"| {mod} | {stats['total']} | {stats['open']} | {stats['closed']} | {top_types} |")
    lines.append("")

    lines.append("### Common Root Causes (from issue analysis)")
    lines.append("")
    lines.append("Based on recurring patterns across issues:")
    lines.append("")

    # Analyze root causes from issues
    root_causes = Counter()
    for issue in issues:
        body = (issue.get("body", "") or "").lower()
        title = issue.get("title", "").lower()
        text = title + " " + body
        if "route" in text and ("404" in text or "not found" in text):
            root_causes["Missing/incorrect API routes"] += 1
        if "rbac" in text or ("permission" in text and "denied" not in text):
            root_causes["RBAC enforcement gaps"] += 1
        if "validat" in text or "required" in text:
            root_causes["Missing input validation"] += 1
        if "sso" in text and ("fail" in text or "error" in text or "invalid" in text):
            root_causes["SSO token handling issues"] += 1
        if "null" in text or "undefined" in text:
            root_causes["Null/undefined reference errors"] += 1
        if "cors" in text:
            root_causes["CORS configuration issues"] += 1
        if "500" in text:
            root_causes["Unhandled server exceptions"] += 1

    for cause, count in sorted(root_causes.items(), key=lambda x: -x[1]):
        lines.append(f"- **{cause}**: {count} occurrences")
    lines.append("")

    # === B. PROGRAMMER PATTERNS ===
    lines.append("---")
    lines.append("")
    lines.append("## B. PROGRAMMER PATTERNS - How Does the Developer Fix Things?")
    lines.append("")

    dev_p = intel["dev_patterns"]

    lines.append("### Developer Response Categories")
    lines.append("")
    lines.append(f"- **Marked as 'by design':** {len(dev_p['by_design'])} issues")
    lines.append(f"- **Marked as 'not a bug':** {len(dev_p['not_a_bug'])} issues")
    lines.append(f"- **Confirmed fixed:** {len(dev_p['fixed'])} issues")
    lines.append(f"- **Won't fix:** {len(dev_p['wont_fix'])} issues")
    lines.append(f"- **Total explanations given:** {len(dev_p['explanations'])}")
    lines.append(f"- **Commit references:** {len(dev_p['commit_refs'])}")
    lines.append("")

    if dev_p["explanations"]:
        lines.append("### Developer Explanations (All Comments from sumitempcloud)")
        lines.append("")
        for exp in dev_p["explanations"]:
            lines.append(f"**Issue #{exp['issue']}:**")
            lines.append(f"> {exp['comment'][:400]}")
            lines.append("")

    if dev_p["by_design"]:
        lines.append("### Issues Marked 'By Design'")
        lines.append("")
        for item in dev_p["by_design"]:
            lines.append(f"- **Issue #{item['issue']}:** {item['comment'][:200]}")
        lines.append("")

    if dev_p["not_a_bug"]:
        lines.append("### Issues Marked 'Not a Bug'")
        lines.append("")
        for item in dev_p["not_a_bug"]:
            lines.append(f"- **Issue #{item['issue']}:** {item['comment'][:200]}")
        lines.append("")

    if dev_p["commit_refs"]:
        lines.append("### Commit References in Fixes")
        lines.append("")
        for item in dev_p["commit_refs"][:20]:
            lines.append(f"- Issue #{item['issue']}: `{item['commit']}`")
        lines.append("")

    # === C. FALSE POSITIVE PATTERNS ===
    lines.append("---")
    lines.append("")
    lines.append("## C. FALSE POSITIVE PATTERNS - What Should We Stop Testing?")
    lines.append("")

    if intel["not_a_bug_issues"]:
        lines.append("### Issues Confirmed 'Not a Bug' (in comments)")
        lines.append("")
        for item in intel["not_a_bug_issues"]:
            lines.append(f"- **#{item['number']}** {item['title']}")
            lines.append(f"  > {item['comment'][:200]}")
        lines.append("")

    if intel["by_design_issues"]:
        lines.append("### Issues Confirmed 'By Design' (in comments)")
        lines.append("")
        for item in intel["by_design_issues"]:
            lines.append(f"- **#{item['number']}** {item['title']}")
            lines.append(f"  > {item['comment'][:200]}")
        lines.append("")

    if intel["false_positives"]:
        lines.append("### Issues With 'Not a Bug' / 'Invalid' / 'Duplicate' Labels")
        lines.append("")
        for item in intel["false_positives"]:
            lines.append(f"- **#{item['number']}** {item['title']} (labels: {', '.join(item['labels'])})")
        lines.append("")

    # Build exclusion list from 404 endpoints
    lines.append("### Exclusion List - API Paths That Don't Exist")
    lines.append("")
    lines.append("These endpoints returned 404 and likely should not be tested:")
    lines.append("")
    for ep in sorted(intel["endpoints_404"]):
        lines.append(f"- `{ep}`")
    if not intel["endpoints_404"]:
        lines.append("- (No 404 endpoints explicitly identified in issues)")
    lines.append("")

    lines.append("### Behaviors That Are 'By Design'")
    lines.append("")
    lines.append("These behaviors have been confirmed as intentional and should not be reported as bugs:")
    lines.append("")
    # Gather from by_design and not_a_bug
    design_items = set()
    for item in intel["by_design_issues"] + intel["not_a_bug_issues"]:
        design_items.add(f"#{item['number']} - {item['title']}")
    for item in sorted(design_items):
        lines.append(f"- {item}")
    if not design_items:
        lines.append("- (No explicit 'by design' items found in comments)")
    lines.append("")

    # Rate limiting note
    lines.append("### Known Non-Issues")
    lines.append("")
    lines.append("- **Rate limiting is intentionally disabled** for E2E testing - do not report rate limit bugs")
    lines.append("- **emp-field and emp-biometrics modules** should be skipped for now")
    lines.append("")

    # === D. MODULE HEALTH MAP ===
    lines.append("---")
    lines.append("")
    lines.append("## D. MODULE HEALTH MAP")
    lines.append("")

    for mod, stats in sorted_modules:
        stability = "STABLE" if stats["open"] == 0 and stats["total"] <= 2 else \
                    "MOSTLY STABLE" if stats["open"] <= 1 else \
                    "UNSTABLE" if stats["open"] >= 3 else "MODERATE"
        lines.append(f"### {mod} [{stability}]")
        lines.append("")
        lines.append(f"- **Total bugs:** {stats['total']}")
        lines.append(f"- **Fixed:** {stats['closed']}")
        lines.append(f"- **Open:** {stats['open']}")
        if stats["bug_types"]:
            lines.append(f"- **Common issues:** {', '.join(f'{k} ({v})' for k, v in sorted(stats['bug_types'].items(), key=lambda x: -x[1]))}")
        lines.append("")

        # List specific bugs
        lines.append("| # | Title | State | Types |")
        lines.append("|---|-------|-------|-------|")
        for bug in stats["bugs"]:
            lines.append(f"| #{bug['number']} | {bug['title'][:60]} | {bug['state']} | {', '.join(bug['types'])} |")
        lines.append("")

    # === E. TEST COVERAGE GAPS ===
    lines.append("---")
    lines.append("")
    lines.append("## E. TEST COVERAGE GAPS")
    lines.append("")

    # Analyze what modules have few or no bugs filed
    tested_modules = set(intel["module_stats"].keys())
    all_known_modules = {
        "emp-attendance", "emp-leave", "emp-payroll", "emp-core", "emp-auth",
        "emp-engage", "emp-performance", "emp-recruit", "emp-field", "emp-biometrics",
        "emp-helpdesk", "emp-expense", "emp-documents", "emp-training"
    }

    untested = all_known_modules - tested_modules
    lightly_tested = {mod for mod, s in intel["module_stats"].items() if s["total"] <= 1}

    lines.append("### Modules With No/Minimal Bug Reports (Potential Coverage Gaps)")
    lines.append("")
    for mod in sorted(untested):
        lines.append(f"- **{mod}** - No bugs filed, potentially untested")
    for mod in sorted(lightly_tested):
        lines.append(f"- **{mod}** - Only {intel['module_stats'][mod]['total']} bug(s) filed, lightly tested")
    lines.append("")

    lines.append("### Untested Scenarios (Recommended)")
    lines.append("")
    lines.append("Based on the issues analyzed, these scenarios need more testing:")
    lines.append("")
    lines.append("- **Concurrent user access** - No issues testing multi-user scenarios")
    lines.append("- **Bulk operations** - Large dataset handling (100+ employees, bulk leave approval)")
    lines.append("- **Edge cases in date handling** - Month boundaries, leap years, fiscal year transitions")
    lines.append("- **File upload/download** - Document management, profile pictures, payslip PDFs")
    lines.append("- **Notification systems** - Email/push notification triggers")
    lines.append("- **Audit trails** - Logging of sensitive operations")
    lines.append("- **Cross-module interactions** - Leave affecting attendance, attendance affecting payroll")
    lines.append("- **Mobile responsiveness** - UI testing on different screen sizes")
    lines.append("")

    # === F. API ENDPOINT MAP ===
    lines.append("---")
    lines.append("")
    lines.append("## F. API ENDPOINT MAP (from issue data)")
    lines.append("")

    lines.append("### Endpoints Returning 200 (Working)")
    lines.append("")
    for ep in sorted(intel["endpoints_200"]):
        lines.append(f"- `{ep}`")
    if not intel["endpoints_200"]:
        lines.append("- (No explicit 200 endpoints identified in issues)")
    lines.append("")

    lines.append("### Endpoints Returning 404 (Not Found / Missing)")
    lines.append("")
    for ep in sorted(intel["endpoints_404"]):
        lines.append(f"- `{ep}`")
    if not intel["endpoints_404"]:
        lines.append("- (No explicit 404 endpoints identified in issues)")
    lines.append("")

    lines.append("### Endpoints Returning 500 (Server Error)")
    lines.append("")
    for ep in sorted(intel["endpoints_500"]):
        lines.append(f"- `{ep}`")
    if not intel["endpoints_500"]:
        lines.append("- (No explicit 500 endpoints identified in issues)")
    lines.append("")

    lines.append("### All Endpoints Mentioned in Issues")
    lines.append("")
    for ep in sorted(intel["all_endpoints"]):
        statuses = intel["endpoint_status"].get(ep, [])
        status_str = f" (status codes seen: {', '.join(sorted(set(statuses)))})" if statuses else ""
        lines.append(f"- `{ep}`{status_str}")
    if not intel["all_endpoints"]:
        lines.append("- (No endpoints explicitly mentioned in issues)")
    lines.append("")

    # === G. SSO INTELLIGENCE ===
    lines.append("---")
    lines.append("")
    lines.append("## G. SSO INTELLIGENCE")
    lines.append("")

    lines.append("### SSO Architecture (from issue analysis)")
    lines.append("")
    lines.append("- **Mechanism:** Token passed via URL parameter")
    lines.append("- **Token expiry:** 15 minutes")
    lines.append("- **Algorithm:** RS256 (RSA Signature with SHA-256)")
    lines.append("- **Flow:** emp-core generates SSO token -> user redirected to module with token in URL -> module validates token")
    lines.append("")

    lines.append("### SSO-Related Issues")
    lines.append("")
    for item in intel["sso_info"]:
        lines.append(f"- **#{item['number']}** [{item['state']}] {item['title']}")
    if not intel["sso_info"]:
        lines.append("- (No SSO-specific issues found)")
    lines.append("")

    lines.append("### SSO Failure Patterns")
    lines.append("")
    sso_failures = [i for i in intel["sso_info"] if any(kw in (i.get("body","") or "").lower() for kw in ["fail", "error", "invalid", "expire", "reject"])]
    for item in sso_failures:
        lines.append(f"- **#{item['number']}** {item['title']}")
    if not sso_failures:
        lines.append("- (No SSO failure patterns explicitly documented in issues)")
    lines.append("")

    # === H. RBAC MAP ===
    lines.append("---")
    lines.append("")
    lines.append("## H. RBAC MAP")
    lines.append("")

    lines.append("### Roles in the System")
    lines.append("")
    lines.append("- **super_admin** - Full system access, manages all organizations")
    lines.append("- **org_admin** - Organization-level admin, manages their org's employees and settings")
    lines.append("- **employee** - Basic employee access, self-service features")
    lines.append("")

    lines.append("### RBAC-Related Issues")
    lines.append("")
    for item in intel["rbac_info"]:
        lines.append(f"- **#{item['number']}** [{item['state']}] {item['title']}")
    if not intel["rbac_info"]:
        lines.append("- (No RBAC-specific issues found)")
    lines.append("")

    lines.append("### Known RBAC Gaps")
    lines.append("")
    rbac_gaps = [i for i in intel["rbac_info"] if "gap" in (i.get("body","") or "").lower() or
                 "employee" in (i.get("body","") or "").lower() and "admin" in (i.get("body","") or "").lower()]
    for item in rbac_gaps:
        lines.append(f"- **#{item['number']}** {item['title']}")
    if not rbac_gaps:
        lines.append("- (No explicit RBAC gaps documented in issues)")
    lines.append("")

    # === I. DATA INTEGRITY ===
    lines.append("---")
    lines.append("")
    lines.append("## I. DATA INTEGRITY FINDINGS")
    lines.append("")

    for item in intel["data_integrity"]:
        lines.append(f"### Issue #{item['number']}: {item['title']} [{item['state']}]")
        lines.append("")
        if item.get("body"):
            lines.append(f"> {item['body'][:300]}")
        lines.append("")
    if not intel["data_integrity"]:
        lines.append("No data integrity issues found in the issue tracker.")
        lines.append("")

    # === J. RECOMMENDED TEST STRATEGY ===
    lines.append("---")
    lines.append("")
    lines.append("## J. RECOMMENDED TEST STRATEGY FOR FUTURE")
    lines.append("")

    lines.append("### Priority 1 - High Value Tests (Run First)")
    lines.append("")
    # Find modules with most open bugs
    high_priority_mods = [(mod, stats) for mod, stats in sorted_modules if stats["open"] > 0]
    for mod, stats in high_priority_mods[:5]:
        lines.append(f"- **{mod}** ({stats['open']} open bugs) - Focus on: {', '.join(list(stats['bug_types'].keys())[:3])}")
    lines.append("")

    lines.append("### Priority 2 - Regression Tests (Verify Fixes)")
    lines.append("")
    lines.append("Re-test all closed bugs to verify they stay fixed:")
    lines.append("")
    closed_bugs = [(i["number"], i["title"]) for mod, stats in sorted_modules for i in stats["bugs"] if i["state"] == "closed"]
    for num, title in closed_bugs[:15]:
        lines.append(f"- #{num}: {title[:60]}")
    lines.append("")

    lines.append("### Priority 3 - Coverage Expansion")
    lines.append("")
    lines.append("Test modules with no/minimal bug reports to find undiscovered issues.")
    lines.append("")

    lines.append("### What to Skip (Known False Positives)")
    lines.append("")
    lines.append("- Rate limiting tests (intentionally disabled)")
    lines.append("- emp-field module (skip for now)")
    lines.append("- emp-biometrics module (skip for now)")
    for item in sorted(design_items):
        lines.append(f"- {item}")
    lines.append("")

    lines.append("### Test Method Recommendations")
    lines.append("")
    lines.append("| Module | Recommended Method | Reason |")
    lines.append("|--------|--------------------|--------|")
    lines.append("| emp-auth/SSO | API tests (requests) | Token validation, expiry, claims |")
    lines.append("| emp-core | API tests | CRUD operations, data integrity |")
    lines.append("| emp-leave | API + Selenium | Balance calculations need UI verification |")
    lines.append("| emp-attendance | API + Selenium | Check-in/out flows, UI state |")
    lines.append("| emp-payroll | API tests | Calculation accuracy, data processing |")
    lines.append("| emp-engage | Selenium | UI-heavy features (announcements, surveys) |")
    lines.append("| emp-performance | API + Selenium | Goal tracking, appraisal workflows |")
    lines.append("| emp-recruit | API + Selenium | Multi-step hiring workflows |")
    lines.append("| RBAC | API tests | Role-based endpoint access checks |")
    lines.append("| Frontend/Dashboard | Selenium | Navigation, rendering, responsive UI |")
    lines.append("")

    lines.append("### Optimal Test Order")
    lines.append("")
    lines.append("1. **SSO/Auth** - Everything depends on authentication working")
    lines.append("2. **emp-core** - Organization, department, employee CRUD (foundation data)")
    lines.append("3. **RBAC** - Verify role enforcement across all modules")
    lines.append("4. **emp-leave** - High bug count, business-critical")
    lines.append("5. **emp-attendance** - Tightly coupled with leave")
    lines.append("6. **emp-payroll** - Depends on attendance + leave data")
    lines.append("7. **emp-engage** - Independent, lower priority")
    lines.append("8. **emp-performance** - Independent, lower priority")
    lines.append("9. **emp-recruit** - Independent, lower priority")
    lines.append("10. **Other modules** - emp-helpdesk, emp-expense, emp-documents, emp-training")
    lines.append("")

    lines.append("### Common Pitfalls to Avoid")
    lines.append("")
    lines.append("1. **Don't test rate limiting** - Intentionally open for testing")
    lines.append("2. **Always use fresh SSO tokens** - They expire in 15 minutes")
    lines.append("3. **Check both API and UI** - Some bugs only manifest in one layer")
    lines.append("4. **Verify RBAC with all three roles** - super_admin, org_admin, employee")
    lines.append("5. **Don't assume 404 = bug** - Some endpoints may not be implemented yet")
    lines.append("6. **Clean test data** - Create fresh test data for each run to avoid state issues")
    lines.append("7. **Check response structure** - Many bugs are about missing fields, not errors")
    lines.append("")

    # === APPENDIX: ALL ISSUES ===
    lines.append("---")
    lines.append("")
    lines.append("## APPENDIX: Complete Issue Index")
    lines.append("")
    lines.append("| # | Title | State | Module | Bug Types | Comments |")
    lines.append("|---|-------|-------|--------|-----------|----------|")
    for issue in sorted(issues, key=lambda x: x["number"]):
        num = issue["number"]
        title = issue["title"][:50]
        state = issue["state"]
        module = classify_module(issue["title"], issue.get("body",""), issue.get("labels",[]))
        types = ", ".join(classify_bug_type(issue["title"], issue.get("body","")))
        comment_count = sum(1 for c in all_comments if c.get("issue_number") == num)
        lines.append(f"| #{num} | {title} | {state} | {module} | {types} | {comment_count} |")
    lines.append("")

    return "\n".join(lines)


def main():
    print("=" * 60)
    print("EmpCloud Intelligence Builder")
    print("=" * 60)

    # Step 1: Fetch all issues
    print("\n[1/4] Fetching all issues...")
    issues = fetch_all_issues()
    print(f"  Total issues fetched: {len(issues)}")

    # Step 2: Fetch all comments (bulk)
    print(f"\n[2/4] Fetching ALL comments (bulk endpoint)...")
    all_comments = fetch_all_comments_bulk()
    print(f"  Total comments fetched: {len(all_comments)}")

    # Step 3: Analyze
    print("\n[3/4] Analyzing data...")
    intel = build_intelligence(issues, all_comments)

    # Step 4: Generate outputs
    print("\n[4/4] Generating outputs...")

    # Save raw data
    raw_data = {
        "issues": [{
            "number": i["number"],
            "title": i["title"],
            "body": i.get("body", ""),
            "state": i["state"],
            "labels": [l["name"] for l in i.get("labels", [])],
            "created_at": i.get("created_at", ""),
            "closed_at": i.get("closed_at", ""),
            "user": i.get("user", {}).get("login", ""),
        } for i in issues],
        "comments": [{
            "issue_number": c.get("issue_number", 0),
            "user": c.get("user", {}).get("login", ""),
            "body": c.get("body", ""),
            "created_at": c.get("created_at", ""),
        } for c in all_comments],
        "intelligence": intel,
    }

    with open(r"C:\emptesting\intelligence_data.json", "w", encoding="utf-8") as f:
        json.dump(raw_data, f, indent=2, ensure_ascii=False, default=str)
    print("  Saved: C:\\emptesting\\intelligence_data.json")

    # Generate markdown
    md = generate_markdown(intel, issues, all_comments)
    with open(r"C:\emptesting\INTELLIGENCE.md", "w", encoding="utf-8") as f:
        f.write(md)
    print("  Saved: C:\\emptesting\\INTELLIGENCE.md")

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Issues analyzed: {intel['total_issues']} ({intel['open_issues']} open, {intel['closed_issues']} closed)")
    print(f"Comments analyzed: {len(all_comments)}")
    print(f"Developer comments: {intel['dev_comments_count']}")
    print(f"Modules identified: {len(intel['module_stats'])}")
    print(f"Bug types found: {len(intel['bug_type_counter'])}")
    print(f"Endpoints discovered: {len(intel['all_endpoints'])}")
    print(f"False positives identified: {len(intel['false_positives']) + len(intel['not_a_bug_issues']) + len(intel['by_design_issues'])}")
    print(f"\nTop bug types:")
    for bt, count in sorted(intel["bug_type_counter"].items(), key=lambda x: -x[1])[:5]:
        print(f"  {bt}: {count}")
    print(f"\nMost buggy modules:")
    for mod, stats in sorted(intel["module_stats"].items(), key=lambda x: -x[1]["total"])[:5]:
        print(f"  {mod}: {stats['total']} total ({stats['open']} open)")
    print("\nDone!")


if __name__ == "__main__":
    main()
