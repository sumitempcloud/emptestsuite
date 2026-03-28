#!/usr/bin/env python3
"""File remaining bugs for feedback update/delete and ticket delete"""
import sys, json, urllib.request, ssl
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

GITHUB_PAT = "$GITHUB_TOKEN"
GITHUB_REPO = "EmpCloud/EmpCloud"
BASE = "https://test-empcloud.empcloud.com/api/v1"
ctx = ssl.create_default_context()

def file_issue(title, body):
    url = f"https://api.github.com/repos/{GITHUB_REPO}/issues"
    headers = {
        "User-Agent": "EmpCloud-CRUD-Tester/4.0",
        "Authorization": f"token {GITHUB_PAT}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json",
    }
    data = json.dumps({"title": title, "body": body, "labels": ["bug", "functional", "api"]}).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
            r = json.loads(resp.read().decode("utf-8"))
            print(f"  Filed: {r.get('html_url')}")
            return r.get("html_url")
    except Exception as e:
        print(f"  FAILED: {e}")
        return None

# Bug 1: Feedback UPDATE/DELETE missing
print("Filing: Feedback PUT/DELETE endpoints missing...")
file_issue(
    "[FUNCTIONAL] PUT/DELETE /feedback/{id} - Endpoints return 404",
    f"""## Functional Bug Report

**Endpoint:** `PUT {BASE}/feedback/{{id}}` and `DELETE {BASE}/feedback/{{id}}`
**Date:** 2026-03-28
**Environment:** test-empcloud.empcloud.com

### Description
Feedback items can be created (POST /feedback returns 201) and listed (GET /feedback returns 200),
but individual feedback items cannot be updated or deleted. Both PUT and DELETE on `/feedback/{{id}}`
return 404 "Endpoint not found". Also tried `/feedback/{{id}}/respond` which also returns 404.

### Steps to Reproduce
1. POST /feedback with `{{"category": "management", "subject": "Test", "message": "Test"}}` -> 201 (ID: 13)
2. PUT /feedback/13 with `{{"status": "acknowledged", "admin_response": "Thanks"}}` -> 404
3. PUT /feedback/13/respond with same body -> 404
4. DELETE /feedback/13 -> 404

### Expected Behavior
- PUT /feedback/{{id}} should allow admin to respond/update feedback status
- DELETE /feedback/{{id}} should allow deletion of feedback entries

### Actual Behavior
Both endpoints return 404 "Endpoint not found"

### Severity
Functional - CRUD update and delete operations missing for feedback module
"""
)

# Bug 2: Helpdesk tickets DELETE missing
print("\nFiling: Helpdesk tickets DELETE endpoint missing...")
file_issue(
    "[FUNCTIONAL] DELETE /helpdesk/tickets/{id} - Endpoint returns 404",
    f"""## Functional Bug Report

**Endpoint:** `DELETE {BASE}/helpdesk/tickets/{{id}}`
**Date:** 2026-03-28
**Environment:** test-empcloud.empcloud.com

### Description
Helpdesk tickets can be created (POST 201), read (GET 200), and updated (PUT 200),
but cannot be deleted. DELETE /helpdesk/tickets/{{id}} returns 404 "Endpoint not found".

### Steps to Reproduce
1. POST /helpdesk/tickets with valid payload -> 201 (creates ticket successfully)
2. PUT /helpdesk/tickets/{{id}} with status update -> 200 (updates successfully)
3. DELETE /helpdesk/tickets/{{id}} -> 404

### Expected Behavior
DELETE /helpdesk/tickets/{{id}} should delete the ticket or return 403 if not allowed.

### Actual Behavior
Returns 404 "Endpoint not found" - the DELETE route is not implemented.

### Severity
Functional - CRUD delete operation missing for helpdesk tickets
"""
)

# Bug 3: Users DELETE - soft delete only
print("\nFiling: Users DELETE soft-delete inconsistency...")
file_issue(
    "[FUNCTIONAL] DELETE /users/{id} - User still accessible after deletion (soft delete not properly indicated)",
    f"""## Functional Bug Report

**Endpoint:** `DELETE {BASE}/users/{{id}}`
**Date:** 2026-03-28
**Environment:** test-empcloud.empcloud.com

### Description
After DELETE /users/{{id}} returns 200 (success), the user is still accessible via GET /users/{{id}}
which also returns 200 with the full user data. The response does not indicate the user has been
deleted or deactivated. If this is a soft delete, the GET response should indicate the deleted status
(e.g., `is_active: false` or `status: deleted`), or GET should return 404.

### Steps to Reproduce
1. POST /users -> 201 (create user, ID: 597)
2. DELETE /users/597 -> 200 (success)
3. GET /users/597 -> 200 (user still fully accessible, no deleted indicator)

### Expected Behavior
After successful DELETE:
- Either GET /users/{{id}} returns 404
- Or the response includes a deleted/inactive status field

### Actual Behavior
User remains fully accessible with no indication of deletion

### Severity
Functional - Delete operation does not effectively remove or mark user as deleted
"""
)

print("\nDone filing remaining bugs.")
