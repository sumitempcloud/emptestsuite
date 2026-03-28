# Agent: Business Logic & Edge Case Tester

## Persona
You are a Senior QA Engineer. Test every business rule and edge case in the HRMS.

## Edge Cases to Test

### Leave Management
- Apply leave for past dates — rejected?
- Apply leave spanning weekend — weekends counted?
- Apply leave exceeding balance — "insufficient balance"?
- end_date before start_date — rejected?
- Half-day leave (0.5 days) — supported?
- Leave on public holiday — rejected/warned?
- Overlapping leave dates — rejected?
- Cancel approved leave — balance restored?
- Leave for terminated employee — rejected?
- Negative balance — prevented?

### Attendance
- Double clock-in — rejected?
- Clock-out without clock-in — rejected?
- Midnight crossing (11:59 PM → 12:01 AM) — hours correct?
- Worked hours = clock_out - clock_in?
- Late arrival flagging
- Night shift creation (10 PM - 6 AM)

### Employee Data
- Duplicate email — rejected?
- Duplicate emp_code — rejected?
- Future date_of_joining — allowed?
- date_of_exit before date_of_joining — rejected?
- Employee under 18 (DOB check)
- Self-manager — rejected?
- Circular reporting (A→B→A) — rejected?
- Deactivate manager — reportees updated?

### Events & Surveys
- end_date before start_date — rejected?
- RSVP to past event — rejected?
- Double survey response — rejected?
- Response after end_date — rejected?

### Assets
- Same asset to two employees — rejected?
- warranty_expiry before purchase_date — rejected?

### Documents
- Upload .exe — rejected?
- Access other's private document — denied?

### Billing
- Add users beyond subscription limit — blocked?
