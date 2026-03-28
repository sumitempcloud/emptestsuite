"""File remaining billing bugs found during deep testing."""
import sys
import requests
import time
import json
import os
import base64
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

GITHUB_PAT = "$GITHUB_TOKEN"
GITHUB_REPO = "EmpCloud/EmpCloud"
GITHUB_HEADERS = {"Authorization": f"token {GITHUB_PAT}", "Accept": "application/vnd.github.v3+json"}
SCREENSHOT_DIR = r"C:\Users\Admin\screenshots\billing_deep"
BASE_URL = "https://test-empcloud.empcloud.com"


def upload_ss(filepath):
    if not filepath or not os.path.exists(filepath):
        return None
    fname = os.path.basename(filepath)
    with open(filepath, "rb") as f:
        content = base64.b64encode(f.read()).decode()
    payload = {"message": f"Upload billing screenshot: {fname}", "content": content, "branch": "main"}
    r = requests.put(
        f"https://api.github.com/repos/{GITHUB_REPO}/contents/screenshots/billing_deep/{fname}",
        json=payload, headers=GITHUB_HEADERS, timeout=30
    )
    time.sleep(2)
    if r.status_code in [200, 201]:
        url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/screenshots/billing_deep/{fname}"
        print(f"  Uploaded: {url}")
        return url
    print(f"  Upload failed: {r.status_code}")
    return None


def file_bug(title, body, severity, ss_path=None):
    label_map = {"critical": "bug-critical", "high": "bug-high", "medium": "bug", "low": "bug-low"}
    labels = [label_map.get(severity, "bug"), "verified-bug", "billing", "e2e-test"]
    full_body = (
        f"**Severity:** {severity.upper()}\n"
        f"**Module:** Billing\n"
        f"**Found by:** Automated Billing Deep Test\n"
        f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        f"**Base URL:** {BASE_URL}\n\n"
        f"{body}"
    )
    if ss_path:
        img_url = upload_ss(ss_path)
        if img_url:
            full_body += f"\n\n**Screenshot:**\n![screenshot]({img_url})"

    time.sleep(5)
    payload = {"title": f"[Billing] {title}", "body": full_body, "labels": labels}
    r = requests.post(
        f"https://api.github.com/repos/{GITHUB_REPO}/issues",
        json=payload, headers=GITHUB_HEADERS, timeout=15
    )
    if r.status_code == 201:
        issue = r.json()
        print(f"FILED #{issue['number']}: {title} -> {issue['html_url']}")
        return issue["html_url"]
    else:
        print(f"FAILED to file: {r.status_code} {r.text[:200]}")
        return None


# Check issue #194 first
print("Checking existing issue #194...")
r = requests.get(f"https://api.github.com/repos/{GITHUB_REPO}/issues/194",
                  headers=GITHUB_HEADERS, timeout=15)
if r.status_code == 200:
    i = r.json()
    print(f"  #{i['number']}: {i['title']} (state: {i['state']})")
    body_preview = (i.get("body") or "")[:300]
    print(f"  Body: {body_preview}")
time.sleep(3)


# Bug 1: Billing tabs do not switch content
print("\n--- Bug 1: Tabs don't switch ---")
file_bug(
    "Billing tabs (Invoices, Payments, Overview) do not switch content - all show subscriptions list",
    "**URL:** https://test-empcloud.empcloud.com/billing\n\n"
    "**Steps to reproduce:**\n"
    "1. Login as Org Admin (ananya@technova.in)\n"
    "2. Navigate to /billing\n"
    "3. The Subscriptions tab shows the subscription list correctly\n"
    "4. Click the **Invoices** tab\n"
    "5. Click the **Payments** tab\n"
    "6. Click the **Overview** tab\n\n"
    "**Expected:** Each tab should show different content:\n"
    "- **Subscriptions:** Module subscription list (currently works)\n"
    "- **Invoices:** Invoice list with dates, amounts, status, PDF download\n"
    "- **Payments:** Payment history, payment methods, add method option\n"
    "- **Overview:** Total spend, monthly trend chart, module-wise cost breakdown\n\n"
    "**Actual:** All 4 tabs display identical content - the subscription list. "
    "Automated text comparison confirms the page content is exactly the same "
    "(2048 characters) regardless of which tab is clicked. The tab buttons appear "
    "clickable and visually highlight, but no content switch occurs.\n\n"
    "**Impact:** Users cannot view invoices, payments, or billing overview. "
    "Only the subscription list is accessible through the billing page.\n\n"
    "**Note:** Previously reported in #194. Re-verified and still broken.",
    "high",
    os.path.join(SCREENSHOT_DIR, "010342_invoices_tab_clicked.png")
)


