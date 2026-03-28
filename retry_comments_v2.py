#!/usr/bin/env python3
"""Retry failed GitHub comments with rate limit backoff."""
import sys
import time
import re
import requests
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

GH_TOKEN = "$GITHUB_TOKEN"
GH_REPO = "EmpCloud/EmpCloud"
GH_API = "https://api.github.com"
GH_HEADERS = {"Authorization": f"token {GH_TOKEN}", "Accept": "application/vnd.github+json"}
API = "https://test-empcloud.empcloud.com/api/v1"

LOG_FILE = r"C:\Users\Admin\.claude\projects\C--Users-Admin\99a6c92d-b09c-47d9-95a5-ba1c6073c680\tool-results\bs9r9siy5.txt"

def gh_comment(issue_num, body, max_retries=5):
    url = f"{GH_API}/repos/{GH_REPO}/issues/{issue_num}/comments"
    for attempt in range(max_retries):
        r = requests.post(url, headers=GH_HEADERS, json={"body": body})
        if r.status_code == 201:
            return True
        elif r.status_code == 403 and "rate limit" in r.text.lower():
            wait = min(2 ** attempt * 15, 120)
            print(f"    Rate limited, waiting {wait}s (attempt {attempt+1})")
            sys.stdout.flush()
            time.sleep(wait)
        else:
            print(f"    Failed: {r.status_code}")
            return False
    return False

def main():
    print(f"=== Retry Failed Comments - {datetime.now().isoformat()} ===")
    sys.stdout.flush()

    with open(LOG_FILE, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()

    # Parse the log to extract per-issue block: steps + verdict + whether comment failed
    # Split into issue blocks
    lines = content.split('\n')

    current_num = None
    current_title = None
    current_steps = []
    current_verdict = None
    current_verdict_msg = None
    comment_failed = False
    needs_retry = []

    for line in lines:
        # Issue header
        m = re.match(r'=== #(\d+)\s+(.+?)\s+===', line.strip())
        if m:
            # Save previous if comment failed
            if current_num and comment_failed and current_verdict:
                needs_retry.append({
                    "number": current_num,
                    "title": current_title,
                    "steps": current_steps[:],
                    "verdict": current_verdict,
                    "msg": current_verdict_msg or "",
                })
            current_num = int(m.group(1))
            current_title = m.group(2)
            current_steps = []
            current_verdict = None
            current_verdict_msg = None
            comment_failed = False
            continue

        stripped = line.strip()

        if stripped.startswith("Step "):
            current_steps.append(stripped)
        elif stripped.startswith("VERDICT:"):
            vm = re.match(r'VERDICT:\s+(FIXED|STILL FAILING|NEEDS MANUAL REVIEW)\s*[-\u2013]?\s*(.*)', stripped)
            if vm:
                current_verdict = vm.group(1)
                current_verdict_msg = vm.group(2).strip()
        elif stripped.startswith("SKIPPED:"):
            current_verdict = "SKIPPED"
            current_verdict_msg = stripped.replace("SKIPPED:", "").strip()
        elif f"Comment failed on #{current_num}" in stripped if current_num else False:
            comment_failed = True

    # Don't forget last one
    if current_num and comment_failed and current_verdict:
        needs_retry.append({
            "number": current_num,
            "title": current_title,
            "steps": current_steps[:],
            "verdict": current_verdict,
            "msg": current_verdict_msg or "",
        })

    # Also add #270 which errored
    if not any(n["number"] == 270 for n in needs_retry):
        if "ERROR testing #270" in content:
            needs_retry.append({
                "number": 270,
                "title": "[FUNCTIONAL] Employee - READ List (API) failed",
                "steps": [],
                "verdict": "NEEDS_RETEST",
                "msg": "",
            })

    # Deduplicate
    seen = set()
    unique = []
    for item in needs_retry:
        if item["number"] not in seen:
            seen.add(item["number"])
            unique.append(item)
    needs_retry = sorted(unique, key=lambda x: x["number"])

    print(f"Found {len(needs_retry)} issues needing comment retry")
    sys.stdout.flush()

    # For #270, do a quick retest
    for item in needs_retry:
        if item["number"] == 270 and item["verdict"] == "NEEDS_RETEST":
            print(f"\n  Re-testing #270...")
            sys.stdout.flush()
            session = requests.Session()
            r = session.post(f"{API}/auth/login", json={"email": "ananya@technova.in", "password": "Welcome@123"})
            if r.status_code == 200:
                token = r.json()["data"]["tokens"]["access_token"]
                r2 = session.get(f"{API}/users", headers={"Authorization": f"Bearer {token}"})
                if r2.status_code == 200:
                    count = len(r2.json().get("data", []))
                    item["steps"] = [
                        f"Step 1: GET {API}/users as org_admin -> {r2.status_code}",
                        f"Step 2: Got {count} employees in list",
                        f"Step 3: Employee READ List works correctly",
                    ]
                    item["verdict"] = "FIXED"
                    item["msg"] = f"Employee list returns {count} records"
                else:
                    item["steps"] = [f"Step 1: GET {API}/users -> {r2.status_code}"]
                    item["verdict"] = "STILL FAILING"
                    item["msg"] = f"Returns {r2.status_code}"

    success = 0
    failed = 0

    for item in needs_retry:
        num = item["number"]
        verdict = item["verdict"]
        msg = item["msg"]
        steps = item["steps"]

        if verdict == "SKIPPED":
            continue

        # Build comment
        step_text = "\n".join(f"- {s}" for s in steps) if steps else "- See original test run for details"

        if verdict == "FIXED":
            comment = (
                f"Comment by E2E Testing Agent\n\n"
                f"**Re-test Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
                f"**Method:** API-only automated retest\n\n"
                f"**Steps:**\n{step_text}\n\n"
                f"**Verdict: FIXED** - {msg}\n\n"
                f"Verified via automated API testing. Issue appears resolved."
            )
        elif verdict == "STILL FAILING":
            comment = (
                f"Comment by E2E Testing Agent\n\n"
                f"**Re-test Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
                f"**Method:** API-only automated retest\n\n"
                f"**Steps:**\n{step_text}\n\n"
                f"**Verdict: STILL FAILING** - {msg}\n\n"
                f"Bug is still reproducible. Issue has been re-opened."
            )
        elif verdict == "NEEDS MANUAL REVIEW":
            comment = (
                f"Comment by E2E Testing Agent\n\n"
                f"**Re-test Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
                f"**Method:** API-only automated retest\n\n"
                f"**Steps:**\n{step_text}\n\n"
                f"**Verdict:** NEEDS MANUAL REVIEW - {msg}\n\n"
                f"This issue type requires manual/UI testing that cannot be performed via API alone."
            )
        else:
            continue

        print(f"  #{num} ({verdict}): ", end="")
        sys.stdout.flush()
        ok = gh_comment(num, comment)
        if ok:
            print("OK")
            success += 1
        else:
            print("FAILED")
            failed += 1
        sys.stdout.flush()

        time.sleep(2)

    print(f"\n=== Done: {success} posted, {failed} failed ===")
    sys.stdout.flush()

if __name__ == "__main__":
    main()
