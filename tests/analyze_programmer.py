"""
Analyze all comments by sumitempcloud on EmpCloud/EmpCloud issues.
Build a programmer behavior profile.
"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import requests
import json
import re
import time
from datetime import datetime, timezone
from collections import Counter, defaultdict

GITHUB_TOKEN = "os.environ.get('GITHUB_TOKEN', 'YOUR_TOKEN_HERE')"
REPO = "EmpCloud/EmpCloud"
HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json"
}
BASE = f"https://api.github.com/repos/{REPO}"
PROGRAMMER = "sumitempcloud"

def api_get(url, retries=3):
    """GET with rate limit handling."""
    for attempt in range(retries):
        r = requests.get(url, headers=HEADERS)
        if r.status_code == 200:
            return r.json()
        if r.status_code == 403 and 'rate limit' in r.text.lower():
            reset = int(r.headers.get('X-RateLimit-Reset', 0))
            wait = max(reset - int(time.time()), 5)
            print(f"  Rate limited, waiting {wait}s...")
            time.sleep(min(wait, 60))
            continue
        if r.status_code == 404:
            return []
        print(f"  HTTP {r.status_code} on {url}")
        time.sleep(2)
    return []

# ── Step 1: Fetch all issues (open + closed) ──
print("Fetching all issues...")
all_issues = []
for state in ["open", "closed"]:
    for page in range(1, 20):
        url = f"{BASE}/issues?state={state}&per_page=100&page={page}"
        data = api_get(url)
        if not data:
            break
        all_issues.extend(data)
        print(f"  state={state} page={page}: {len(data)} issues")
        if len(data) < 100:
            break

print(f"Total issues fetched: {len(all_issues)}")
issue_map = {i["number"]: i for i in all_issues}

# ── Step 2: Use repo-level comments endpoint (much faster) ──
print("\nFetching ALL repo-level issue comments...")
all_repo_comments = []
for page in range(1, 100):
    url = f"{BASE}/issues/comments?per_page=100&page={page}&sort=created&direction=asc"
    data = api_get(url)
    if not data:
        break
    all_repo_comments.extend(data)
    print(f"  Page {page}: {len(data)} comments (total: {len(all_repo_comments)})")
    if len(data) < 100:
        break

print(f"Total repo comments: {len(all_repo_comments)}")

# ── Step 3: Filter for programmer comments ──
programmer_comments = []
for c in all_repo_comments:
    user = c.get("user", {}).get("login", "")
    if user.lower() == PROGRAMMER.lower():
        # Extract issue number from URL
        issue_url = c.get("issue_url", "")
        num_match = re.search(r'/issues/(\d+)$', issue_url)
        if num_match:
            num = int(num_match.group(1))
            iss = issue_map.get(num, {})
            programmer_comments.append({
                "issue_number": num,
                "issue_title": iss.get("title", f"Issue #{num}"),
                "issue_state": iss.get("state", "unknown"),
                "issue_labels": [l["name"] for l in iss.get("labels", [])],
                "issue_created_at": iss.get("created_at", ""),
                "issue_closed_at": iss.get("closed_at", ""),
                "comment_id": c["id"],
                "comment_body": c["body"] or "",
                "comment_created_at": c["created_at"],
                "comment_url": c.get("html_url", ""),
            })

print(f"\nTotal programmer comments found: {len(programmer_comments)}")

# Save raw data
with open("C:/emptesting/programmer_comments.json", "w", encoding="utf-8") as f:
    json.dump(programmer_comments, f, indent=2, ensure_ascii=False)
print("Saved raw data to programmer_comments.json")

# ── Step 4: Analyze ──
print("\n=== ANALYSIS ===\n")

# A. FIX PATTERNS
fix_words = Counter()
keyword_list = [
    "fixed", "fix", "added", "deployed", "resolved", "updated", "not a bug",
    "by design", "working as expected", "implemented", "removed", "changed",
    "corrected", "patched", "merged", "pushed", "closed", "duplicate",
    "won't fix", "wontfix", "invalid", "works for me", "cannot reproduce",
    "done", "completed", "handled", "addressed", "refactored", "optimized",
    "route", "guard", "rbac", "validation", "middleware", "sso", "token",
    "api", "endpoint", "database", "query", "migration", "schema"
]

commit_refs = []
file_refs = []

for pc in programmer_comments:
    body = pc["comment_body"].lower()
    for kw in keyword_list:
        if kw in body:
            fix_words[kw] += 1
    # Commit references
    sha_matches = re.findall(r'\b[0-9a-f]{7,40}\b', body)
    for sha in sha_matches:
        if len(sha) >= 7 and not sha.isdigit():
            commit_refs.append({"sha": sha, "issue": pc["issue_number"]})
    # File references
    file_matches = re.findall(r'[\w/\\]+\.\w{1,5}', body)
    file_refs.extend(file_matches)

# B. "NOT A BUG" explanations
not_a_bug_comments = []
not_bug_keywords = ["not a bug", "by design", "expected behavior", "working as expected",
                    "false positive", "intended", "not an issue", "working fine",
                    "as expected", "correct behavior", "won't fix", "this is how",
                    "not broken", "behaves correctly", "working correctly",
                    "already", "doesn't apply", "not applicable"]

for pc in programmer_comments:
    body_lower = pc["comment_body"].lower()
    for kw in not_bug_keywords:
        if kw in body_lower:
            not_a_bug_comments.append(pc)
            break

# C. Architecture insights
arch_keywords = ["database", "mongo", "postgres", "mysql", "redis", "queue", "kafka",
                 "microservice", "gateway", "proxy", "nginx", "docker", "k8s",
                 "jwt", "token", "session", "cookie", "oauth", "sso",
                 "middleware", "interceptor", "guard", "rbac", "role",
                 "tenant", "multi-tenant", "organization", "org",
                 "api", "rest", "graphql", "websocket", "socket",
                 "route", "controller", "service", "repository", "model",
                 "schema", "migration", "seed", "soft delete", "soft-delete",
                 "cron", "scheduler", "worker", "bull", "nest", "nestjs", "express",
                 "react", "next", "angular", "vue"]

arch_comments = []
for pc in programmer_comments:
    body_lower = pc["comment_body"].lower()
    found = [kw for kw in arch_keywords if kw in body_lower]
    if found:
        arch_comments.append({"comment": pc, "keywords": found})

# D. Common fixes categorization
fix_categories = defaultdict(list)
category_patterns = {
    "Added route": ["added route", "new route", "route added", "missing route", "added endpoint"],
    "Added validation": ["added validation", "validation added", "input validation", "added check"],
    "Added RBAC/guard": ["rbac", "guard", "role check", "permission check", "access control", "authorization"],
    "Fixed SSO": ["sso", "single sign", "token", "auth token", "session"],
    "Fixed API": ["api", "endpoint", "request", "response", "status code", "500", "404", "401", "403"],
    "Database fix": ["database", "query", "migration", "schema", "model", "collection"],
    "UI fix": ["ui", "frontend", "react", "component", "render", "display", "css", "style"],
    "Deployment": ["deployed", "deployment", "production", "staging", "server"],
}

for pc in programmer_comments:
    body_lower = pc["comment_body"].lower()
    for cat, patterns in category_patterns.items():
        for pat in patterns:
            if pat in body_lower:
                fix_categories[cat].append(pc)
                break

# E. Response time analysis
response_times = []
module_times = defaultdict(list)

for pc in programmer_comments:
    if pc["issue_created_at"] and pc["comment_created_at"]:
        try:
            created = datetime.fromisoformat(pc["issue_created_at"].replace("Z", "+00:00"))
            commented = datetime.fromisoformat(pc["comment_created_at"].replace("Z", "+00:00"))
            delta = commented - created
            hours = delta.total_seconds() / 3600
            if hours >= 0:
                response_times.append({
                    "issue": pc["issue_number"],
                    "title": pc["issue_title"],
                    "hours": round(hours, 1),
                    "labels": pc["issue_labels"]
                })
                title_lower = pc["issue_title"].lower()
                for mod in ["payroll", "recruit", "performance", "lms", "exit", "rewards",
                            "monitor", "project", "attendance", "leave", "sso", "auth",
                            "dashboard", "admin", "employee", "api", "security", "rbac"]:
                    if mod in title_lower or mod in " ".join(pc["issue_labels"]).lower():
                        module_times[mod].append(hours)
        except Exception:
            pass

closure_times = []
for issue in all_issues:
    if issue.get("state") == "closed" and issue.get("created_at") and issue.get("closed_at"):
        try:
            created = datetime.fromisoformat(issue["created_at"].replace("Z", "+00:00"))
            closed = datetime.fromisoformat(issue["closed_at"].replace("Z", "+00:00"))
            delta = closed - created
            hours = delta.total_seconds() / 3600
            if hours >= 0:
                closure_times.append(hours)
        except Exception:
            pass

# Batch analysis
comment_dates = Counter()
for pc in programmer_comments:
    try:
        dt = datetime.fromisoformat(pc["comment_created_at"].replace("Z", "+00:00"))
        comment_dates[dt.strftime("%Y-%m-%d")] += 1
    except Exception:
        pass

# ── Build the report ──
print("Building report...")

report = []
report.append("# Programmer Behavior Profile: sumitempcloud")
report.append(f"\n**Analysis Date:** 2026-03-28")
report.append(f"**Total Issues Analyzed:** {len(all_issues)}")
report.append(f"**Total Programmer Comments Found:** {len(programmer_comments)}")
report.append("")

# === A. FIX PATTERNS ===
report.append("---")
report.append("## A. Fix Patterns")
report.append("")
report.append("### Vocabulary / Keywords Used")
report.append("| Keyword | Count |")
report.append("|---------|-------|")
for kw, count in fix_words.most_common():
    if count > 0:
        report.append(f"| {kw} | {count} |")

report.append("")
report.append("### Commit References")
if commit_refs:
    report.append(f"Found {len(commit_refs)} commit SHA references:")
    for cr in commit_refs[:20]:
        report.append(f"- Issue #{cr['issue']}: `{cr['sha']}`")
else:
    report.append("No explicit commit SHA references found in comments.")

report.append("")
report.append("### File/Function References")
if file_refs:
    file_counter = Counter(file_refs)
    report.append(f"Found {len(file_refs)} file references:")
    for f_name, count in file_counter.most_common(30):
        report.append(f"- `{f_name}` ({count}x)")
else:
    report.append("No explicit file references found in comments.")

# === B. NOT A BUG ===
report.append("")
report.append("---")
report.append("## B. 'Not a Bug' Explanations")
report.append("")
report.append(f"**Total 'not a bug' style comments:** {len(not_a_bug_comments)}")
report.append("")

if not_a_bug_comments:
    nab_categories = defaultdict(list)
    for pc in not_a_bug_comments:
        body_lower = pc["comment_body"].lower()
        categorized = False
        if "by design" in body_lower or "intended" in body_lower or "expected behavior" in body_lower:
            nab_categories["By Design"].append(pc)
            categorized = True
        if "false positive" in body_lower:
            nab_categories["False Positive"].append(pc)
            categorized = True
        if "soft delete" in body_lower or "soft-delete" in body_lower:
            nab_categories["Soft Delete"].append(pc)
            categorized = True
        if "xss" in body_lower or "react" in body_lower or "sanitiz" in body_lower:
            nab_categories["XSS/React Sanitization"].append(pc)
            categorized = True
        if "sso" in body_lower:
            nab_categories["SSO Related"].append(pc)
            categorized = True
        if "api" in body_lower or "route" in body_lower or "path" in body_lower:
            nab_categories["Wrong API Path"].append(pc)
            categorized = True
        if "already" in body_lower:
            nab_categories["Already Handled/Exists"].append(pc)
            categorized = True
        if not categorized:
            nab_categories["Other"].append(pc)

    for cat, items in sorted(nab_categories.items(), key=lambda x: -len(x[1])):
        report.append(f"### {cat} ({len(items)} comments)")
        for pc in items:
            body_preview = pc["comment_body"][:300].replace("\n", " ").replace("|", "\\|")
            report.append(f"- **Issue #{pc['issue_number']}** ({pc['issue_title']}): {body_preview}")
        report.append("")

    report.append("### DO NOT TEST List (Based on Programmer Explanations)")
    report.append("")
    report.append("These are things the programmer explicitly said are NOT bugs:")
    report.append("")
    for pc in not_a_bug_comments:
        report.append(f"- **Issue #{pc['issue_number']}**: {pc['issue_title']}")
        body_clean = pc["comment_body"][:400].replace("\n", " ")
        report.append(f"  - Reason: {body_clean}")
    report.append("")

# === FULL COMMENT TEXT ===
report.append("---")
report.append("## B2. Every Programmer Comment (Full Text)")
report.append("")
for pc in programmer_comments:
    report.append(f"### Issue #{pc['issue_number']}: {pc['issue_title']}")
    report.append(f"- **State:** {pc['issue_state']}")
    report.append(f"- **Labels:** {', '.join(pc['issue_labels']) if pc['issue_labels'] else 'none'}")
    report.append(f"- **Comment Date:** {pc['comment_created_at']}")
    report.append(f"- **Link:** {pc['comment_url']}")
    report.append("")
    report.append("```")
    report.append(pc["comment_body"])
    report.append("```")
    report.append("")

# === C. ARCHITECTURE INSIGHTS ===
report.append("---")
report.append("## C. Architecture Insights from Comments")
report.append("")
report.append(f"**Comments with architecture keywords:** {len(arch_comments)}")
report.append("")

if arch_comments:
    kw_groups = defaultdict(list)
    for ac in arch_comments:
        for kw in ac["keywords"]:
            kw_groups[kw].append(ac["comment"])

    for kw in sorted(kw_groups.keys(), key=lambda k: -len(kw_groups[k])):
        items = kw_groups[kw]
        report.append(f"### Keyword: `{kw}` ({len(items)} mentions)")
        for pc in items[:10]:
            body_preview = pc["comment_body"][:300].replace("\n", " ")
            report.append(f"- Issue #{pc['issue_number']}: {body_preview}")
        report.append("")

# === D. COMMON FIXES ===
report.append("---")
report.append("## D. Common Fixes")
report.append("")
for cat in sorted(fix_categories.keys(), key=lambda x: -len(fix_categories[x])):
    items = fix_categories[cat]
    report.append(f"### {cat} ({len(items)} comments)")
    for pc in items:
        body_preview = pc["comment_body"][:250].replace("\n", " ")
        report.append(f"- **Issue #{pc['issue_number']}** ({pc['issue_title']}): {body_preview}")
    report.append("")

# === E. RESPONSE TIME ===
report.append("---")
report.append("## E. Response Time Analysis")
report.append("")

if response_times:
    hours_list = [rt["hours"] for rt in response_times]
    avg_hours = sum(hours_list) / len(hours_list)
    sorted_hours = sorted(hours_list)
    report.append(f"**Average time from issue creation to first programmer comment:** {avg_hours:.1f} hours ({avg_hours/24:.1f} days)")
    report.append(f"**Fastest response:** {min(hours_list):.1f} hours")
    report.append(f"**Slowest response:** {max(hours_list):.1f} hours")
    report.append(f"**Median response:** {sorted_hours[len(sorted_hours)//2]:.1f} hours")
    report.append("")

    report.append("### Fastest Responses")
    for rt in sorted(response_times, key=lambda x: x["hours"])[:10]:
        report.append(f"- Issue #{rt['issue']}: {rt['hours']}h - {rt['title']}")

    report.append("")
    report.append("### Slowest Responses")
    for rt in sorted(response_times, key=lambda x: -x["hours"])[:10]:
        report.append(f"- Issue #{rt['issue']}: {rt['hours']}h ({rt['hours']/24:.1f}d) - {rt['title']}")

if closure_times:
    avg_close = sum(closure_times) / len(closure_times)
    report.append("")
    report.append(f"**Average issue closure time (all closed issues):** {avg_close:.1f} hours ({avg_close/24:.1f} days)")
    report.append(f"**Fastest closure:** {min(closure_times):.1f} hours")
    report.append(f"**Slowest closure:** {max(closure_times):.1f} hours")

report.append("")
report.append("### Module Response Times")
if module_times:
    report.append("| Module | Avg Response (hours) | Count |")
    report.append("|--------|---------------------|-------|")
    for mod in sorted(module_times.keys(), key=lambda m: sum(module_times[m])/len(module_times[m])):
        times = module_times[mod]
        avg = sum(times) / len(times)
        report.append(f"| {mod} | {avg:.1f} | {len(times)} |")

report.append("")
report.append("### Batch Fix Analysis (comments per day)")
if comment_dates:
    report.append("| Date | Comments |")
    report.append("|------|----------|")
    for date, count in sorted(comment_dates.items()):
        report.append(f"| {date} | {count} |")
    report.append("")
    max_day = max(comment_dates.values()) if comment_dates else 0
    avg_day = sum(comment_dates.values()) / len(comment_dates) if comment_dates else 0
    report.append(f"**Max comments in one day:** {max_day}")
    report.append(f"**Average comments per active day:** {avg_day:.1f}")
    if max_day > 5:
        report.append("**Pattern: Programmer tends to batch-fix issues (multiple fixes per day)**")

# === F. PROGRAMMER PROFILE ===
report.append("")
report.append("---")
report.append("## F. Programmer Profile Summary")
report.append("")

# Communication style
report.append("### Communication Style")
top_words = fix_words.most_common(5)
if top_words:
    report.append(f"- Most used keywords: {', '.join(f'{w} ({c}x)' for w, c in top_words)}")
report.append(f"- Total comments analyzed: {len(programmer_comments)}")
avg_len = sum(len(pc["comment_body"]) for pc in programmer_comments) / max(len(programmer_comments), 1)
report.append(f"- Average comment length: {avg_len:.0f} characters")
if avg_len < 100:
    report.append("- Style: **Terse/concise** - short, action-oriented comments")
elif avg_len < 300:
    report.append("- Style: **Moderate** - provides some explanation")
else:
    report.append("- Style: **Detailed** - provides thorough explanations")

# Word frequency across all comments
all_words = Counter()
for pc in programmer_comments:
    words = re.findall(r'[a-zA-Z]{3,}', pc["comment_body"].lower())
    all_words.update(words)

report.append("")
report.append("### Most Frequent Words in Comments")
report.append("| Word | Count |")
report.append("|------|-------|")
stopwords = {"the", "and", "for", "this", "that", "with", "has", "was", "are", "not", "but",
             "have", "been", "from", "will", "can", "all", "its", "they", "you", "our",
             "which", "when", "there", "their", "what", "about", "would", "could", "should",
             "also", "more", "than", "other", "into", "some", "any", "each", "only", "does"}
for word, count in all_words.most_common(50):
    if word not in stopwords and count >= 2:
        report.append(f"| {word} | {count} |")

report.append("")
report.append("### Priorities (Inferred)")
if fix_categories:
    sorted_cats = sorted(fix_categories.items(), key=lambda x: -len(x[1]))
    for cat, items in sorted_cats:
        report.append(f"- **{cat}:** {len(items)} fixes")

report.append("")
report.append("### Testing Recommendations")
report.append("")
report.append("Based on programmer behavior, future testing should:")
report.append("")

if not_a_bug_comments:
    report.append("#### AVOID testing these patterns (programmer confirmed not bugs):")
    seen_titles = set()
    for pc in not_a_bug_comments:
        if pc["issue_title"] not in seen_titles:
            report.append(f"- {pc['issue_title']}")
            seen_titles.add(pc["issue_title"])

report.append("")
report.append("#### FOCUS testing on areas the programmer actively fixes:")
for cat, items in sorted(fix_categories.items(), key=lambda x: -len(x[1])):
    if len(items) >= 2:
        report.append(f"- **{cat}**: {len(items)} fixes found, likely area of active development")

report.append("")
report.append("---")
report.append("*Generated by automated analysis of GitHub issue comments*")

# Write report
report_text = "\n".join(report)
with open("C:/emptesting/PROGRAMMER_PROFILE.md", "w", encoding="utf-8") as f:
    f.write(report_text)

print(f"\nReport saved to C:/emptesting/PROGRAMMER_PROFILE.md")
print(f"Raw data saved to C:/emptesting/programmer_comments.json")
print(f"\nDone! {len(programmer_comments)} comments analyzed across {len(all_issues)} issues.")
