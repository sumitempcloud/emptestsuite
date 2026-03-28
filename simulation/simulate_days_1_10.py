#!/usr/bin/env python3
"""
EMP Cloud 30-Day HRMS Simulation — Days 1-10
Simulates 163 real people using the system daily across 3 organizations.
"""

import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

_builtin_print = print
def print(*args, **kwargs):
    kwargs.setdefault('flush', True)
    _builtin_print(*args, **kwargs)

import json
import time
import random
import requests
from datetime import datetime, timedelta
from pathlib import Path

# ─── Config ────────────────────────────────────────────────────────────────────
BASE_URL = "https://test-empcloud-api.empcloud.com/api/v1"
GITHUB_PAT = "os.environ.get('GITHUB_TOKEN', 'YOUR_TOKEN_HERE')"
GITHUB_REPO = "EmpCloud/EmpCloud"
SETUP_PATH = r"C:\emptesting\simulation\setup_data.json"
STATE_PATH = r"C:\emptesting\simulation\day1_10_state.json"
SIM_START = datetime(2026, 3, 1)
REQ_DELAY = 0.02

# ─── Load Setup Data ──────────────────────────────────────────────────────────
with open(SETUP_PATH, "r", encoding="utf-8") as f:
    SETUP = json.load(f)
ORGS = SETUP["organizations"]
ALL_EMPLOYEES = SETUP["employees"]

# ─── Helpers ───────────────────────────────────────────────────────────────────

def get_org_employees(org_name):
    emps = []
    for e in ALL_EMPLOYEES:
        if e["organization"] != org_name:
            continue
        if not e.get("emp_code"):
            continue
        if e["email"].startswith("qa-") or e["email"].startswith("dup_"):
            continue
        if e["email"].startswith("dir") or e["email"].startswith("retest"):
            continue
        if "test" in e["first_name"].lower():
            continue
        emps.append(e)
    return emps

def get_org_managers(employees):
    return [e for e in employees if e.get("designation") and
            any(k in e["designation"].lower() for k in ["manager", "lead"])]

def get_leave_type_id(org, leave_name):
    for lt in org["leave_types"]:
        if leave_name.lower() in lt["name"].lower():
            return lt["id"]
    return None

_forum_cat_cache = {}
def get_forum_category(api, org_name):
    if org_name in _forum_cat_cache:
        return _forum_cat_cache[org_name]
    r = api.get("/forum/categories")
    cats = extract_list(r)
    cid = None
    for c in cats:
        if "general" in c.get("name", "").lower():
            cid = c["id"]; break
    if not cid and cats:
        cid = cats[0]["id"]
    _forum_cat_cache[org_name] = cid
    return cid

# ─── API Client with Token Cache ──────────────────────────────────────────────

_token_cache = {}  # email -> (token, expiry_time)
TOKEN_TTL = 780  # 13 minutes (tokens expire in 15 min)

class API:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        self.token = None
        self.email = None

    def _req(self, method, path, **kwargs):
        time.sleep(REQ_DELAY)
        try:
            r = self.session.request(method, f"{BASE_URL}{path}", timeout=15, **kwargs)
            # Auto-refresh on 401
            if r and r.status_code == 401 and self.email:
                if self.email in _token_cache:
                    del _token_cache[self.email]
                if self._do_login(self.email):
                    time.sleep(REQ_DELAY)
                    r = self.session.request(method, f"{BASE_URL}{path}", timeout=15, **kwargs)
            return r
        except Exception:
            return None

    def _do_login(self, email, password="Welcome@123"):
        time.sleep(REQ_DELAY)
        try:
            r = self.session.request("POST", f"{BASE_URL}/auth/login",
                                     json={"email": email, "password": password}, timeout=15)
        except Exception:
            return False
        if r and r.status_code == 200:
            data = r.json().get("data", {})
            token = None
            tokens = data.get("tokens", {})
            if isinstance(tokens, dict):
                token = tokens.get("access_token")
            if not token:
                token = data.get("token") or data.get("access_token")
            if token:
                _token_cache[email] = (token, time.time() + TOKEN_TTL)
                self.token = token
                self.session.headers["Authorization"] = f"Bearer {token}"
                self.email = email
                return True
        return False

    def login(self, email, password="Welcome@123"):
        cached = _token_cache.get(email)
        if cached and cached[1] > time.time():
            self.token = cached[0]
            self.session.headers["Authorization"] = f"Bearer {self.token}"
            self.email = email
            return True
        # Token expired or not cached
        if email in _token_cache:
            del _token_cache[email]
        return self._do_login(email, password)

    def get(self, path, params=None):
        return self._req("GET", path, params=params)

    def post(self, path, data=None):
        return self._req("POST", path, json=data)

    def put(self, path, data=None):
        return self._req("PUT", path, json=data)

def ok(r, codes=None):
    if r is None: return False
    return r.status_code in (codes or (200, 201, 204))

def ok_attendance(r):
    """Check-in/out: 200/201 = success, 409 = already done (counts as success)."""
    if r is None: return False
    return r.status_code in (200, 201, 409)

def extract_id(r):
    if not r or r.status_code not in (200, 201): return None
    try:
        d = r.json()
        if isinstance(d, dict):
            if "id" in d: return d["id"]
            dd = d.get("data", {})
            if isinstance(dd, dict): return dd.get("id")
    except: pass
    return None

