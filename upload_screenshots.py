#!/usr/bin/env python
"""
Upload local screenshots referenced in GitHub issues to the repo,
and update issue bodies/comments with the GitHub raw URLs.
"""

import urllib.request
import urllib.error
import json
import base64
import re
import os
import time

GITHUB_TOKEN = "$GITHUB_TOKEN"
REPO = "EmpCloud/EmpCloud"
API_BASE = f"https://api.github.com/repos/{REPO}"
RAW_BASE = f"https://raw.githubusercontent.com/{REPO}/main/screenshots"
MAX_FILE_SIZE = 1 * 1024 * 1024  # 1MB limit

HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json",
    "User-Agent": "EmpCloud-Screenshot-Uploader"
}

# Regex to find local Windows paths to screenshots
# Matches patterns like C:\Users\Admin\screenshots\...\file.png
# or C:\\Users\\Admin\\screenshots\\...\file.png
# Also handles forward slashes
LOCAL_PATH_PATTERN = re.compile(
    r'(C:[\\\/]+Users[\\\/]+Admin[\\\/]+screenshots[\\\/]+[^\s\)\]\"\'<>]+\.(?:png|jpg|jpeg|gif))',
    re.IGNORECASE
)

def api_request(url, method="GET", data=None, extra_headers=None):
    """Make an API request and return parsed JSON."""
    headers = dict(HEADERS)
    if extra_headers:
        headers.update(extra_headers)
    if data is not None:
        data = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=data, headers=headers, method=method)

    retries = 3
    for attempt in range(retries):
        try:
            resp = urllib.request.urlopen(req, timeout=60)
            return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            if e.code == 422 and "sha" in body.lower() and attempt < retries - 1:
                # File exists, need SHA - will be handled by caller
                raise
            if e.code == 409 and attempt < retries - 1:
                time.sleep(2)
                continue
            print(f"  HTTP {e.code}: {body[:200]}")
            raise
        except urllib.error.URLError as e:
            if attempt < retries - 1:
                time.sleep(2)
                continue
            raise


def fetch_all_issues(state="all", max_issues=200):
    """Fetch all issues (not PRs) from the repo."""
    issues = []
    page = 1
    per_page = 100
    while len(issues) < max_issues:
        url = f"{API_BASE}/issues?state={state}&per_page={per_page}&page={page}"
        batch = api_request(url)
        if not batch:
            break
        # Filter out pull requests
        for issue in batch:
            if "pull_request" not in issue:
                issues.append(issue)
        if len(batch) < per_page:
            break
        page += 1
    return issues[:max_issues]


def fetch_comments(issue_number):
    """Fetch all comments for an issue."""
    url = f"{API_BASE}/issues/{issue_number}/comments?per_page=100"
    return api_request(url)


def normalize_path(path_str):
    """Normalize a path from the issue body to a local file path."""
    # Replace forward slashes and double backslashes with single backslash
    normalized = path_str.replace("/", os.sep).replace("\\\\", os.sep).replace("\\", os.sep)
    # On Windows in git bash, convert to proper path
    if os.sep == "/":
        # Running in git bash - convert C:\... to /c/...
        normalized = normalized.replace("\\", "/")
        if normalized.startswith("C:"):
            normalized = "/c" + normalized[2:]
    return normalized


def find_local_file(path_str):
    """Try to find the local file from the path in the issue."""
    normalized = normalize_path(path_str)
    if os.path.isfile(normalized):
        return normalized

    # Try alternate normalizations
    alts = [
        path_str.replace("\\\\", "/").replace("\\", "/"),
        path_str.replace("\\\\", os.sep).replace("\\", os.sep),
    ]
    # Also try with C: -> /c
    for alt in list(alts):
        if alt.startswith("C:"):
            alts.append("/c" + alt[2:])

    for alt in alts:
        if os.path.isfile(alt):
            return alt

    return None


def get_existing_file_sha(repo_path):
    """Check if a file already exists in the repo and get its SHA."""
    url = f"{API_BASE}/contents/{repo_path}"
    try:
        result = api_request(url)
        return result.get("sha")
    except (urllib.error.HTTPError, urllib.error.URLError):
        return None


def upload_file_to_repo(local_path, repo_path, commit_message):
    """Upload a file to the GitHub repo via contents API."""
    with open(local_path, "rb") as f:
        content = f.read()

    file_size = len(content)
    if file_size > MAX_FILE_SIZE:
        print(f"  Skipping {local_path} - too large ({file_size // 1024}KB > 1024KB)")
        return None

    encoded = base64.b64encode(content).decode("utf-8")

    # Check if file already exists
    sha = get_existing_file_sha(repo_path)

    payload = {
        "message": commit_message,
        "content": encoded,
    }
    if sha:
        payload["sha"] = sha

    url = f"{API_BASE}/contents/{repo_path}"
    try:
        result = api_request(url, method="PUT", data=payload)
        download_url = result.get("content", {}).get("download_url", "")
        if not download_url:
            download_url = f"{RAW_BASE}/{repo_path.split('screenshots/')[-1]}"
        return download_url
    except urllib.error.HTTPError as e:
        print(f"  Failed to upload {repo_path}: {e}")
        return None


