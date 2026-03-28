# EMP Cloud E2E Test Suite

Comprehensive end-to-end testing suite for the [EMP Cloud HRMS Platform](https://github.com/EmpCloud/EmpCloud).

## Quick Start

```bash
# Set GitHub token as environment variable
export GITHUB_TOKEN=your_github_pat_here

# Install Python dependencies
pip install requests selenium webdriver-manager

# Install Playwright
npm install
npx playwright install chromium

# Run Playwright E2E tests
npx playwright test e2e/billing-tests.spec.ts
npx playwright test e2e/project-module-tests.spec.ts
npx playwright test e2e/project-deep-functional.spec.ts

# Run API-only retest (45 seconds, no browser)
python cron_retest.py
```

## Structure

```
├── CLAUDE.md                        # Project instructions & rules
├── EmpCloud_E2E_Test_Plan.md        # Master test plan (150+ test cases)
├── EmpCloud_Bug_Report.md           # Initial security bug report
├── EMPCLOUD_API_REFERENCE.md        # Full API reference (1,679 lines)
├── CORRECT_API_PATHS.md             # Wrong → correct API path mapping
├── KNOWLEDGE_BASE.md                # 626 endpoints mapped across all modules
├── INTELLIGENCE.md                  # Bug patterns, programmer behavior analysis
├── PROGRAMMER_PROFILE.md            # Developer response patterns (2,979 comments)
├── BUSINESS_RULES.md                # Business rules checklist (~200 rules)
├── BUSINESS_RULES_V2.md             # Advanced rules (~150 rules)
├── BUSINESS_RULES_V3.md             # Deep compliance rules (~680 rules)
│
├── e2e/                             # Playwright E2E tests
│   ├── billing-tests.spec.ts        # Billing module (16 tests, all pass)
│   ├── project-module-tests.spec.ts # Project module SSO & basics (30 tests)
│   ├── project-deep-functional.spec.ts # Deep Project module testing (28 tests)
│   └── screenshots/                 # Test screenshots (gitignored)
│
├── agents/                          # Human persona test definitions
│   ├── 01_ananya_hr_admin.md
│   ├── 02_priya_employee.md
│   ├── 03_vikram_superadmin.md
│   ├── 04_aditya_newjoiner.md
│   ├── 05_ravi_manager.md
│   ├── 06_meera_finance.md
│   ├── 07_cross_module_dataflow.md
│   ├── 08_business_logic_edge_cases.md
│   └── 09_validation_deep.md
│
├── Agent_Test_Suites/               # Module-specific test suites
│   ├── 01_Core_HR_Tests.md
│   ├── 02_Payroll_Tests.md
│   ├── 03_Recruit_Tests.md
│   ├── 04_Performance_Tests.md
│   ├── 05_Rewards_Tests.md
│   ├── 06_Exit_Tests.md
│   ├── 07_LMS_Tests.md
│   └── 08_Cross_Module_Integrations.md
│
├── fresh/                           # Latest round of API tests
│   ├── test_hr_admin.py
│   ├── test_employee_priya.py
│   ├── test_superadmin.py
│   ├── test_billing.py
│   ├── test_rbac_all.py
│   └── ...
│
├── simulation/                      # 30-day org simulation
│   ├── simulate_days_*.py
│   ├── test_modules_real_sso.py
│   └── readmes/                     # All module READMEs
│
├── cron_retest.py                   # API-only retest (45s, crash-proof)
├── playwright.config.ts             # Playwright configuration
└── package.json                     # Node dependencies (Playwright)
```

## Test Environment

| Item | Value |
|------|-------|
| Core URL | https://test-empcloud.empcloud.com |
| Core API | https://test-empcloud.empcloud.com/api/v1 |
| Issues Repo | https://github.com/EmpCloud/EmpCloud |

## Test Credentials

| Role | Email | Password |
|------|-------|----------|
| Super Admin | admin@empcloud.com | SuperAdmin@123 |
| Org Admin | ananya@technova.in | Welcome@123 |
| Employee | priya@technova.in | Welcome@123 |
| Other Org | john@globaltech.com | Welcome@123 |

## Module Subdomains (SSO Only)

| Module | Frontend | API |
|--------|----------|-----|
| Payroll | testpayroll.empcloud.com | testpayroll-api.empcloud.com |
| Recruit | test-recruit.empcloud.com | test-recruit-api.empcloud.com |
| Performance | test-performance.empcloud.com | test-performance-api.empcloud.com |
| Rewards | test-rewards.empcloud.com | test-rewards-api.empcloud.com |
| Exit | test-exit.empcloud.com | test-exit-api.empcloud.com |
| LMS | testlms.empcloud.com | testlms-api.empcloud.com |
| Projects | test-project.empcloud.com | test-project-api.empcloud.com |
| Monitor | test-empmonitor.empcloud.com | test-empmonitor-api.empcloud.com |

## SSO Authentication

All external modules require SSO from EMP Cloud core:

```python
# 1. Login at core
resp = requests.post('https://test-empcloud.empcloud.com/api/v1/auth/login', json={
    'email': 'ananya@technova.in', 'password': 'Welcome@123'
})
token = resp.json()['data']['tokens']['access_token']

# 2. Navigate to module with token (15-min expiry)
driver.get(f'https://testpayroll.empcloud.com?sso_token={token}')
```

## Testing Approach

- **Playwright** for all E2E, functional, and workflow tests (no Selenium)
- **Python API scripts** for recurring/cron tests (no browser needed)
- **Human personas** — test like real HR managers, employees, and admins
- **1,030+ business rules** across Indian labor law compliance, payroll, leave, attendance

## Current Status (2026-03-30)

- **1,212+ issues filed** on EmpCloud/EmpCloud
- **626 API endpoints mapped** across all modules
- **63+ test scripts** (Python + Playwright)
- **3 Playwright E2E specs** covering billing and project modules
- **9 human personas** defined
- **10 modules** tested via SSO

### Known Blockers
- **Project module severely broken** — cannot create projects, tasks, or sprints (issues #1190-#1212)
- Multi-persona project testing blocked until programmer fixes critical bugs

## Token Setup

Set `GITHUB_TOKEN` environment variable before running scripts:

```bash
export GITHUB_TOKEN=your_pat_here
```

Scripts read from this variable or from `.env` file (gitignored).
