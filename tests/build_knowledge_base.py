#!/usr/bin/env python3
"""
EmpCloud Knowledge Base Builder
Reads all test results, API references, READMEs, and simulation data
to build a comprehensive knowledge base for future automated testing.
"""
import sys
import os
import json
import glob
import re
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

BASE = r"C:\emptesting"

def safe_read_json(path):
    try:
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            return json.load(f)
    except Exception as e:
        print(f"  WARN: Could not read {path}: {e}")
        return None

def safe_read_text(path):
    try:
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            return f.read()
    except Exception as e:
        print(f"  WARN: Could not read {path}: {e}")
        return ""

def main():
    print("=" * 60)
    print("EmpCloud Knowledge Base Builder")
    print("=" * 60)

    # ── Load all source data ──────────────────────────────────
    print("\n[1/6] Loading source data...")

    claude_md = safe_read_text(os.path.join(BASE, "CLAUDE.md"))
    api_ref = safe_read_text(os.path.join(BASE, "EMPCLOUD_API_REFERENCE.md"))
    correct_paths = safe_read_text(os.path.join(BASE, "CORRECT_API_PATHS.md"))
    setup_data = safe_read_json(os.path.join(BASE, "simulation", "setup_data.json"))
    feature_coverage = safe_read_json(os.path.join(BASE, "simulation", "feature_coverage.json"))
    readme_vs_reality = safe_read_json(os.path.join(BASE, "simulation", "readme_vs_reality.json"))
    month_end = safe_read_json(os.path.join(BASE, "simulation", "month_end_report.json"))

    # Load all test result files
    result_files = glob.glob(os.path.join(BASE, "results", "*.json"))
    test_results = {}
    for rf in result_files:
        name = os.path.basename(rf).replace('.json', '')
        data = safe_read_json(rf)
        if data:
            test_results[name] = data
    print(f"  Loaded {len(test_results)} test result files")

    # Load all README files
    readme_files = glob.glob(os.path.join(BASE, "simulation", "readmes", "*.md"))
    readmes = {}
    for rf in readme_files:
        name = os.path.basename(rf).replace('_README.md', '').replace('.md', '')
        readmes[name] = safe_read_text(rf)
    print(f"  Loaded {len(readmes)} module READMEs")

    # ── A. DEFINITIVE API MAP ─────────────────────────────────
    print("\n[2/6] Building Definitive API Map...")

    api_map = {}

    # Module definitions
    modules_config = {
        "core": {
            "name": "EMP Cloud Core",
            "api_base": "https://test-empcloud-api.empcloud.com",
            "prefix": "/api/v1/",
            "auth": "JWT (native)",
            "needs_sso": False,
        },
        "payroll": {
            "name": "EMP Payroll",
            "api_base": "https://testpayroll-api.empcloud.com",
            "prefix": "/api/v1/",
            "auth": "SSO token",
            "needs_sso": True,
        },
        "recruit": {
            "name": "EMP Recruit",
            "api_base": "https://test-recruit-api.empcloud.com",
            "prefix": "/api/v1/",
            "auth": "SSO only",
            "needs_sso": True,
        },
        "performance": {
            "name": "EMP Performance",
            "api_base": "https://test-performance-api.empcloud.com",
            "prefix": "/api/v1/",
            "auth": "SSO only",
            "needs_sso": True,
        },
        "rewards": {
            "name": "EMP Rewards",
            "api_base": "https://test-rewards-api.empcloud.com",
            "prefix": "/api/v1/",
            "auth": "SSO only",
            "needs_sso": True,
        },
        "exit": {
            "name": "EMP Exit",
            "api_base": "https://test-exit-api.empcloud.com",
            "prefix": "/api/v1/",
            "auth": "SSO only",
            "needs_sso": True,
        },
        "lms": {
            "name": "EMP LMS",
            "api_base": "https://testlms-api.empcloud.com",
            "prefix": "/api/v1/",
            "auth": "SSO preferred (also has /login)",
            "needs_sso": True,
        },
        "project": {
            "name": "EMP Project",
            "api_base": "https://test-project-api.empcloud.com",
            "prefix": "/v1/",
            "auth": "Separate",
            "needs_sso": True,
        },
        "monitor": {
            "name": "EMP Monitor",
            "api_base": "https://test-empmonitor-api.empcloud.com",
            "prefix": "N/A",
            "auth": "Separate (Laravel + Node.js)",
            "needs_sso": False,
        },
        "billing": {
            "name": "EMP Billing",
            "api_base": "internal:4001",
            "prefix": "/api/v1/",
            "auth": "JWT (internal)",
            "needs_sso": False,
        },
    }

    # Extract endpoints from feature_coverage
    if feature_coverage and "results" in feature_coverage:
        for entry in feature_coverage["results"]:
            ep = entry.get("endpoint", "")
            method = entry.get("method", "GET")
            status = entry.get("status", 0)
            notes = entry.get("notes", "")
            keys = entry.get("response_keys", [])
            cat = entry.get("category", "Unknown")
            count = entry.get("data_count")

            key = f"core|{method}|{ep}"
            api_map[key] = {
                "module": "core",
                "method": method,
                "path": ep,
                "status_code": status,
                "category": cat,
                "notes": notes,
                "response_keys": keys,
                "data_count": count,
                "admin_works": status in [200, 201, 400, 409] if "working" in str(notes).lower() else False,
                "employee_works": None,  # Not tested separately in coverage
                "needs_sso": False,
            }

    # Extract from readme_vs_reality
    if readme_vs_reality and "modules" in readme_vs_reality:
        for mod_key, mod_data in readme_vs_reality["modules"].items():
            if "endpoint_details" in mod_data:
                for ep_detail in mod_data["endpoint_details"]:
                    method = ep_detail.get("method", "GET")
                    path = ep_detail.get("path", "")
                    status = ep_detail.get("status", 0)
                    verdict = ep_detail.get("verdict", "")
                    tested_url = ep_detail.get("tested_url", "")

                    key = f"{mod_key}|{method}|{path}"
                    if key not in api_map:
                        api_map[key] = {
                            "module": mod_key,
                            "method": method,
                            "path": path,
                            "status_code": status,
                            "category": "",
                            "notes": verdict,
                            "response_keys": [],
                            "data_count": None,
                            "admin_works": verdict in ["working", "working_validation"],
                            "employee_works": None,
                            "needs_sso": modules_config.get(mod_key, {}).get("needs_sso", False),
                            "tested_url": tested_url,
                        }

    print(f"  Total endpoints mapped: {len(api_map)}")

    # Group by module
    endpoints_by_module = {}
    for key, data in api_map.items():
        mod = data["module"]
        if mod not in endpoints_by_module:
            endpoints_by_module[mod] = []
        endpoints_by_module[mod].append(data)

    # ── B. MODULE FEATURE MATRIX ──────────────────────────────
    print("\n[3/6] Building Module Feature Matrix...")

    feature_matrix = {}

    # Core module features from feature_coverage
    core_features = {
        "Auth": {"in_readme": True, "api_exists": True, "ui_works": True, "admin": True, "employee": True},
        "OAuth/OIDC": {"in_readme": True, "api_exists": True, "ui_works": True, "admin": True, "employee": False},
        "Organizations": {"in_readme": True, "api_exists": True, "ui_works": True, "admin": True, "employee": False},
        "Users/Employees": {"in_readme": True, "api_exists": True, "ui_works": True, "admin": True, "employee": True},
        "Attendance": {"in_readme": True, "api_exists": True, "ui_works": True, "admin": True, "employee": True},
        "Leave Management": {"in_readme": True, "api_exists": True, "ui_works": True, "admin": True, "employee": True},
        "Documents": {"in_readme": True, "api_exists": True, "ui_works": True, "admin": True, "employee": True},
        "Announcements": {"in_readme": True, "api_exists": True, "ui_works": True, "admin": True, "employee": True},
        "Policies": {"in_readme": True, "api_exists": True, "ui_works": True, "admin": True, "employee": True},
        "Notifications": {"in_readme": True, "api_exists": True, "ui_works": True, "admin": True, "employee": True},
        "Dashboard": {"in_readme": True, "api_exists": True, "ui_works": True, "admin": True, "employee": True},
        "Helpdesk": {"in_readme": True, "api_exists": True, "ui_works": True, "admin": True, "employee": True},
        "Surveys": {"in_readme": True, "api_exists": True, "ui_works": True, "admin": True, "employee": True},
        "Assets": {"in_readme": True, "api_exists": True, "ui_works": True, "admin": True, "employee": True},
        "Positions": {"in_readme": True, "api_exists": True, "ui_works": True, "admin": True, "employee": False},
        "Forum": {"in_readme": True, "api_exists": True, "ui_works": True, "admin": True, "employee": True},
        "Events": {"in_readme": True, "api_exists": True, "ui_works": True, "admin": True, "employee": True},
        "Wellness": {"in_readme": True, "api_exists": False, "ui_works": False, "admin": False, "employee": False},
        "Feedback": {"in_readme": True, "api_exists": True, "ui_works": True, "admin": True, "employee": True},
        "Whistleblowing": {"in_readme": True, "api_exists": False, "ui_works": False, "admin": False, "employee": False},
        "Custom Fields": {"in_readme": True, "api_exists": False, "ui_works": False, "admin": False, "employee": False},
        "Biometrics": {"in_readme": True, "api_exists": False, "ui_works": False, "admin": False, "employee": False},
        "Manager Dashboard": {"in_readme": True, "api_exists": False, "ui_works": False, "admin": False, "employee": False},
        "Bulk Import": {"in_readme": True, "api_exists": False, "ui_works": False, "admin": False, "employee": False},
        "AI Chatbot": {"in_readme": True, "api_exists": False, "ui_works": True, "admin": True, "employee": True},
        "AI Config": {"in_readme": True, "api_exists": False, "ui_works": True, "admin": True, "employee": False},
        "Audit Log": {"in_readme": True, "api_exists": True, "ui_works": True, "admin": True, "employee": False},
        "Billing": {"in_readme": True, "api_exists": False, "ui_works": True, "admin": True, "employee": False},
        "Org Chart": {"in_readme": True, "api_exists": True, "ui_works": True, "admin": True, "employee": True},
        "Admin Health": {"in_readme": True, "api_exists": True, "ui_works": True, "admin": True, "employee": False},
    }
    feature_matrix["core"] = core_features

    # Payroll features
    feature_matrix["payroll"] = {
        "Auth/Login": {"in_readme": True, "api_exists": True, "ui_works": True, "admin": True, "employee": True},
        "Employee Management": {"in_readme": True, "api_exists": True, "ui_works": True, "admin": True, "employee": False},
        "Payroll Runs": {"in_readme": True, "api_exists": True, "ui_works": True, "admin": True, "employee": False},
        "Payslips": {"in_readme": True, "api_exists": True, "ui_works": True, "admin": True, "employee": True},
        "Salary Structures": {"in_readme": True, "api_exists": True, "ui_works": True, "admin": True, "employee": False},
        "Benefits": {"in_readme": True, "api_exists": True, "ui_works": False, "admin": True, "employee": True},
        "Insurance": {"in_readme": True, "api_exists": True, "ui_works": False, "admin": True, "employee": False},
        "GL Accounting": {"in_readme": True, "api_exists": False, "ui_works": False, "admin": False, "employee": False},
        "Global Payroll": {"in_readme": True, "api_exists": False, "ui_works": False, "admin": False, "employee": False},
        "Earned Wage Access": {"in_readme": True, "api_exists": False, "ui_works": False, "admin": False, "employee": False},
        "Pay Equity": {"in_readme": True, "api_exists": False, "ui_works": False, "admin": False, "employee": False},
        "Compensation Benchmarks": {"in_readme": True, "api_exists": False, "ui_works": False, "admin": False, "employee": False},
        "Self-Service": {"in_readme": True, "api_exists": True, "ui_works": True, "admin": False, "employee": True},
        "Tax Engine": {"in_readme": True, "api_exists": True, "ui_works": True, "admin": True, "employee": True},
        "Loans": {"in_readme": True, "api_exists": False, "ui_works": False, "admin": False, "employee": False},
        "Reimbursements": {"in_readme": True, "api_exists": False, "ui_works": False, "admin": False, "employee": False},
    }

    # Recruit features
    feature_matrix["recruit"] = {
        "SSO Auth": {"in_readme": True, "api_exists": True, "ui_works": True, "admin": True, "employee": False},
        "Job Postings": {"in_readme": True, "api_exists": True, "ui_works": True, "admin": True, "employee": False},
        "Candidates": {"in_readme": True, "api_exists": True, "ui_works": True, "admin": True, "employee": False},
        "Applications/ATS": {"in_readme": True, "api_exists": True, "ui_works": True, "admin": True, "employee": False},
        "Interviews": {"in_readme": True, "api_exists": True, "ui_works": True, "admin": True, "employee": False},
        "Offers": {"in_readme": True, "api_exists": True, "ui_works": True, "admin": True, "employee": False},
        "AI Resume Scoring": {"in_readme": True, "api_exists": True, "ui_works": False, "admin": True, "employee": False},
        "Background Checks": {"in_readme": True, "api_exists": True, "ui_works": False, "admin": True, "employee": False},
        "Pipeline Stages": {"in_readme": True, "api_exists": True, "ui_works": True, "admin": True, "employee": False},
        "Candidate Portal": {"in_readme": True, "api_exists": True, "ui_works": False, "admin": False, "employee": False},
        "Onboarding": {"in_readme": True, "api_exists": True, "ui_works": False, "admin": True, "employee": False},
        "Public Career Page": {"in_readme": True, "api_exists": True, "ui_works": False, "admin": False, "employee": False},
        "Psychometric Assessments": {"in_readme": True, "api_exists": True, "ui_works": False, "admin": True, "employee": False},
    }

    # Performance features
    feature_matrix["performance"] = {
        "SSO Auth": {"in_readme": True, "api_exists": True, "ui_works": True, "admin": True, "employee": False},
        "Review Cycles": {"in_readme": True, "api_exists": True, "ui_works": True, "admin": True, "employee": True},
        "Goals & OKRs": {"in_readme": True, "api_exists": True, "ui_works": True, "admin": True, "employee": True},
        "Goal Alignment": {"in_readme": True, "api_exists": True, "ui_works": False, "admin": True, "employee": False},
        "9-Box Grid": {"in_readme": True, "api_exists": True, "ui_works": True, "admin": True, "employee": False},
        "Succession Planning": {"in_readme": True, "api_exists": True, "ui_works": False, "admin": True, "employee": False},
        "Skills Gap Analysis": {"in_readme": True, "api_exists": True, "ui_works": False, "admin": True, "employee": True},
        "Manager Effectiveness": {"in_readme": True, "api_exists": True, "ui_works": False, "admin": True, "employee": False},
        "AI Review Summaries": {"in_readme": True, "api_exists": True, "ui_works": False, "admin": True, "employee": False},
        "Performance Letters": {"in_readme": True, "api_exists": True, "ui_works": False, "admin": True, "employee": False},
        "Competency Frameworks": {"in_readme": True, "api_exists": True, "ui_works": False, "admin": True, "employee": False},
        "PIPs": {"in_readme": True, "api_exists": True, "ui_works": True, "admin": True, "employee": True},
        "Career Paths": {"in_readme": True, "api_exists": True, "ui_works": False, "admin": True, "employee": True},
        "1-on-1 Meetings": {"in_readme": True, "api_exists": True, "ui_works": False, "admin": True, "employee": True},
        "Continuous Feedback": {"in_readme": True, "api_exists": True, "ui_works": False, "admin": True, "employee": True},
        "Peer Reviews": {"in_readme": True, "api_exists": True, "ui_works": False, "admin": True, "employee": True},
        "Analytics": {"in_readme": True, "api_exists": True, "ui_works": False, "admin": True, "employee": False},
    }

    # Rewards features
    feature_matrix["rewards"] = {
        "Kudos": {"in_readme": True, "api_exists": True, "ui_works": True, "admin": True, "employee": True},
        "Points": {"in_readme": True, "api_exists": True, "ui_works": True, "admin": True, "employee": True},
        "Badges": {"in_readme": True, "api_exists": True, "ui_works": True, "admin": True, "employee": True},
        "Rewards Catalog": {"in_readme": True, "api_exists": True, "ui_works": False, "admin": True, "employee": True},
        "Redemptions": {"in_readme": True, "api_exists": True, "ui_works": False, "admin": True, "employee": True},
        "Nominations": {"in_readme": True, "api_exists": True, "ui_works": False, "admin": True, "employee": True},
        "Leaderboard": {"in_readme": True, "api_exists": True, "ui_works": True, "admin": True, "employee": True},
        "Celebrations": {"in_readme": True, "api_exists": True, "ui_works": True, "admin": True, "employee": True},
        "Team Challenges": {"in_readme": True, "api_exists": True, "ui_works": False, "admin": True, "employee": True},
        "Milestones": {"in_readme": True, "api_exists": True, "ui_works": False, "admin": True, "employee": False},
        "Slack Integration": {"in_readme": True, "api_exists": True, "ui_works": False, "admin": True, "employee": False},
        "Teams Integration": {"in_readme": True, "api_exists": True, "ui_works": False, "admin": True, "employee": False},
        "Push Notifications": {"in_readme": True, "api_exists": True, "ui_works": False, "admin": True, "employee": True},
    }

    # Exit features
    feature_matrix["exit"] = {
        "Exit Requests": {"in_readme": True, "api_exists": True, "ui_works": True, "admin": True, "employee": False},
        "Self-Service Resignation": {"in_readme": True, "api_exists": True, "ui_works": True, "admin": False, "employee": True},
        "Checklist Templates": {"in_readme": True, "api_exists": True, "ui_works": False, "admin": True, "employee": False},
        "Clearance": {"in_readme": True, "api_exists": True, "ui_works": False, "admin": True, "employee": False},
        "Exit Interviews": {"in_readme": True, "api_exists": True, "ui_works": False, "admin": True, "employee": True},
        "F&F Settlement": {"in_readme": True, "api_exists": True, "ui_works": False, "admin": True, "employee": False},
        "Asset Returns": {"in_readme": True, "api_exists": True, "ui_works": False, "admin": True, "employee": False},
        "Knowledge Transfer": {"in_readme": True, "api_exists": True, "ui_works": False, "admin": True, "employee": True},
        "Letters": {"in_readme": True, "api_exists": True, "ui_works": False, "admin": True, "employee": False},
        "Flight Risk / Attrition": {"in_readme": True, "api_exists": True, "ui_works": False, "admin": True, "employee": False},
        "Notice Buyout": {"in_readme": True, "api_exists": True, "ui_works": False, "admin": True, "employee": True},
        "Rehire": {"in_readme": True, "api_exists": True, "ui_works": False, "admin": True, "employee": False},
        "NPS": {"in_readme": True, "api_exists": True, "ui_works": False, "admin": True, "employee": False},
    }

    # LMS features
    feature_matrix["lms"] = {
        "Auth (SSO + Login)": {"in_readme": True, "api_exists": True, "ui_works": True, "admin": True, "employee": True},
        "Courses": {"in_readme": True, "api_exists": True, "ui_works": True, "admin": True, "employee": True},
        "Enrollments": {"in_readme": True, "api_exists": True, "ui_works": True, "admin": True, "employee": True},
        "Quizzes": {"in_readme": True, "api_exists": True, "ui_works": False, "admin": True, "employee": True},
        "Learning Paths": {"in_readme": True, "api_exists": True, "ui_works": False, "admin": True, "employee": True},
        "Certifications": {"in_readme": True, "api_exists": True, "ui_works": False, "admin": True, "employee": True},
        "Compliance": {"in_readme": True, "api_exists": True, "ui_works": False, "admin": True, "employee": True},
        "ILT Sessions": {"in_readme": True, "api_exists": True, "ui_works": False, "admin": True, "employee": True},
        "SCORM": {"in_readme": True, "api_exists": True, "ui_works": False, "admin": True, "employee": True},
        "Gamification": {"in_readme": True, "api_exists": True, "ui_works": False, "admin": True, "employee": True},
        "Discussions": {"in_readme": True, "api_exists": True, "ui_works": False, "admin": True, "employee": True},
        "Analytics": {"in_readme": True, "api_exists": True, "ui_works": False, "admin": True, "employee": False},
        "AI Recommendations": {"in_readme": True, "api_exists": True, "ui_works": False, "admin": True, "employee": True},
        "Video": {"in_readme": True, "api_exists": True, "ui_works": False, "admin": True, "employee": True},
    }

    # ── C. KNOWN WORKING FLOWS ────────────────────────────────
    print("\n[4/6] Building Known Working/Broken Flows...")

    known_working_flows = [
        {
            "name": "Admin Login + Token",
            "steps": [
                "POST /api/v1/auth/login with {email: 'ananya@technova.in', password: 'Welcome@123'}",
                "Response: {success: true, data: {access_token: '...', user: {...}}}",
                "Use access_token in Authorization: Bearer header for subsequent requests"
            ],
            "verified": True,
            "notes": "Works for all user roles. Token expires in 15 minutes."
        },
        {
            "name": "Employee Directory + Profile",
            "steps": [
                "GET /api/v1/users (returns paginated user list with meta)",
                "GET /api/v1/users/:id (individual user details)",
                "GET /api/v1/employees/:id/profile (extended profile)",
                "GET /api/v1/employees/:id/addresses (address list)",
                "GET /api/v1/employees/:id/education (education history)",
                "GET /api/v1/employees/:id/experience (work experience)",
                "GET /api/v1/employees/:id/dependents (dependents list)"
            ],
            "verified": True,
            "notes": "Note: /api/v1/employees (list) returns 404 -- use /api/v1/users instead. Org chart at /api/v1/users/org-chart (NOT /employees/org-chart)."
        },
        {
            "name": "Attendance Check-in/Check-out",
            "steps": [
                "POST /api/v1/attendance/check-in (returns 200 or 409 if already checked in)",
                "GET /api/v1/attendance/records (list with pagination)",
                "GET /api/v1/attendance/dashboard (dashboard data)",
                "POST /api/v1/attendance/check-out (returns 200 or 409 if already checked out)"
            ],
            "verified": True,
            "notes": "409 Conflict is expected when already checked in/out for the day."
        },
        {
            "name": "Leave Application + Approval",
            "steps": [
                "GET /api/v1/leave/types (list leave types with IDs)",
                "GET /api/v1/leave/balances (check available balance)",
                "POST /api/v1/leave/applications {leave_type_id, start_date, end_date, reason}",
                "GET /api/v1/leave/applications (list all applications)",
                "POST /api/v1/leave/applications/:id/approve (admin approves)"
            ],
            "verified": True,
            "notes": "Leave types vary by org. TechNova has Casual, Sick, Earned, Compensatory, Maternity, Paternity."
        },
        {
            "name": "Helpdesk Ticket Lifecycle",
            "steps": [
                "GET /api/v1/helpdesk/categories (list categories)",
                "POST /api/v1/helpdesk/tickets {subject, description, category_id, priority}",
                "GET /api/v1/helpdesk/tickets (list all)",
                "GET /api/v1/helpdesk/tickets/:id (detail)",
                "PUT /api/v1/helpdesk/tickets/:id {status: 'in_progress'} (update status)",
                "PUT /api/v1/helpdesk/tickets/:id {status: 'resolved'} (close ticket)"
            ],
            "verified": True,
            "notes": "80% resolution rate observed in simulation. Knowledge base articles also available."
        },
        {
            "name": "SSO Into External Module (Payroll Example)",
            "steps": [
                "POST /api/v1/auth/login on test-empcloud-api.empcloud.com -> get access_token",
                "Navigate browser to: https://testpayroll.empcloud.com?sso_token=<access_token>",
                "Module reads token from URL and authenticates",
                "For API: capture module session cookie from redirect response"
            ],
            "verified": True,
            "notes": "Token lifetime is 15 minutes. Same pattern for all modules (recruit, performance, rewards, exit, lms, project)."
        },
        {
            "name": "Payroll Self-Service (Employee View)",
            "steps": [
                "SSO into payroll module",
                "GET /api/v1/self-service/payslips (my payslips)",
                "GET /api/v1/self-service/payslips/:id/pdf (download payslip)",
                "GET /api/v1/self-service/salary (my salary)",
                "GET /api/v1/self-service/tax/declarations (my declarations)",
                "GET /api/v1/self-service/tax/form16 (form 16)"
            ],
            "verified": True,
            "notes": "Employee role in payroll module has limited access (most admin endpoints return 403)."
        },
        {
            "name": "Announcement CRUD",
            "steps": [
                "POST /api/v1/announcements {title, content, priority, target_type: 'all'}",
                "GET /api/v1/announcements (list, paginated)",
                "GET /api/v1/announcements/:id (detail)",
                "PUT /api/v1/announcements/:id (update)",
                "POST /api/v1/announcements/:id/read (mark as read)",
                "GET /api/v1/announcements/unread-count (count)"
            ],
            "verified": True,
            "notes": "Admin creates, employees read. Soft delete is by design."
        },
        {
            "name": "Policy + Acknowledgment",
            "steps": [
                "POST /api/v1/policies {title, content, category}",
                "GET /api/v1/policies (list)",
                "GET /api/v1/policies/pending (pending acknowledgments)",
                "POST /api/v1/policies/:id/acknowledge (employee acknowledges)"
            ],
            "verified": True,
            "notes": "23 pending acknowledgments in TechNova as of simulation."
        },
        {
            "name": "Forum Post + Reply",
            "steps": [
                "GET /api/v1/forum/categories (list categories)",
                "POST /api/v1/forum/categories {name, description} (admin creates)",
                "POST /api/v1/forum/posts {title, content, category_id}",
                "GET /api/v1/forum/posts (list with pagination)",
                "GET /api/v1/forum/posts/:id (with replies)",
                "POST /api/v1/forum/posts/:id/replies {content}",
                "POST /api/v1/forum/posts/:id/react {type: 'like'}"
            ],
            "verified": True,
            "notes": "19 posts in TechNova simulation."
        },
        {
            "name": "Survey Creation + Response",
            "steps": [
                "POST /api/v1/surveys {title, description, type, is_anonymous, questions: [...]}",
                "GET /api/v1/surveys (list)",
                "GET /api/v1/surveys/:id (with responses)",
                "POST /api/v1/surveys/:id/respond {answers: [...]}"
            ],
            "verified": True,
            "notes": "20 surveys in TechNova. Supports engagement, pulse, and custom types."
        },
        {
            "name": "Asset Management",
            "steps": [
                "GET /api/v1/assets/categories (list categories)",
                "POST /api/v1/assets {name, asset_tag, category_id, serial_number}",
                "GET /api/v1/assets (list)",
                "POST /api/v1/assets/:id/assign {user_id}",
                "GET /api/v1/assets/my (employee: my assigned assets)"
            ],
            "verified": True,
            "notes": "Asset tracking with categories, serial numbers, warranty tracking."
        },
        {
            "name": "Events CRUD + Registration",
            "steps": [
                "POST /api/v1/events {title, description, event_type, start_date, end_date, location}",
                "GET /api/v1/events (list)",
                "POST /api/v1/events/:id/register (RSVP)"
            ],
            "verified": True,
            "notes": "14 events in TechNova. Calendar endpoint requires date params."
        },
    ]

    # ── D. KNOWN BROKEN FLOWS ──────────────────────────────────
    known_broken_flows = [
        {
            "name": "Payroll Run by Org Admin",
            "broken_step": "POST /api/v1/payroll (create payroll run)",
            "error": "Org admin SSO token maps to 'employee' role in payroll module, returning 403 Forbidden",
            "issue": "#722 - Org admin can't run payroll -- role mapped as 'employee' in payroll module",
            "workaround": "Use payroll's native auth (POST /api/v1/auth/login) with admin credentials if available"
        },
        {
            "name": "Payroll Run for Innovate Solutions",
            "broken_step": "POST /api/v1/payroll for org_id 39",
            "error": "Payroll run fails for Innovate Solutions organization",
            "issue": "#727 - Payroll run fails for Innovate Solutions - March 2026",
            "workaround": "None known -- only TechNova payroll runs have succeeded"
        },
        {
            "name": "SSO Validate Endpoint",
            "broken_step": "POST /api/v1/auth/sso/validate",
            "error": "Returns 404 Not Found",
            "issue": "Endpoint listed in README but not found on API. Modules may use direct sso_token URL param instead.",
            "workaround": "Use sso_token as URL parameter (e.g., ?sso_token=<token>) instead of API validate call"
        },
        {
            "name": "Password Reset",
            "broken_step": "POST /api/v1/auth/password-reset",
            "error": "Returns 404 Not Found",
            "issue": "Endpoint listed in README but not deployed",
            "workaround": "None -- use known passwords for testing"
        },
        {
            "name": "Wellness Module",
            "broken_step": "GET /api/v1/wellness/*",
            "error": "Returns 404 -- wellness endpoints not deployed",
            "issue": "All wellness endpoints (/dashboard, /check-in, /goals) return 404",
            "workaround": "Skip wellness testing -- APIs not implemented yet"
        },
        {
            "name": "Whistleblowing Module",
            "broken_step": "GET /api/v1/whistleblowing",
            "error": "Returns 404 -- endpoints not deployed",
            "issue": "Listed in README but returns 404",
            "workaround": "Skip whistleblowing testing"
        },
        {
            "name": "Custom Fields",
            "broken_step": "GET /api/v1/custom-fields/definitions",
            "error": "Returns 404",
            "issue": "Custom fields endpoints not deployed",
            "workaround": "Skip custom fields testing"
        },
        {
            "name": "Bulk Leave Approve/Reject",
            "broken_step": "POST /api/v1/leave/bulk-approve",
            "error": "Returns 404",
            "issue": "Bulk approve/reject endpoints not deployed",
            "workaround": "Approve/reject individually via POST /api/v1/leave/applications/:id/approve"
        },
        {
            "name": "Leave Dashboard",
            "broken_step": "GET /api/v1/leave/dashboard",
            "error": "Returns 404",
            "issue": "Leave dashboard endpoint not deployed",
            "workaround": "Use /api/v1/leave/balances and /api/v1/leave/applications separately"
        },
        {
            "name": "Attendance Reports/Export",
            "broken_step": "GET /api/v1/attendance/reports and /export",
            "error": "Returns 404",
            "issue": "Report and export endpoints not deployed",
            "workaround": "Use /api/v1/attendance/records with date filters"
        },
        {
            "name": "Attendance Shift Assignments",
            "broken_step": "GET /api/v1/attendance/shift-assignments",
            "error": "Returns 404",
            "issue": "Shift assignment listing endpoint not deployed",
            "workaround": "Shifts themselves work (GET /api/v1/attendance/shifts)"
        },
        {
            "name": "Document Upload",
            "broken_step": "POST /api/v1/documents",
            "error": "Returns 404 for POST",
            "issue": "Document upload endpoint not responding to POST",
            "workaround": "Documents can be read via GET /api/v1/documents"
        },
        {
            "name": "Payroll GL Accounting",
            "broken_step": "All /api/v1/gl-accounting/* endpoints",
            "error": "Returns 404 (Cannot GET/POST)",
            "issue": "GL accounting module not deployed in payroll",
            "workaround": "None -- skip GL accounting tests"
        },
        {
            "name": "Payroll Global Payroll",
            "broken_step": "All /api/v1/global-payroll/* endpoints",
            "error": "Returns 404",
            "issue": "Global payroll module not deployed",
            "workaround": "None -- skip global payroll tests"
        },
        {
            "name": "Payroll Earned Wage Access",
            "broken_step": "All /api/v1/earned-wage/* endpoints",
            "error": "Returns 404",
            "issue": "EWA module not deployed",
            "workaround": "None -- skip EWA tests"
        },
    ]

    # ── E. OPTIMAL TEST SUITE ──────────────────────────────────
    print("\n[5/6] Building Optimal Test Suite...")

    test_suite = {
        "smoke_tests": {
            "description": "Run FIRST -- verifies basic connectivity and auth",
            "estimated_time": "30 seconds",
            "tests": [
                {"name": "Health Check", "endpoint": "GET /health", "expected": 200},
                {"name": "Admin Login", "endpoint": "POST /api/v1/auth/login (ananya@technova.in)", "expected": 200},
                {"name": "Employee Login", "endpoint": "POST /api/v1/auth/login (priya@technova.in)", "expected": 200},
                {"name": "Super Admin Login", "endpoint": "POST /api/v1/auth/login (admin@empcloud.com)", "expected": 200},
                {"name": "List Users", "endpoint": "GET /api/v1/users", "expected": 200},
                {"name": "Org Info", "endpoint": "GET /api/v1/organizations/me", "expected": 200},
                {"name": "Swagger Docs", "endpoint": "GET /api/docs", "expected": 200},
                {"name": "OIDC Discovery", "endpoint": "GET /.well-known/openid-configuration", "expected": 200},
            ]
        },
        "core_regression": {
            "description": "Core HRMS module regression tests",
            "estimated_time": "3-5 minutes",
            "tests": [
                {"name": "Departments CRUD", "endpoints": ["GET /organizations/me/departments", "POST /organizations/me/departments"]},
                {"name": "Locations CRUD", "endpoints": ["GET /organizations/me/locations", "POST /organizations/me/locations"]},
                {"name": "User Profile", "endpoints": ["GET /users/:id", "PUT /users/:id", "GET /employees/:id/profile"]},
                {"name": "Attendance Flow", "endpoints": ["POST /attendance/check-in", "GET /attendance/records", "POST /attendance/check-out"]},
                {"name": "Leave Flow", "endpoints": ["GET /leave/types", "GET /leave/balances", "POST /leave/applications", "POST /leave/applications/:id/approve"]},
                {"name": "Announcements", "endpoints": ["GET /announcements", "POST /announcements", "GET /announcements/unread-count"]},
                {"name": "Policies", "endpoints": ["GET /policies", "POST /policies", "GET /policies/pending", "POST /policies/:id/acknowledge"]},
                {"name": "Documents", "endpoints": ["GET /documents", "GET /documents/categories", "GET /documents/my"]},
                {"name": "Helpdesk", "endpoints": ["GET /helpdesk/tickets", "POST /helpdesk/tickets", "PUT /helpdesk/tickets/:id"]},
                {"name": "Surveys", "endpoints": ["GET /surveys", "POST /surveys/:id/respond"]},
                {"name": "Forum", "endpoints": ["GET /forum/categories", "GET /forum/posts", "POST /forum/posts"]},
                {"name": "Events", "endpoints": ["GET /events", "POST /events", "POST /events/:id/register"]},
                {"name": "Assets", "endpoints": ["GET /assets", "POST /assets", "POST /assets/:id/assign"]},
                {"name": "Notifications", "endpoints": ["GET /notifications", "GET /notifications/unread-count"]},
                {"name": "Feedback", "endpoints": ["GET /feedback", "POST /feedback"]},
                {"name": "Audit Log", "endpoints": ["GET /audit"]},
            ]
        },
        "module_regression": {
            "description": "External module tests (require SSO)",
            "estimated_time": "5-10 minutes",
            "tests": [
                {"name": "Payroll SSO + Self-Service", "module": "payroll", "endpoints": [
                    "SSO to testpayroll.empcloud.com",
                    "GET /self-service/payslips",
                    "GET /self-service/salary",
                    "GET /salary-structures/employee/:empId"
                ]},
                {"name": "Payroll Admin", "module": "payroll", "endpoints": [
                    "GET /payroll (list runs)",
                    "GET /employees (payroll employees)",
                    "GET /salary-structures"
                ]},
                {"name": "Recruit SSO + Jobs", "module": "recruit", "endpoints": [
                    "POST /auth/sso",
                    "GET /jobs",
                    "GET /candidates",
                    "GET /interviews"
                ]},
                {"name": "Performance SSO + Reviews", "module": "performance", "endpoints": [
                    "POST /auth/sso",
                    "GET /review-cycles",
                    "GET /goals",
                    "GET /competency-frameworks"
                ]},
                {"name": "Rewards SSO + Kudos", "module": "rewards", "endpoints": [
                    "GET /kudos",
                    "GET /leaderboard",
                    "GET /badges",
                    "GET /celebrations"
                ]},
                {"name": "Exit SSO + Exits", "module": "exit", "endpoints": [
                    "GET /exits",
                    "GET /checklist-templates",
                    "GET /predictions/dashboard"
                ]},
                {"name": "LMS SSO + Courses", "module": "lms", "endpoints": [
                    "POST /auth/sso",
                    "GET /courses",
                    "GET /enrollments/my",
                    "GET /learning-paths"
                ]},
            ]
        },
        "rbac_security": {
            "description": "Role-based access control tests",
            "estimated_time": "2-3 minutes",
            "tests": [
                {"name": "Employee cannot access admin endpoints", "details": [
                    "Login as priya@technova.in",
                    "GET /api/v1/admin/organizations -> expect 403",
                    "POST /api/v1/organizations/me/departments -> expect 403",
                    "GET /api/v1/audit -> expect 403 or filtered"
                ]},
                {"name": "Org admin cannot see other org data", "details": [
                    "Login as ananya@technova.in (TechNova)",
                    "Try to access GlobalTech user IDs -> expect 404 or empty"
                ]},
                {"name": "Super admin has full access", "details": [
                    "Login as admin@empcloud.com",
                    "GET /api/v1/admin/organizations -> expect 200 with all orgs",
                    "GET /api/v1/admin/health -> expect 200"
                ]},
                {"name": "Payroll RBAC via SSO", "details": [
                    "SSO as employee -> most admin payroll endpoints return 403",
                    "SSO as org admin -> currently maps as employee (bug #722)"
                ]},
            ]
        },
        "data_integrity": {
            "description": "Data consistency and validation tests",
            "estimated_time": "2-3 minutes",
            "tests": [
                {"name": "Leave balance non-negative", "check": "GET /leave/balances -> all balances >= 0"},
                {"name": "Attendance + Leave = Working Days", "check": "Cross-reference attendance records with leave applications"},
                {"name": "Employee count consistency", "check": "GET /users count matches setup_data expectations"},
                {"name": "Duplicate prevention", "check": "POST /users/invite with existing email -> error"},
                {"name": "Soft delete behavior", "check": "DELETE item -> GET item still returns (by design)"},
                {"name": "Pagination works", "check": "GET /users?page=1&limit=5 -> returns correct count"},
            ]
        },
        "skip_list": {
            "description": "Tests to SKIP (known false positives or not ready)",
            "tests": [
                {"name": "Rate limiting", "reason": "All rate limits removed for testing"},
                {"name": "Field Force (emp-field)", "reason": "Module not ready for testing"},
                {"name": "Biometrics (emp-biometrics)", "reason": "Module not ready for testing"},
                {"name": "Direct subdomain login", "reason": "Modules use SSO only, not direct login"},
                {"name": "Soft delete items accessible", "reason": "By design for audit trail"},
                {"name": "XSS stored in DB", "reason": "React auto-escapes, Knex parameterizes -- not exploitable"},
                {"name": "Wellness endpoints", "reason": "All return 404 -- not deployed"},
                {"name": "Whistleblowing endpoints", "reason": "All return 404 -- not deployed"},
                {"name": "Custom Fields endpoints", "reason": "All return 404 -- not deployed"},
                {"name": "GL Accounting (Payroll)", "reason": "All return 404 -- not deployed"},
                {"name": "Global Payroll", "reason": "All return 404 -- not deployed"},
                {"name": "Earned Wage Access", "reason": "All return 404 -- not deployed"},
                {"name": "Pay Equity", "reason": "Not deployed"},
                {"name": "Compensation Benchmarks", "reason": "Not deployed"},
                {"name": "EMP Monitor API tests", "reason": "Different tech stack (QT/Laravel/Node.js), no standard API"},
            ]
        }
    }

    # ── F. ENVIRONMENT CONFIGURATION ───────────────────────────
    env_config = {
        "app_url": "https://test-empcloud.empcloud.com",
        "api_url": "https://test-empcloud-api.empcloud.com",
        "swagger_url": "https://test-empcloud-api.empcloud.com/api/docs",
        "credentials": {
            "super_admin": {"email": "admin@empcloud.com", "password": "SuperAdmin@2026", "role": "super_admin"},
            "org_admin_technova": {"email": "ananya@technova.in", "password": "Welcome@123", "role": "org_admin", "org_id": 5},
            "employee_technova": {"email": "priya@technova.in", "password": "Welcome@123", "role": "employee", "org_id": 5},
            "org_admin_globaltech": {"email": "john@globaltech.com", "password": "Welcome@123", "role": "org_admin", "org_id": 9},
            "org_admin_innovate": {"email": "hr@innovate.io", "password": "Welcome@123", "role": "org_admin", "org_id": 39},
        },
        "module_urls": {
            "payroll": {"frontend": "https://testpayroll.empcloud.com", "api": "https://testpayroll-api.empcloud.com"},
            "recruit": {"frontend": "https://test-recruit.empcloud.com", "api": "https://test-recruit-api.empcloud.com"},
            "performance": {"frontend": "https://test-performance.empcloud.com", "api": "https://test-performance-api.empcloud.com"},
            "rewards": {"frontend": "https://test-rewards.empcloud.com", "api": "https://test-rewards-api.empcloud.com"},
            "exit": {"frontend": "https://test-exit.empcloud.com", "api": "https://test-exit-api.empcloud.com"},
            "lms": {"frontend": "https://testlms.empcloud.com", "api": "https://testlms-api.empcloud.com"},
            "project": {"frontend": "https://test-project.empcloud.com", "api": "https://test-project-api.empcloud.com"},
            "monitor": {"frontend": "https://test-empmonitor.empcloud.com", "api": "https://test-empmonitor-api.empcloud.com"},
        },
        "sso_mechanism": "sso_token URL parameter -- navigate to module_url?sso_token=<access_token>",
        "token_expiry": "15 minutes (access token)",
        "api_pagination_defaults": {"page": 1, "limit": 20},
        "rate_limiting": "DISABLED for testing",
        "api_response_format": {
            "success": "{success: true, data: ..., message: '...'}",
            "error": "{success: false, error: {code: '...', message: '...'}}",
            "paginated": "{success: true, data: [...], meta: {page, limit, total, totalPages}}"
        },
        "special_pages": {
            "super_admin_dashboard": "/admin/super",
            "ai_config": "/admin/ai-config",
            "log_dashboard": "/admin/logs",
            "swagger_docs": "/api/docs",
            "ai_chatbot": "Purple bubble bottom-right (all users)",
        },
        "github": {
            "repo": "EmpCloud/EmpCloud",
            "pat": "os.environ.get('GITHUB_TOKEN', 'YOUR_TOKEN_HERE')",
        },
        "organizations": [],
    }

    # Add org data from setup
    if setup_data and "organizations" in setup_data:
        for org in setup_data["organizations"]:
            env_config["organizations"].append({
                "name": org["name"],
                "id": org["id"],
                "admin_email": org["admin_email"],
                "departments": org.get("departments", []),
                "leave_types": org.get("leave_types", []),
                "shifts": org.get("shifts", []),
            })

    # ── BUILD OUTPUT ────────────────────────────────────────────
    print("\n[6/6] Writing output files...")

    # Build JSON knowledge base
    knowledge_base_json = {
        "generated_at": datetime.now().isoformat(),
        "version": "1.0",
        "sections": {
            "A_api_map": {
                "total_endpoints": len(api_map),
                "by_module": {},
                "modules_config": modules_config,
            },
            "B_feature_matrix": feature_matrix,
            "C_known_working_flows": known_working_flows,
            "D_known_broken_flows": known_broken_flows,
            "E_test_suite": test_suite,
            "F_environment": env_config,
        },
        "simulation_summary": {
            "total_bugs_filed": month_end.get("summary", {}).get("total_bugs_filed", 0) if month_end else 0,
            "bugs": month_end.get("summary", {}).get("bugs", []) if month_end else [],
            "api_errors_count": month_end.get("summary", {}).get("api_errors_count", 0) if month_end else 0,
            "orgs_tested": list(month_end.get("organizations", {}).keys()) if month_end else [],
        },
        "readme_vs_reality_summary": {},
    }

    # Add per-module endpoint data to JSON
    for mod_key, endpoints in endpoints_by_module.items():
        working = [e for e in endpoints if e.get("admin_works")]
        broken = [e for e in endpoints if not e.get("admin_works")]
        knowledge_base_json["sections"]["A_api_map"]["by_module"][mod_key] = {
            "total": len(endpoints),
            "working": len(working),
            "broken_or_untested": len(broken),
            "endpoints": endpoints,
        }

    # Add readme_vs_reality summary
    if readme_vs_reality and "modules" in readme_vs_reality:
        for mod_key, mod_data in readme_vs_reality["modules"].items():
            tr = mod_data.get("test_results", {})
            knowledge_base_json["readme_vs_reality_summary"][mod_key] = {
                "readme_endpoints": tr.get("endpoints_in_readme", 0),
                "working": tr.get("working", 0),
                "missing_404": tr.get("missing_404", 0),
                "broken_500": tr.get("broken_500", 0),
                "auth_errors": tr.get("auth_errors", 0),
                "coverage_pct": tr.get("coverage_pct", 0),
            }

    # Write JSON
    json_path = os.path.join(BASE, "knowledge_base.json")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(knowledge_base_json, f, indent=2, default=str)
    print(f"  Wrote {json_path}")

    # ── BUILD MARKDOWN ──────────────────────────────────────────
    md_lines = []
    md = md_lines.append

    md("# EmpCloud Comprehensive Knowledge Base")
    md(f"\n> Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    md(f"> Source: All test results, API references, READMEs, simulation data")
    md(f"> Total endpoints mapped: {len(api_map)}")
    md("")

    # Table of contents
    md("## Table of Contents")
    md("- [A. Definitive API Map](#a-definitive-api-map)")
    md("- [B. Module Feature Matrix](#b-module-feature-matrix)")
    md("- [C. Known Working Flows](#c-known-working-flows)")
    md("- [D. Known Broken Flows](#d-known-broken-flows)")
    md("- [E. Optimal Test Suite](#e-optimal-test-suite)")
    md("- [F. Environment Configuration](#f-environment-configuration)")
    md("")

    # ── A. API MAP ──────────────────────────────────────────────
    md("---")
    md("## A. Definitive API Map")
    md("")

    for mod_key in ["core", "payroll", "recruit", "performance", "rewards", "exit", "lms", "project", "monitor"]:
        cfg = modules_config.get(mod_key, {})
        md(f"### {cfg.get('name', mod_key)}")
        md(f"- **API Base**: `{cfg.get('api_base', 'N/A')}`")
        md(f"- **Prefix**: `{cfg.get('prefix', '/api/v1/')}`")
        md(f"- **Auth**: {cfg.get('auth', 'N/A')}")
        md(f"- **Needs SSO**: {'Yes' if cfg.get('needs_sso') else 'No'}")
        md("")

        mod_eps = endpoints_by_module.get(mod_key, [])
        if mod_eps:
            working_eps = [e for e in mod_eps if e.get("admin_works")]
            broken_eps = [e for e in mod_eps if not e.get("admin_works")]
            md(f"**Verified Working ({len(working_eps)} endpoints):**")
            md("")
            md("| Method | Path | Status | Response Keys |")
            md("|--------|------|--------|---------------|")
            for ep in sorted(working_eps, key=lambda x: x["path"]):
                keys = ", ".join(ep.get("response_keys", [])[:3])
                md(f"| {ep['method']} | `{ep['path']}` | {ep['status_code']} | {keys} |")
            md("")

            if broken_eps:
                md(f"**Not Working / Not Deployed ({len(broken_eps)} endpoints):**")
                md("")
                md("| Method | Path | Status | Notes |")
                md("|--------|------|--------|-------|")
                for ep in sorted(broken_eps, key=lambda x: x["path"])[:20]:
                    md(f"| {ep['method']} | `{ep['path']}` | {ep['status_code']} | {ep.get('notes', '')} |")
                if len(broken_eps) > 20:
                    md(f"| ... | *{len(broken_eps) - 20} more* | | |")
                md("")
        else:
            md("*No endpoint test data available for this module.*")
            md("")

    # README vs Reality summary
    md("### README vs Reality Summary")
    md("")
    md("| Module | README Endpoints | Working | Missing (404) | Broken (500) | Auth Errors | Coverage |")
    md("|--------|-----------------|---------|---------------|--------------|-------------|----------|")
    if readme_vs_reality and "modules" in readme_vs_reality:
        for mod_key, mod_data in readme_vs_reality["modules"].items():
            tr = mod_data.get("test_results", {})
            md(f"| {mod_key} | {tr.get('endpoints_in_readme', 0)} | {tr.get('working', 0)} | {tr.get('missing_404', 0)} | {tr.get('broken_500', 0)} | {tr.get('auth_errors', 0)} | {tr.get('coverage_pct', 0):.1f}% |")
    md("")

    # ── B. FEATURE MATRIX ───────────────────────────────────────
    md("---")
    md("## B. Module Feature Matrix")
    md("")

    for mod_key, features in feature_matrix.items():
        mod_name = modules_config.get(mod_key, {}).get("name", mod_key)
        md(f"### {mod_name}")
        md("")
        md("| Feature | In README | API Exists | UI Works | Admin | Employee |")
        md("|---------|-----------|-----------|----------|-------|----------|")
        for feat_name, feat_data in features.items():
            in_readme = "Yes" if feat_data["in_readme"] else "No"
            api_exists = "Yes" if feat_data["api_exists"] else "No"
            ui_works = "Yes" if feat_data["ui_works"] else "No"
            admin = "Yes" if feat_data["admin"] else "No"
            employee = "Yes" if feat_data["employee"] else "No"
            md(f"| {feat_name} | {in_readme} | {api_exists} | {ui_works} | {admin} | {employee} |")
        md("")

    # ── C. KNOWN WORKING FLOWS ──────────────────────────────────
    md("---")
    md("## C. Known Working Flows")
    md("")

    for i, flow in enumerate(known_working_flows, 1):
        md(f"### {i}. {flow['name']}")
        md("")
        for j, step in enumerate(flow["steps"], 1):
            md(f"{j}. `{step}`")
        md("")
        if flow.get("notes"):
            md(f"**Notes:** {flow['notes']}")
        md("")

    # ── D. KNOWN BROKEN FLOWS ──────────────────────────────────
    md("---")
    md("## D. Known Broken Flows")
    md("")

    for i, flow in enumerate(known_broken_flows, 1):
        md(f"### {i}. {flow['name']}")
        md(f"- **Broken Step:** `{flow['broken_step']}`")
        md(f"- **Error:** {flow['error']}")
        if flow.get("issue"):
            md(f"- **Issue:** {flow['issue']}")
        if flow.get("workaround"):
            md(f"- **Workaround:** {flow['workaround']}")
        md("")

    # ── E. OPTIMAL TEST SUITE ──────────────────────────────────
    md("---")
    md("## E. Optimal Test Suite")
    md("")

    for suite_key, suite_data in test_suite.items():
        md(f"### {suite_key.replace('_', ' ').title()}")
        md(f"*{suite_data['description']}*")
        if "estimated_time" in suite_data:
            md(f"**Estimated time:** {suite_data['estimated_time']}")
        md("")

        for test in suite_data["tests"]:
            name = test.get("name", "")
            if "endpoint" in test:
                md(f"- **{name}**: `{test['endpoint']}` -> expect {test.get('expected', '200')}")
            elif "endpoints" in test:
                eps = ", ".join([f"`{e}`" for e in test["endpoints"]])
                mod = test.get("module", "core")
                md(f"- **{name}** ({mod}): {eps}")
            elif "details" in test:
                md(f"- **{name}**:")
                for d in test["details"]:
                    md(f"  - {d}")
            elif "check" in test:
                md(f"- **{name}**: {test['check']}")
            elif "reason" in test:
                md(f"- **{name}**: {test['reason']}")
        md("")

    # ── F. ENVIRONMENT CONFIGURATION ───────────────────────────
    md("---")
    md("## F. Environment Configuration")
    md("")

    md("### URLs")
    md(f"- **App**: {env_config['app_url']}")
    md(f"- **API**: {env_config['api_url']}")
    md(f"- **Swagger**: {env_config['swagger_url']}")
    md("")

    md("### Credentials")
    md("")
    md("| Role | Email | Password | Org ID |")
    md("|------|-------|----------|--------|")
    for name, cred in env_config["credentials"].items():
        md(f"| {cred['role']} | {cred['email']} | {cred['password']} | {cred.get('org_id', 'N/A')} |")
    md("")

    md("### Module URLs")
    md("")
    md("| Module | Frontend | API | SSO URL Pattern |")
    md("|--------|----------|-----|-----------------|")
    for mod, urls in env_config["module_urls"].items():
        sso = f"{urls['frontend']}?sso_token=<JWT>"
        md(f"| {mod} | {urls['frontend']} | {urls['api']} | `{sso}` |")
    md("")

    md("### SSO Mechanism")
    md(f"- {env_config['sso_mechanism']}")
    md(f"- Token expires in {env_config['token_expiry']}")
    md(f"- Rate limiting: {env_config['rate_limiting']}")
    md(f"- Pagination defaults: page={env_config['api_pagination_defaults']['page']}, limit={env_config['api_pagination_defaults']['limit']}")
    md("")

    md("### API Response Format")
    md("```json")
    md('// Success: {"success": true, "data": {...}}')
    md('// Error:   {"success": false, "error": {"code": "...", "message": "..."}}')
    md('// Paginated: {"success": true, "data": [...], "meta": {"page": 1, "limit": 20, "total": N, "totalPages": M}}')
    md("```")
    md("")

    md("### Organizations")
    md("")
    for org in env_config["organizations"]:
        md(f"#### {org['name']} (ID: {org['id']})")
        md(f"- Admin: {org['admin_email']}")
        if org.get("departments"):
            dept_names = [d["name"] for d in org["departments"]]
            md(f"- Departments: {', '.join(dept_names)}")
        if org.get("leave_types"):
            lt_names = [lt["name"] for lt in org["leave_types"] if not lt["name"].startswith("Test") and not lt["name"].startswith("LType")]
            md(f"- Leave Types: {', '.join(lt_names)}")
        if org.get("shifts"):
            shift_names = [s["name"] for s in org["shifts"]]
            md(f"- Shifts: {', '.join(shift_names)}")
        md("")

    md("### Critical Rules (from CLAUDE.md)")
    md("")
    md("1. **Module Auth**: External modules use SSO from EMP Cloud. Core JWT does NOT work on module APIs.")
    md("2. **Correct API Paths**: See CORRECT_API_PATHS.md. Common mistakes: /departments -> /organizations/me/departments, /leave/apply -> /leave/applications")
    md("3. **Soft Delete**: DELETE returns 200 but items remain accessible. This is BY DESIGN for audit trail.")
    md("4. **XSS in DB**: Script tags stored in DB are NOT a vulnerability (React auto-escapes, Knex parameterizes).")
    md("5. **Do NOT Report**: Rate limiting issues, Field Force, Biometrics, direct subdomain login failures, soft delete, stored XSS.")
    md("6. **Bug Reports**: Must include URL, Steps to Reproduce, Expected vs Actual, Screenshot.")
    md("7. **Read Programmer Comments**: Before re-opening bugs, read ALL comments from sumitempcloud.")
    md("8. **Consolidate Bugs**: Group similar issues into ONE issue.")
    md("9. **Human-Style Titles**: Write like a real person, not a robot.")
    md("10. **EMP Project uses /v1/ prefix** (not /api/v1/)")
    md("")

    md("### Simulation Statistics (March 2026)")
    md("")
    if month_end:
        md(f"- Total bugs filed during simulation: {month_end.get('summary', {}).get('total_bugs_filed', 0)}")
        md(f"- API errors encountered: {month_end.get('summary', {}).get('api_errors_count', 0)}")
        md(f"- Organizations tested: 3 (TechNova, GlobalTech, Innovate Solutions)")
        md(f"- Employees per org: 20")
        md(f"- Working days simulated: 22")
        for org_name, org_data in month_end.get("organizations", {}).items():
            md(f"\n**{org_name}:**")
            hc = org_data.get("headcount", {})
            att = org_data.get("attendance", {})
            lv = org_data.get("leave", {})
            eng = org_data.get("engagement", {})
            md(f"  - Headcount: {hc.get('total_employees', 0)} active, {hc.get('exits_march', 0)} exits")
            md(f"  - Attendance: {att.get('total_records', 0)} records, {att.get('late_arrivals', 0)} late")
            md(f"  - Leave: {lv.get('total_applications', 0)} applications")
            md(f"  - Engagement: {eng.get('surveys', 0)} surveys, {eng.get('forum_posts', 0)} forum posts, {eng.get('helpdesk_total', 0)} tickets")
    md("")

    # Write markdown
    md_path = os.path.join(BASE, "KNOWLEDGE_BASE.md")
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(md_lines))
    print(f"  Wrote {md_path}")

    # ── Summary ─────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("KNOWLEDGE BASE BUILD COMPLETE")
    print("=" * 60)
    print(f"  Total endpoints mapped:    {len(api_map)}")
    print(f"  Modules covered:           {len(feature_matrix)}")
    print(f"  Working flows documented:  {len(known_working_flows)}")
    print(f"  Broken flows documented:   {len(known_broken_flows)}")
    print(f"  Test suites defined:       {len(test_suite)}")
    print(f"  Organizations configured:  {len(env_config['organizations'])}")
    print(f"\nOutput files:")
    print(f"  Markdown: {md_path}")
    print(f"  JSON:     {json_path}")

if __name__ == "__main__":
    main()
