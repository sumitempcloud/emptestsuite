#!/usr/bin/env python3
"""
Add 'Verified by E2E Test Lead. Bug confirmed.' comment to all issues
that have verified-bug label but no such comment yet.
Run this after the rate limit resets (usually ~10 minutes).
"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import requests
import time

GH_TOKEN = "$GITHUB_TOKEN"
GH_REPO = "EmpCloud/EmpCloud"
GH_API = "https://api.github.com"
GH_HEADERS = {
    "Authorization": f"token {GH_TOKEN}",
    "Accept": "application/vnd.github+json"
}

COMMENT_TEXT = "Verified by E2E Test Lead. Bug confirmed."
DELAY = 10  # generous delay to avoid secondary rate limit

issues = [944, 925, 921, 903, 902, 901, 900, 898, 896, 895, 894, 893, 892,
          891, 890, 889, 888, 887, 886, 885, 881, 880, 879, 877, 876, 874,
          873, 872, 871, 870, 869, 867, 866, 865, 864, 863, 862, 817, 814, 732]

def has_comment(num):
    """Check if issue already has the verification comment."""
    r = requests.get(f"{GH_API}/repos/{GH_REPO}/issues/{num}/comments",
                     headers=GH_HEADERS, timeout=30)
    if r.status_code == 200:
        for c in r.json():
            if COMMENT_TEXT in (c.get("body") or ""):
                return True
    return False

def main():
    success = 0
    skipped = 0
    failed = 0

    for i, num in enumerate(issues):
        print(f"[{i+1}/{len(issues)}] Issue #{num}...", end=" ")

        # Check if already commented
        if has_comment(num):
            print("already has comment, skipping")
            skipped += 1
            time.sleep(3)
            continue

        time.sleep(DELAY)

        r = requests.post(f"{GH_API}/repos/{GH_REPO}/issues/{num}/comments",
                          headers=GH_HEADERS, json={"body": COMMENT_TEXT}, timeout=30)
        if r.status_code == 201:
            print("comment added")
            success += 1
        elif r.status_code == 403 and "secondary rate" in r.text.lower():
            print(f"RATE LIMITED - waiting 120s then retrying")
            time.sleep(120)
            r2 = requests.post(f"{GH_API}/repos/{GH_REPO}/issues/{num}/comments",
                               headers=GH_HEADERS, json={"body": COMMENT_TEXT}, timeout=30)
            if r2.status_code == 201:
                print(f"  retry succeeded")
                success += 1
            else:
                print(f"  retry failed: {r2.status_code}")
                failed += 1
        else:
            print(f"FAILED: {r.status_code}")
            failed += 1

    print(f"\nDone: {success} added, {skipped} skipped, {failed} failed")

if __name__ == "__main__":
    main()
