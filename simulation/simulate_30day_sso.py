#!/usr/bin/env python
"""
30-Day HRMS Simulation with SSO Authentication
=============================================
Part 1: Core HRMS via API (JWT token) - attendance, leave, announcements, etc.
Part 2: Module Testing via Selenium SSO - payroll, recruit, performance, rewards, exit, LMS
Part 3: Month-End Payroll processing via Selenium
Part 4: Data Integrity Audit
"""

import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import json
import time
import os
import random
import traceback
import requests
from datetime import datetime, timedelta
from collections import defaultdict

# Selenium imports
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, WebDriverException,
    StaleElementReferenceException
)

# ============================================================
# CONFIGURATION
# ============================================================
API_BASE = "https://test-empcloud-api.empcloud.com/api/v1"
FRONTEND_URL = "https://test-empcloud.empcloud.com"
GITHUB_PAT = "os.environ.get('GITHUB_TOKEN', 'YOUR_TOKEN_HERE')"
GITHUB_REPO = "EmpCloud/EmpCloud"
CHROME_PATH = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
SCREENSHOT_DIR = r"C:\emptesting\simulation\screenshots"
SETUP_DATA_PATH = r"C:\emptesting\simulation\setup_data.json"
REPORT_PATH = r"C:\emptesting\simulation\simulation_report.json"

os.makedirs(SCREENSHOT_DIR, exist_ok=True)

MODULE_URLS = {
    "payroll": "https://testpayroll.empcloud.com",
    "recruit": "https://test-recruit.empcloud.com",
    "performance": "https://test-performance.empcloud.com",
    "rewards": "https://test-rewards.empcloud.com",
    "exit": "https://test-exit.empcloud.com",
    "lms": "https://testlms.empcloud.com",
}

ORGS = [
    {"name": "TechNova", "email": "ananya@technova.in", "password": "Welcome@123"},
    {"name": "GlobalTech", "email": "john@globaltech.com", "password": "Welcome@123"},
    {"name": "Innovate", "email": "hr@innovate.io", "password": "Welcome@123"},
]

# ============================================================
# TRACKING / STATS
# ============================================================
stats = {
    "attendance_checkins": 0,
    "attendance_checkouts": 0,
    "attendance_conflicts": 0,
    "leave_applications_created": 0,
    "leave_applications_approved": 0,
    "announcements_created": 0,
    "events_created": 0,
    "surveys_created": 0,
    "helpdesk_tickets_created": 0,
    "forum_posts_created": 0,
    "wellness_checkins": 0,
    "feedback_created": 0,
    "assets_created": 0,
    "assets_assigned": 0,
    "policies_created": 0,
    "policies_acknowledged": 0,
    "notifications_checked": 0,
    "audit_logs_checked": 0,
    "api_errors": [],
    "bugs_filed": [],
    "module_tests": {},
    "data_integrity": {},
}

# ============================================================
# HELPERS
# ============================================================
def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


API_TIMEOUT = 10  # seconds per request


def api_login(email, password):
    """Login and return (token, user_data, org_data)."""
    r = requests.post(f"{API_BASE}/auth/login",
                      json={"email": email, "password": password}, timeout=API_TIMEOUT)
    r.raise_for_status()
    d = r.json()["data"]
    token = d["tokens"]["access_token"]
    return token, d["user"], d["org"]


def api_get(endpoint, token, params=None):
    h = {"Authorization": f"Bearer {token}"}
    r = requests.get(f"{API_BASE}{endpoint}", headers=h, params=params, timeout=API_TIMEOUT)
    return r


def api_post(endpoint, token, payload=None):
    h = {"Authorization": f"Bearer {token}"}
    r = requests.post(f"{API_BASE}{endpoint}", headers=h, json=payload or {}, timeout=API_TIMEOUT)
    return r


def api_put(endpoint, token, payload=None):
    h = {"Authorization": f"Bearer {token}"}
    r = requests.put(f"{API_BASE}{endpoint}", headers=h, json=payload or {}, timeout=API_TIMEOUT)
    return r


def make_driver():
    """Create a headless Chrome driver."""
    opts = Options()
    opts.binary_location = CHROME_PATH
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--ignore-certificate-errors")
    opts.add_argument("--disable-extensions")
    opts.add_argument("--disable-background-networking")
    driver = webdriver.Chrome(options=opts)
    driver.set_page_load_timeout(20)
    driver.implicitly_wait(3)
    return driver


def safe_quit_driver(driver):
    """Safely quit a driver."""
    if driver:
        try:
            driver.quit()
        except Exception:
            pass


def screenshot(driver, name):
    """Take a screenshot and save it."""
    safe_name = name.replace(" ", "_").replace("/", "_").replace(":", "")[:80]
    path = os.path.join(SCREENSHOT_DIR, f"{safe_name}.png")
    try:
        driver.save_screenshot(path)
        return path
    except Exception:
        return None


def file_bug(title, body, labels=None):
    """File a GitHub issue as a bug."""
    labels = labels or ["bug", "30-day-sim"]
    full_title = f"[30-Day Sim SSO] {title}"
    log(f"  BUG: {full_title}")
    try:
        r = requests.post(
            f"https://api.github.com/repos/{GITHUB_REPO}/issues",
            headers={
                "Authorization": f"token {GITHUB_PAT}",
                "Accept": "application/vnd.github.v3+json",
            },
            json={"title": full_title, "body": body, "labels": labels},
            timeout=30,
        )
        if r.status_code == 201:
            issue_url = r.json().get("html_url", "")
            log(f"    Filed: {issue_url}")
            stats["bugs_filed"].append({"title": full_title, "url": issue_url})
            return issue_url
        else:
            log(f"    Failed to file bug: {r.status_code} {r.text[:200]}")
    except Exception as e:
        log(f"    Error filing bug: {e}")
    return None


# ============================================================
# LOAD SETUP DATA
# ============================================================
log("Loading setup data...")
with open(SETUP_DATA_PATH) as f:
    setup_data = json.load(f)

org_configs = setup_data["organizations"]
all_employees = setup_data["employees"]

# Group employees by org
employees_by_org = defaultdict(list)
for emp in all_employees:
    employees_by_org[emp["organization"]].append(emp)

log(f"Loaded {len(all_employees)} employees across {len(org_configs)} orgs")
for org_name, emps in employees_by_org.items():
    log(f"  {org_name}: {len(emps)} employees")


