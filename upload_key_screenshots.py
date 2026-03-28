#!/usr/bin/env python3
"""Upload key screenshots (dashboards + notable pages) to GitHub."""
import os, base64, requests, time, glob

GH_TOKEN = "$GITHUB_TOKEN"
GH_REPO = "EmpCloud/EmpCloud"
HEADERS = {"Authorization": f"token {GH_TOKEN}", "Accept": "application/vnd.github.v3+json"}
SSDIR = r"C:\emptesting\screenshots\admin_all_modules"

# Upload key screenshots - dashboards, modules page, login, and notable failures
PATTERNS = [
    "01_login_success_20260328_064549.png",
    "02_modules_page_*.png",
    "Payroll_Dashboard_*.png",
    "Payroll_My_Payslips_20260328_064625.png",
    "Payroll_My_Tax_20260328_064651.png",
    "Payroll_My_Salary_20260328_064635.png",
    "Payroll_Payroll_Reports_20260328_064733.png",
    "Recruitment_Dashboard_*.png",
    "Recruitment_Job_Postings_20260328_064828.png",
    "Recruitment_Candidates_20260328_064845.png",
    "Recruitment_Settings_20260328_064922.png",
    "Performance_Dashboard_*.png",
    "Performance_Review_Cycles_*.png",
    "Performance_Analytics_*.png",
    "Rewards_Dashboard_*.png",
    "Rewards_Kudos_*.png",
    "Rewards_Team_Challenges_20260328_065219.png",
    "Exit_Management_Dashboard_*.png",
    "Exit_Management_Clearance_*.png",
    "Exit_Management_FnF_*.png",
    "Exit_Management_Analytics_*.png",
    "LMS_Dashboard_*.png",
    "LMS_Analytics_*.png",
    "LMS_My_Learning_*.png",
    "Projects_Dashboard_*.png",
    "sso_*.png",
]

uploaded = 0
for pattern in PATTERNS:
    matches = glob.glob(os.path.join(SSDIR, pattern))
    for filepath in matches[:1]:  # Only first match per pattern
        fname = os.path.basename(filepath)
        try:
            with open(filepath, "rb") as f:
                content = base64.b64encode(f.read()).decode()
            path = f"test-screenshots/admin-modules-sso/{fname}"
            url = f"https://api.github.com/repos/{GH_REPO}/contents/{path}"
            r = requests.get(url, headers=HEADERS, timeout=10)
            data = {"message": f"Add screenshot {fname}", "content": content}
            if r.status_code == 200:
                data["sha"] = r.json().get("sha")
            r = requests.put(url, headers=HEADERS, json=data, timeout=30)
            if r.status_code in (200, 201):
                uploaded += 1
                print(f"  Uploaded: {fname}")
            else:
                print(f"  FAILED ({r.status_code}): {fname}")
            time.sleep(1)
        except Exception as e:
            print(f"  Error: {fname}: {e}")

print(f"\nUploaded {uploaded} screenshots to GitHub.")
