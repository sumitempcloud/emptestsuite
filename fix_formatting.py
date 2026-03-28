#!/usr/bin/env python
"""
Fix formatting of already-updated issues - remove backticks around image markdown
and clean up "Saved locally:" prefix text.
"""

import urllib.request
import urllib.error
import json
import re
import time

GITHUB_TOKEN = "$GITHUB_TOKEN"
REPO = "EmpCloud/EmpCloud"
API_BASE = f"https://api.github.com/repos/{REPO}"
RAW_BASE = "https://raw.githubusercontent.com/EmpCloud/EmpCloud/main/screenshots"

HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json",
    "User-Agent": "EmpCloud-Screenshot-Uploader"
}

# Pattern to find the broken formatting
# Matches: Saved locally: `![Screenshot](URL)`
# or just `![Screenshot](URL)` with backticks
BROKEN_PATTERN = re.compile(
    r'Saved locally:\s*`(!\[Screenshot\]\(https://raw\.githubusercontent\.com/EmpCloud/EmpCloud/main/screenshots/[^)]+\))`'
)
# Also match just backtick-wrapped image
BACKTICK_IMG_PATTERN = re.compile(
    r'`(!\[Screenshot\]\(https://raw\.githubusercontent\.com/EmpCloud/EmpCloud/main/screenshots/[^)]+\))`'
)


def api_request(url, method="GET", data=None):
    headers = dict(HEADERS)
    if data is not None:
        data = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    resp = urllib.request.urlopen(req, timeout=60)
    return json.loads(resp.read().decode("utf-8"))


def fetch_all_issues(max_issues=200):
    issues = []
    page = 1
    while len(issues) < max_issues:
        url = f"{API_BASE}/issues?state=all&per_page=100&page={page}"
        batch = api_request(url)
        if not batch:
            break
        for issue in batch:
            if "pull_request" not in issue:
                issues.append(issue)
        if len(batch) < 100:
            break
        page += 1
    return issues[:max_issues]


def main():
    print("Fetching all issues to fix formatting...")
    issues = fetch_all_issues()
    print(f"Found {len(issues)} issues\n")

    fixed = 0
    for issue in issues:
        number = issue["number"]
        body = issue.get("body") or ""

        new_body = body
        changed = False

        # Fix "Saved locally: `![Screenshot](URL)`" -> "\n![Screenshot](URL)\n"
        if BROKEN_PATTERN.search(new_body):
            new_body = BROKEN_PATTERN.sub(r'\n\1\n', new_body)
            changed = True

        # Fix remaining "`![Screenshot](URL)`" -> "![Screenshot](URL)"
        if BACKTICK_IMG_PATTERN.search(new_body):
            new_body = BACKTICK_IMG_PATTERN.sub(r'\1', new_body)
            changed = True

        if changed:
            print(f"  Fixing formatting for issue #{number}...", end=" ", flush=True)
            url = f"{API_BASE}/issues/{number}"
            api_request(url, method="PATCH", data={"body": new_body})
            print("done")
            fixed += 1
            time.sleep(0.5)

        # Also check comments
        try:
            comments = api_request(f"{API_BASE}/issues/{number}/comments?per_page=100")
            for c in comments:
                c_body = c.get("body") or ""
                new_c_body = c_body
                c_changed = False
                if BROKEN_PATTERN.search(new_c_body):
                    new_c_body = BROKEN_PATTERN.sub(r'\n\1\n', new_c_body)
                    c_changed = True
                if BACKTICK_IMG_PATTERN.search(new_c_body):
                    new_c_body = BACKTICK_IMG_PATTERN.sub(r'\1', new_c_body)
                    c_changed = True
                if c_changed:
                    print(f"  Fixing comment {c['id']} on issue #{number}...", end=" ", flush=True)
                    api_request(f"{API_BASE}/issues/comments/{c['id']}", method="PATCH", data={"body": new_c_body})
                    print("done")
                    time.sleep(0.5)
        except Exception as e:
            pass

    print(f"\nFixed formatting on {fixed} issues")


if __name__ == "__main__":
    main()