# ============================================================
# PART 1: CORE HRMS API SIMULATION (30 days)
# ============================================================
def run_core_simulation():
    log("=" * 70)
    log("PART 1: CORE HRMS API SIMULATION")
    log("=" * 70)

    sim_start = datetime(2026, 3, 1)
    sim_end = datetime(2026, 3, 30)

    for org_cfg in ORGS:
        org_name = org_cfg["name"]
        log(f"\n--- Org: {org_name} ---")

        try:
            token, user, org = api_login(org_cfg["email"], org_cfg["password"])
            log(f"  Logged in as {user.get('first_name', '')} {user.get('last_name', '')} (user_id={user.get('id')})")
        except Exception as e:
            log(f"  LOGIN FAILED for {org_name}: {e}")
            stats["api_errors"].append({"org": org_name, "error": f"Login failed: {e}"})
            continue

        org_id = org.get("id")
        admin_user_id = user.get("id")
        # Map org name to setup data
        setup_org = None
        for oc in org_configs:
            if oc["admin_email"] == org_cfg["email"]:
                setup_org = oc
                break

        # Get forum category for this org
        org_forum_category_id = 1
        try:
            cat_r = api_get("/forum/categories", token)
            if cat_r.status_code == 200:
                cats = cat_r.json().get("data", [])
                if cats:
                    org_forum_category_id = cats[0]["id"]
        except Exception:
            pass

        org_key = org_name.replace(" ", "")
        matching_emps = []
        for emp_list_key, emp_list in employees_by_org.items():
            if org_name.lower() in emp_list_key.lower() or emp_list_key.lower() in org_name.lower():
                matching_emps = emp_list
                break
        if not matching_emps:
            # Try by domain
            for oc in org_configs:
                if oc["name"].lower().startswith(org_name.lower()[:5]):
                    domain = oc["domain"]
                    matching_emps = [e for e in all_employees if domain in e.get("email", "")]
                    break

        log(f"  Found {len(matching_emps)} employees for {org_name}")

        # ---- DAILY SIMULATION ----
        leave_app_ids = []
        leave_apps_submitted = 0
        target_leave_apps = 10

        for day_offset in range(30):
            current_date = sim_start + timedelta(days=day_offset)
            day_str = current_date.strftime("%Y-%m-%d")
            weekday = current_date.weekday()  # 0=Mon, 6=Sun

            # Skip weekends
            if weekday >= 5:
                continue

            day_num = day_offset + 1
            if day_num % 5 == 1:
                log(f"  Day {day_num} ({day_str}) - {org_name}")

            # --- ATTENDANCE (all employees) ---
            # The API only supports check-in for the current logged-in user for today.
            # We do a single admin check-in/check-out to verify the endpoint works.
            try:
                r = api_post("/attendance/check-in", token)
                if r.status_code == 200:
                    stats["attendance_checkins"] += 1
                elif r.status_code == 409:
                    stats["attendance_conflicts"] += 1
                else:
                    stats["api_errors"].append({
                        "org": org_name, "day": day_str,
                        "endpoint": "/attendance/check-in",
                        "status": r.status_code, "body": r.text[:200]
                    })
            except Exception as e:
                stats["api_errors"].append({"org": org_name, "endpoint": "/attendance/check-in", "error": str(e)})

            try:
                r = api_post("/attendance/check-out", token)
                if r.status_code == 200:
                    stats["attendance_checkouts"] += 1
                elif r.status_code == 409:
                    stats["attendance_conflicts"] += 1
            except Exception:
                pass

            # --- LEAVE APPLICATIONS (spread across 30 days, 10 per org) ---
            if leave_apps_submitted < target_leave_apps and day_num % 3 == 0:
                leave_types = setup_org["leave_types"] if setup_org else []
                if leave_types:
                    lt = random.choice(leave_types[:3])  # Use standard types
                    # Use future dates far enough apart to avoid overlap
                    start_d = datetime(2026, 5, 1) + timedelta(days=leave_apps_submitted * 5)
                    days_count = random.choice([1, 2])
                    end_d = start_d + timedelta(days=days_count - 1)
                    reasons = [
                        "Family event attendance",
                        "Personal medical appointment",
                        "Home renovation work",
                        "Family emergency",
                        "Personal commitment",
                        "Wellness day off",
                        "Child school event",
                        "Bank and government office visit",
                        "Travel for personal work",
                        "Religious festival celebration",
                    ]
                    payload = {
                        "leave_type_id": lt["id"],
                        "start_date": start_d.strftime("%Y-%m-%d"),
                        "end_date": end_d.strftime("%Y-%m-%d"),
                        "days_count": days_count,
                        "reason": reasons[leave_apps_submitted % len(reasons)],
                    }
                    try:
                        r = api_post("/leave/applications", token, payload)
                        if r.status_code in (200, 201):
                            stats["leave_applications_created"] += 1
                            leave_apps_submitted += 1
                            resp_data = r.json().get("data", {})
                            app_id = resp_data.get("id")
                            if app_id:
                                leave_app_ids.append(app_id)
                            log(f"    Leave app created: {lt['name']}, {start_d.strftime('%m/%d')}-{end_d.strftime('%m/%d')}")
                        else:
                            stats["api_errors"].append({
                                "org": org_name, "endpoint": "/leave/applications",
                                "status": r.status_code, "body": r.text[:200]
                            })
                    except Exception as e:
                        stats["api_errors"].append({"org": org_name, "endpoint": "/leave/applications", "error": str(e)})

            # --- LEAVE APPROVALS (approve pending ones) ---
            if day_num % 4 == 0 and leave_app_ids:
                for app_id in list(leave_app_ids):
                    try:
                        r = api_put(f"/leave/applications/{app_id}/approve", token)
                        if r.status_code == 200:
                            stats["leave_applications_approved"] += 1
                            leave_app_ids.remove(app_id)
                            log(f"    Leave app {app_id} approved")
                        # 400 means already processed - that's ok
                    except Exception:
                        pass

            # --- HELPDESK TICKETS (daily, 1 per org) ---
            categories = ["general", "it", "hr", "finance", "facilities"]
            priorities = ["low", "medium", "high"]
            subjects = [
                f"Laptop battery draining fast - Day {day_num}",
                f"VPN connection issues - Day {day_num}",
                f"Request for ergonomic chair - Day {day_num}",
                f"Email not syncing on phone - Day {day_num}",
                f"Building access card not working - Day {day_num}",
                f"Software license renewal needed - Day {day_num}",
                f"Projector malfunction in conference room - Day {day_num}",
                f"Parking space allocation request - Day {day_num}",
                f"Internet speed slow on floor 3 - Day {day_num}",
                f"Need additional monitor - Day {day_num}",
            ]
            ticket_payload = {
                "subject": subjects[day_num % len(subjects)],
                "description": f"Simulation ticket for {org_name} on {day_str}. This is part of the 30-day HRMS simulation.",
                "category": categories[day_num % len(categories)],
                "priority": priorities[day_num % len(priorities)],
            }
            try:
                r = api_post("/helpdesk/tickets", token, ticket_payload)
                if r.status_code in (200, 201):
                    stats["helpdesk_tickets_created"] += 1
                else:
                    stats["api_errors"].append({
                        "org": org_name, "endpoint": "/helpdesk/tickets",
                        "status": r.status_code, "body": r.text[:200]
                    })
            except Exception as e:
                stats["api_errors"].append({"org": org_name, "endpoint": "/helpdesk/tickets", "error": str(e)})

            # --- FORUM POSTS (daily) ---
            post_types = ["discussion", "question", "idea", "announcement"]
            post_titles = [
                f"Best practices for remote team collaboration - Day {day_num}",
                f"How to improve code review process - Day {day_num}",
                f"Suggestion: Friday team lunches - Day {day_num}",
                f"Question about new expense policy - Day {day_num}",
                f"Idea: Internal hackathon quarterly - Day {day_num}",
                f"Discussion: Flexible work hours - Day {day_num}",
                f"Knowledge sharing session proposal - Day {day_num}",
                f"New onboarding buddy system - Day {day_num}",
            ]
            forum_payload = {
                "title": post_titles[day_num % len(post_titles)],
                "content": f"Simulation forum post for {org_name} on {day_str}. "
                           f"Part of 30-day HRMS simulation.",
                "post_type": post_types[day_num % len(post_types)],
                "category_id": org_forum_category_id,
                "tags": ["simulation", "testing"],
            }
            try:
                r = api_post("/forum/posts", token, forum_payload)
                if r.status_code in (200, 201):
                    stats["forum_posts_created"] += 1
                else:
                    stats["api_errors"].append({
                        "org": org_name, "endpoint": "/forum/posts",
                        "status": r.status_code, "body": r.text[:200]
                    })
            except Exception as e:
                stats["api_errors"].append({"org": org_name, "endpoint": "/forum/posts", "error": str(e)})

            # --- WELLNESS CHECK-INS (daily) ---
            moods = ["great", "good", "okay", "stressed", "tired"]
            wellness_payload = {
                "mood": moods[day_num % len(moods)],
                "energy_level": random.randint(1, 5),
                "sleep_hours": round(random.uniform(5.0, 9.0), 1),
                "exercise_minutes": random.choice([0, 15, 30, 45, 60]),
                "notes": f"Sim wellness day {day_num} {org_name}",
                "check_in_date": day_str,
            }
            try:
                r = api_post("/wellness/check-ins", token, wellness_payload)
                if r.status_code in (200, 201):
                    stats["wellness_checkins"] += 1
                elif r.status_code != 409:  # 409 = already checked in
                    # Try alternate
                    r2 = api_post("/wellness/check-in", token, wellness_payload)
                    if r2.status_code in (200, 201):
                        stats["wellness_checkins"] += 1
            except Exception:
                pass

            # --- WEEKLY: ANNOUNCEMENTS (every 5 working days) ---
            if day_num % 5 == 1:
                ann_payload = {
                    "title": f"Weekly Update - Week of {day_str} - {org_name}",
                    "content": f"This is the weekly announcement for {org_name}. "
                               f"Week starting {day_str}. Key updates: team standup schedule, "
                               f"upcoming deadlines, and project milestones. "
                               f"Part of 30-day HRMS simulation.",
                    "priority": random.choice(["low", "medium", "high"]),
                    "target_type": "all",
                }
                try:
                    r = api_post("/announcements", token, ann_payload)
                    if r.status_code in (200, 201):
                        stats["announcements_created"] += 1
                        log(f"    Announcement created: {ann_payload['title'][:50]}")
                    else:
                        stats["api_errors"].append({
                            "org": org_name, "endpoint": "/announcements",
                            "status": r.status_code, "body": r.text[:200]
                        })
                except Exception as e:
                    stats["api_errors"].append({"org": org_name, "endpoint": "/announcements", "error": str(e)})

            # --- WEEKLY: FEEDBACK (every 5 working days) ---
            if day_num % 5 == 3:
                fb_categories = ["management", "workplace", "process", "culture", "benefits"]
                fb_payload = {
                    "category": fb_categories[day_num % len(fb_categories)],
                    "subject": f"Feedback on {fb_categories[day_num % len(fb_categories)]} - {org_name} Day {day_num}",
                    "message": f"Simulation feedback for {org_name}. Day {day_num}. "
                               f"Providing constructive feedback on {fb_categories[day_num % len(fb_categories)]} "
                               f"as part of the 30-day HRMS simulation.",
                    "is_anonymous": random.choice([True, False]),
                }
                try:
                    r = api_post("/feedback", token, fb_payload)
                    if r.status_code in (200, 201):
                        stats["feedback_created"] += 1
                    else:
                        stats["api_errors"].append({
                            "org": org_name, "endpoint": "/feedback",
                            "status": r.status_code, "body": r.text[:200]
                        })
                except Exception:
                    pass

        # ---- END OF DAILY LOOP ----

        # --- EVENTS (2 per org) ---
        for i in range(2):
            evt_payload = {
                "title": f"{org_name} {'Town Hall' if i == 0 else 'Team Outing'} - March 2026",
                "description": f"Simulation event {i+1} for {org_name}. Part of 30-day HRMS sim.",
                "event_type": "meeting" if i == 0 else "social",
                "start_date": f"2026-03-{10 + i*10:02d}T10:00:00",
                "end_date": f"2026-03-{10 + i*10:02d}T17:00:00",
                "location": "Main Office" if i == 0 else "Outdoor Venue",
                "target_type": "all",
                "is_mandatory": True if i == 0 else False,
            }
            try:
                r = api_post("/events", token, evt_payload)
                if r.status_code in (200, 201):
                    stats["events_created"] += 1
                    log(f"    Event created: {evt_payload['title']}")
                else:
                    stats["api_errors"].append({
                        "org": org_name, "endpoint": "/events",
                        "status": r.status_code, "body": r.text[:200]
                    })
            except Exception as e:
                stats["api_errors"].append({"org": org_name, "endpoint": "/events", "error": str(e)})

        # --- SURVEYS (1 per org) ---
        log(f"    Creating survey for {org_name}...")
        survey_payload = {
            "title": f"{org_name} Employee Satisfaction Survey - March 2026",
            "description": f"Monthly employee satisfaction survey for {org_name}. Part of 30-day simulation.",
            "type": "engagement",
            "is_anonymous": True,
            "target_type": "all",
        }
        try:
            r = api_post("/surveys", token, survey_payload)
            if r.status_code in (200, 201):
                stats["surveys_created"] += 1
                log(f"    Survey created: {survey_payload['title']}")
            else:
                log(f"    Survey failed: {r.status_code} - {r.text[:100]}")
                stats["api_errors"].append({
                    "org": org_name, "endpoint": "/surveys",
                    "status": r.status_code, "body": r.text[:200]
                })
        except Exception as e:
            log(f"    Survey exception: {e}")
            pass

        # --- ASSETS (create + assign) ---
        log(f"    Creating assets for {org_name}...")
        asset_types = ["Laptop", "Monitor", "Keyboard", "Mouse", "Headset"]
        for i, atype in enumerate(asset_types):
            ts_tag = int(time.time()) + i
            asset_payload = {
                "name": f"{org_name} {atype} Sim-{ts_tag}",
                "serial_number": f"SIM-{ts_tag}",
                "status": "available",
                "condition_status": "new",
            }
            try:
                r = api_post("/assets", token, asset_payload)
                if r.status_code in (200, 201):
                    stats["assets_created"] += 1
                    asset_id = r.json().get("data", {}).get("id")
                    # Assign to an employee
                    if asset_id and matching_emps and i < len(matching_emps):
                        emp_id = matching_emps[i]["id"]
                        r2 = api_post(f"/assets/{asset_id}/assign", token, {"assigned_to": emp_id})
                        if r2.status_code == 200:
                            stats["assets_assigned"] += 1
                else:
                    stats["api_errors"].append({
                        "org": org_name, "endpoint": "/assets",
                        "status": r.status_code, "body": r.text[:200]
                    })
            except Exception:
                pass

        # --- POLICIES (create + acknowledge) ---
        log(f"    Creating policies for {org_name}...")
        policy_titles = [
            "Remote Work Policy - March 2026",
            "Data Security Policy - March 2026",
            "Code of Conduct - March 2026",
        ]
        for pt in policy_titles:
            pol_payload = {
                "title": f"{org_name} {pt}",
                "content": f"This is the {pt} for {org_name}. All employees must comply. "
                           f"Part of 30-day HRMS simulation. Effective immediately.",
                "category": "HR",
                "is_active": True,
            }
            try:
                r = api_post("/policies", token, pol_payload)
                if r.status_code in (200, 201):
                    stats["policies_created"] += 1
                    pol_id = r.json().get("data", {}).get("id")
                    if pol_id:
                        r2 = api_post(f"/policies/{pol_id}/acknowledge", token)
                        if r2.status_code == 200:
                            stats["policies_acknowledged"] += 1
                else:
                    stats["api_errors"].append({
                        "org": org_name, "endpoint": "/policies",
                        "status": r.status_code, "body": r.text[:200]
                    })
            except Exception:
                pass

        # --- NOTIFICATIONS CHECK ---
        try:
            r = api_get("/notifications", token)
            if r.status_code == 200:
                notif_data = r.json().get("data", [])
                stats["notifications_checked"] += 1
                log(f"    Notifications: {len(notif_data)} found")
            else:
                stats["api_errors"].append({
                    "org": org_name, "endpoint": "/notifications",
                    "status": r.status_code
                })
        except Exception:
            pass

        # --- AUDIT LOG CHECK ---
        try:
            r = api_get("/audit", token)
            if r.status_code == 200:
                audit_data = r.json().get("data", [])
                stats["audit_logs_checked"] += 1
                log(f"    Audit logs: {len(audit_data)} entries")
            else:
                stats["api_errors"].append({
                    "org": org_name, "endpoint": "/audit",
                    "status": r.status_code
                })
        except Exception:
            pass

        # --- CHECK LEAVE BALANCES ---
        try:
            r = api_get("/leave/balances", token)
            if r.status_code == 200:
                bal_data = r.json().get("data", [])
                log(f"    Leave balances: {len(bal_data)} entries")
        except Exception:
            pass

    log("\n  CORE SIMULATION COMPLETE")
    log(f"  Attendance check-ins: {stats['attendance_checkins']}")
    log(f"  Attendance conflicts (already checked in): {stats['attendance_conflicts']}")
    log(f"  Leave apps created: {stats['leave_applications_created']}")
    log(f"  Leave apps approved: {stats['leave_applications_approved']}")
    log(f"  Announcements: {stats['announcements_created']}")
    log(f"  Events: {stats['events_created']}")
    log(f"  Surveys: {stats['surveys_created']}")
    log(f"  Helpdesk tickets: {stats['helpdesk_tickets_created']}")
    log(f"  Forum posts: {stats['forum_posts_created']}")
    log(f"  Wellness check-ins: {stats['wellness_checkins']}")
    log(f"  Feedback: {stats['feedback_created']}")
    log(f"  Assets created/assigned: {stats['assets_created']}/{stats['assets_assigned']}")
    log(f"  Policies created/ack: {stats['policies_created']}/{stats['policies_acknowledged']}")
    log(f"  API errors: {len(stats['api_errors'])}")


