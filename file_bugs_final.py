import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import requests
import time
from datetime import datetime

PAT = "$GITHUB_TOKEN"
h = {"Authorization": f"token {PAT}", "Accept": "application/vnd.github.v3+json"}
api = "https://api.github.com/repos/EmpCloud/EmpCloud/issues"

bugs = [
    {
        "title": "[Projects] Module stuck on landing page - no login or app access for any user",
        "body": (
            "## Bug Report (Automated E2E Test)\n\n"
            "**Module:** Project Management\n"
            "**Severity:** CRITICAL\n"
            "**URL:** https://test-project.empcloud.com\n\n"
            "### Description\n"
            "The Project Management module at https://test-project.empcloud.com does not load the actual application. "
            "Instead, it displays a static EmpMonitor marketing/landing page with the text "
            "'Empower Your Team with Advanced Project Management in EmpMonitor' and a "
            "'Streamline Your Projects Now' button. No login form is presented, and no project management "
            "features are accessible.\n\n"
            "Additionally, navigating to /tasks returns a 404 error page.\n\n"
            "This affects both Admin and Employee users -- neither role can access the module.\n\n"
            "### Steps to Reproduce\n"
            "1. Navigate to https://test-project.empcloud.com\n"
            "2. Observe: Landing page displayed instead of login/dashboard\n"
            "3. No login form, no sidebar, no project features accessible\n"
            "4. /tasks path returns 404\n\n"
            "### Expected Behavior\n"
            "- Login page or SSO redirect should appear\n"
            "- After authentication, project dashboard with projects list, time tracking, and task management should load\n\n"
            "---\n*Filed by automated E2E test suite*"
        ),
        "labels": ["bug", "e2e-test", "projects", "severity:critical"],
    },
    {
        "title": "[Projects] Task management page returns 404 Not Found",
        "body": (
            "## Bug Report (Automated E2E Test)\n\n"
            "**Module:** Project Management\n"
            "**Severity:** HIGH\n"
            "**URL:** https://test-project.empcloud.com/tasks\n\n"
            "### Description\n"
            "Navigating to the tasks page on the Project Management module returns a 404 error page "
            "with the message 'Uh oh! Looks like you got lost. Go back to the homepage!'\n\n"
            "### Steps to Reproduce\n"
            "1. Navigate to https://test-project.empcloud.com\n"
            "2. Try to access /tasks or task management via sidebar\n"
            "3. 404 page is displayed\n\n"
            "### Expected Behavior\n"
            "Task management page should load showing tasks, kanban board, or task list.\n\n"
            "---\n*Filed by automated E2E test suite*"
        ),
        "labels": ["bug", "e2e-test", "projects", "severity:high"],
    },
    {
        "title": "[Exit] Dashboard statistics cards not rendering on Exit Management dashboard",
        "body": (
            "## Bug Report (Automated E2E Test)\n\n"
            "**Module:** Exit Management\n"
            "**Severity:** MEDIUM\n"
            "**URL:** https://test-exit.empcloud.com/dashboard\n\n"
            "### Description\n"
            "The Exit Management dashboard at https://test-exit.empcloud.com/dashboard loads and shows "
            "the 'Recent Exits' table and top-level counters (Active Exits: 1, Clearance Pending: 0, "
            "Exit Pending: 0, Completed/Blocked: 0), but no standard dashboard stat card/widget elements "
            "are detected by automated testing. The counters appear as plain text rather than styled cards.\n\n"
            "### Steps to Reproduce\n"
            "1. Login as Org Admin to https://test-exit.empcloud.com\n"
            "2. View the dashboard\n"
            "3. Observe stat counters lack card/widget styling\n\n"
            "### Expected Behavior\n"
            "Dashboard statistics should render as styled cards/widgets.\n\n"
            "---\n*Filed by automated E2E test suite*"
        ),
        "labels": ["bug", "e2e-test", "exit", "severity:medium"],
    },
]

for bug in bugs:
    try:
        r = requests.post(api, json=bug, headers=h, timeout=15)
        if r.status_code == 201:
            print(f"FILED: {bug['title']} -> {r.json()['html_url']}", flush=True)
        else:
            print(f"FAILED ({r.status_code}): {bug['title']}", flush=True)
    except Exception as e:
        print(f"ERROR: {bug['title']} - {e}", flush=True)
    time.sleep(10)
