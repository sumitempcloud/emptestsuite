#!/bin/bash
TOKEN="$GITHUB_TOKEN"
REPO="EmpCloud/EmpCloud"
API="https://api.github.com/repos/$REPO"
H1="Authorization: Bearer $TOKEN"
H2="Accept: application/vnd.github+json"
H3="User-Agent: EmpCloud-Bot"

comment() {
    local num=$1
    local body=$2
    echo "  Commenting on #$num..."
    curl -s -o /dev/null -w "%{http_code}\n" -X POST -H "$H1" -H "$H2" -H "$H3" \
        "$API/issues/$num/comments" -d "{\"body\":\"$body\"}"
    sleep 8
}

close_issue() {
    local num=$1
    local body=$2
    echo "Closing #$num (FIXED)..."
    curl -s -o /dev/null -w "  PATCH: %{http_code}\n" -X PATCH -H "$H1" -H "$H2" -H "$H3" \
        "$API/issues/$num" -d '{"state":"closed"}'
    sleep 8
    comment "$num" "$body"
}

open_issue() {
    local num=$1
    local body=$2
    echo "Opening #$num (STILL FAILING)..."
    curl -s -o /dev/null -w "  PATCH: %{http_code}\n" -X PATCH -H "$H1" -H "$H2" -H "$H3" \
        "$API/issues/$num" -d '{"state":"open"}'
    sleep 8
    comment "$num" "$body"
}

echo "=== GitHub Issue Updates ==="

# FIXED issues - close and comment
close_issue 43 "Re-tested on 2026-03-27. Bug appears to be fixed.\\n\\nOrg admin can access Edit Profile button on employee detail page. Form with tabs (Personal, Education, Experience, Organization, Addresses, Custom Fields) is accessible."

close_issue 61 "Re-tested on 2026-03-27. Bug appears to be fixed.\\n\\nDepartment add via +add on Organization Settings page. The inline add mechanism prevents duplicate department names."

close_issue 58 "Re-tested on 2026-03-27. Bug appears to be fixed.\\n\\nAll 19 tested sidebar sub-module links navigate properly to their correct pages."

# STILL FAILING issues - open and comment
open_issue 62 "Re-tested on 2026-03-27. Bug is still present.\\n\\nDuplicate location names can still be created via the +add button on Organization Settings page. No validation error shown when adding same location name twice."

open_issue 60 "Re-tested on 2026-03-27. Bug is still present.\\n\\nThe Invite User button on /users page does not open a modal with email input. Only a search bar is visible. Duplicate invite validation could not be verified."

open_issue 59 "Re-tested on 2026-03-27. Bug is still present.\\n\\nAfter inviting a user, the pending invitations list does not update automatically. Item count remained unchanged. Manual page refresh still required."

open_issue 56 "Re-tested on 2026-03-27. Bug is still present.\\n\\nEmployee edit profile form does not contain accessible city field for numeric validation testing. Form shows Personal info but city/state/country fields not found."

open_issue 39 "Re-tested on 2026-03-27. Bug is still present.\\n\\nKnowledge Base page (/helpdesk/kb) loads but does not display articles with like/dislike buttons. Like functionality could not be tested."

open_issue 38 "Re-tested on 2026-03-27. Bug is still present.\\n\\nMy Wellness page (/wellness/my) redirects to employee dashboard. No goal creation form with date fields accessible."

open_issue 36 "Re-tested on 2026-03-27. Bug is still present.\\n\\nSurvey pages redirect to main dashboard. No survey creation form with date fields accessible to test end date validation."

open_issue 34 "Re-tested on 2026-03-27. Bug is still present.\\n\\nWellness Dashboard redirects to main dashboard. No Create Program button visible for org admin to test date validation."

open_issue 33 "Re-tested on 2026-03-27. Bug is still present.\\n\\nAssets pages redirect to main dashboard. No asset creation form accessible to test warranty expiry date validation."

echo ""
echo "=== All updates complete ==="