# ============================================================
# PART 2: SELENIUM SSO MODULE TESTING
# ============================================================
def selenium_login(driver, email, password):
    """Login via the EMP Cloud frontend."""
    driver.get(f"{FRONTEND_URL}/login")
    time.sleep(3)

    # Try to find and fill login form
    try:
        wait = WebDriverWait(driver, 15)

        # Try email field
        email_field = None
        for selector in ["input[type='email']", "input[name='email']", "#email",
                         "input[placeholder*='email' i]", "input[placeholder*='Email']"]:
            try:
                email_field = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                break
            except TimeoutException:
                continue

        if not email_field:
            # Try all inputs
            inputs = driver.find_elements(By.TAG_NAME, "input")
            if inputs:
                email_field = inputs[0]

        if email_field:
            email_field.clear()
            email_field.send_keys(email)
        else:
            log(f"    Could not find email field on login page")
            screenshot(driver, f"login_no_email_field")
            return False

        # Password field
        pwd_field = None
        for selector in ["input[type='password']", "input[name='password']", "#password"]:
            try:
                pwd_field = driver.find_element(By.CSS_SELECTOR, selector)
                break
            except NoSuchElementException:
                continue

        if not pwd_field:
            inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='password']")
            if inputs:
                pwd_field = inputs[0]

        if pwd_field:
            pwd_field.clear()
            pwd_field.send_keys(password)
        else:
            log(f"    Could not find password field")
            screenshot(driver, f"login_no_password_field")
            return False

        # Submit
        btn = None
        for selector in ["button[type='submit']", "button:has-text('Login')",
                         "button:has-text('Sign in')", "button.login-btn"]:
            try:
                btn = driver.find_element(By.CSS_SELECTOR, selector)
                break
            except NoSuchElementException:
                continue

        if not btn:
            buttons = driver.find_elements(By.TAG_NAME, "button")
            for b in buttons:
                txt = b.text.lower()
                if "login" in txt or "sign in" in txt or "submit" in txt:
                    btn = b
                    break
            if not btn and buttons:
                btn = buttons[-1]  # Last button is often submit

        if btn:
            btn.click()
        else:
            log(f"    Could not find submit button")
            screenshot(driver, f"login_no_submit")
            return False

        # Wait for redirect to dashboard
        time.sleep(5)
        current_url = driver.current_url
        if "/login" not in current_url or "/dashboard" in current_url or "/modules" in current_url:
            log(f"    Login successful, at: {current_url}")
            return True
        else:
            log(f"    Login may have failed, still at: {current_url}")
            screenshot(driver, f"login_may_have_failed")
            return True  # Continue anyway - might be SPA

    except Exception as e:
        log(f"    Login error: {e}")
        screenshot(driver, f"login_error")
        return False