# Bug 2: Billing sub-routes redirect to root
print("\n--- Bug 2: Sub-routes redirect ---")
file_bug(
    "Billing sub-routes (/billing/subscriptions, /invoices, /payments, /overview) redirect to root",
    "**Steps to reproduce:**\n"
    "1. Login as Org Admin\n"
    "2. Navigate directly to any billing sub-route:\n\n"
    "| Route | Result |\n"
    "|-------|--------|\n"
    "| /billing/subscriptions | Redirects to / |\n"
    "| /billing/invoices | Redirects to / |\n"
    "| /billing/payments | Redirects to / |\n"
    "| /billing/overview | Redirects to / |\n"
    "| /billing | Works correctly |\n\n"
    "**Expected:** Each sub-route loads the billing page with the "
    "corresponding tab active (deep-linking support).\n\n"
    "**Actual:** All sub-routes redirect to the root URL. Only /billing "
    "(without sub-path) loads correctly.\n\n"
    "**Impact:** Cannot bookmark or share direct links to billing sections. "
    "Browser back/forward navigation between billing tabs is broken.",
    "medium",
    os.path.join(SCREENSHOT_DIR, "010008_billing_route_subscriptions.png")
)


# Bug 3: Super Admin /admin/billing blank page
print("\n--- Bug 3: Admin billing blank ---")
file_bug(
    "Super Admin /admin/billing page loads with empty content area",
    "**URL:** https://test-empcloud.empcloud.com/admin/billing\n\n"
    "**Steps to reproduce:**\n"
    "1. Login as Super Admin (admin@empcloud.com)\n"
    "2. Navigate to /admin/billing\n\n"
    "**Expected:** Admin billing dashboard with revenue overview or redirect "
    "to /admin/revenue.\n\n"
    "**Actual:** Page loads with sidebar navigation visible but the main "
    "content area is completely blank - no billing data, no error message, "
    "just an empty white area.\n\n"
    "**Workaround:** The sidebar has separate 'Revenue' and 'Subscriptions' "
    "links that work correctly:\n"
    "- /admin/revenue - Shows MRR (Rs 7.14 Cr), ARR (Rs 85.68 Cr), revenue "
    "by module, trend chart, top customers\n"
    "- /admin/subscriptions - Shows seat metrics, tier distribution, cycle "
    "distribution\n\n"
    "The /admin/billing route appears to be unimplemented or broken.",
    "low",
    os.path.join(SCREENSHOT_DIR, "010104_superadmin_billing__admin_billing.png")
)


# Bug 4: Platform-wide 0% seat utilization
print("\n--- Bug 4: 0% seat utilization ---")
file_bug(
    "Platform-wide 0% seat utilization despite 215 active users across all orgs",
    "**Endpoints affected:**\n"
    "- GET /api/v1/admin/subscriptions (Super Admin)\n"
    "- GET /api/v1/subscriptions/billing-summary (Org Admin)\n"
    "- Super Admin UI: /admin/subscriptions\n\n"
    "**Data observed (Super Admin Subscription Metrics):**\n"
    "- Total Seats: 1,298\n"
    "- Used Seats: 0\n"
    "- Seat Utilization: 0%\n"
    "- Active Users: 215 (10 inactive)\n\n"
    "**Per-tier breakdown (all 0%):**\n"
    "| Tier | Used | Total | Utilization |\n"
    "|------|------|-------|-------------|\n"
    "| Basic | 0 | 1,186 | 0% |\n"
    "| Professional | 0 | 100 | 0% |\n"
    "| Enterprise | 0 | 12 | 0% |\n\n"
    "**TechNova org specifically:**\n"
    "- 20 active employees\n"
    "- 10 module subscriptions\n"
    "- All modules show 0 used seats (e.g., 0/10, 0/12, 0/106)\n\n"
    "**Expected:** used_seats should reflect active users assigned to each "
    "module subscription. With 215 active users, utilization should be non-zero.\n\n"
    "**Actual:** Every subscription across all organizations shows used_seats=0.\n\n"
    "**Impact:** Organizations cannot track how many purchased seats are "
    "actually in use. Seat-based cost optimization is impossible.",
    "high",
    os.path.join(SCREENSHOT_DIR, "010413_superadmin_subscriptions_page.png")
)


print("\n\nAll remaining bugs filed.")
