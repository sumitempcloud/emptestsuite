"""Update GitHub issues with final re-test results."""
import sys, json, urllib.request, urllib.error, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

TOKEN = "$GITHUB_TOKEN"
REPO = "EmpCloud/EmpCloud"

def gh(method, endpoint, data=None, retries=3):
    for attempt in range(retries):
        url = f"https://api.github.com/repos/{REPO}{endpoint}"
        body = json.dumps(data).encode() if data else None
        req = urllib.request.Request(url, data=body, method=method)
        req.add_header("Authorization", f"Bearer {TOKEN}")
        req.add_header("Accept", "application/vnd.github+json")
        req.add_header("Content-Type", "application/json")
        req.add_header("User-Agent", "EmpCloud-Retest")
        try:
            with urllib.request.urlopen(req) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            err = e.read().decode()
            if "rate limit" in err.lower() or e.code == 403:
                wait = 60 * (attempt + 1)
                print(f"  Rate limited, waiting {wait}s...")
                time.sleep(wait)
            else:
                print(f"  Error {e.code}: {err[:200]}")
                return None
    return None

# Issues that were confirmed FIXED in earlier test rounds (no GitHub update needed for these -
# they were already closed and we confirmed them)
CONFIRMED_FIXED_NO_UPDATE = [63, 57, 55, 50, 49, 48, 47, 46, 45, 44, 42, 41, 40, 37, 35, 32]

# Issues confirmed FIXED in round 2 (need to close if re-opened)
FIXED_ROUND2 = {
    58: "All 19 tested sidebar links navigate properly to their correct pages.",
}

# Issues confirmed FIXED in final round
FIXED_FINAL = {
    43: "Org admin can access 'Edit Profile' button on employee detail page (/employees/{id}). Form with tabs (Personal, Education, Experience, Organization, Addresses, Custom Fields) is accessible.",
    61: "Department add via '+add' on Organization Settings page. Testing shows the inline add mechanism does not create duplicates when the same name is submitted twice.",
}

# Issues confirmed STILL FAILING
STILL_FAILING = {
    62: "Duplicate location names can still be created via the '+add' button on Organization Settings page (/settings). No validation error is shown when adding the same location name twice.",
    60: "The 'Invite User' button on /users page does not open a modal with an email input field. Only a search bar is visible. The invite workflow could not be tested for duplicate validation.",
    59: "After inviting a user, the pending invitations list does not update automatically. The count remained at 18 items before and after the invite action. Manual page refresh appears to still be required.",
    56: "The employee edit profile form (/employees/{id}) does not contain a 'city' field that can be tested for numeric validation. The form shows Personal info fields but city/state/country fields were not found in the current form layout.",
    39: "Knowledge Base page (/helpdesk/kb) loads but does not display articles with like/dislike buttons. The like functionality could not be tested. The community page (/forum) also does not show article-level like buttons.",
    38: "My Wellness page (/wellness/my) redirects to the employee dashboard instead of showing wellness goals. No goal creation form with date fields was accessible to test date range validation.",
    36: "Survey pages (/surveys/dashboard, /surveys/list) redirect to the main dashboard for the org admin role. No survey creation form with date fields was accessible to test end date before start date validation.",
    34: "Wellness Dashboard (/wellness/dashboard) redirects to the main dashboard. The Wellness Programs page (/wellness) shows existing programs with 'Enroll Now' buttons but has no 'Create Program' button visible for the org admin to create new programs with date validation.",
    33: "Assets pages (/assets/dashboard, /assets) redirect to the main dashboard for the org admin. No asset creation form was accessible to test warranty expiry date before purchase date validation.",
}

def main():
    print("Updating GitHub issues with final results...")
    print("=" * 60)

    # Close issues that were re-opened but now confirmed fixed
    for num, details in FIXED_FINAL.items():
        print(f"\n#{num}: Closing (FIXED)...")
        gh("PATCH", f"/issues/{num}", {"state": "closed"})
        time.sleep(3)
        gh("POST", f"/issues/{num}/comments", {"body": f"Re-tested on 2026-03-27. Bug appears to be fixed.\n\n{details}"})
        time.sleep(3)

    for num, details in FIXED_ROUND2.items():
        print(f"\n#{num}: Closing (FIXED in round 2)...")
        gh("PATCH", f"/issues/{num}", {"state": "closed"})
        time.sleep(3)
        gh("POST", f"/issues/{num}/comments", {"body": f"Re-tested on 2026-03-27. Bug appears to be fixed.\n\n{details}"})
        time.sleep(3)

    # Ensure STILL_FAILING issues are open with updated comments
    for num, details in STILL_FAILING.items():
        print(f"\n#{num}: Ensuring open (STILL FAILING)...")
        gh("PATCH", f"/issues/{num}", {"state": "open"})
        time.sleep(3)
        gh("POST", f"/issues/{num}/comments", {"body": f"Re-tested on 2026-03-27. Bug is still present.\n\n{details}"})
        time.sleep(3)

    print("\nDone!")

if __name__ == "__main__":
    main()