def navigate_to_module(driver, module_name):
    """Navigate to /modules and click Launch for the given module."""
    try:
        driver.get(f"{FRONTEND_URL}/modules")
        time.sleep(3)
        screenshot(driver, f"modules_page_{module_name}")

        # Look for launch links/buttons for this module
        module_url = MODULE_URLS.get(module_name, "")
        module_label = module_name.capitalize()

        # Try clicking various selectors
        launched = False

        # Method 1: Find link with module URL
        try:
            links = driver.find_elements(By.TAG_NAME, "a")
            for link in links:
                href = link.get_attribute("href") or ""
                text = link.text.lower()
                if module_url and module_url in href:
                    link.click()
                    launched = True
                    break
                if module_name.lower() in text and ("launch" in text or "open" in text):
                    link.click()
                    launched = True
                    break
        except Exception:
            pass

        if not launched:
            # Method 2: Find a card/button with module name, then click Launch inside it
            try:
                cards = driver.find_elements(By.CSS_SELECTOR, "[class*='card'], [class*='module'], [class*='tile']")
                for card in cards:
                    if module_label.lower() in card.text.lower():
                        # Find launch button inside
                        try:
                            launch_btn = card.find_element(By.CSS_SELECTOR, "a, button")
                            launch_btn.click()
                            launched = True
                            break
                        except NoSuchElementException:
                            card.click()
                            launched = True
                            break
            except Exception:
                pass

        if not launched:
            # Method 3: Try direct navigation to module URL
            log(f"    Could not find Launch for {module_name}, navigating directly")
            driver.get(module_url)

        time.sleep(5)
        current_url = driver.current_url
        log(f"    After module launch, at: {current_url}")
        screenshot(driver, f"module_{module_name}_landed")

        return True

    except Exception as e:
        log(f"    Module navigation error for {module_name}: {e}")
        screenshot(driver, f"module_{module_name}_nav_error")
        return False


