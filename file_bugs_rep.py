import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import requests
import time
from datetime import datetime

GITHUB_PAT = "$GITHUB_TOKEN"
GITHUB_REPO = "EmpCloud/EmpCloud"
headers = {"Authorization": f"token {GITHUB_PAT}", "Accept": "application/vnd.github.v3+json"}
api = f"https://api.github.com/repos/{GITHUB_REPO}/issues"

bugs = [
    {
        "title": "[Exit] Page error (500/error state) detected on Full & Final Settlement page",
        "module": "exit",
        "severity": "high",
        "description": "After navigating to the F&F Settlement section in the Exit module, the page contains error indicators (500 or error state text). The Full & Final Settlement section loads but displays error content.",
        "url": "https://test-exit.empcloud.com",
    },
    {
        "title": "[Projects] Admin login fails - Org Admin cannot authenticate to Project Management module",
        "module": "projects",
        "severity": "critical",
        "description": "Login as Org Admin (ananya@technova.in) to https://test-project.empcloud.com fails. The login form is submitted but authentication does not succeed. The admin can see dashboard content but login detection fails, suggesting a login flow issue or redirect problem.",
        "url": "https://test-project.empcloud.com",
    },
    {
        "title": "[Projects] Employee login fails - Employee cannot authenticate to Project Management module",
        "module": "projects",
        "severity": "critical",
        "description": "Login as Employee (priya@technova.in) to https://test-project.empcloud.com fails. Employee cannot access assigned projects or timesheet features.",
        "url": "https://test-project.empcloud.com",
    },
]

for bug in bugs:
    body = (
        f"## Bug Report (Automated E2E Test)\n\n"
        f"**Module:** {bug['module'].title()}\n"
        f"**Severity:** {bug['severity'].upper()}\n"
        f"**URL:** {bug['url']}\n"
        f"**Timestamp:** {datetime.now().isoformat()}\n\n"
        f"### Description\n{bug['description']}\n\n"
        f"### Steps to Reproduce\n"
        f"1. Navigate to {bug['url']}\n"
        f"2. Login with the provided credentials\n"
        f"3. Observe the error\n\n"
        f"### Expected Behavior\nPage should load and function correctly without errors.\n\n"
        f"### Screenshot\nScreenshots saved in `C:\\Users\\Admin\\screenshots\\rewards_exit_projects\\`\n\n"
        f"---\n*Filed by automated E2E test suite*"
    )
    payload = {
        "title": bug["title"],
        "body": body,
        "labels": ["bug", "e2e-test", bug["module"], f"severity:{bug['severity']}"],
    }
    try:
        r = requests.post(api, json=payload, headers=headers, timeout=15)
        if r.status_code == 201:
            print(f"FILED: {bug['title']} -> {r.json().get('html_url', '')}", flush=True)
        else:
            print(f"FAILED ({r.status_code}): {bug['title']} - {r.text[:150]}", flush=True)
    except Exception as e:
        print(f"ERROR: {bug['title']} - {e}", flush=True)
    time.sleep(5)