def extract_list(r):
    if not r or r.status_code not in (200, 201): return []
    try:
        d = r.json()
        if isinstance(d, list): return d
        if isinstance(d, dict):
            dd = d.get("data", d)
            if isinstance(dd, list): return dd
            if isinstance(dd, dict):
                return dd.get("items", dd.get("rows", []))
    except: pass
    return []

# ─── State Tracker ─────────────────────────────────────────────────────────────

class SimState:
    def __init__(self):
        self.data = {
            "attendance": {}, "leave_applications": [], "assets_assigned": [],
            "tickets_created": [], "survey_responses": [], "announcements": [],
            "policies": [], "events": [], "forum_posts": [], "errors": [],
            "bugs_filed": [], "daily_summaries": {}, "active_surveys": {}
        }

    def add_attendance(self, org, day, count):
        self.data["attendance"].setdefault(org, {})[str(day)] = count

    def add_error(self, day, org, action, detail):
        self.data["errors"].append({"day": day, "org": org, "action": action, "detail": str(detail)[:200]})

    def save(self):
        with open(STATE_PATH, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, default=str)

state = SimState()

# ─── Bug Filing ────────────────────────────────────────────────────────────────

filed_bugs = set()

def file_bug(title, body):
    if title in filed_bugs: return
    filed_bugs.add(title)
    try:
        headers = {"Authorization": f"token {GITHUB_PAT}", "Accept": "application/vnd.github.v3+json"}
        r = requests.get(f"https://api.github.com/repos/{GITHUB_REPO}/issues",
                         headers=headers, params={"state": "open", "per_page": 100}, timeout=15)
        if r.status_code == 200:
            for issue in r.json():
                if title.lower() in issue["title"].lower():
                    requests.post(f"https://api.github.com/repos/{GITHUB_REPO}/issues/{issue['number']}/comments",
                                  headers=headers, json={"body": f"Comment by E2E Testing Agent -- 30-Day Simulation\n\n{body}"}, timeout=15)
                    state.data["bugs_filed"].append({"title": title, "action": "commented", "issue": issue["number"]})
                    return
        r = requests.post(f"https://api.github.com/repos/{GITHUB_REPO}/issues",
                          headers=headers, json={"title": title, "body": f"Comment by E2E Testing Agent -- 30-Day Simulation\n\n{body}", "labels": ["bug", "e2e-simulation"]}, timeout=15)
        if r.status_code == 201:
            state.data["bugs_filed"].append({"title": title, "action": "created", "issue": r.json()["number"]})
            print(f"  [BUG FILED] {title}")
    except Exception as e:
        print(f"  [BUG FILING ERROR] {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# DAY 1 — Onboarding & First Login
# ═══════════════════════════════════════════════════════════════════════════════

def simulate_day1():
    print("\n" + "=" * 60)
    print("=== DAY 1 -- Onboarding & First Login ===")
    print("=" * 60)
    day_summary = {}

    for org in ORGS:
        nm = org["name"]
        emps = get_org_employees(nm)
        api = API()
        print(f"\n--- {nm} ({len(emps)} employees) ---")

        if not api.login(org["admin_email"], org["admin_password"]):
            print(f"  [ERROR] Admin login failed")
            state.add_error(1, nm, "admin_login", "Failed")
            day_summary[nm] = {"employees": len(emps), "errors": 1}
            continue
        print(f"  Admin logged in")

        # Test 5 random employee logins
        test_emps = random.sample(emps, min(5, len(emps)))
        login_ok = sum(1 for e in test_emps if API().login(e["email"]))
        print(f"  Login test: {login_ok}/5 succeeded")

        # Announcement
        r = api.post("/announcements", {
            "title": f"Welcome to {nm} -- Q1 Kickoff",
            "content": f"Welcome everyone to {nm}! Let's make Q1 2026 our best quarter yet.",
            "priority": "high"
        })
        ann_id = extract_id(r)
        print(f"  Announcement: {'OK' if ann_id else 'FAILED'} (id={ann_id})")
        if ann_id: state.data["announcements"].append({"id": ann_id, "org": nm, "day": 1})

        # Policy
        r = api.post("/policies", {
            "title": "Work from Home Policy",
            "content": "Employees may work from home up to 2 days per week with manager approval.",
            "category": "HR"
        })
        pol_id = extract_id(r)
        print(f"  Policy: {'OK' if pol_id else 'FAILED'} (id={pol_id})")
        if pol_id: state.data["policies"].append({"id": pol_id, "org": nm, "day": 1})

        # Event (correct fields: start_date, end_date, event_type)
        r = api.post("/events", {
            "title": f"All Hands Meeting -- March 1",
            "description": f"Quarterly all-hands for {nm}. Q1 goals, updates, Q&A.",
            "event_type": "meeting",
            "start_date": SIM_START.strftime("%Y-%m-%dT10:00:00"),
            "end_date": SIM_START.strftime("%Y-%m-%dT11:30:00"),
            "location": "Main Conference Room / Zoom"
        })
        evt_id = extract_id(r)
        print(f"  Event: {'OK' if evt_id else 'FAILED'} (id={evt_id})")
        if evt_id: state.data["events"].append({"id": evt_id, "org": nm, "day": 1})

        # Document (skip file upload, just log)
        print(f"  Document: SKIPPED (requires file upload)")

        # 10 employees: profile, acknowledge policy, RSVP
        active = random.sample(emps, min(10, len(emps)))
        prof_ok = pol_ack = evt_rsvp = 0
        for emp in active:
            ea = API()
            if not ea.login(emp["email"]): continue
            if ok(ea.get(f"/employees/{emp['id']}/profile")): prof_ok += 1
            if pol_id and ok(ea.post(f"/policies/{pol_id}/acknowledge", {})): pol_ack += 1
            if evt_id and ok(ea.post(f"/events/{evt_id}/register", {})): evt_rsvp += 1

        print(f"  Profiles: {prof_ok}/10, Policy acks: {pol_ack}/10, Event RSVPs: {evt_rsvp}/10")
        day_summary[nm] = {
            "employees": len(emps), "login_tested": login_ok,
            "announcement": 1 if ann_id else 0, "policy": 1 if pol_id else 0,
            "event": 1 if evt_id else 0, "profiles": prof_ok, "pol_acks": pol_ack, "rsvps": evt_rsvp
        }

    state.data["daily_summaries"]["day1"] = day_summary
    _print_day_summary(1, day_summary)


# ═══════════════════════════════════════════════════════════════════════════════
# DAY 2 — First Full Working Day
# ═══════════════════════════════════════════════════════════════════════════════

def simulate_day2():
    print("\n" + "=" * 60)
    print("=== DAY 2 -- First Full Working Day ===")
    print("=" * 60)
    sim_date = SIM_START + timedelta(days=1)
    day_summary = {}

    for org in ORGS:
        nm = org["name"]
        emps = get_org_employees(nm)
        print(f"\n--- {nm} ---")

        # Clock in all employees
        ci_ok = co_ok = late = 0
        for i, emp in enumerate(emps):
            ea = API()
            if not ea.login(emp["email"]): continue

            if i < 5:
                hour, minute = 10, random.randint(0, 45)
                late += 1
            else:
                hour = random.choice([8, 9])
                minute = random.randint(0, 59) if hour == 9 else random.randint(45, 59)

            ci_time = sim_date.replace(hour=hour, minute=minute)
            r = ea.post("/attendance/check-in", {"timestamp": ci_time.isoformat(), "date": sim_date.strftime("%Y-%m-%d")})
            if ok_attendance(r): ci_ok += 1

            # Clock out (3 skip)
            if i >= 3:
                co_h = random.randint(17, 18)
                co_m = random.randint(0, 59) if co_h == 17 else random.randint(0, 30)
                co_time = sim_date.replace(hour=co_h, minute=co_m)
                r = ea.post("/attendance/check-out", {"timestamp": co_time.isoformat(), "date": sim_date.strftime("%Y-%m-%d")})
                if ok_attendance(r): co_ok += 1

        print(f"  Check-ins: {ci_ok}/{len(emps)}, Check-outs: {co_ok}/{len(emps)-3}, Late: {late}")
        state.add_attendance(nm, 2, ci_ok)

        # 5 employees: tickets, forum posts
        ticket_titles = ["VPN not working from home", "Need software license for Adobe", "Laptop keyboard sticking",
                         "Cannot access shared drive", "Email not syncing on mobile"]
        forum_topics = ["Coffee machine on 3rd floor broken", "Carpool from Whitefield?",
                        "Book club: March reading suggestions", "Lost: blue umbrella in cafeteria", "Team lunch spots?"]
        active5 = random.sample(emps, min(5, len(emps)))
        tkt = frm = 0
        for j, emp in enumerate(active5):
            ea = API()
            if not ea.login(emp["email"]): continue
            # Ticket (uses 'subject' not 'title')
            r = ea.post("/helpdesk/tickets", {
                "subject": ticket_titles[j], "description": f"Issue: {ticket_titles[j]}. Please help.",
                "priority": random.choice(["low", "medium", "high"]), "category": "general"
            })
            if ok(r):
                tkt += 1
                state.data["tickets_created"].append({"id": extract_id(r), "org": nm, "day": 2, "title": ticket_titles[j]})
            # Forum (uses category_id, post_type)
            r = ea.post("/forum/posts", {
                "title": forum_topics[j], "content": f"Hey everyone! {forum_topics[j]}",
                "category_id": get_forum_category(ea, nm), "post_type": "discussion"
            })
            if ok(r):
                frm += 1
                state.data["forum_posts"].append({"org": nm, "day": 2})

        print(f"  Tickets: {tkt}/5, Forum: {frm}/5")
        day_summary[nm] = {"checkins": ci_ok, "checkouts": co_ok, "late": late, "tickets": tkt, "forum": frm}

    state.data["daily_summaries"]["day2"] = day_summary
    _print_day_summary(2, day_summary)


# ═══════════════════════════════════════════════════════════════════════════════
# DAY 3 — Leave Applications
# ═══════════════════════════════════════════════════════════════════════════════

def simulate_day3():
    print("\n" + "=" * 60)
    print("=== DAY 3 -- Leave Applications ===")
    print("=" * 60)
    sim_date = SIM_START + timedelta(days=2)
    day_summary = {}

    for org in ORGS:
        nm = org["name"]
        emps = get_org_employees(nm)
        managers = get_org_managers(emps)
        non_mgr = [e for e in emps if e not in managers]
        print(f"\n--- {nm} ---")

        sick_lt = get_leave_type_id(org, "Sick")
        casual_lt = get_leave_type_id(org, "Casual")
        earned_lt = get_leave_type_id(org, "Earned")
        leave_apps = []

        def apply_leave(emp, lt_id, lt_name, start, end, reason):
            ea = API()
            if not ea.login(emp["email"]): return
            days_count = (end - start).days + 1
            r = ea.post("/leave/applications", {
                "leave_type_id": lt_id, "start_date": start.strftime("%Y-%m-%d"),
                "end_date": end.strftime("%Y-%m-%d"), "days_count": days_count, "reason": reason
            })
            lid = extract_id(r)
            if ok(r):
                leave_apps.append({"id": lid, "emp": emp["id"], "type": lt_name, "status": "pending"})
            else:
                if r: print(f"    Leave fail {emp['email']}: {r.status_code} {r.text[:80]}")

        # 5 Sick Leave
        sick_emps = random.sample(non_mgr, min(5, len(non_mgr)))
        for emp in sick_emps:
            days = random.randint(1, 2)
            s = sim_date + timedelta(days=1)
            apply_leave(emp, sick_lt, "Sick", s, s + timedelta(days=days-1),
                       random.choice(["Fever and cold", "Doctor appointment", "Migraine", "Stomach bug"]))

        # 3 Casual Leave
        remaining = [e for e in non_mgr if e not in sick_emps]
        casual_emps = random.sample(remaining, min(3, len(remaining)))
        for emp in casual_emps:
            d = sim_date + timedelta(days=2)
            apply_leave(emp, casual_lt, "Casual", d, d,
                       random.choice(["Personal work", "Family event", "Bank work"]))

        # 2 Earned Leave
        remaining2 = [e for e in remaining if e not in casual_emps]
        earned_emps = random.sample(remaining2, min(2, len(remaining2)))
        for emp in earned_emps:
            days = random.randint(3, 5)
            s = sim_date + timedelta(days=5)
            apply_leave(emp, earned_lt, "Earned", s, s + timedelta(days=days-1),
                       random.choice(["Family vacation", "Travel plans", "Wedding"]))

        print(f"  Leave apps submitted: {len(leave_apps)}")

        # Admin approves 7, rejects 3
        admin = API()
        if admin.login(org["admin_email"], org["admin_password"]):
            approved = rejected = 0
            reject_reasons = ["Project deadline approaching", "Too many on leave", "Critical sprint week"]
            for i, la in enumerate(leave_apps):
                if la["id"] is None: continue
                if i < 7:
                    r = admin.put(f"/leave/applications/{la['id']}/approve", {"remarks": "Approved"})
                    if ok(r): la["status"] = "approved"; approved += 1
                else:
                    r = admin.put(f"/leave/applications/{la['id']}/reject", {"remarks": reject_reasons[i % 3]})
                    if ok(r): la["status"] = "rejected"; rejected += 1
            print(f"  Approved: {approved}, Rejected: {rejected}")

        for la in leave_apps:
            la["org"] = nm; la["day"] = 3
            state.data["leave_applications"].append(la)

        day_summary[nm] = {
            "submitted": len(leave_apps),
            "sick": len([l for l in leave_apps if l["type"] == "Sick"]),
            "casual": len([l for l in leave_apps if l["type"] == "Casual"]),
            "earned": len([l for l in leave_apps if l["type"] == "Earned"]),
            "approved": len([l for l in leave_apps if l["status"] == "approved"]),
            "rejected": len([l for l in leave_apps if l["status"] == "rejected"])
        }

    state.data["daily_summaries"]["day3"] = day_summary
    _print_day_summary(3, day_summary)


# ═══════════════════════════════════════════════════════════════════════════════
# DAY 4 — Normal Working Day
# ═══════════════════════════════════════════════════════════════════════════════

def simulate_day4():
    print("\n" + "=" * 60)
    print("=== DAY 4 -- Normal Working Day ===")
    print("=" * 60)
    sim_date = SIM_START + timedelta(days=3)
    day_summary = {}
    on_leave = {la["emp"] for la in state.data["leave_applications"] if la["status"] == "approved"}

    for org in ORGS:
        nm = org["name"]
        emps = get_org_employees(nm)
        working = [e for e in emps if e["id"] not in on_leave]
        on_lv = [e for e in emps if e["id"] in on_leave]
        print(f"\n--- {nm} (working: {len(working)}, leave: {len(on_lv)}) ---")

        ci_ok = co_ok = 0
        for emp in working:
            ea = API()
            if not ea.login(emp["email"]): continue
            h = random.choice([8, 9])
            m = random.randint(30, 59) if h == 8 else random.randint(0, 30)
            r = ea.post("/attendance/check-in", {"timestamp": sim_date.replace(hour=h, minute=m).isoformat(), "date": sim_date.strftime("%Y-%m-%d")})
            if ok_attendance(r): ci_ok += 1
            co_h = random.randint(17, 19)
            r = ea.post("/attendance/check-out", {"timestamp": sim_date.replace(hour=co_h, minute=random.randint(0, 59)).isoformat(), "date": sim_date.strftime("%Y-%m-%d")})
            if ok_attendance(r): co_ok += 1

        print(f"  Check-ins: {ci_ok}, Check-outs: {co_ok}")
        state.add_attendance(nm, 4, ci_ok)

        # 2 tickets
        tkt = 0
        for emp in random.sample(working, min(2, len(working))):
            ea = API()
            if not ea.login(emp["email"]): continue
            r = ea.post("/helpdesk/tickets", {
                "subject": random.choice(["Printer not working", "Need Jira access"]),
                "description": "Please help.", "priority": "normal", "category": "general"
            })
            if ok(r): tkt += 1; state.data["tickets_created"].append({"id": extract_id(r), "org": nm, "day": 4})

        # 1 feedback
        fb = 0
        emp = random.choice(working)
        ea = API()
        if ea.login(emp["email"]):
            r = ea.post("/feedback", {
                "category": "general", "subject": "Onboarding feedback",
                "message": "The new onboarding process was smooth. Suggestion: add a buddy system.", "is_anonymous": True
            })
            if ok(r): fb = 1

        print(f"  Tickets: {tkt}, Feedback: {fb}")
        day_summary[nm] = {"working": len(working), "on_leave": len(on_lv), "checkins": ci_ok, "checkouts": co_ok, "tickets": tkt, "feedback": fb}

    state.data["daily_summaries"]["day4"] = day_summary
    _print_day_summary(4, day_summary)


# ═══════════════════════════════════════════════════════════════════════════════
# DAY 5 — Asset Assignment
# ═══════════════════════════════════════════════════════════════════════════════

def simulate_day5():
    print("\n" + "=" * 60)
    print("=== DAY 5 -- Asset Assignment ===")
    print("=" * 60)
    day_summary = {}

    for org in ORGS:
        nm = org["name"]
        emps = get_org_employees(nm)
        api = API()
        print(f"\n--- {nm} ---")
        if not api.login(org["admin_email"], org["admin_password"]):
            print(f"  [ERROR] Admin login failed"); continue

        # Get asset categories
        r = api.get("/assets/categories")
        cats = extract_list(r)
        laptop_cat = next((c["id"] for c in cats if "laptop" in c["name"].lower()), cats[0]["id"] if cats else None)
        monitor_cat = next((c["id"] for c in cats if "monitor" in c["name"].lower()), cats[0]["id"] if cats else None)
        acc_cat = next((c["id"] for c in cats if "accessor" in c["name"].lower()), cats[0]["id"] if cats else None)

        # Create 20 assets
        assets = []
        prefix = nm[:2].upper()
        for i in range(10):
            r = api.post("/assets", {"name": f"Dell Latitude {5000+i}", "category_id": laptop_cat,
                                     "serial_number": f"SIM-{prefix}-L{i:03d}", "status": "available"})
            if ok(r): assets.append({"id": extract_id(r), "type": "Laptop"})
        for i in range(5):
            r = api.post("/assets", {"name": f"LG Monitor {27+i}in", "category_id": monitor_cat,
                                     "serial_number": f"SIM-{prefix}-M{i:03d}", "status": "available"})
            if ok(r): assets.append({"id": extract_id(r), "type": "Monitor"})
        for i in range(5):
            r = api.post("/assets", {"name": f"Logitech Keyboard {i}", "category_id": acc_cat,
                                     "serial_number": f"SIM-{prefix}-K{i:03d}", "status": "available"})
            if ok(r): assets.append({"id": extract_id(r), "type": "Keyboard"})
        print(f"  Assets created: {len(assets)}")

        # Assign
        assign_emps = random.sample(emps, min(15, len(emps)))
        assigned = 0
        laptops = [a for a in assets if a["type"] == "Laptop"]
        monitors = [a for a in assets if a["type"] == "Monitor"]

        for i, emp in enumerate(assign_emps[:10]):
            if i < len(laptops) and laptops[i]["id"]:
                r = api.post(f"/assets/{laptops[i]['id']}/assign", {"assigned_to": emp["id"]})
                if ok(r):
                    assigned += 1
                    state.data["assets_assigned"].append({"asset_id": laptops[i]["id"], "emp_id": emp["id"], "org": nm, "type": "Laptop"})
        for i, emp in enumerate(assign_emps[10:15]):
            if i < len(monitors) and monitors[i]["id"]:
                r = api.post(f"/assets/{monitors[i]['id']}/assign", {"assigned_to": emp["id"]})
                if ok(r):
                    assigned += 1
                    state.data["assets_assigned"].append({"asset_id": monitors[i]["id"], "emp_id": emp["id"], "org": nm, "type": "Monitor"})
        print(f"  Assigned: {assigned}")

        # 5 check my assets
        my_ok = 0
        for emp in random.sample(assign_emps[:10], min(5, len(assign_emps[:10]))):
            ea = API()
            if ea.login(emp["email"]) and ok(ea.get("/assets/my")): my_ok += 1
        print(f"  My Assets checked: {my_ok}/5")

        day_summary[nm] = {"created": len(assets), "assigned": assigned, "verified": my_ok}

    state.data["daily_summaries"]["day5"] = day_summary
    _print_day_summary(5, day_summary)


# ═══════════════════════════════════════════════════════════════════════════════
# DAY 6 — HR Admin Tasks
# ═══════════════════════════════════════════════════════════════════════════════

def simulate_day6():
    print("\n" + "=" * 60)
    print("=== DAY 6 -- HR Admin Tasks ===")
    print("=" * 60)
    day_summary = {}

    for org in ORGS:
        nm = org["name"]
        api = API()
        print(f"\n--- {nm} ---")
        if not api.login(org["admin_email"], org["admin_password"]): continue

        # Announcement
        r = api.post("/announcements", {"title": "Company Holiday -- March 14",
            "content": "March 14 is a company holiday. Offices closed.", "priority": "normal"})
        ann_ok = ok(r)
        if ann_ok: state.data["announcements"].append({"id": extract_id(r), "org": nm, "day": 6})
        print(f"  Announcement: {'OK' if ann_ok else 'FAILED'}")

        # Survey
        r = api.post("/surveys", {"title": "Office Satisfaction Survey",
            "description": "Help us improve your workplace!", "type": "engagement",
            "is_anonymous": True, "target_type": "all"})
        sid = extract_id(r)
        print(f"  Survey: {'OK' if sid else 'FAILED'} (id={sid})")
        if sid: state.data["active_surveys"][nm] = sid

        # Attendance report
        r = api.get("/attendance/monthly-report")
        print(f"  Attendance report: {'OK' if ok(r) else 'FAILED'}")

        # Leave dashboard
        r = api.get("/leave/calendar")
        print(f"  Leave dashboard: {'OK' if ok(r) else 'FAILED'}")

        day_summary[nm] = {"announcement": 1 if ann_ok else 0, "survey": 1 if sid else 0}

    state.data["daily_summaries"]["day6"] = day_summary
    _print_day_summary(6, day_summary)


# ═══════════════════════════════════════════════════════════════════════════════
# DAY 7 — Employee Engagement
# ═══════════════════════════════════════════════════════════════════════════════

def simulate_day7():
    print("\n" + "=" * 60)
    print("=== DAY 7 -- Employee Engagement ===")
    print("=" * 60)
    sim_date = SIM_START + timedelta(days=6)
    day_summary = {}

    forum_topics = [
        "Tips for productive WFH", "Best lunch spots near office", "Cricket match this weekend?",
        "Standing desk recommendations", "Q2 team building ideas", "Good leadership reads",
        "Fitness challenge -- who's in?", "Parking needs improvement", "New cafe menu is great", "Weekend hiking group"
    ]

    for org in ORGS:
        nm = org["name"]
        emps = get_org_employees(nm)
        active = random.sample(emps, min(10, len(emps)))
        sid = state.data.get("active_surveys", {}).get(nm)
        print(f"\n--- {nm} ---")

        srv = frm = notif = 0
        for i, emp in enumerate(active):
            ea = API()
            if not ea.login(emp["email"]): continue

            # Survey response
            if sid:
                r = ea.post(f"/surveys/{sid}/respond", {
                    "responses": [{"questionIndex": 0, "answer": random.choice(["Very satisfied", "Satisfied", "Neutral", "Needs improvement"])}]
                })
                if ok(r): srv += 1; state.data["survey_responses"].append({"org": nm, "day": 7, "survey_id": sid})

            # Forum
            r = ea.post("/forum/posts", {"title": forum_topics[i], "content": f"Thoughts on: {forum_topics[i]}",
                                         "category_id": get_forum_category(ea, nm), "post_type": "discussion"})
            if ok(r): frm += 1; state.data["forum_posts"].append({"org": nm, "day": 7})

            # Notifications
            if ok(ea.get("/notifications")): notif += 1

        print(f"  Survey: {srv}/10, Forum: {frm}/10, Notif: {notif}/10")
        day_summary[nm] = {"surveys": srv, "forum": frm, "notifications": notif}

    state.data["daily_summaries"]["day7"] = day_summary
    _print_day_summary(7, day_summary)


# ═══════════════════════════════════════════════════════════════════════════════
# DAY 8 — More Leave & Comp-Off
# ═══════════════════════════════════════════════════════════════════════════════

def simulate_day8():
    print("\n" + "=" * 60)
    print("=== DAY 8 -- More Leave & Comp-Off ===")
    print("=" * 60)
    sim_date = SIM_START + timedelta(days=7)
    day_summary = {}

    for org in ORGS:
        nm = org["name"]
        emps = get_org_employees(nm)
        managers = get_org_managers(emps)
        non_mgr = [e for e in emps if e not in managers]
        print(f"\n--- {nm} ---")

        comp_lt = get_leave_type_id(org, "Compensatory")
        sick_lt = get_leave_type_id(org, "Sick")
        casual_lt = get_leave_type_id(org, "Casual")
        earned_lt = get_leave_type_id(org, "Earned")
        leave_apps = []

        # 3 comp-off
        for emp in random.sample(non_mgr, min(3, len(non_mgr))):
            ea = API()
            if not ea.login(emp["email"]): continue
            r = ea.post("/leave/comp-off", {"date": (sim_date + timedelta(days=2)).strftime("%Y-%m-%d"),
                "workedOn": (sim_date - timedelta(days=2)).strftime("%Y-%m-%d"),
                "reason": "Worked on Saturday for release"})
            if ok(r):
                leave_apps.append({"id": extract_id(r), "emp": emp["id"], "type": "Comp-Off", "status": "pending"})
            else:
                # fallback
                r = ea.post("/leave/applications", {"leaveTypeId": comp_lt,
                    "startDate": (sim_date + timedelta(days=2)).strftime("%Y-%m-%d"),
                    "endDate": (sim_date + timedelta(days=2)).strftime("%Y-%m-%d"),
                    "reason": "Comp-off for Saturday work", "type": "full_day"})
                if ok(r):
                    leave_apps.append({"id": extract_id(r), "emp": emp["id"], "type": "Comp-Off", "status": "pending"})

        # 4 mixed
        lt_mix = [(sick_lt, "Sick", "Not feeling well"), (casual_lt, "Casual", "Personal work"),
                  (earned_lt, "Earned", "Short trip"), (casual_lt, "Casual", "Family function")]
        used = {la["emp"] for la in leave_apps}
        pool = [e for e in non_mgr if e["id"] not in used]
        for i, emp in enumerate(random.sample(pool, min(4, len(pool)))):
            ea = API()
            if not ea.login(emp["email"]): continue
            lt_id, lt_name, reason = lt_mix[i]
            days = 1 if lt_name in ("Casual", "Sick") else random.randint(2, 3)
            s = sim_date + timedelta(days=3)
            r = ea.post("/leave/applications", {"leave_type_id": lt_id, "start_date": s.strftime("%Y-%m-%d"),
                "end_date": (s + timedelta(days=days-1)).strftime("%Y-%m-%d"), "days_count": days, "reason": reason})
            if ok(r):
                leave_apps.append({"id": extract_id(r), "emp": emp["id"], "type": lt_name, "status": "pending"})

        print(f"  Leave apps: {len(leave_apps)}")

        # Admin approves all
        admin = API()
        ap = 0
        if admin.login(org["admin_email"], org["admin_password"]):
            for la in leave_apps:
                if la["id"] and ok(admin.put(f"/leave/applications/{la['id']}/approve", {"remarks": "Approved"})):
                    la["status"] = "approved"; ap += 1
        print(f"  Approved: {ap}")

        # Balance checks
        bc = 0
        for emp in random.sample(emps, min(3, len(emps))):
            ea = API()
            if ea.login(emp["email"]) and ok(ea.get("/leave/balances")): bc += 1
        print(f"  Balance checks: {bc}")

        for la in leave_apps:
            la["org"] = nm; la["day"] = 8
            state.data["leave_applications"].append(la)

        day_summary[nm] = {"comp_off": len([l for l in leave_apps if l["type"] == "Comp-Off"]),
                           "other": len([l for l in leave_apps if l["type"] != "Comp-Off"]),
                           "approved": ap, "balance_checks": bc}

    state.data["daily_summaries"]["day8"] = day_summary
    _print_day_summary(8, day_summary)


# ═══════════════════════════════════════════════════════════════════════════════
# DAY 9 — Helpdesk & Knowledge Base
# ═══════════════════════════════════════════════════════════════════════════════

def simulate_day9():
    print("\n" + "=" * 60)
    print("=== DAY 9 -- Helpdesk & Knowledge Base ===")
    print("=" * 60)
    day_summary = {}

    tickets_t = [
        ("WiFi keeps disconnecting", "WiFi drops every 10 minutes on my laptop."),
        ("Need dual monitor", "Productivity limited with single screen."),
        ("Outlook not syncing", "Calendar events missing on mobile."),
        ("Badge not working", "Cannot enter building since yesterday."),
        ("Software crashes after update", "Laptop crashes randomly after Windows update."),
    ]

    for org in ORGS:
        nm = org["name"]
        emps = get_org_employees(nm)
        print(f"\n--- {nm} ---")

        # 5 tickets
        tkt_emps = random.sample(emps, min(5, len(emps)))
        tkt = 0
        for i, emp in enumerate(tkt_emps):
            ea = API()
            if not ea.login(emp["email"]): continue
            subj, desc = tickets_t[i]
            r = ea.post("/helpdesk/tickets", {"subject": subj, "description": desc,
                "priority": random.choice(["low", "medium", "high"]), "category": "general"})
            if ok(r):
                tkt += 1
                state.data["tickets_created"].append({"id": extract_id(r), "org": nm, "day": 9, "title": subj})
        print(f"  Tickets: {tkt}/5")

        # Admin resolves/updates
        admin = API()
        resolved = in_prog = 0
        if admin.login(org["admin_email"], org["admin_password"]):
            r = admin.get("/helpdesk/tickets")
            tickets = extract_list(r)
            open_tickets = [t for t in tickets if t.get("status") == "open"]
            for i, t in enumerate(open_tickets[:5]):
                tid = t.get("id")
                if not tid: continue
                if i < 3:
                    if ok(admin.put(f"/helpdesk/tickets/{tid}", {"status": "resolved"})): resolved += 1
                else:
                    if ok(admin.put(f"/helpdesk/tickets/{tid}", {"status": "in_progress"})): in_prog += 1
            print(f"  Resolved: {resolved}, In Progress: {in_prog}")

            # Knowledge base (endpoint returns 404 -- not yet implemented)
            print(f"  KB article: SKIPPED (endpoint not available)")

        day_summary[nm] = {"tickets": tkt, "resolved": resolved, "in_progress": in_prog}

    state.data["daily_summaries"]["day9"] = day_summary
    _print_day_summary(9, day_summary)


# ═══════════════════════════════════════════════════════════════════════════════
# DAY 10 — Mid-Month Check
# ═══════════════════════════════════════════════════════════════════════════════

def simulate_day10():
    print("\n" + "=" * 60)
    print("=== DAY 10 -- Mid-Month Check ===")
    print("=" * 60)
    day_summary = {}

    for org in ORGS:
        nm = org["name"]
        emps = get_org_employees(nm)
        api = API()
        print(f"\n--- {nm} ---")
        if not api.login(org["admin_email"], org["admin_password"]): continue

        # Reports
        att = ok(api.get("/attendance/monthly-report"))
        leave = ok(api.get("/leave/calendar"))
        bal = ok(api.get("/leave/balances"))
        org_chart = ok(api.get("/users/org-chart"))
        print(f"  Att report: {'OK' if att else 'FAIL'}, Leave dash: {'OK' if leave else 'FAIL'}, "
              f"Balances: {'OK' if bal else 'FAIL'}, Org chart: {'OK' if org_chart else 'FAIL'}")

        # Announcement
        r = api.post("/announcements", {"title": "Mid-month team update",
            "content": f"Great progress {nm}! Onboarding complete, survey results coming, performance reviews next week.",
            "priority": "normal"})
        ann = ok(r)
        if ann: state.data["announcements"].append({"id": extract_id(r), "org": nm, "day": 10})
        print(f"  Announcement: {'OK' if ann else 'FAIL'}")

        # Stats
        org_lv = [l for l in state.data["leave_applications"] if l.get("org") == nm]
        org_tk = [t for t in state.data["tickets_created"] if t.get("org") == nm]
        org_as = [a for a in state.data["assets_assigned"] if a.get("org") == nm]
        print(f"  10-day totals: {len(org_lv)} leaves, {len(org_tk)} tickets, {len(org_as)} assets")

        day_summary[nm] = {"att_report": att, "leave_dash": leave, "org_chart": org_chart,
                           "announcement": ann, "leaves": len(org_lv), "tickets": len(org_tk), "assets": len(org_as)}

    state.data["daily_summaries"]["day10"] = day_summary
    _print_day_summary(10, day_summary)


# ─── Utilities ─────────────────────────────────────────────────────────────────

def _print_day_summary(day, summary):
    print(f"\n=== DAY {day} Summary ===")
    for nm, s in summary.items():
        parts = [f"{k}={v}" for k, v in s.items()]
        print(f"  {nm}: {', '.join(parts)}")
    print(f"  Bugs filed: {len(state.data['bugs_filed'])}")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    print("=" * 60)
    print("EMP Cloud 30-Day Simulation -- Days 1-10")
    print(f"Start: {SIM_START.strftime('%Y-%m-%d')}")
    print(f"Orgs: {', '.join(o['name'] for o in ORGS)}")
    for o in ORGS:
        print(f"  {o['name']}: {len(get_org_employees(o['name']))} employees")
    print("=" * 60)

    days = [
        (1, simulate_day1), (2, simulate_day2), (3, simulate_day3),
        (4, simulate_day4), (5, simulate_day5), (6, simulate_day6),
        (7, simulate_day7), (8, simulate_day8), (9, simulate_day9),
        (10, simulate_day10),
    ]

    for day_num, day_func in days:
        try:
            day_func()
        except Exception as e:
            print(f"\n[CRITICAL ERROR] Day {day_num}: {e}")
            import traceback; traceback.print_exc()
            state.add_error(day_num, "ALL", "day_execution", str(e))
        state.save()
        print(f"[State saved]")

    # Final
    print("\n" + "=" * 60)
    print("=== FINAL 10-DAY SUMMARY ===")
    print("=" * 60)
    for o in ORGS:
        nm = o["name"]
        emps = get_org_employees(nm)
        lv = [l for l in state.data["leave_applications"] if l.get("org") == nm]
        tk = [t for t in state.data["tickets_created"] if t.get("org") == nm]
        a = [x for x in state.data["assets_assigned"] if x.get("org") == nm]
        sv = [x for x in state.data["survey_responses"] if x.get("org") == nm]
        an = [x for x in state.data["announcements"] if x.get("org") == nm]
        att = sum(state.data["attendance"].get(nm, {}).values())
        print(f"\n{nm}: {len(emps)} employees")
        print(f"  Attendance records: {att}")
        print(f"  Leaves: {len(lv)} (approved: {len([l for l in lv if l['status']=='approved'])})")
        print(f"  Assets: {len(a)}, Tickets: {len(tk)}, Surveys: {len(sv)}, Announcements: {len(an)}")

    print(f"\nBugs filed: {len(state.data['bugs_filed'])}")
    print(f"Errors: {len(state.data['errors'])}")
    print(f"Tokens cached: {len(_token_cache)}")
    print(f"State: {STATE_PATH}")

if __name__ == "__main__":
    main()