def test_module_page(driver, module_name, page_url, page_name):
    """Navigate to a page and take a screenshot, return page info."""
    result = {"page": page_name, "url": page_url, "status": "unknown", "details": ""}
    try:
        driver.get(page_url)
        time.sleep(3)
        current_url = driver.current_url
        title = driver.title
        body_text = ""
        try:
            body = driver.find_element(By.TAG_NAME, "body")
            body_text = body.text[:500]
        except Exception:
            pass

        sc_path = screenshot(driver, f"{module_name}_{page_name}")

        # Check for error indicators
        error_indicators = ["404", "not found", "error", "forbidden", "unauthorized", "500", "server error"]
        page_lower = body_text.lower()

        if any(err in page_lower for err in error_indicators) and len(body_text) < 200:
            result["status"] = "error"
            result["details"] = f"Error page detected. Title: {title}. Body: {body_text[:200]}"
        elif "/login" in current_url and "/login" not in page_url:
            result["status"] = "redirect_to_login"
            result["details"] = f"Redirected to login. SSO may have failed."
        elif body_text.strip() == "":
            result["status"] = "blank"
            result["details"] = "Blank page loaded"
        else:
            result["status"] = "loaded"
            result["details"] = f"Page loaded. Title: {title}. Content length: {len(body_text)}"

        result["screenshot"] = sc_path
        log(f"      {page_name}: {result['status']} - {result['details'][:80]}")
        return result

    except TimeoutException:
        result["status"] = "timeout"
        result["details"] = "Page load timed out"
        screenshot(driver, f"{module_name}_{page_name}_timeout")
        log(f"      {page_name}: TIMEOUT")
        return result
    except Exception as e:
        result["status"] = "error"
        result["details"] = str(e)[:200]
        log(f"      {page_name}: ERROR - {e}")
        return result


def test_payroll_module(driver):
    """Test Payroll module."""
    log("  Testing PAYROLL module...")
    module_results = []
    base = MODULE_URLS["payroll"]

    pages = [
        (f"{base}/dashboard", "dashboard"),
        (f"{base}/payslips", "payslips"),
        (f"{base}/salary-structure", "salary_structure"),
        (f"{base}/tax-details", "tax_details"),
        (f"{base}/payroll", "payroll_processing"),
        (f"{base}/payroll/run", "run_payroll"),
        (f"{base}/reports", "reports"),
    ]

    for url, name in pages:
        result = test_module_page(driver, "payroll", url, name)
        module_results.append(result)

    # Try to find and click "Download Payslip"
    try:
        driver.get(f"{base}/payslips")
        time.sleep(3)
        download_btns = driver.find_elements(By.XPATH,
            "//*[contains(text(), 'Download') or contains(text(), 'PDF')]")
        if download_btns:
            log(f"      Found {len(download_btns)} download buttons on payslips page")
            module_results.append({"page": "payslip_download", "status": "available",
                                   "details": f"{len(download_btns)} download options found"})
        else:
            module_results.append({"page": "payslip_download", "status": "not_found",
                                   "details": "No download buttons found"})
    except Exception as e:
        module_results.append({"page": "payslip_download", "status": "error", "details": str(e)[:100]})

    return module_results


def test_recruit_module(driver):
    """Test Recruitment module."""
    log("  Testing RECRUITMENT module...")
    module_results = []
    base = MODULE_URLS["recruit"]

    pages = [
        (f"{base}/dashboard", "dashboard"),
        (f"{base}/jobs", "job_postings"),
        (f"{base}/candidates", "candidates"),
        (f"{base}/interviews", "interview_schedule"),
        (f"{base}/pipeline", "pipeline"),
    ]

    for url, name in pages:
        result = test_module_page(driver, "recruit", url, name)
        module_results.append(result)

    # Try to create a job posting
    try:
        driver.get(f"{base}/jobs/new")
        time.sleep(3)
        sc = screenshot(driver, "recruit_create_job")
        body_text = driver.find_element(By.TAG_NAME, "body").text[:300]
        if "create" in body_text.lower() or "new" in body_text.lower() or "form" in body_text.lower():
            module_results.append({"page": "create_job", "status": "form_available",
                                   "details": "Job creation form found"})
        else:
            module_results.append({"page": "create_job", "status": "loaded",
                                   "details": body_text[:100]})
    except Exception as e:
        module_results.append({"page": "create_job", "status": "error", "details": str(e)[:100]})

    return module_results


def test_performance_module(driver):
    """Test Performance module."""
    log("  Testing PERFORMANCE module...")
    module_results = []
    base = MODULE_URLS["performance"]

    pages = [
        (f"{base}/dashboard", "dashboard"),
        (f"{base}/reviews", "review_cycles"),
        (f"{base}/goals", "goals"),
        (f"{base}/9-box", "nine_box_grid"),
        (f"{base}/analytics", "analytics"),
        (f"{base}/competencies", "competencies"),
    ]

    for url, name in pages:
        result = test_module_page(driver, "performance", url, name)
        module_results.append(result)

    # Try to create a goal
    try:
        driver.get(f"{base}/goals/new")
        time.sleep(3)
        screenshot(driver, "performance_create_goal")
        body_text = driver.find_element(By.TAG_NAME, "body").text[:200]
        module_results.append({"page": "create_goal", "status": "loaded", "details": body_text[:100]})
    except Exception as e:
        module_results.append({"page": "create_goal", "status": "error", "details": str(e)[:100]})

    return module_results


