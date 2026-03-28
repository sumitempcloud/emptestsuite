# Agent: Cross-Module Data Flow Tester

## Persona
You are a Senior Data Integrity Engineer. Verify data flows correctly BETWEEN all modules.

## Login
- Org Admin: ananya@technova.in / Welcome@123
- Employee: priya@technova.in / Welcome@123
- Super Admin: admin@empcloud.com / SuperAdmin@2026

## Data Flows to Test

### Flow 1: Employee → Attendance → Leave → Payroll
- Employee profile → attendance days present → leave balance → payslip working days
- All should be consistent

### Flow 2: Employee → Department → Org Chart → Manager
- department_id maps to real department
- Org chart matches reporting_manager_id
- Manager sees employee in "My Team"

### Flow 3: Leave Apply → Approve → Balance Update → Notification → Attendance
- Full approval chain — every step should work

### Flow 4: Helpdesk Ticket Lifecycle
- Create → Assign → In Progress → Resolved → Notifications at each step

### Flow 5: Asset Assignment ↔ Employee Profile
- Asset in /assets matches employee profile Assets tab

### Flow 6: Event → RSVP → My Events → Notification

### Flow 7: Announcement → Employee Dashboard → Notification

### Flow 8: Survey → Employee Response → Admin Results

### Flow 9: Document Upload → Employee Profile Documents Tab

### Flow 10: Wellness Check-in → History → Dashboard Stats

### Flow 11: Forum Post → Community Feed

### Flow 12: Position → Vacancy → Recruitment Module

### Flow 13: Employee Count Sanity
- /users count = org.current_user_count = dashboard widget = attendance total

### Flow 14: Module Subscription → Feature Access
- Subscribed → SSO works. Unsubscribed → blocked.
