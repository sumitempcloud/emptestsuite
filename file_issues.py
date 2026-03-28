"""File detailed GitHub issues for discovered bugs."""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import json
import requests

GITHUB_PAT = "$GITHUB_TOKEN"
GITHUB_REPO = "EmpCloud/EmpCloud"
headers = {
    "Authorization": f"token {GITHUB_PAT}",
    "Accept": "application/vnd.github.v3+json"
}

def file_issue(title, body, labels):
    resp = requests.post(
        f"https://api.github.com/repos/{GITHUB_REPO}/issues",
        headers=headers,
        json={"title": title, "body": body, "labels": labels},
        timeout=30
    )
    url = resp.json().get("html_url", "")
    print(f"  [{resp.status_code}] {title[:70]}")
    print(f"    {url}")
    return url

# Issue 1: Leave application vague error
file_issue(
    "Leave application API gives vague 'Invalid request data' without saying which field is missing",
    """## What I was trying to do
As employee Priya, applying for 2 days of sick leave next week.

## What happened
The leave application API (POST /api/v1/leave/applications) returns a generic 400 error:
```json
{"success":false,"error":{"code":"VALIDATION_ERROR","message":"Invalid request data"}}
```

After extensive trial-and-error, I discovered that `days_count` is a **required** field, but the error message does not indicate which field is missing or invalid.

### Payload that FAILS (400):
```json
{
  "leave_type_id": 17,
  "start_date": "2026-05-11",
  "end_date": "2026-05-12",
  "reason": "Not feeling well",
  "is_half_day": false
}
```

### Payload that SUCCEEDS (201):
```json
{
  "leave_type_id": 17,
  "start_date": "2026-05-11",
  "end_date": "2026-05-12",
  "days_count": 2,
  "is_half_day": 0,
  "reason": "Not feeling well"
}
```

## What I expected
1. The API should auto-calculate `days_count` from start_date and end_date (since it is deterministic)
2. If `days_count` is required, the validation error should say: "days_count is required"
3. The OpenAPI spec should document required fields for this endpoint

## Additional notes
- The OpenAPI spec at /api/docs/openapi.json has no request body schema for this endpoint
- This makes the API extremely difficult to integrate with
- 7 different payload variations were tried before finding the required field

## Environment
- API: https://test-empcloud-api.empcloud.com
- User: priya@technova.in (employee)
- Date: 2026-03-28
""",
    ["bug", "api", "hr-journey-test"]
)

# Issue 2: Document upload 500 error
file_issue(
    "Document upload returns 500 server error when multipart field name is wrong instead of 400",
    """## What I was trying to do
Uploading an employee's offer letter to the Documents section.

## What happened
Document upload endpoint (POST /api/v1/documents/upload) returns **500 Internal Server Error** when the file field is named "document" instead of "file".

A 500 error indicates an unhandled exception on the server, not a validation issue.

### Fails with 500:
```
POST /api/v1/documents/upload
files: {"document": ("offer_letter.pdf", file_data, "application/pdf")}
data: {"name": "Offer Letter", "category_id": 14, "user_id": 608}
```

### Works correctly (201):
```
POST /api/v1/documents/upload
files: {"file": ("offer_letter.pdf", file_data, "application/pdf")}
data: {"name": "Offer Letter", "category_id": 14}
```

## What I expected
- The API should return 400 with a clear message like "file field is required" instead of 500
- Server should validate the multipart form data before processing

## Environment
- API: https://test-empcloud-api.empcloud.com
- User: ananya@technova.in (HR Manager)
- Date: 2026-03-28
""",
    ["bug", "api", "hr-journey-test"]
)

# Issue 3: HR cannot apply leave via API
file_issue(
    "HR Manager cannot apply leave through API - always returns validation error regardless of payload",
    """## What I was trying to do
As HR Manager (org_admin role), trying to apply leave for myself and on behalf of employees.

## What happened
POST /api/v1/leave/applications always returns 400 "Invalid request data" for HR manager users, regardless of the payload format.

### Tested payloads that ALL fail:
```json
// HR applying for self
{"leave_type_id": 17, "start_date": "2026-05-15", "end_date": "2026-05-16", "reason": "Medical appointment", "days_count": 2, "is_half_day": 0}

// HR applying on behalf of employee
{"user_id": 524, "leave_type_id": 17, "start_date": "2026-05-18", "end_date": "2026-05-18", "reason": "Medical appointment", "days_count": 1, "is_half_day": 0}
```

Note: The exact same payload structure works for employees (role: employee), but fails for HR (role: org_admin).

## What I expected
- HR Manager should be able to apply leave for themselves
- HR Manager should be able to apply leave on behalf of employees
- The error message should explain what's wrong

## Environment
- API: https://test-empcloud-api.empcloud.com
- User: ananya@technova.in (org_admin role)
- Date: 2026-03-28
""",
    ["bug", "api", "hr-journey-test"]
)