def test_rewards_module(driver):
    """Test Rewards module."""
    log("  Testing REWARDS module...")
    module_results = []
    base = MODULE_URLS["rewards"]

    pages = [
        (f"{base}/dashboard", "dashboard"),
        (f"{base}/kudos", "kudos"),
        (f"{base}/leaderboard", "leaderboard"),
        (f"{base}/badges", "badges"),
        (f"{base}/rewards", "rewards_catalog"),
    ]

    for url, name in pages:
        result = test_module_page(driver, "rewards", url, name)
        module_results.append(result)

    return module_results


def test_exit_module(driver):
    """Test Exit module."""
    log("  Testing EXIT module...")
    module_results = []
    base = MODULE_URLS["exit"]

    pages = [
        (f"{base}/dashboard", "dashboard"),
        (f"{base}/clearance", "clearance"),
        (f"{base}/full-and-final", "fnf_settlement"),
        (f"{base}/exit-interviews", "exit_interviews"),
        (f"{base}/analytics", "analytics"),
    ]

    for url, name in pages:
        result = test_module_page(driver, "exit", url, name)
        module_results.append(result)

    return module_results


def test_lms_module(driver):
    """Test LMS module."""
    log("  Testing LMS module...")
    module_results = []
    base = MODULE_URLS["lms"]

    pages = [
        (f"{base}/dashboard", "dashboard"),
        (f"{base}/courses", "courses"),
        (f"{base}/learning-paths", "learning_paths"),
        (f"{base}/my-learning", "my_learning"),
        (f"{base}/catalog", "catalog"),
    ]

    for url, name in pages:
        result = test_module_page(driver, "lms", url, name)
        module_results.append(result)

    return module_results


def run_module_tests():
    log("\n" + "=" * 70)
    log("PART 2: MODULE TESTING VIA SELENIUM SSO")
    log("=" * 70)

    # Test with TechNova admin (primary org)
    org = ORGS[0]
    module_tests = [
        ("payroll", test_payroll_module),
        ("recruit", test_recruit_module),
        ("performance", test_performance_module),
        ("rewards", test_rewards_module),
        ("exit", test_exit_module),
        ("lms", test_lms_module),
    ]

    driver = None
    modules_tested = 0

    for module_name, test_fn in module_tests:
        # Restart driver every 2 modules
        if modules_tested % 2 == 0:
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass
                time.sleep(2)
            log(f"\n  Creating fresh Chrome driver (modules tested so far: {modules_tested})")
            try:
                driver = make_driver()
            except Exception as e:
                log(f"  FATAL: Cannot create Chrome driver: {e}")
                stats["module_tests"][module_name] = [{"status": "driver_error", "details": str(e)}]
                continue

            # Login
            log(f"  Logging in as {org['email']}...")
            login_ok = selenium_login(driver, org["email"], org["password"])
            if not login_ok:
                log(f"  Login failed, trying direct module access")

        log(f"\n  --- Module: {module_name.upper()} ---")

        # Navigate to module via SSO
        navigate_to_module(driver, module_name)

        try:
            results = test_fn(driver)
            stats["module_tests"][module_name] = results

            # Check for issues to file as bugs
            for r in results:
                if r.get("status") in ("error", "timeout", "blank", "redirect_to_login"):
                    bug_title = f"{module_name.capitalize()} module - {r['page']} page {r['status']}"
                    bug_body = (f"**Module:** {module_name}\n"
                                f"**Page:** {r['page']}\n"
                                f"**URL:** {r.get('url', 'N/A')}\n"
                                f"**Status:** {r['status']}\n"
                                f"**Details:** {r.get('details', 'N/A')}\n\n"
                                f"Found during 30-day HRMS simulation with SSO auth.\n"
                                f"Screenshot: {r.get('screenshot', 'N/A')}")
                    # Only file if it's a real error (not just redirect to login which is expected for SSO)
                    if r.get("status") != "redirect_to_login":
                        file_bug(bug_title, bug_body)

        except Exception as e:
            log(f"  Module test error for {module_name}: {e}")
            traceback.print_exc()
            stats["module_tests"][module_name] = [{"status": "exception", "details": str(e)[:200]}]

        modules_tested += 1

    if driver:
        try:
            driver.quit()
        except Exception:
            pass

    log("\n  MODULE TESTING COMPLETE")
    for mod, results in stats["module_tests"].items():
        loaded = sum(1 for r in results if r.get("status") == "loaded")
        errors = sum(1 for r in results if r.get("status") in ("error", "timeout", "blank"))
        redirects = sum(1 for r in results if r.get("status") == "redirect_to_login")
        log(f"    {mod}: {loaded} loaded, {errors} errors, {redirects} SSO redirects, {len(results)} total pages")

    # File a single SSO bug covering all modules that redirect to login
    all_redirect_modules = []
    for mod, results in stats["module_tests"].items():
        redirects = sum(1 for r in results if r.get("status") == "redirect_to_login")
        if redirects > 0:
            all_redirect_modules.append(f"{mod} ({redirects} pages)")
    if all_redirect_modules:
        file_bug(
            "All modules redirect to login - SSO via direct navigation does not work",
            f"**Affected modules:** {', '.join(all_redirect_modules)}\n\n"
            f"When navigating directly to module URLs after logging into the core platform, "
            f"all modules redirect to their /login page. SSO tokens are generated by the frontend "
            f"when clicking 'Launch' on the /modules page, so direct URL navigation cannot establish "
            f"authenticated sessions on module subdomains.\n\n"
            f"This means API-only or direct-navigation testing of modules is not possible without "
            f"the frontend SSO token generation flow.\n\n"
            f"Found during 30-day HRMS simulation.",
            labels=["bug", "sso", "30-day-sim"]
        )


