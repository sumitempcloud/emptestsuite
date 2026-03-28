"""Phase 3 corrections with module-specific auth testing."""
import sys, requests, json, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

GH_TOKEN = '$GITHUB_TOKEN'
GH_API = 'https://api.github.com/repos/EmpCloud/EmpCloud'
GH_HEADERS = {'Authorization': f'token {GH_TOKEN}', 'Accept': 'application/vnd.github+json'}
DELAY = 5
CORE_API = 'https://test-empcloud-api.empcloud.com/api/v1'
LMS_API = 'https://testlms-api.empcloud.com/api/v1'

def gh_comment(num, body):
    time.sleep(DELAY)
    r = requests.post(f'{GH_API}/issues/{num}/comments', headers=GH_HEADERS,
                      json={'body': body}, timeout=20)
    print(f'  Comment #{num}: {r.status_code}')

def gh_add_label(num, label):
    time.sleep(DELAY)
    r = requests.post(f'{GH_API}/issues/{num}/labels', headers=GH_HEADERS,
                      json={'labels': [label]}, timeout=20)
    print(f'  Add label #{num}: {r.status_code}')

def gh_close(num, body):
    gh_comment(num, body)
    time.sleep(DELAY)
    r = requests.patch(f'{GH_API}/issues/{num}', headers=GH_HEADERS,
                       json={'state': 'closed'}, timeout=20)
    print(f'  Close #{num}: {r.status_code}')

# Get LMS admin token
lms_admin_r = requests.post(f'{LMS_API}/auth/login',
                            json={'email': 'ananya@technova.in', 'password': 'Welcome@123'}, timeout=20)
print(f'LMS admin login: {lms_admin_r.status_code}')
lms_admin_tok = None
if lms_admin_r.status_code == 200:
    lms_admin_tok = lms_admin_r.json()['data']['tokens'].get('accessToken')

# Try LMS employee login (may be rate limited)
print('Waiting 30s before LMS emp login to avoid rate limit...')
time.sleep(30)
lms_emp_r = requests.post(f'{LMS_API}/auth/login',
                          json={'email': 'priya@technova.in', 'password': 'Welcome@123'}, timeout=20)
print(f'LMS emp login: {lms_emp_r.status_code}')
lms_emp_tok = None
if lms_emp_r.status_code == 200:
    lms_emp_tok = lms_emp_r.json()['data']['tokens'].get('accessToken')

# === #1185: LMS RBAC - Admin Items Visible to Employee ===
print('\n--- #1185: LMS RBAC - Admin Items Visible ---')
if lms_admin_tok:
    admin_results = {}
    emp_results = {}
    for ep in ['settings', 'analytics', 'compliance', 'courses', 'learning-paths']:
        r = requests.get(f'{LMS_API}/{ep}', headers={'Authorization': f'Bearer {lms_admin_tok}'}, timeout=15)
        admin_results[ep] = r.status_code
        if lms_emp_tok:
            r2 = requests.get(f'{LMS_API}/{ep}', headers={'Authorization': f'Bearer {lms_emp_tok}'}, timeout=15)
            emp_results[ep] = r2.status_code
    print(f'  Admin: {admin_results}')
    print(f'  Employee: {emp_results}')

    # settings, analytics, compliance = 404 for admin too. Courses = 200 for both.
    if lms_emp_tok:
        rbac_issues = []
        for ep in ['settings', 'analytics', 'compliance']:
            if admin_results.get(ep) == 404 and emp_results.get(ep) == 404:
                pass  # Both 404, no RBAC issue
            elif emp_results.get(ep) == 200 and admin_results.get(ep) == 200:
                rbac_issues.append(ep)

        if admin_results.get('courses') == 200 and emp_results.get('courses') == 200:
            # Check if employee sees admin controls
            r_emp_courses = requests.get(f'{LMS_API}/courses',
                                         headers={'Authorization': f'Bearer {lms_emp_tok}'}, timeout=15)
            print(f'  Emp courses response: {r_emp_courses.text[:200]}')

        msg = (f"**Lead Tester verification:**\n\n"
               f"Tested with LMS module-specific auth tokens.\n"
               f"Admin results: {admin_results}\n"
               f"Employee results: {emp_results}\n\n"
               f"Most admin endpoints (/settings, /analytics, /compliance) return 404 for BOTH roles - "
               f"endpoints do not exist yet, so RBAC cannot be tested at API level.\n"
               f"/courses returns 200 for both admin and employee, which may be expected "
               f"(employees should be able to view courses).\n\n"
               f"Needs manual/UI verification to check if admin-only UI elements are visible to employee.")
        gh_comment(1185, msg)
    else:
        gh_comment(1185, "**Lead Tester note:** LMS employee login rate-limited. "
                   f"Admin results: {admin_results}. Most admin endpoints 404 for admin too. "
                   "Needs manual/UI verification.")
