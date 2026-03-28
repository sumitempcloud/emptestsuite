# EMP Cloud E2E Testing — Project Instructions

## Application Under Test
- **URL:** https://test-empcloud.empcloud.com
- **API:** https://test-empcloud.empcloud.com/api/v1
- **Repo:** https://github.com/EmpCloud/EmpCloud
- **GitHub PAT:** $GITHUB_TOKEN

## Login Credentials

| Role | Email | Password |
|------|-------|----------|
| Super Admin | admin@empcloud.com | SuperAdmin@2026 |
| Org Admin | ananya@technova.in | Welcome@123 |
| Employee | priya@technova.in | Welcome@123 |
| Other Org Admin | john@globaltech.com | Welcome@123 |

## Critical Rules — MUST FOLLOW

### 1. Module Authentication — SSO Flow (CRITICAL)
External modules (Payroll, Recruit, LMS, Performance, Rewards, Exit, Projects) use **SSO from EMP Cloud**. The core JWT token DOES NOT work on module APIs.

**Correct SSO Flow for API testing:**
1. Login at EMP Cloud → `POST /api/v1/auth/login` → get `access_token`
2. Get SSO URL from dashboard → the frontend generates an `sso_token` URL
3. Call module's SSO callback → `GET module.empcloud.com/sso/callback?sso_token=<token>`
4. Module validates with EMP Cloud → `POST empcloud.com/api/v1/auth/sso/validate`
5. Module creates local session → returns module-specific token/cookie
6. Use module token for all module API calls

**For Selenium testing:** Login at test-empcloud.empcloud.com → navigate to /modules → click module card → SSO auto-authenticates → then test module pages

**SSO is simple — append access_token as URL parameter:**
1. Login at EMP Cloud → `POST /api/v1/auth/login` → get `access_token`
2. Navigate to: `https://testpayroll.empcloud.com?sso_token=<access_token>`
3. Module reads the token from URL and authenticates

**For Selenium:** `driver.get(f'https://testpayroll.empcloud.com?sso_token={token}')`
**For API:** The module may set its own session cookie after SSO — capture it from the redirect

**Module SSO URLs:**
- Payroll: `https://testpayroll.empcloud.com?sso_token=<JWT>`
- Recruit: `https://test-recruit.empcloud.com?sso_token=<JWT>`
- Performance: `https://test-performance.empcloud.com?sso_token=<JWT>`
- Rewards: `https://test-rewards.empcloud.com?sso_token=<JWT>`
- Exit: `https://test-exit.empcloud.com?sso_token=<JWT>`
- LMS: `https://testlms.empcloud.com?sso_token=<JWT>`
- Projects: `https://test-project.empcloud.com?sso_token=<JWT>`

**Token lifetime is 15 minutes** — get a fresh token before each module test

### 2. Use Correct API Paths (from READMEs)
See `C:\emptesting\CORRECT_API_PATHS.md` for FULL mapping. Key corrections:

**EMP Cloud Core (test-empcloud-api.empcloud.com):**
- `/api/v1/organizations/me/departments` (NOT `/departments`)
- `/api/v1/organizations/me/locations` (NOT `/locations`)
- `/api/v1/employees/:id/profile` (NOT `/employees/:id/extended`)
- `/api/v1/attendance/check-in` and `/check-out` (hyphenated)
- `/api/v1/leave/applications` for POST (NOT `/leave/apply`)
- `/api/v1/leave/applications/:id/approve` (ID before action)
- `/api/v1/policies/:id/acknowledge` (ID before action)
- `/api/v1/notifications/:id/read` (per-notification)
- `/api/v1/documents` for POST upload (NOT `/documents/upload`)

**All modules use SSO only (NOT direct login):**
- Recruit: `/api/v1/auth/sso` (NOT `/auth/login`)
- Performance: `/api/v1/auth/sso`
- All others: same pattern

**EMP Project uses DIFFERENT prefix:**
- `/v1/` NOT `/api/v1/` — it's Next.js + MongoDB
- Swagger at `/explorer` not `/api/docs`

**EMP Monitor is completely different stack:**
- QT desktop + Laravel frontend + Node.js backend
- Does NOT share API patterns with other modules

### 3. Soft Delete is By Design
DELETE returns 200 but items remain accessible via GET /:id — this is **intentional for audit trail**. Do NOT report as a bug.

