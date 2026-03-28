#!/usr/bin/env python3
"""
Close duplicate/alt-path issues and consolidate similar bugs per module.
Rules:
- Close all "(alt)" path issues with a comment pointing to the main issue
- Consolidate similar 404 bugs per module into one tracking issue
"""
import requests, time, re

GH_TOKEN = "$GITHUB_TOKEN"
GH_REPO = "EmpCloud/EmpCloud"
HEADERS = {"Authorization": f"token {GH_TOKEN}", "Accept": "application/vnd.github.v3+json"}
BASE = f"https://api.github.com/repos/{GH_REPO}"

def get_issues(range_start=585, range_end=656):
    """Get all issues in our filed range."""
    issues = []
    page = 1
    while True:
        r = requests.get(f"{BASE}/issues", headers=HEADERS,
                        params={"state": "open", "per_page": 100, "page": page}, timeout=30)
        if r.status_code != 200:
            break
        batch = r.json()
        if not batch:
            break
        for i in batch:
            if range_start <= i["number"] <= range_end:
                issues.append(i)
        page += 1
    return sorted(issues, key=lambda x: x["number"])

def close_with_comment(issue_number, comment):
    """Add comment and close an issue."""
    # Add comment
    requests.post(f"{BASE}/issues/{issue_number}/comments", headers=HEADERS,
                 json={"body": comment}, timeout=30)
    time.sleep(0.5)
    # Close
    requests.patch(f"{BASE}/issues/{issue_number}", headers=HEADERS,
                  json={"state": "closed"}, timeout=30)
    time.sleep(0.5)
    print(f"  Closed #{issue_number}")

def update_issue_body(issue_number, new_body):
    """Update issue body."""
    requests.patch(f"{BASE}/issues/{issue_number}", headers=HEADERS,
                  json={"body": new_body}, timeout=30)
    time.sleep(0.5)

def main():
    issues = get_issues()
    print(f"Found {len(issues)} issues in range 585-656")

    # Group by module
    modules = {}
    for issue in issues:
        title = issue["title"]
        # Extract module name
        match = re.match(r'^(?:\[Feature Request\]\s*)?(.+?)\s*[—\-]\s*(.+)$', title)
        if match:
            module = match.group(1).strip()
            page_desc = match.group(2).strip()
        else:
            module = "Unknown"
            page_desc = title

        if module not in modules:
            modules[module] = []
        modules[module].append({
            "number": issue["number"],
            "title": title,
            "page_desc": page_desc,
            "body": issue.get("body", ""),
            "is_alt": "(alt)" in page_desc.lower(),
            "is_404": "404" in page_desc.lower() or "404" in (issue.get("body") or ""),
            "is_feature": title.startswith("[Feature Request]"),
        })

    # For each module, consolidate
    for module, mod_issues in modules.items():
        print(f"\n=== {module} ({len(mod_issues)} issues) ===")

        # Separate: alt-path duplicates, real 404s, and other bugs
        alt_issues = [i for i in mod_issues if i["is_alt"]]
        real_404s = [i for i in mod_issues if i["is_404"] and not i["is_alt"]]
        other_issues = [i for i in mod_issues if not i["is_404"] and not i["is_alt"]]
        features = [i for i in mod_issues if i["is_feature"]]

        # Close all alt-path issues - they're just URL guesses
        for alt in alt_issues:
            close_with_comment(alt["number"],
                f"Closing as duplicate — this was an alternative URL path guess. "
                f"The actual routing issue is tracked in the main bug for this module.")

        # If there are multiple 404s for the same module, consolidate into one
        if len(real_404s) > 1:
            # Keep the first one, consolidate rest into it
            primary = real_404s[0]
            others_to_close = real_404s[1:]

            # Build consolidated body
            pages_list = "\n".join(f"- {i['page_desc']} (#{i['number']})" for i in real_404s)
            consolidated_body = (
                f"Multiple pages in the **{module}** module return 404 errors.\n\n"
                f"**Affected pages:**\n{pages_list}\n\n"
                f"**Steps to reproduce:**\n"
                f"1. Login as HR Admin (ananya@technova.in)\n"
                f"2. Navigate to {module} module via SSO from dashboard\n"
                f"3. Try to access the pages listed above\n\n"
                f"**Expected:** Each page loads with its content\n"
                f"**Actual:** All return 404 Not Found\n\n"
                f"This suggests these routes may not be implemented yet or have different URL patterns.\n\n"
                f"---\n*Filed by automated SSO module testing*"
            )

            # Update primary issue title and body
            new_title = f"{module} — Multiple pages return 404 ({len(real_404s)} pages affected)"
            requests.patch(f"{BASE}/issues/{primary['number']}", headers=HEADERS,
                         json={"title": new_title, "body": consolidated_body}, timeout=30)
            time.sleep(0.5)
            print(f"  Updated #{primary['number']} as consolidated issue: {new_title}")

            # Close the others pointing to the consolidated one
            for other in others_to_close:
                close_with_comment(other["number"],
                    f"Consolidated into #{primary['number']} — tracking all 404 errors for {module} module in one issue.")

        # Keep other bugs and features as-is
        for issue in other_issues:
            if not issue["is_feature"]:
                print(f"  Keeping #{issue['number']}: {issue['title']}")
        for feat in features:
            print(f"  Keeping feature #{feat['number']}: {feat['title']}")

    print("\nDone consolidating!")

if __name__ == "__main__":
    main()