# ============================================================
# PART 3: MONTH-END PAYROLL VIA SELENIUM
# ============================================================
def run_payroll_processing():
    log("\n" + "=" * 70)
    log("PART 3: MONTH-END PAYROLL PROCESSING")
    log("=" * 70)

    payroll_results = {}
    driver = None

    # Only test with primary org since SSO redirect is the same for all
    for org in ORGS[:1]:
        org_name = org["name"]
        log(f"\n  --- Payroll for {org_name} ---")

        try:
            if driver:
                driver.quit()
                time.sleep(1)
            driver = make_driver()

            # Login
            selenium_login(driver, org["email"], org["password"])

            # Navigate to payroll module
            navigate_to_module(driver, "payroll")

            base = MODULE_URLS["payroll"]

            # Check dashboard
            driver.get(f"{base}/dashboard")
            time.sleep(3)
            sc = screenshot(driver, f"payroll_dashboard_{org_name}")
            body_text = ""
            try:
                body_text = driver.find_element(By.TAG_NAME, "body").text[:1000]
            except Exception:
                pass

            # Look for payroll processing
            driver.get(f"{base}/payroll")
            time.sleep(3)
            screenshot(driver, f"payroll_processing_{org_name}")

            try:
                page_text = driver.find_element(By.TAG_NAME, "body").text
            except Exception:
                page_text = ""

            # Look for "Run Payroll" button
            run_payroll_found = False
            try:
                btns = driver.find_elements(By.XPATH,
                    "//*[contains(text(), 'Run Payroll') or contains(text(), 'Process Payroll') or contains(text(), 'Generate')]")
                if btns:
                    run_payroll_found = True
                    log(f"    Found 'Run Payroll' button: {btns[0].text}")
                    # Try clicking it
                    try:
                        btns[0].click()
                        time.sleep(3)
                        screenshot(driver, f"payroll_run_clicked_{org_name}")
                        # Look for month selector / confirmation
                        dialog_text = driver.find_element(By.TAG_NAME, "body").text[:500]
                        log(f"    After click: {dialog_text[:100]}")
                    except Exception as e:
                        log(f"    Could not click Run Payroll: {e}")
                else:
                    log(f"    No 'Run Payroll' button found")
            except Exception:
                pass

            # Check payslips
            driver.get(f"{base}/payslips")
            time.sleep(3)
            screenshot(driver, f"payroll_payslips_{org_name}")

            try:
                payslip_text = driver.find_element(By.TAG_NAME, "body").text[:500]
            except Exception:
                payslip_text = ""

            # Check deductions (PF, ESI, TDS)
            deduction_found = any(kw in payslip_text.lower() for kw in ["pf", "esi", "tds", "deduction", "provident"])

            payroll_results[org_name] = {
                "dashboard_loaded": len(body_text) > 50,
                "run_payroll_available": run_payroll_found,
                "payslips_page": len(payslip_text) > 50,
                "deductions_visible": deduction_found,
                "page_text_sample": page_text[:200],
            }

            log(f"    Dashboard: {'OK' if len(body_text) > 50 else 'EMPTY'}")
            log(f"    Run Payroll: {'FOUND' if run_payroll_found else 'NOT FOUND'}")
            log(f"    Payslips: {'OK' if len(payslip_text) > 50 else 'EMPTY'}")
            log(f"    Deductions: {'VISIBLE' if deduction_found else 'NOT VISIBLE'}")

        except Exception as e:
            log(f"    Payroll error for {org_name}: {e}")
            payroll_results[org_name] = {"error": str(e)[:200]}

    if driver:
        try:
            driver.quit()
        except Exception:
            pass

    stats["payroll_processing"] = payroll_results
    log("\n  PAYROLL PROCESSING COMPLETE")


# ============================================================
# PART 4: DATA INTEGRITY AUDIT
# ============================================================
def run_data_integrity_audit():
    log("\n" + "=" * 70)
    log("PART 4: DATA INTEGRITY AUDIT")
    log("=" * 70)

    audit_results = {}

    for org_cfg in ORGS:
        org_name = org_cfg["name"]
        log(f"\n  --- Audit: {org_name} ---")

        try:
            token, user, org = api_login(org_cfg["email"], org_cfg["password"])
        except Exception as e:
            log(f"  Login failed for audit: {e}")
            audit_results[org_name] = {"error": str(e)}
            continue

        results = {}

        # 1. Check employee count
        try:
            r = api_get("/users", token)
            if r.status_code == 200:
                users = r.json().get("data", [])
                results["employee_count"] = len(users)
                log(f"    Employees in API: {len(users)}")

                # Compare with setup data
                setup_count = 0
                for oc in org_configs:
                    if oc["admin_email"] == org_cfg["email"]:
                        domain = oc["domain"]
                        setup_count = len([e for e in all_employees if domain in e.get("email", "")])
                        break
                results["setup_employee_count"] = setup_count
                results["employee_count_match"] = len(users) >= setup_count
                log(f"    Setup data employees: {setup_count}")
                log(f"    Match: {results['employee_count_match']}")
        except Exception as e:
            results["employee_count_error"] = str(e)

        # 2. Check leave applications
        try:
            r = api_get("/leave/applications", token)
            if r.status_code == 200:
                leaves = r.json().get("data", [])
                results["total_leave_applications"] = len(leaves)
                status_counts = defaultdict(int)
                for lv in leaves:
                    status_counts[lv.get("status", "unknown")] += 1
                results["leave_status_breakdown"] = dict(status_counts)
                log(f"    Leave applications: {len(leaves)} (breakdown: {dict(status_counts)})")
        except Exception as e:
            results["leave_error"] = str(e)

        # 3. Check leave balances
        try:
            r = api_get("/leave/balances", token)
            if r.status_code == 200:
                balances = r.json().get("data", [])
                results["leave_balance_entries"] = len(balances)
                log(f"    Leave balance entries: {len(balances)}")
        except Exception as e:
            results["leave_balance_error"] = str(e)

        # 4. Check announcements
        try:
            r = api_get("/announcements", token)
            if r.status_code == 200:
                anns = r.json().get("data", [])
                results["announcements_count"] = len(anns)
                log(f"    Announcements: {len(anns)}")
        except Exception as e:
            results["announcements_error"] = str(e)

        # 5. Check helpdesk tickets
        try:
            r = api_get("/helpdesk/tickets", token)
            if r.status_code == 200:
                tickets = r.json().get("data", [])
                results["helpdesk_tickets_count"] = len(tickets)
                log(f"    Helpdesk tickets: {len(tickets)}")
        except Exception as e:
            results["tickets_error"] = str(e)

        # 6. Check forum posts
        try:
            r = api_get("/forum/posts", token)
            if r.status_code == 200:
                posts = r.json().get("data", [])
                results["forum_posts_count"] = len(posts)
                log(f"    Forum posts: {len(posts)}")
        except Exception as e:
            results["forum_error"] = str(e)

        # 7. Check assets
        try:
            r = api_get("/assets", token)
            if r.status_code == 200:
                assets = r.json().get("data", [])
                results["assets_count"] = len(assets)
                assigned = sum(1 for a in assets if a.get("assigned_to"))
                results["assets_assigned_count"] = assigned
                log(f"    Assets: {len(assets)} total, {assigned} assigned")
        except Exception as e:
            results["assets_error"] = str(e)

        # 8. Check policies
        try:
            r = api_get("/policies", token)
            if r.status_code == 200:
                policies = r.json().get("data", [])
                results["policies_count"] = len(policies)
                total_ack = sum(p.get("acknowledgment_count", 0) for p in policies)
                results["total_acknowledgments"] = total_ack
                log(f"    Policies: {len(policies)}, total acknowledgments: {total_ack}")
        except Exception as e:
            results["policies_error"] = str(e)

        # 9. Check events
        try:
            r = api_get("/events", token)
            if r.status_code == 200:
                events = r.json().get("data", [])
                results["events_count"] = len(events)
                log(f"    Events: {len(events)}")
        except Exception as e:
            results["events_error"] = str(e)

        # 10. Check surveys
        try:
            r = api_get("/surveys", token)
            if r.status_code == 200:
                surveys = r.json().get("data", [])
                results["surveys_count"] = len(surveys)
                log(f"    Surveys: {len(surveys)}")
        except Exception as e:
            results["surveys_error"] = str(e)

        # 11. Check audit trail
        try:
            r = api_get("/audit", token)
            if r.status_code == 200:
                audits = r.json().get("data", [])
                results["audit_entries"] = len(audits)
                log(f"    Audit entries: {len(audits)}")
        except Exception as e:
            results["audit_error"] = str(e)

        # 12. Check feedback
        try:
            r = api_get("/feedback", token)
            if r.status_code == 200:
                fb = r.json().get("data", [])
                results["feedback_count"] = len(fb)
                log(f"    Feedback: {len(fb)}")
        except Exception as e:
            results["feedback_error"] = str(e)

        # Data consistency flags
        issues = []
        if results.get("employee_count", 0) == 0:
            issues.append("No employees found via API")
        if not results.get("employee_count_match", True):
            issues.append(f"Employee count mismatch: API={results.get('employee_count')} vs setup={results.get('setup_employee_count')}")
        if results.get("total_leave_applications", 0) == 0:
            issues.append("No leave applications found")
        if results.get("announcements_count", 0) == 0:
            issues.append("No announcements found")

        results["data_issues"] = issues
        if issues:
            log(f"    DATA ISSUES: {issues}")
            for issue in issues:
                file_bug(
                    f"Data integrity issue for {org_name}: {issue}",
                    f"**Organization:** {org_name}\n**Issue:** {issue}\n\n"
                    f"Found during 30-day simulation data integrity audit.\n"
                    f"Full audit results: {json.dumps(results, indent=2, default=str)[:500]}"
                )

        audit_results[org_name] = results

    stats["data_integrity"] = audit_results
    log("\n  DATA INTEGRITY AUDIT COMPLETE")


