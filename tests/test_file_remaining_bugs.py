"""
File remaining bugs from marketplace/billing testing.
"""

import sys, os, requests
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

GITHUB_PAT = "os.environ.get('GITHUB_TOKEN', 'YOUR_TOKEN_HERE')"
GITHUB_REPO = "EmpCloud/EmpCloud"
BASE_URL = "https://test-empcloud.empcloud.com"
bugs_filed = []

def file_bug(title, body, severity="medium"):
    label_map = {"critical": "bug-critical", "high": "bug-high", "medium": "bug", "low": "bug-low"}
    labels = [label_map.get(severity, "bug"), "marketplace", "e2e-test"]
    full_body = (f"**Severity:** {severity.upper()}\n**Found by:** Automated E2E Test\n"
                 f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n**URL:** {BASE_URL}\n\n{body}")
    headers = {"Authorization": f"token {GITHUB_PAT}", "Accept": "application/vnd.github.v3+json"}
    payload = {"title": f"[E2E-Marketplace] {title}", "body": full_body, "labels": labels}
    try:
        r = requests.post(f"https://api.github.com/repos/{GITHUB_REPO}/issues",
                          json=payload, headers=headers, timeout=15)
        if r.status_code == 201:
            url = r.json().get("html_url", "")
            num = r.json().get("number", "?")
            print(f"  [FILED] #{num} [{severity.upper()}] {title}")
            print(f"          {url}")
            bugs_filed.append({"num": num, "title": title, "severity": severity, "url": url})
        else:
            print(f"  [FAILED] {r.status_code}: {r.text[:200]}")
    except Exception as e:
        print(f"  [ERROR] {e}")


print("=" * 70)
print("  FILING REMAINING MARKETPLACE & BILLING BUGS")
print("=" * 70)

# Bug 1: Super Admin dashboard blank page
file_bug(
    "Super Admin dashboard (/admin/super) renders blank page",
    "The Super Admin dashboard at `/admin/super` loads but renders a completely blank/empty page. "
    "No content, navigation, statistics, or organization data is displayed.\n\n"
    "The super admin sidebar IS visible with links to:\n"
    "- Customer Dashboard\n"
    "- Organizations\n"
    "- Module Analytics\n"
    "- Revenue\n"
    "- Notifications\n"
    "- AI Configuration\n"
    "- Log Dashboard\n\n"
    "However, the main content area is completely empty.\n\n"
    "**Steps to reproduce:**\n"
    "1. Login as Super Admin (admin@empcloud.com)\n"
    "2. Navigate to `/admin/super`\n"
    "3. Page loads with sidebar but main content area is blank\n\n"
    "**Expected:** Dashboard should show platform overview, organization stats, revenue summary, etc.\n"
    "**Actual:** Blank page in the main content area\n\n"
    "**Screenshot:** `233712_p5_admin_super.png`",
    severity="high"
)

# Bug 2: Module Analytics shows all zeros
file_bug(
    "Super Admin Module Analytics shows all zero metrics despite active subscriptions",
    "The Module Analytics page at `/admin/modules` displays all-zero metrics:\n"
    "- Active Modules: **0**\n"
    "- Total Subscribers: **0**\n"
    "- Total Seats: **0**\n"
    "- Total Module Revenue: **Rs 0**\n\n"
    "The 'Revenue by Module' chart shows 'No revenue data' and 'Subscriber Distribution' shows 'No subscriber data'.\n\n"
    "However, the TechNova org has **10+ active module subscriptions** "
    "(Biometric, Monitor, Exit, Field Force, LMS, Payroll, Performance, Project, Recruit, Rewards) "
    "and an active billing of Rs 1,00,000/month. These metrics should be reflected in the admin analytics.\n\n"
    "**Steps to reproduce:**\n"
    "1. Login as Super Admin\n"
    "2. Navigate to `/admin/modules`\n"
    "3. All metrics show 0 despite organizations having active subscriptions\n\n"
    "**Expected:** Module analytics reflecting actual subscription data\n"
    "**Actual:** All metrics are zero\n\n"
    "**Screenshot:** `233715_p5_admin_modules.png`",
    severity="high"
)

# Bug 3: Subscription Metrics show 0% usage
file_bug(
    "Super Admin Subscription Metrics show 0 Used Seats and 0% Active Users despite active orgs",
    "The Subscription Metrics page at `/admin/subscriptions` shows:\n"
    "- Total Seats: **198**\n"
    "- Used Seats: **0**\n"
    "- Active Users: **0%**\n\n"
    "The 'Plan Tier Distribution' chart shows Basic (66%) and Enterprise (33%), and "
    "'Subscription Status' shows all Active. However, the seat utilization shows zero usage "
    "despite organizations having employees (TechNova has 17 employees, 10 active users).\n\n"
    "**Steps to reproduce:**\n"
    "1. Login as Super Admin\n"
    "2. Navigate to `/admin/subscriptions`\n"
    "3. Observe Used Seats = 0 and Active Users = 0%\n\n"
    "**Expected:** Used Seats and Active Users should reflect actual employee/user counts\n"
    "**Actual:** Zero usage shown despite active employees\n\n"
    "**Screenshot:** `233719_p5_admin_subscriptions.png`",
    severity="medium"
)

# Bug 4: Module pricing not visible
file_bug(
    "Module Marketplace does not display pricing or plan tier information for modules",
    "The Module Marketplace at `/modules` lists 10+ modules but most of them do not display "
    "any pricing information, monthly cost, or plan tier details. Only the Exit Management module "
    "shows a 'Free tier' badge.\n\n"
    "Modules without pricing info:\n"
    "- Biometric Verification & Access Control\n"
    "- Employee Monitoring & Activity Tracking\n"
    "- Field Force Management & GPS Tracking\n"
    "- Learning Management & Training\n"
    "- Payroll Management\n"
    "- Performance Management & Career Development\n"
    "- Project Management & Time Tracking\n"
    "- Recruitment & Talent Acquisition\n"
    "- Rewards & Recognition\n\n"
    "When an admin is deciding whether to subscribe to a module, they need to know the cost "
    "and plan options before clicking Subscribe.\n\n"
    "**Steps to reproduce:**\n"
    "1. Login as Org Admin\n"
    "2. Navigate to `/modules`\n"
    "3. Observe that most module cards only show name, description, and Subscribe/Unsubscribe\n"
    "4. No pricing, tier, or cost information displayed\n\n"
    "**Expected:** Each module should show pricing tiers (Free/Basic/Pro/Enterprise) and costs\n"
    "**Actual:** No pricing information visible for most modules\n\n"
    "**Screenshot:** `232302_marketplace_deep_start.png`",
    severity="medium"
)

# Bug 5: Admin billing redirects
file_bug(
    "Super Admin /admin/billing redirects to homepage instead of admin billing view",
    "When a Super Admin navigates to `/admin/billing`, they are redirected to the homepage (`/`) "
    "instead of seeing an admin-level billing management page.\n\n"
    "Other admin pages work correctly:\n"
    "- `/admin/modules` -> Module Analytics (accessible)\n"
    "- `/admin/subscriptions` -> Subscription Metrics (accessible)\n"
    "- `/admin/billing` -> Redirects to `/` (broken)\n\n"
    "**Steps to reproduce:**\n"
    "1. Login as Super Admin\n"
    "2. Navigate to `/admin/billing`\n"
    "3. Page redirects to homepage\n\n"
    "**Expected:** Admin billing page showing revenue, payment history across organizations\n"
    "**Actual:** Redirect to homepage\n\n"
    "**Screenshot:** `233722_p5_admin_billing.png`",
    severity="medium"
)


print("\n" + "=" * 70)
print("  SUMMARY OF ALL BUGS FILED")
print("=" * 70)
print(f"\n  Total new bugs filed: {len(bugs_filed)}")
for b in bugs_filed:
    print(f"    #{b['num']} [{b['severity'].upper()}] {b['title']}")
    print(f"       {b['url']}")

print("\n  Previously filed bugs:")
print("    #194 [HIGH] Billing page tabs (Invoices, Payments, Overview) do not switch content")
print("    #197 [MEDIUM] No plan upgrade/downgrade option on Billing page subscriptions")

print("\n" + "=" * 70)