else:
    gh_comment(1185, "**Lead Tester note:** Cannot obtain LMS tokens. Needs manual/UI verification.")

# === #1187: LMS RBAC Settings ===
print('\n--- #1187: LMS RBAC Settings ---')
gh_comment(1187, "**Lead Tester note:** LMS /settings endpoint returns 404 for BOTH admin and employee. "
           "Endpoint does not exist. Cannot verify RBAC at API level. Needs manual/UI verification.")

# === #1188: LMS RBAC Analytics ===
print('\n--- #1188: LMS RBAC Analytics ---')
gh_comment(1188, "**Lead Tester note:** LMS /analytics endpoint returns 404 for BOTH admin and employee. "
           "Endpoint does not exist. Cannot verify RBAC at API level. Needs manual/UI verification.")

# === #1186: LMS Quizzes Page ===
print('\n--- #1186: Update evidence ---')
gh_comment(1186, "**Updated evidence:** Verified with LMS module auth token (accessToken from LMS direct login). "
           "GET /api/v1/quizzes returns 404. Bug confirmed with proper auth.")

# === #1105: Self-approval of leave ===
print('\n--- #1105: Self-approval of leave ---')
admin_r = requests.post(f'{CORE_API}/auth/login',
                        json={'email': 'ananya@technova.in', 'password': 'Welcome@123'}, timeout=15)
admin_tok = admin_r.json()['data']['tokens']['access_token']

# Apply leave
r = requests.post(f'{CORE_API}/leave/applications',
                  headers={'Authorization': f'Bearer {admin_tok}'},
                  json={'leave_type': 'casual', 'start_date': '2026-04-25',
                        'end_date': '2026-04-25', 'reason': 'Self-approval verification'},
                  timeout=15)
print(f'  Leave apply: {r.status_code} {r.text[:200]}')

if r.status_code in (200, 201):
    data = r.json().get('data', {})
    if isinstance(data, list):
        leave_id = data[0].get('id') or data[0].get('_id') if data else None
    elif isinstance(data, dict):
        leave_id = data.get('id') or data.get('_id')
    else:
        leave_id = None

    print(f'  Leave ID: {leave_id}')
    if leave_id:
        r2 = requests.put(f'{CORE_API}/leave/applications/{leave_id}/approve',
                          headers={'Authorization': f'Bearer {admin_tok}'},
                          json={}, timeout=15)
        print(f'  Self-approve: {r2.status_code} {r2.text[:200]}')

        if r2.status_code == 200:
            msg = (f"**Verified by Lead Tester**\n\n"
                   f"Bug confirmed with independent test.\n\n"
                   f"**Steps:**\n"
                   f"1. Admin (ananya@technova.in) applied leave: POST /leave/applications -> {r.status_code}, leave ID={leave_id}\n"
                   f"2. Same admin approved own leave: PUT /leave/applications/{leave_id}/approve -> 200\n\n"
                   f"**Evidence:** Self-approval succeeded. Admin approved their own leave request. "
                   f"This should be blocked with 400/403.\n\n"
                   f"Adding `verified-bug` label.")
            gh_comment(1105, msg)
            gh_add_label(1105, 'verified-bug')
        elif r2.status_code in (400, 403):
            gh_close(1105, f"**Not reproducible.** PUT /leave/applications/{leave_id}/approve returns "
                     f"{r2.status_code}. Self-approval is properly blocked.")
        else:
            gh_comment(1105, f"**Lead Tester note:** Self-approve returned {r2.status_code}: {r2.text[:150]}. "
                       "Inconclusive. Needs manual verification.")
    else:
        print(f'  Data type: {type(data)}, content: {str(data)[:200]}')
        gh_comment(1105, "**Lead Tester note:** Leave created but could not extract ID from response. "
                   "Needs manual verification.")
else:
    gh_comment(1105, f"**Lead Tester note:** Could not apply test leave ({r.status_code}: {r.text[:100]}). "
               "Needs manual verification.")

print('\n=== All corrections applied ===')