# ============================================================
# MAIN
# ============================================================
def main():
    start_time = time.time()
    log("=" * 70)
    log("30-DAY HRMS SIMULATION WITH SSO - STARTING")
    log(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"API: {API_BASE}")
    log(f"Organizations: {[o['name'] for o in ORGS]}")
    log(f"Total employees: {len(all_employees)}")
    log("=" * 70)

    # PART 1: Core HRMS API
    try:
        run_core_simulation()
    except Exception as e:
        log(f"PART 1 FATAL ERROR: {e}")
        traceback.print_exc()

    # PART 2: Module testing via Selenium
    try:
        run_module_tests()
    except Exception as e:
        log(f"PART 2 FATAL ERROR: {e}")
        traceback.print_exc()

    # PART 3: Month-end payroll
    try:
        run_payroll_processing()
    except Exception as e:
        log(f"PART 3 FATAL ERROR: {e}")
        traceback.print_exc()

    # PART 4: Data integrity audit
    try:
        run_data_integrity_audit()
    except Exception as e:
        log(f"PART 4 FATAL ERROR: {e}")
        traceback.print_exc()

    # ---- FINAL REPORT ----
    elapsed = time.time() - start_time
    stats["elapsed_seconds"] = round(elapsed, 1)
    stats["completed_at"] = datetime.now().isoformat()

    log("\n" + "=" * 70)
    log("SIMULATION COMPLETE")
    log("=" * 70)
    log(f"Duration: {elapsed:.0f} seconds ({elapsed/60:.1f} minutes)")
    log(f"\nCORE API STATS:")
    log(f"  Attendance check-ins: {stats['attendance_checkins']}")
    log(f"  Attendance check-outs: {stats['attendance_checkouts']}")
    log(f"  Attendance conflicts: {stats['attendance_conflicts']}")
    log(f"  Leave apps created: {stats['leave_applications_created']}")
    log(f"  Leave apps approved: {stats['leave_applications_approved']}")
    log(f"  Announcements: {stats['announcements_created']}")
    log(f"  Events: {stats['events_created']}")
    log(f"  Surveys: {stats['surveys_created']}")
    log(f"  Helpdesk tickets: {stats['helpdesk_tickets_created']}")
    log(f"  Forum posts: {stats['forum_posts_created']}")
    log(f"  Wellness check-ins: {stats['wellness_checkins']}")
    log(f"  Feedback: {stats['feedback_created']}")
    log(f"  Assets created/assigned: {stats['assets_created']}/{stats['assets_assigned']}")
    log(f"  Policies created/ack: {stats['policies_created']}/{stats['policies_acknowledged']}")
    log(f"  API errors: {len(stats['api_errors'])}")

    log(f"\nMODULE TESTS:")
    for mod, results in stats.get("module_tests", {}).items():
        loaded = sum(1 for r in results if r.get("status") == "loaded")
        total = len(results)
        log(f"  {mod}: {loaded}/{total} pages loaded")

    log(f"\nBUGS FILED: {len(stats['bugs_filed'])}")
    for bug in stats["bugs_filed"]:
        log(f"  - {bug['title']}: {bug.get('url', 'N/A')}")

    log(f"\nDATA INTEGRITY:")
    for org_name, results in stats.get("data_integrity", {}).items():
        issues = results.get("data_issues", [])
        log(f"  {org_name}: {len(issues)} issues")
        for issue in issues:
            log(f"    - {issue}")

    # Save report
    try:
        # Make stats JSON serializable
        def make_serializable(obj):
            if isinstance(obj, (dict, defaultdict)):
                return {k: make_serializable(v) for k, v in obj.items()}
            elif isinstance(obj, (list, tuple)):
                return [make_serializable(i) for i in obj]
            elif isinstance(obj, (int, float, str, bool, type(None))):
                return obj
            else:
                return str(obj)

        serializable_stats = make_serializable(stats)
        with open(REPORT_PATH, "w") as f:
            json.dump(serializable_stats, f, indent=2, default=str)
        log(f"\nReport saved to: {REPORT_PATH}")
    except Exception as e:
        log(f"Failed to save report: {e}")

    # Print API errors summary
    if stats["api_errors"]:
        log(f"\nAPI ERRORS ({len(stats['api_errors'])} total):")
        # Group by endpoint
        by_endpoint = defaultdict(list)
        for err in stats["api_errors"]:
            ep = err.get("endpoint", "unknown")
            by_endpoint[ep].append(err)
        for ep, errs in by_endpoint.items():
            log(f"  {ep}: {len(errs)} errors")
            if errs:
                log(f"    Sample: {json.dumps(errs[0], default=str)[:200]}")


if __name__ == "__main__":
    main()