# Issue 4: Missing OpenAPI schemas
file_issue(
    "API docs missing request body schemas for most POST/PUT endpoints - impossible to know required fields",
    """## What I was trying to do
Using the API documentation to understand how to call various endpoints for HR workflows.

## What happened
The OpenAPI spec at /api/docs/openapi.json is missing request body schemas for most POST/PUT endpoints:

- POST /api/v1/leave/applications - no request body schema
- POST /api/v1/announcements - no request body schema
- POST /api/v1/users - no request body schema
- POST /api/v1/users/invite - no request body schema
- PUT /api/v1/organizations/me - no request body schema
- POST /api/v1/attendance/check-in - no request body schema
- And many more...

Only POST /api/v1/documents/upload has a partial schema (missing required field indicators).

## What I expected
Each POST/PUT endpoint should document:
1. Required vs optional fields
2. Field types and formats
3. Example request bodies
4. Detailed validation error responses

## Impact
- Makes integration development a trial-and-error process
- Makes test automation extremely difficult
- Combined with vague "Invalid request data" errors, API is nearly unusable without source code access

## Environment
- API Docs: https://test-empcloud-api.empcloud.com/api/docs/
- Total endpoints: 94 documented
- Date: 2026-03-28
""",
    ["documentation", "api", "hr-journey-test"]
)

# Issue 5: Org chart only 2 entries
file_issue(
    "Org chart shows only 2 entries when organization has 20+ employees",
    """## What I was trying to do
Viewing the organization chart to see company hierarchy and reporting structure.

## What happened
GET /api/v1/users/org-chart returns only 2 entries, despite:
- Employee directory showing 20 employees
- Org stats showing 17 total users

## What I expected
The org chart should show ALL employees in a hierarchical tree based on `reporting_manager_id` relationships.

A proper org chart should help HR visualize:
- Who reports to whom
- Department structure
- Team sizes
- New hires (like Rahul Sharma added today)

## Environment
- API: https://test-empcloud-api.empcloud.com
- User: ananya@technova.in (org_admin)
- Date: 2026-03-28
""",
    ["bug", "hr-journey-test"]
)

# Issue 6: No Add Employee button in UI
file_issue(
    "No visible 'Add Employee' button on employees page - only way to add is via API",
    """## What I was trying to do
Adding a new joiner (Rahul Sharma, Software Engineer in Engineering) on his first day.

## What happened
Navigated to the Employees page (/employees). The page loads and shows the employee list, but there is no visible "Add Employee", "New Employee", or "Create" button anywhere on the page.

I was only able to add the employee by discovering and using the POST /api/v1/users API endpoint directly, which is not something an HR Manager would normally do.

## What I expected
A prominent "Add Employee" or "+" button on the employees list page that opens a form with fields for:
- First name, Last name
- Email
- Phone number
- Department (dropdown)
- Designation
- Date of joining
- Reporting manager
- Employment type

## Screenshot
The employees page with no Add button visible was captured during testing.

## Environment
- URL: https://test-empcloud.empcloud.com/employees
- User: ananya@technova.in (HR Manager)
- Date: 2026-03-28
""",
    ["bug", "ux", "hr-journey-test"]
)

# Issue 7: Attendance dashboard has no date/department filters visible
file_issue(
    "Attendance page has no visible date or department filters for HR to drill down",
    """## What I was trying to do
Checking Monday morning attendance - wanted to filter by date and department to see who's absent in Engineering.

## What happened
The attendance page shows attendance data (which is good!), and the API confirms the dashboard works:
- Total employees: 17
- Present: 2
- Absent: 15
- Late: 0
- On leave: 0

However, the UI does not show visible filter controls for:
- Date selection (to check past dates)
- Department filter (to see per-department attendance)
- Late arrivals filter

## What I expected
As an HR Manager, I need to:
1. Filter attendance by specific dates
2. Filter by department to see team-level attendance
3. Identify who was late
4. Export attendance data

## Environment
- URL: https://test-empcloud.empcloud.com/attendance
- API: GET /api/v1/attendance/dashboard returns correct data
- Date: 2026-03-28
""",
    ["enhancement", "ux", "hr-journey-test"]
)

print("\nDone filing issues!")