def process_text(text, issue_number, start_index=0):
    """
    Find local paths in text, upload files, replace with GitHub URLs.
    Returns (new_text, num_uploaded, next_index).
    """
    if not text:
        return text, 0, start_index

    matches = LOCAL_PATH_PATTERN.findall(text)
    if not matches:
        return text, 0, start_index

    new_text = text
    num_uploaded = 0
    idx = start_index

    for match in matches:
        local_file = find_local_file(match)
        if not local_file:
            print(f"  WARNING: Could not find local file for path: {match}")
            continue

        idx += 1
        repo_filename = f"issue_{issue_number}_{idx}.png"
        repo_path = f"screenshots/{repo_filename}"
        commit_msg = f"Upload screenshot for issue #{issue_number}"

        print(f"  Uploading screenshot for issue #{issue_number}... ", end="", flush=True)
        download_url = upload_file_to_repo(local_file, repo_path, commit_msg)

        if download_url:
            github_url = f"{RAW_BASE}/{repo_filename}"
            # Replace the local path with markdown image
            # Handle various formats the path might appear in:
            # 1. Already in markdown image: ![...](C:\path)
            # 2. Just the raw path
            # 3. In a "Screenshot:" line

            # First check if it's already in a markdown image syntax
            md_img_pattern = re.compile(
                r'!\[[^\]]*\]\(' + re.escape(match) + r'\)',
                re.IGNORECASE
            )
            if md_img_pattern.search(new_text):
                new_text = md_img_pattern.sub(
                    f'![Screenshot]({github_url})',
                    new_text
                )
            else:
                # Replace bare path with markdown image
                new_text = new_text.replace(match, f'![Screenshot]({github_url})')

            print(f"done ({github_url})")
            num_uploaded += 1
            # Small delay to avoid rate limiting
            time.sleep(1)
        else:
            print("FAILED")

    return new_text, num_uploaded, idx


def update_issue_body(issue_number, new_body):
    """Update an issue's body via PATCH."""
    url = f"{API_BASE}/issues/{issue_number}"
    payload = {"body": new_body}
    api_request(url, method="PATCH", data=payload)


def update_comment(comment_id, new_body):
    """Update a comment's body via PATCH."""
    url = f"{API_BASE}/issues/comments/{comment_id}"
    payload = {"body": new_body}
    api_request(url, method="PATCH", data=payload)


def main():
    print("Fetching all issues from EmpCloud/EmpCloud...")
    issues = fetch_all_issues(state="all", max_issues=200)
    print(f"Found {len(issues)} issues (excluding PRs)\n")

    total_issues_updated = 0
    total_screenshots_uploaded = 0

    for issue in issues:
        number = issue["number"]
        title = issue["title"][:60]
        body = issue.get("body") or ""
        state = issue["state"]

        # Check if body has local paths
        body_matches = LOCAL_PATH_PATTERN.findall(body)

        # Check comments
        comments = []
        comment_matches_found = False
        if body_matches:
            pass  # We'll process body below
        # Always check comments too
        try:
            comments = fetch_comments(number)
            for c in comments:
                c_body = c.get("body") or ""
                if LOCAL_PATH_PATTERN.search(c_body):
                    comment_matches_found = True
                    break
        except Exception as e:
            print(f"  Error fetching comments for #{number}: {e}")

        if not body_matches and not comment_matches_found:
            continue

        print(f"\n--- Issue #{number} ({state}): {title} ---")
        screenshot_idx = 0
        issue_updated = False

        # Process issue body
        if body_matches:
            print(f"  Found {len(body_matches)} local path(s) in issue body")
            new_body, uploaded, screenshot_idx = process_text(body, number, screenshot_idx)
            if uploaded > 0:
                print(f"  Updating issue #{number} body...")
                update_issue_body(number, new_body)
                total_screenshots_uploaded += uploaded
                issue_updated = True

        # Process comments
        if comment_matches_found:
            for c in comments:
                c_body = c.get("body") or ""
                if LOCAL_PATH_PATTERN.search(c_body):
                    c_matches = LOCAL_PATH_PATTERN.findall(c_body)
                    print(f"  Found {len(c_matches)} local path(s) in comment {c['id']}")
                    new_c_body, uploaded, screenshot_idx = process_text(c_body, number, screenshot_idx)
                    if uploaded > 0:
                        print(f"  Updating comment {c['id']}...")
                        update_comment(c["id"], new_c_body)
                        total_screenshots_uploaded += uploaded
                        issue_updated = True

        if issue_updated:
            total_issues_updated += 1

    print(f"\n{'='*50}")
    print(f"Updated {total_issues_updated} issues with {total_screenshots_uploaded} screenshots")


if __name__ == "__main__":
    main()