### 4. XSS in Database is NOT a Vulnerability
Script tags stored in the database are NOT a security issue:
- **React JSX auto-escapes** all text content — `<script>` tags render as plain text, never execute
- **Knex ORM** uses parameterized queries — SQL injection is prevented at the query layer
- Only report XSS if the payload actually **EXECUTES in the browser**

### 5. Do NOT Report These as Bugs — HARD RULES
- **Rate limiting — NEVER test, NEVER report, NEVER re-open.** All rate limits removed for testing. If you get a 429, just wait and retry — do NOT file a bug.
- Field Force module (emp-field) — not ready for testing
- Biometrics module (emp-biometrics) — not ready for testing
- Direct subdomain login failures (SSO only — see rule #1)
- Missing API endpoints that don't exist as standalone routes (see rule #2)
- Soft-deleted items still accessible (see rule #3)
- XSS/SQL payloads stored in DB without execution (see rule #4)

### 6. Always Include in Bug Reports
Every bug filed or re-opened MUST include:
```markdown
## URL Tested
[exact URL or API endpoint]

## Steps to Reproduce
1. Navigate to https://test-empcloud.empcloud.com/login
2. Login as [role] ([email] / [password])
3. [specific steps]

## Expected Result
[what should happen]

## Actual Result
[what actually happens]

## Screenshot
![Screenshot](https://raw.githubusercontent.com/EmpCloud/EmpCloud/main/screenshots/issue_{number}.png)
```

### 7. Screenshots / Proof MANDATORY on ALL GitHub Actions — NO EXCEPTIONS
EVERY bug filed, re-opened, verified, or commented on MUST include PROOF:
- Filing a bug → screenshot of the broken page/error OR full API request + response
- Re-opening → screenshot proving it's still broken OR API evidence
- Verifying fixed → screenshot proving it works OR API evidence
- **NEVER file or re-open a bug without proof. If you can't provide proof, DON'T file it.**

For Selenium tests: `driver.save_screenshot()` → upload to repo → embed `![Screenshot](url)`
For API tests: Include the FULL request and response in the comment:
```
Request: GET /api/v1/users (as employee priya@technova.in)
Response: HTTP 200 — returned 20 users (should be 403)
```

### Screenshot Upload Method
Upload to repo then embed:
```python
PUT /repos/EmpCloud/EmpCloud/contents/screenshots/{name}.png
{"message": "Screenshot for issue #X", "content": "<base64>"}
```
Then use: `![Screenshot](https://raw.githubusercontent.com/EmpCloud/EmpCloud/main/screenshots/{name}.png)`

### 8. Read Programmer Comments — VERIFY, NEVER BLINDLY SKIP
Before re-opening ANY closed bug, you MUST:
1. Fetch ALL comments on the issue via `GET /repos/EmpCloud/EmpCloud/issues/{num}/comments`
2. Read every comment from `sumitempcloud` (the programmer)
3. **DO NOT just skip because programmer commented — VERIFY what he said:**

**Verification Rules:**

| Programmer Says | What To Do |
|----------------|------------|
| "fixed" / "deployed" / "resolved" | **Re-test to verify the fix actually works.** If still failing → re-open with "programmer says fixed but re-test shows still failing" |
| "use /organizations/me/X" or suggests a path | **Test THAT specific path.** If it works → mark as PASS. If not → re-open |
| "not a bug" / "by design" | **Extract any paths/endpoints mentioned, test them.** If they work → respect it. If not → re-open with evidence |
| "soft delete by design" | Confirm by-design per project rules (items accessible after DELETE is correct) |
| "React escapes XSS" | Confirm — stored XSS in DB is not a vulnerability per project rules |
| "duplicate of #X" | Skip (consolidated) |
| No comment at all | Re-open — programmer must explain before closing |

**NEVER blindly skip. NEVER trust programmer comments at face value. ALWAYS re-verify independently.**

The programmer's comments are INFORMATION, not TRUTH. Use them to understand:
- What endpoint/path he suggests → test THAT path
- What he claims to have fixed → verify the fix ACTUALLY works
- What he says is "by design" → test it yourself to confirm

But NEVER mark something as PASS just because the programmer said "fixed" or "deployed". Always run your own test and confirm with evidence.

Example: If programmer comments "Fixed in commit abc123 — added validation for date fields", then:
1. Send invalid date (end_date before start_date)
2. Check if API returns 400 validation error
3. If YES → verified fixed
4. If NO (still accepts invalid dates) → re-open: "Programmer says fixed but validation still not working"

### 9. Verify ALL Closed Issues — Bugs AND Enhancements
The Lead Tester must verify EVERY closed issue — not just bugs but also enhancement/feature requests:
- **Bugs closed by programmer** → re-test to confirm fix works
- **Enhancements closed by programmer** → verify the feature was actually built and works
- Only label `verified-closed-lead-tester` after YOUR OWN independent test confirms it

**Enhancement verification flow:**
1. Programmer marks enhancement as done and closes it
2. Lead Tester tests if the feature actually works
3. If WORKS → label `verified-closed-lead-tester` ✅
4. If DOES NOT WORK → convert to bug:
   a. Re-open the issue
   b. Change label from `enhancement` to `bug`
   c. Add label `verified-bug`
   d. Comment: "Enhancement marked done by programmer but feature not working. Converting to verified bug. Evidence: [test result]"
   e. Programmer will only pick up `verified-bug` labeled issues

**The programmer only works on `verified-bug` issues. If an enhancement doesn't work after he says it's done, it becomes a verified bug for him to fix.**

### 10. verified-fixed Issues Must ALWAYS Be Closed — HARD RULE
If an issue has the `verified-fixed` label, it MUST be in CLOSED state. NEVER leave it open.
- If you add `verified-fixed` label → close the issue in the same API call
- If you see an open issue with `verified-fixed` → close it immediately
- The 30-min cron auto-closes any open `verified-fixed` as a safety net
- `verified-fixed` = permanently done, never re-open, never re-test

### 11. NEVER Verify Without Actual Test Evidence
If you CANNOT reproduce or test the bug, do NOT mark it as `verified-closed-lead-tester`. Instead:
- Leave it as-is (closed with `verified-bug` label)
- Comment: "Cannot independently verify — no testable endpoint available. Leaving for manual verification."
- NEVER write "accepting programmer's fix based on code changes" — that is NOT verification
- NEVER write "could not reproduce but accepting" — if you can't test it, you can't verify it

Only use `verified-closed-lead-tester` when you have ACTUAL evidence:
- API call returned expected result (200/403/400)
- Selenium screenshot showing the fix works
- Specific data proving the issue is resolved

### 11. Always Verify BEFORE Tagging as verified-bug
Do NOT blindly tag issues as `verified-bug`. Before tagging:
1. Actually TEST the bug to confirm it's real
2. Check for DUPLICATES — search existing open issues for the same bug before tagging/filing
3. Only tag `verified-bug` after your own test confirms the issue
4. Programmer only picks up `verified-bug` — unverified issues will be ignored

### 11. Check for Duplicates Before Filing
Before filing ANY new issue:
1. Search open issues for similar titles/keywords
2. If duplicate exists → add a comment to the existing issue, don't create a new one
3. If you filed duplicates by mistake → close the duplicates with "Closing as duplicate of #X"

### 12. NEVER Close a Bug Without a Comment
Every bug closure MUST include a comment explaining WHY:
- "Closing: Confirmed fixed — [test result]"
- "Closing: Not a bug — [explanation]"
- "Closing: Duplicate of #XX"
- "Closing: By design — [reason]"

If the programmer closes a bug without commenting, RE-OPEN it and ask for explanation.

### 10. Consolidate Similar Bugs Into ONE Issue
Do NOT file separate issues for every field or variation. Group related bugs:
- All validation gaps for one endpoint → ONE issue listing all fields
- All XSS on different endpoints → ONE issue listing all affected endpoints
- Same bug on multiple pages → ONE issue listing all pages
- Example: Instead of 50 issues like "PUT /users - email validation gap", "PUT /users - name validation gap", file ONE: "User update endpoint missing validation on multiple fields: email, name, DOB, phone"

### 11. File Feature Requests in Plain English for a Layman
If a feature is MISSING, file as a feature request written so ANY person can understand it — no technical jargon, no internal rule numbers (SC001, B002, etc.), no code references.

**BAD title:** "[Feature Request] SC001 — Salary validation not implemented"
**GOOD title:** "Salary field should not accept zero or negative values"

**BAD body:** "Rule TX002 from BUSINESS_RULES_V2.md is not enforced on the ESI threshold endpoint"
**GOOD body:**
```
## What's needed
When HR enters an employee's salary, the system should automatically check if ESI (Employee State Insurance) applies. ESI only applies when the employee's monthly gross salary is Rs 21,000 or less. Currently the system doesn't check this.

## Who needs it
HR Manager — when setting up payroll for new employees

## How it should work
1. When salary is entered/updated, check if gross <= Rs 21,000
2. If yes, enable ESI deduction (1.75% employee + 3.25% employer)
3. If no, disable ESI deduction
4. Show a clear indicator on the payslip

## Why it matters
Wrong ESI deductions mean non-compliance with labor law and incorrect payslips.
```

Never use internal rule numbers in bug titles or descriptions. Write like you're explaining to a non-technical person.

### 12. Human-Style Bug Titles
Write bug titles like a REAL person, not a robot:
- GOOD: "Can't apply for leave — dropdown shows no options"
- GOOD: "New employee not showing in list after adding"
- BAD: "[FUNCTIONAL] POST /api/v1/leave returns 400"
- BAD: "[VALIDATION] PUT /users/599 - date_of_birth: medium validation gap"

## Architecture Notes

- **Frontend:** Vite + React SPA behind Cloudflare. All routes return same HTML shell (599 bytes). 404 detection must check page content, not HTTP status.
- **Backend:** Express.js + Knex ORM. API at `/api/v1/`.
- **External Modules:** Accessed via SSO JWT tokens from Module Insights cards on dashboard. Not in sidebar.
- **Org Admin sidebar:** ~49 links
- **Employee sidebar:** ~26 links (admin sections hidden via RBAC client guards)

## Correct API Endpoints (from READMEs)

**See full reference: `C:\emptesting\EMPCLOUD_API_REFERENCE.md` (1,679 lines)**
**See path corrections: `C:\emptesting\CORRECT_API_PATHS.md` (945 lines)**

### EMP Cloud Core API (test-empcloud-api.empcloud.com)
```
# Auth
POST   /api/v1/auth/login
POST   /api/v1/auth/register
POST   /api/v1/auth/sso/validate

# Users & Org
GET    /api/v1/users
GET    /api/v1/users/:id
PUT    /api/v1/users/:id
GET    /api/v1/employees/:id/profile
GET    /api/v1/organizations/me
GET    /api/v1/organizations/me/departments
GET    /api/v1/organizations/me/locations
GET    /api/v1/users/org-chart

# Attendance
POST   /api/v1/attendance/check-in
POST   /api/v1/attendance/check-out
GET    /api/v1/attendance/records
GET    /api/v1/attendance/shifts

# Leave
GET    /api/v1/leave/balances
GET    /api/v1/leave/types
POST   /api/v1/leave/applications
PUT    /api/v1/leave/applications/:id/approve
PUT    /api/v1/leave/applications/:id/reject
GET    /api/v1/leave/policies
GET    /api/v1/leave/comp-off

# Content
GET    /api/v1/announcements
GET    /api/v1/documents
GET    /api/v1/events
GET    /api/v1/surveys
GET    /api/v1/policies
POST   /api/v1/policies/:id/acknowledge

# Engagement
GET    /api/v1/feedback
GET    /api/v1/forum/posts
GET    /api/v1/forum/categories
GET    /api/v1/helpdesk/tickets
GET    /api/v1/wellness
POST   /api/v1/wellness/check-in

# Assets & Positions
GET    /api/v1/assets
GET    /api/v1/positions
GET    /api/v1/notifications
GET    /api/v1/audit
GET    /api/v1/modules
GET    /api/v1/subscriptions

# Admin
GET    /api/v1/admin/organizations
GET    /api/v1/admin/health
GET    /api/v1/admin/data-sanity
```

### Module APIs (each on its own subdomain)
```
# Payroll (testpayroll-api.empcloud.com)
POST /api/v1/payroll              — Run payroll
GET  /api/v1/payroll/:id/payslips — Get payslips
GET  /api/v1/salary-structures/employee/:empId
GET  /api/v1/self-service/payslips
GET  /api/v1/self-service/tax/declarations

# Recruit (test-recruit-api.empcloud.com)
POST /api/v1/auth/sso             — SSO only
GET  /api/v1/jobs
POST /api/v1/jobs/:id/applications
GET  /api/v1/interviews
POST /api/v1/ai/score-resume

# Performance (test-performance-api.empcloud.com)
GET  /api/v1/review-cycles
GET  /api/v1/goals
GET  /api/v1/goals/:id/key-results
GET  /api/v1/nine-box
GET  /api/v1/pips
GET  /api/v1/one-on-ones
GET  /api/v1/competency-frameworks

# Rewards (test-rewards-api.empcloud.com)
GET  /api/v1/kudos
POST /api/v1/kudos
GET  /api/v1/points/balance
GET  /api/v1/leaderboard
GET  /api/v1/badges

# Exit (test-exit-api.empcloud.com)
POST /api/v1/exits
GET  /api/v1/clearance/:exitId
POST /api/v1/fnf/:exitId/calculate
GET  /api/v1/exit-interviews

# LMS (testlms-api.empcloud.com)
GET  /api/v1/courses
POST /api/v1/enrollments
GET  /api/v1/certifications
GET  /api/v1/learning-paths

# Project (test-project-api.empcloud.com) — NOTE: /v1/ not /api/v1/
GET  /v1/projects
POST /v1/tasks
GET  /v1/time-entries
```

## Testing Approach
- Use **API-only scripts** for recurring/cron tests (no Selenium crashes)
- For Selenium: **restart driver every 3-5 tests** to avoid Windows ChromeDriver crashes
- Chrome location: `C:\Program Files (x86)\Google\Chrome\Application\chrome.exe`
- All test scripts stored in `C:\emptesting\`
- Screenshots in `C:\Users\Admin\screenshots\`

## Special Pages

| Page | URL | Access |
|------|-----|--------|
| Super Admin Dashboard | /admin/super | Super Admin only |
| AI Configuration | /admin/ai-config | Super Admin only |
| Log Dashboard | /admin/logs | Super Admin only |
| Swagger API Docs | /api/docs | Public |
| AI Chatbot | Purple bubble (bottom-right) | All users |

## Module Subdomains (SSO Only)

| Module | Frontend | API |
|--------|----------|-----|
| Payroll | https://testpayroll.empcloud.com | https://testpayroll-api.empcloud.com |
| Recruit | https://test-recruit.empcloud.com | https://test-recruit-api.empcloud.com |
| Performance | https://test-performance.empcloud.com | https://test-performance-api.empcloud.com |
| Rewards | https://test-rewards.empcloud.com | https://test-rewards-api.empcloud.com |
| Exit | https://test-exit.empcloud.com | https://test-exit-api.empcloud.com |
| LMS | https://testlms.empcloud.com | https://testlms-api.empcloud.com |
| Projects | https://test-project.empcloud.com | https://test-project-api.empcloud.com |
| Monitor | https://test-empmonitor.empcloud.com | https://test-empmonitor-api.empcloud.com |

---

## Human Testing Personas

Test like REAL humans, not bots. Each persona has their own brain and daily workflow.

### Persona 1: Ananya — HR Manager (Org Admin)
**Login:** ananya@technova.in / Welcome@123
**Daily routine to test:**
1. Check dashboard — who's absent today, pending approvals, upcoming events
2. Review attendance — present vs absent at a glance, filter by date/department, who's late
3. Approve/reject 3 pending leave requests — find them, see details, one-click approve
4. Onboard new employee Rahul Sharma — fill all fields (name, email, phone, department, designation, DOJ, manager), submit, verify in list
5. Assign laptop to Rahul — go to Assets, create asset, assign to employee
6. Upload Rahul's offer letter — go to Documents, upload PDF, select employee/category
7. Create company event (all-hands meeting) — title, date, location, description
8. Create quarterly survey — title, questions, publish, check employee can see it
9. Check org chart — verify hierarchy, click names
10. Post on forum — team building event announcement
11. Check reports — headcount, attendance summary, leave utilization
12. Check billing — plan, cost, modules subscribed
13. Update company address in Settings
14. Check audit log — who did what, when
15. Invite new user — send invite email

**Think about what's missing:**
- Bulk leave approval?
- Export employee data to Excel?
- Notification when someone applies for leave?
- Automated leave policies?
- Probation period tracking?
- Offer letter generation?
- Training/certification tracking?

### Persona 2: Priya — Employee (Software Engineer)
**Login:** priya@technova.in / Welcome@123
**Daily routine to test:**
1. Login & check dashboard — personalized for YOU (your name, leave balance, pending items)
2. Clock In for the day
3. Check profile — all tabs (Personal, Job, Education, Experience, Addresses, Documents)
4. Edit phone number or emergency contact
5. Apply for sick leave — next Tuesday, "Doctor's appointment", check it's pending
6. Check attendance history — this month's records, calendar view
7. Raise helpdesk ticket — "Laptop keyboard sticking", Priority: High
8. Check payslip via SSO to Payroll module — salary breakdown, download PDF
9. Fill active survey
10. Daily wellness check-in — mood, energy, sleep, exercise
11. Check assigned assets — laptop, monitor
12. Read and acknowledge company policies
13. Check upcoming events, RSVP
14. Submit anonymous feedback about cafeteria
15. Post in community forum — "Best coffee spots near office?"
16. Submit whistleblowing report anonymously, track it
17. Check notifications bell — new items, mark as read
18. Try AI chatbot — "What is my leave balance?"
19. Clock Out — verify correct hours recorded
20. Resize browser to mobile (375px) — does it work on phone?

**Think about what's frustrating:**
- Too many clicks for simple things?
- Confusing navigation?
- Slow page loads?
- Dead sidebar links?
- Cryptic error messages?
- Missing features an employee would expect?

### Persona 3: Vikram — Platform Super Admin
**Login:** admin@empcloud.com / SuperAdmin@2026
**Daily routine to test:**
1. Login to Super Admin dashboard — org count, total users, revenue, system health
2. Check all organizations — TechNova, GlobalTech details, user counts, subscriptions
3. Monitor system health — /admin/logs, error rates, slow queries, auth events
4. AI Configuration — providers (Claude, OpenAI, Gemini), API keys (masked), enable/disable
5. Module management — available modules, subscriber counts, enable/disable globally
6. Revenue analytics — MRR/ARR, per-org billing, overdue payments
7. Audit trail — who did what, filter by action/user/date
8. User management across orgs — search user, deactivate, password reset
9. Subscription metrics — used seats vs allowed, upgrade/downgrade org plans
10. Platform settings — email config, timezone, security, password policy
11. Check each external module's health via SSO
12. Cross-org data isolation — verify org separation
13. New org onboarding flow — can you create org from admin panel?

**Think about what's missing for platform admin:**
- Real-time active users count?
- Alerting for system issues?
- Broadcast maintenance message to all orgs?
- Impersonate org admin for debugging?
- API usage per org?
- Export platform analytics?
- Email template management?
- Changelog/version info?

---

## Business Logic Edge Cases to Test

### Leave Management
- Apply leave for past dates — should be rejected?
- Apply leave spanning weekends — are weekends counted?
- Apply leave exceeding balance — should get "insufficient balance"
- Apply leave with end_date before start_date — rejected?
- Apply half-day leave (0.5 days)
- Apply leave on public holiday — rejected or warned?
- Overlapping leave dates — rejected?
- Cancel approved leave — balance restored?
- Leave for terminated employee — rejected?
- Negative leave balance — prevented?
- Carry-forward logic at year end

### Attendance
- Double clock-in — second rejected?
- Clock-out without clock-in — rejected?
- Midnight crossing (11:59 PM → 12:01 AM) — hours correct?
- Late arrival flagging
- Attendance on holiday
- Attendance for someone on leave — shows "On Leave"?
- Night shift (10 PM - 6 AM) creation
- Overlapping shift assignment

### Employee Data
- Duplicate email — rejected?
- Duplicate emp_code — rejected?
- Future date_of_joining — allowed?
- date_of_exit before date_of_joining — rejected?
- Employee under 18 (DOB check)
- Self-manager (reporting_manager_id = own ID) — rejected?
- Circular reporting chain (A→B→A) — rejected?
- Deactivate a manager — what happens to reportees?

### Events
- end_date before start_date — rejected?
- Past event creation — allowed?
- RSVP to past event — rejected?
- RSVP capacity limits
- Cancel RSVP — attendee count decreases?

### Surveys
- Double response — rejected?
- Response after end_date — rejected?
- Publish survey with no questions — rejected?

### Assets
- Same asset assigned to two employees — rejected?
- warranty_expiry before purchase_date — rejected?

### Documents
- Upload > max file size — error?
- Upload .exe file — rejected?
- Access another employee's private document — denied?

### Forum
- Edit/delete another user's post — denied?
- Post with empty content — rejected?

---

## Bug Report Style

Write bug titles like a HUMAN, not a robot:
- GOOD: "Can't apply for leave — dropdown shows no options"
- GOOD: "New employee not showing in list after adding"
- GOOD: "Dashboard shows $0 revenue despite active subscriptions"
- BAD: "[FUNCTIONAL] POST /api/v1/leave returns 400"
- BAD: "[E2E] XSS payload stored at /announcements"

---

## Project Status

- **Total issues filed:** 389+
- **Test scripts:** 63+ in C:\emptesting\
- **Screenshots:** 1200+ in C:\Users\Admin\screenshots\
- **Cron retest script:** C:\emptesting\cron_retest.py (API-only, 45s, crash-proof)
