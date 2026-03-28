#!/usr/bin/env python3
"""
EMP Cloud HRMS - 30-Day Simulation Setup
Creates 3 orgs with 50 employees each, departments, leave types, shifts.
"""

import sys
import os
import json
import time
import random
import requests
from datetime import date, timedelta

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
API_BASE = "https://test-empcloud-api.empcloud.com/api/v1"
HEADERS = {"Content-Type": "application/json"}

SUPER_ADMIN = {"email": "admin@empcloud.com", "password": "SuperAdmin@2026"}

ORG_ADMINS = {
    "TechNova": {"email": "ananya@technova.in", "password": "Welcome@123", "domain": "technova.in"},
    "GlobalTech": {"email": "john@globaltech.com", "password": "Welcome@123", "domain": "globaltech.com"},
    "Innovate Solutions": {"email": "hr@innovate.io", "password": "Welcome@123", "domain": "innovate.io"},
}

DEPARTMENTS = [
    {"name": "Engineering", "target": 15},
    {"name": "Sales", "target": 10},
    {"name": "HR", "target": 5},
    {"name": "Finance", "target": 5},
    {"name": "Operations", "target": 15},
]

DESIGNATIONS_BY_DEPT = {
    "Engineering": ["Software Engineer", "Senior Engineer", "Team Lead", "DevOps Engineer", "QA Engineer", "Data Scientist"],
    "Sales": ["Sales Executive", "Senior Sales Executive", "Team Lead", "Manager"],
    "HR": ["HR Executive", "Senior HR Executive", "Team Lead", "Manager"],
    "Finance": ["Accountant", "Senior Accountant", "Analyst", "Manager"],
    "Operations": ["Operations Executive", "Team Lead", "Manager", "Product Manager", "Designer"],
}

LEAVE_TYPES = [
    {"name": "Earned Leave", "code": "EL", "description": "Annual earned leave", "is_paid": True, "is_carry_forward": True, "max_carry_forward_days": 10, "is_encashable": True, "requires_approval": True, "is_active": True, "color": "#4CAF50"},
    {"name": "Sick Leave", "code": "SL", "description": "Medical sick leave", "is_paid": True, "is_carry_forward": False, "max_carry_forward_days": 0, "is_encashable": False, "requires_approval": True, "is_active": True, "color": "#F44336"},
    {"name": "Casual Leave", "code": "CL", "description": "Casual leave", "is_paid": True, "is_carry_forward": False, "max_carry_forward_days": 0, "is_encashable": False, "requires_approval": True, "is_active": True, "color": "#FF9800"},
    {"name": "Maternity Leave", "code": "ML", "description": "Maternity leave", "is_paid": True, "is_carry_forward": False, "max_carry_forward_days": 0, "is_encashable": False, "requires_approval": True, "is_active": True, "color": "#E91E63"},
    {"name": "Paternity Leave", "code": "PL", "description": "Paternity leave", "is_paid": True, "is_carry_forward": False, "max_carry_forward_days": 0, "is_encashable": False, "requires_approval": True, "is_active": True, "color": "#9C27B0"},
    {"name": "Compensatory Off", "code": "CO", "description": "Comp off for extra working days", "is_paid": True, "is_carry_forward": False, "max_carry_forward_days": 0, "is_encashable": False, "requires_approval": True, "is_active": True, "color": "#607D8B"},
]

SHIFTS = [
    {"name": "General Shift", "start_time": "09:00", "end_time": "18:00"},
    {"name": "Morning Shift", "start_time": "06:00", "end_time": "14:00"},
    {"name": "Night Shift", "start_time": "22:00", "end_time": "06:00"},
]

# Realistic Indian names
MALE_FIRST = [
    "Aarav", "Vivaan", "Aditya", "Vihaan", "Arjun", "Sai", "Reyansh", "Ayaan", "Krishna", "Ishaan",
    "Shaurya", "Atharva", "Advait", "Dhruv", "Kabir", "Ritvik", "Aarush", "Kian", "Darsh", "Veer",
    "Rohan", "Arnav", "Laksh", "Sahil", "Yash", "Pranav", "Kunal", "Nikhil", "Rahul", "Amit",
    "Deepak", "Suresh", "Rajesh", "Vikram", "Manoj", "Sanjay", "Ravi", "Arun", "Karthik", "Ganesh",
    "Harish", "Naveen", "Prasad", "Venkat", "Mohan", "Girish", "Ashwin", "Tarun", "Varun", "Chetan",
    "Neeraj", "Pankaj", "Sachin", "Gaurav", "Abhishek", "Ankur", "Sumit", "Rakesh", "Dinesh", "Akash",
]
FEMALE_FIRST = [
    "Ananya", "Diya", "Myra", "Sara", "Aadhya", "Isha", "Kiara", "Riya", "Priya", "Neha",
    "Shreya", "Kavya", "Anika", "Tanya", "Meera", "Nisha", "Pooja", "Swati", "Divya", "Komal",
    "Anjali", "Sonal", "Bhavna", "Deepika", "Esha", "Falguni", "Gauri", "Hina", "Ira", "Jaya",
    "Kritika", "Lavanya", "Mahi", "Nandini", "Pallavi", "Rachna", "Saanvi", "Tanvi", "Urvi", "Vaani",
    "Vidya", "Yamini", "Zara", "Aishwarya", "Bhoomika", "Charvi", "Daksha", "Ekta", "Garima", "Hemani",
]
LAST_NAMES = [
    "Sharma", "Verma", "Gupta", "Singh", "Kumar", "Patel", "Reddy", "Nair", "Iyer", "Menon",
    "Joshi", "Desai", "Shah", "Mehta", "Chauhan", "Yadav", "Mishra", "Pandey", "Dubey", "Tiwari",
    "Saxena", "Agarwal", "Bansal", "Kapoor", "Malhotra", "Khanna", "Bhatia", "Chopra", "Sinha", "Das",
    "Roy", "Bose", "Sen", "Ghosh", "Mukherjee", "Chatterjee", "Pillai", "Warrier", "Kulkarni", "Patil",
    "Deshpande", "Jog", "Kamath", "Hegde", "Rao", "Naidu", "Choudhury", "Thakur", "Rathore", "Ranganathan",
]

# Track used emails per domain to avoid duplicates
used_emails = {}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def api(method, path, token=None, data=None, label=""):
    """Make API call with retry logic."""
    url = f"{API_BASE}{path}"
    hdrs = dict(HEADERS)
    if token:
        hdrs["Authorization"] = f"Bearer {token}"

    for attempt in range(3):
        try:
            if method == "GET":
                r = requests.get(url, headers=hdrs, timeout=30)
            elif method == "POST":
                r = requests.post(url, headers=hdrs, json=data, timeout=30)
            elif method == "PUT":
                r = requests.put(url, headers=hdrs, json=data, timeout=30)
            elif method == "PATCH":
                r = requests.patch(url, headers=hdrs, json=data, timeout=30)
            else:
                raise ValueError(f"Unknown method {method}")

            if r.status_code == 429:
                wait = int(r.headers.get("Retry-After", 5))
                print(f"  [429] Rate limited on {label or path}, waiting {wait}s...")
                time.sleep(wait)
                continue

            return r
        except requests.exceptions.RequestException as e:
            print(f"  [ERR] {label or path} attempt {attempt+1}: {e}")
            time.sleep(2)

    print(f"  [FAIL] {label or path} after 3 attempts")
    return None


def login(email, password, label=""):
    """Login and return token."""
    r = api("POST", "/auth/login", data={"email": email, "password": password}, label=f"login:{label or email}")
    if r and r.status_code == 200:
        body = r.json()
        token = None
        data = body.get("data", {})
        if isinstance(data, dict):
            tokens_obj = data.get("tokens", {})
            if isinstance(tokens_obj, dict):
                token = tokens_obj.get("access_token") or tokens_obj.get("token")
            if not token:
                token = data.get("access_token") or data.get("token")
        if not token:
            token = body.get("token") or body.get("access_token")
        if token:
            print(f"  [OK] Logged in as {email}")
            return token
        else:
            print(f"  [WARN] Login OK but no token found in response: {json.dumps(body)[:300]}")
            return None
    else:
        status = r.status_code if r else "no response"
        text = r.text[:300] if r else ""
        print(f"  [FAIL] Login {email}: {status} {text}")
        return None


def generate_unique_email(first, last, domain):
    """Generate unique email for domain."""
    if domain not in used_emails:
        used_emails[domain] = set()

    base = f"{first.lower()}.{last.lower()}"
    email = f"{base}@{domain}"
    if email not in used_emails[domain]:
        used_emails[domain].add(email)
        return email

    # Add number suffix
    for i in range(1, 100):
        email = f"{base}{i}@{domain}"
        if email not in used_emails[domain]:
            used_emails[domain].add(email)
            return email
    return f"{base}{random.randint(100,999)}@{domain}"


def generate_employees(count, domain, org_prefix, dept_ids, dept_names, start_emp_num=1):
    """Generate employee data dicts."""
    employees = []
    # Distribute across departments
    dept_targets = [d["target"] for d in DEPARTMENTS]
    total_target = sum(dept_targets)

    # Scale targets to actual count
    dept_counts = []
    remaining = count
    for i, t in enumerate(dept_targets):
        if i == len(dept_targets) - 1:
            dept_counts.append(remaining)
        else:
            c = round(count * t / total_target)
            dept_counts.append(c)
            remaining -= c

    emp_num = start_emp_num
    for dept_idx, dept_count in enumerate(dept_counts):
        dept_id = dept_ids[dept_idx]
        dept_name = dept_names[dept_idx]
        desigs = DESIGNATIONS_BY_DEPT.get(dept_name, ["Executive"])

        for j in range(dept_count):
            gender = random.choice(["male", "female"])
            if gender == "male":
                first = random.choice(MALE_FIRST)
            else:
                first = random.choice(FEMALE_FIRST)
            last = random.choice(LAST_NAMES)
            email = generate_unique_email(first, last, domain)

            # First employee in dept is manager/team lead
            if j == 0:
                designation = "Manager" if "Manager" in desigs else "Team Lead"
            elif j == 1 and dept_count > 5:
                designation = "Team Lead" if "Team Lead" in desigs else "Senior Engineer"
            else:
                designation = random.choice(desigs)

            # Date of joining - staggered across years
            year = random.choice([2022, 2022, 2023, 2023, 2023, 2024, 2024, 2024, 2025, 2025, 2026])
            month = random.randint(1, 12)
            day = random.randint(1, 28)
            if year == 2026 and month > 3:
                month = random.randint(1, 3)
            doj = f"{year}-{month:02d}-{day:02d}"

            # Date of birth - ages 22-55
            birth_year = random.randint(1971, 2004)
            dob = f"{birth_year}-{random.randint(1,12):02d}-{random.randint(1,28):02d}"

            contact = f"{random.choice(['98','97','96','95','94','93','91','90','89','88','87','86','85','70','76','77','78','79'])}{random.randint(10000000,99999999)}"

            emp = {
                "first_name": first,
                "last_name": last,
                "email": email,
                "password": "Welcome@123",
                "emp_code": f"{org_prefix}-{emp_num:03d}",
                "department_id": dept_id,
                "designation": designation,
                "date_of_joining": doj,
                "employment_type": "full_time",
                "date_of_birth": dob,
                "gender": gender,
                "contact_number": contact,
                "role": "employee",
                "_dept_name": dept_name,
                "_dept_idx": dept_idx,
                "_is_manager": j == 0,
            }
            employees.append(emp)
            emp_num += 1

    return employees


def safe_json(r, label=""):
    """Safely parse JSON response."""
    try:
        return r.json()
    except Exception:
        print(f"  [WARN] Non-JSON response for {label}: {r.text[:200]}")
        return {}


# ---------------------------------------------------------------------------
# Main Setup
# ---------------------------------------------------------------------------

def main():
    setup_data = {
        "organizations": [],
        "employees": [],
        "departments": [],
        "leave_types": [],
        "shifts": [],
    }

    # ===== STEP 1: Map existing orgs =====
    print("=" * 60)
    print("STEP 1: Mapping existing organizations")
    print("=" * 60)

    # Login as Super Admin
    sa_token = login(SUPER_ADMIN["email"], SUPER_ADMIN["password"], "SuperAdmin")
    if not sa_token:
        print("FATAL: Cannot login as Super Admin. Aborting.")
        sys.exit(1)

    # List all orgs
    r = api("GET", "/admin/organizations", token=sa_token, label="list-orgs")
    orgs_list = []
    if r and r.status_code == 200:
        body = safe_json(r, "list-orgs")
        orgs_list = body.get("data", body.get("organizations", []))
        if isinstance(orgs_list, dict):
            orgs_list = orgs_list.get("organizations", orgs_list.get("rows", orgs_list.get("items", [])))
        if not isinstance(orgs_list, list):
            orgs_list = []
        print(f"  Found {len(orgs_list)} organizations")
        for o in orgs_list:
            name = o.get("name", o.get("org_name", "?"))
            oid = o.get("id", o.get("_id", "?"))
            print(f"    - {name} (ID: {oid})")
    else:
        status = r.status_code if r else "no response"
        text = r.text[:300] if r else ""
        print(f"  Could not list orgs: {status} {text}")

    # Login as each org admin and count employees
    org_employee_counts = {}
    org_tokens = {}
    org_ids = {}

    for org_name, creds in list(ORG_ADMINS.items())[:2]:
        token = login(creds["email"], creds["password"], org_name)
        if token:
            org_tokens[org_name] = token

            # Get org info from login response
            r_login = api("POST", "/auth/login", data=creds, label=f"login-orgid:{org_name}")
            if r_login and r_login.status_code == 200:
                login_body = safe_json(r_login, f"login-orgid:{org_name}")
                login_data = login_body.get("data", {})
                if isinstance(login_data, dict):
                    oid = (login_data.get("org", {}) or {}).get("id") or (login_data.get("user", {}) or {}).get("organization_id")
                    org_ids[org_name] = oid
                    print(f"  {org_name} org ID: {oid}")

            # Count employees
            r = api("GET", "/users", token=token, label=f"users:{org_name}")
            if r and r.status_code == 200:
                body = safe_json(r, f"users:{org_name}")
                users = body.get("data", body.get("users", []))
                if isinstance(users, dict):
                    users = users.get("users", users.get("rows", users.get("items", [])))
                    if isinstance(users, dict):
                        # Maybe paginated with total
                        total = body.get("data", {}).get("total", body.get("total", 0))
                        print(f"  {org_name}: {total} employees (paginated)")
                        org_employee_counts[org_name] = total
                    else:
                        org_employee_counts[org_name] = len(users) if isinstance(users, list) else 0
                        print(f"  {org_name}: {org_employee_counts[org_name]} employees")
                elif isinstance(users, list):
                    org_employee_counts[org_name] = len(users)
                    print(f"  {org_name}: {len(users)} employees")

                    # Track existing emails
                    domain = creds["domain"]
                    if domain not in used_emails:
                        used_emails[domain] = set()
                    for u in users:
                        em = u.get("email", "")
                        if em:
                            used_emails[domain].add(em)
            else:
                # Try with pagination
                r2 = api("GET", "/users?page=1&limit=100", token=token, label=f"users-paged:{org_name}")
                if r2 and r2.status_code == 200:
                    body = safe_json(r2, f"users-paged:{org_name}")
                    data = body.get("data", {})
                    if isinstance(data, dict):
                        total = data.get("total", data.get("count", 0))
                        users = data.get("users", data.get("rows", data.get("items", [])))
                        if isinstance(users, list):
                            org_employee_counts[org_name] = max(total, len(users))
                            print(f"  {org_name}: {org_employee_counts[org_name]} employees")
                            domain = creds["domain"]
                            if domain not in used_emails:
                                used_emails[domain] = set()
                            for u in users:
                                em = u.get("email", "")
                                if em:
                                    used_emails[domain].add(em)
                else:
                    org_employee_counts[org_name] = 0

    print(f"\n  Employee counts: {org_employee_counts}")

    # ===== STEP 2: Register 3rd org if needed =====
    print("\n" + "=" * 60)
    print("STEP 2: Registering 3rd organization (Innovate Solutions)")
    print("=" * 60)

    # Check if Innovate Solutions already exists
    innovate_exists = False
    for o in orgs_list:
        name = o.get("name", o.get("org_name", "")).lower()
        if "innovate" in name:
            innovate_exists = True
            org_ids["Innovate Solutions"] = o.get("id", o.get("_id"))
            print(f"  Innovate Solutions already exists (ID: {org_ids['Innovate Solutions']})")
            break

    if not innovate_exists:
        # Try registration
        reg_data = {
            "email": "hr@innovate.io",
            "password": "Welcome@123",
            "org_name": "Innovate Solutions",
            "first_name": "Neha",
            "last_name": "Kapoor",
        }
        r = api("POST", "/auth/register", data=reg_data, label="register-innovate")
        if r and r.status_code in (200, 201):
            body = safe_json(r, "register-innovate")
            print(f"  [OK] Registered Innovate Solutions: {json.dumps(body)[:300]}")
            # Try to extract org id
            data = body.get("data", body)
            if isinstance(data, dict):
                org_ids["Innovate Solutions"] = data.get("organization_id") or data.get("org_id") or (data.get("organization", {}) or {}).get("id")
        else:
            status = r.status_code if r else "no response"
            text = r.text[:500] if r else ""
            print(f"  Registration response: {status} {text}")

            # Try Super Admin to create org
            print("  Trying Super Admin to create org...")
            create_data = {
                "name": "Innovate Solutions",
                "org_name": "Innovate Solutions",
                "email": "hr@innovate.io",
                "admin_email": "hr@innovate.io",
                "admin_password": "Welcome@123",
                "admin_first_name": "Neha",
                "admin_last_name": "Kapoor",
                "first_name": "Neha",
                "last_name": "Kapoor",
                "password": "Welcome@123",
            }
            for endpoint in ["/admin/organizations", "/admin/organizations/create", "/organizations"]:
                r2 = api("POST", endpoint, token=sa_token, data=create_data, label=f"sa-create-org:{endpoint}")
                if r2 and r2.status_code in (200, 201):
                    body2 = safe_json(r2, f"sa-create-org:{endpoint}")
                    print(f"  [OK] Created via {endpoint}: {json.dumps(body2)[:300]}")
                    data = body2.get("data", body2)
                    if isinstance(data, dict):
                        org_ids["Innovate Solutions"] = data.get("id") or data.get("_id") or data.get("organization_id")
                    break
                else:
                    status2 = r2.status_code if r2 else "no response"
                    text2 = r2.text[:300] if r2 else ""
                    print(f"  {endpoint}: {status2} {text2}")

    # Login as Innovate Solutions admin
    time.sleep(1)
    inv_token = login("hr@innovate.io", "Welcome@123", "Innovate Solutions")
    if inv_token:
        org_tokens["Innovate Solutions"] = inv_token
        org_employee_counts["Innovate Solutions"] = 0

        if "Innovate Solutions" not in org_ids or not org_ids.get("Innovate Solutions"):
            r = api("GET", "/auth/me", token=inv_token, label="me:Innovate")
            if r and r.status_code == 200:
                body = safe_json(r, "me:Innovate")
                user_data = body.get("data", body)
                if isinstance(user_data, dict):
                    oid = user_data.get("organization_id") or user_data.get("org_id") or (user_data.get("organization", {}) or {}).get("id")
                    org_ids["Innovate Solutions"] = oid
                    print(f"  Innovate Solutions org ID: {oid}")
    else:
        print("  [WARN] Cannot login as Innovate Solutions admin - will skip this org")

    print(f"\n  Organization IDs: {org_ids}")

    # ===== STEP 3: Create departments =====
    print("\n" + "=" * 60)
    print("STEP 3: Creating departments (5 per org)")
    print("=" * 60)

    org_departments = {}  # org_name -> [{name, id, target}]

    for org_name, token in org_tokens.items():
        print(f"\n  --- {org_name} ---")

        # Check existing departments
        r = api("GET", "/organizations/me/departments", token=token, label=f"get-depts:{org_name}")
        existing_depts = {}
        if r and r.status_code == 200:
            body = safe_json(r, f"get-depts:{org_name}")
            dept_list = body.get("data", body.get("departments", []))
            if isinstance(dept_list, dict):
                dept_list = dept_list.get("departments", dept_list.get("rows", dept_list.get("items", [])))
            if isinstance(dept_list, list):
                for d in dept_list:
                    dname = d.get("name", "")
                    did = d.get("id") or d.get("_id")
                    existing_depts[dname.lower()] = {"name": dname, "id": did}
                    print(f"    Existing: {dname} (ID: {did})")

        org_departments[org_name] = []
        for dept_def in DEPARTMENTS:
            dept_name = dept_def["name"]
            if dept_name.lower() in existing_depts:
                dept_info = existing_depts[dept_name.lower()]
                dept_info["target"] = dept_def["target"]
                org_departments[org_name].append(dept_info)
                print(f"    [EXISTS] {dept_name}")
            else:
                create_dept = {"name": dept_name, "description": f"{dept_name} department"}
                r = api("POST", "/organizations/me/departments", token=token, data=create_dept, label=f"create-dept:{org_name}:{dept_name}")
                if r and r.status_code in (200, 201):
                    body = safe_json(r, f"create-dept:{org_name}:{dept_name}")
                    data = body.get("data", body)
                    did = None
                    if isinstance(data, dict):
                        did = data.get("id") or data.get("_id")
                    org_departments[org_name].append({"name": dept_name, "id": did, "target": dept_def["target"]})
                    print(f"    [CREATED] {dept_name} (ID: {did})")
                else:
                    status = r.status_code if r else "no response"
                    text = r.text[:200] if r else ""
                    print(f"    [FAIL] {dept_name}: {status} {text}")
                    org_departments[org_name].append({"name": dept_name, "id": None, "target": dept_def["target"]})
                time.sleep(0.3)

    # ===== STEP 4: Create employees =====
    print("\n" + "=" * 60)
    print("STEP 4: Creating employees (50 per org)")
    print("=" * 60)

    org_employees = {}  # org_name -> [employee records]
    emp_code_prefixes = {"TechNova": "TN", "GlobalTech": "GT", "Innovate Solutions": "IS"}

    for org_name, token in org_tokens.items():
        print(f"\n  --- {org_name} ---")
        creds = ORG_ADMINS[org_name]
        domain = creds["domain"]
        prefix = emp_code_prefixes[org_name]
        existing_count = org_employee_counts.get(org_name, 0)
        needed = max(0, 50 - existing_count)
        print(f"  Existing: {existing_count}, Need to create: {needed}")

        dept_ids = [d["id"] for d in org_departments.get(org_name, [])]
        dept_names = [d["name"] for d in org_departments.get(org_name, [])]

        if not dept_ids or all(d is None for d in dept_ids):
            print(f"  [WARN] No department IDs for {org_name}, creating without dept assignment")
            dept_ids = [None] * 5
            dept_names = [d["name"] for d in DEPARTMENTS]

        if needed <= 0:
            print(f"  Already have 50+ employees, skipping creation")
            org_employees[org_name] = []
            continue

        employees = generate_employees(needed, domain, prefix, dept_ids, dept_names, start_emp_num=existing_count + 1)
        created = []
        managers_by_dept = {}  # dept_idx -> manager_id

        for i, emp in enumerate(employees):
            dept_idx = emp.pop("_dept_idx")
            dept_name = emp.pop("_dept_name")
            is_manager = emp.pop("_is_manager")

            # Set reporting manager if available
            if not is_manager and dept_idx in managers_by_dept:
                emp["reporting_manager_id"] = managers_by_dept[dept_idx]

            # Remove None values
            payload = {k: v for k, v in emp.items() if v is not None}

            r = api("POST", "/users", token=token, data=payload, label=f"create-emp:{org_name}:{emp['email']}")
            if r and r.status_code in (200, 201):
                body = safe_json(r, f"create-emp:{emp['email']}")
                data = body.get("data", body)
                emp_id = None
                if isinstance(data, dict):
                    emp_id = data.get("id") or data.get("_id") or data.get("user_id")

                if is_manager and emp_id:
                    managers_by_dept[dept_idx] = emp_id

                record = {
                    "id": emp_id,
                    "first_name": emp["first_name"],
                    "last_name": emp["last_name"],
                    "email": emp["email"],
                    "emp_code": emp["emp_code"],
                    "department": dept_name,
                    "department_id": emp.get("department_id"),
                    "designation": emp["designation"],
                    "gender": emp["gender"],
                    "date_of_joining": emp["date_of_joining"],
                    "is_manager": is_manager,
                }
                created.append(record)
                if (i + 1) % 10 == 0:
                    print(f"    Created {i+1}/{needed} employees...")
            elif r and r.status_code == 409:
                print(f"    [SKIP] {emp['email']} already exists")
                # Try to get their ID
                body = safe_json(r, f"dup:{emp['email']}")
                data = body.get("data", body)
                emp_id = data.get("id") if isinstance(data, dict) else None
                record = {
                    "id": emp_id,
                    "first_name": emp["first_name"],
                    "last_name": emp["last_name"],
                    "email": emp["email"],
                    "emp_code": emp["emp_code"],
                    "department": dept_name,
                    "department_id": emp.get("department_id"),
                    "designation": emp["designation"],
                    "gender": emp["gender"],
                    "date_of_joining": emp["date_of_joining"],
                    "is_manager": is_manager,
                }
                created.append(record)
            else:
                status = r.status_code if r else "no response"
                text = r.text[:200] if r else ""
                print(f"    [FAIL] {emp['email']}: {status} {text}")

            time.sleep(0.2)

        org_employees[org_name] = created
        print(f"  Total created for {org_name}: {len(created)}")

    # ===== STEP 5: Create leave types =====
    print("\n" + "=" * 60)
    print("STEP 5: Creating leave types per org")
    print("=" * 60)

    org_leave_types = {}

    for org_name, token in org_tokens.items():
        print(f"\n  --- {org_name} ---")

        # Check existing leave types
        r = api("GET", "/leave/types", token=token, label=f"get-leave-types:{org_name}")
        existing_lt = {}
        if r and r.status_code == 200:
            body = safe_json(r, f"get-leave-types:{org_name}")
            lt_list = body.get("data", body.get("leave_types", []))
            if isinstance(lt_list, dict):
                lt_list = lt_list.get("leave_types", lt_list.get("rows", lt_list.get("items", []))  )
            if isinstance(lt_list, list):
                for lt in lt_list:
                    lname = lt.get("name", "")
                    lid = lt.get("id") or lt.get("_id")
                    existing_lt[lname.lower()] = {"name": lname, "id": lid}
                    print(f"    Existing: {lname} (ID: {lid})")

        org_leave_types[org_name] = []
        for lt_def in LEAVE_TYPES:
            if lt_def["name"].lower() in existing_lt:
                org_leave_types[org_name].append(existing_lt[lt_def["name"].lower()])
                print(f"    [EXISTS] {lt_def['name']}")
            else:
                payload = {k: v for k, v in lt_def.items()}
                r = api("POST", "/leave/types", token=token, data=payload, label=f"create-lt:{org_name}:{lt_def['name']}")
                if r and r.status_code in (200, 201):
                    body = safe_json(r, f"create-lt:{lt_def['name']}")
                    data = body.get("data", body)
                    lid = data.get("id") or data.get("_id") if isinstance(data, dict) else None
                    org_leave_types[org_name].append({"name": lt_def["name"], "id": lid})
                    print(f"    [CREATED] {lt_def['name']} (ID: {lid})")
                else:
                    status = r.status_code if r else "no response"
                    text = r.text[:200] if r else ""
                    print(f"    [FAIL] {lt_def['name']}: {status} {text}")
                    org_leave_types[org_name].append({"name": lt_def["name"], "id": None})
                time.sleep(0.3)

    # ===== STEP 6: Create shifts =====
    print("\n" + "=" * 60)
    print("STEP 6: Creating shifts per org")
    print("=" * 60)

    org_shifts = {}

    for org_name, token in org_tokens.items():
        print(f"\n  --- {org_name} ---")

        # Check existing shifts
        r = api("GET", "/attendance/shifts", token=token, label=f"get-shifts:{org_name}")
        existing_shifts = {}
        if r and r.status_code == 200:
            body = safe_json(r, f"get-shifts:{org_name}")
            sh_list = body.get("data", body.get("shifts", []))
            if isinstance(sh_list, dict):
                sh_list = sh_list.get("shifts", sh_list.get("rows", sh_list.get("items", [])))
            if isinstance(sh_list, list):
                for s in sh_list:
                    sname = s.get("name", "")
                    sid = s.get("id") or s.get("_id")
                    existing_shifts[sname.lower()] = {"name": sname, "id": sid}
                    print(f"    Existing: {sname} (ID: {sid})")

        org_shifts[org_name] = []
        for sh_def in SHIFTS:
            if sh_def["name"].lower() in existing_shifts:
                org_shifts[org_name].append(existing_shifts[sh_def["name"].lower()])
                print(f"    [EXISTS] {sh_def['name']}")
            else:
                payload = {
                    "name": sh_def["name"],
                    "start_time": sh_def["start_time"],
                    "end_time": sh_def["end_time"],
                    "is_active": True,
                }
                r = api("POST", "/attendance/shifts", token=token, data=payload, label=f"create-shift:{org_name}:{sh_def['name']}")
                if r and r.status_code in (200, 201):
                    body = safe_json(r, f"create-shift:{sh_def['name']}")
                    data = body.get("data", body)
                    sid = data.get("id") or data.get("_id") if isinstance(data, dict) else None
                    org_shifts[org_name].append({"name": sh_def["name"], "id": sid})
                    print(f"    [CREATED] {sh_def['name']} (ID: {sid})")
                else:
                    status = r.status_code if r else "no response"
                    text = r.text[:200] if r else ""
                    print(f"    [FAIL] {sh_def['name']}: {status} {text}")
                    org_shifts[org_name].append({"name": sh_def["name"], "id": None})
                time.sleep(0.3)

    # ===== STEP 7: Save setup data =====
    print("\n" + "=" * 60)
    print("STEP 7: Saving setup data")
    print("=" * 60)

    for org_name, creds in ORG_ADMINS.items():
        org_entry = {
            "name": org_name,
            "id": org_ids.get(org_name),
            "admin_email": creds["email"],
            "admin_password": creds["password"],
            "domain": creds["domain"],
            "departments": org_departments.get(org_name, []),
            "leave_types": org_leave_types.get(org_name, []),
            "shifts": org_shifts.get(org_name, []),
        }
        setup_data["organizations"].append(org_entry)

    for org_name, emps in org_employees.items():
        for e in emps:
            e["organization"] = org_name
            setup_data["employees"].append(e)

    # Flatten departments
    for org_name, depts in org_departments.items():
        for d in depts:
            d_copy = dict(d)
            d_copy["organization"] = org_name
            setup_data["departments"].append(d_copy)

    # Flatten leave types
    for org_name, lts in org_leave_types.items():
        for lt in lts:
            lt_copy = dict(lt)
            lt_copy["organization"] = org_name
            setup_data["leave_types"].append(lt_copy)

    # Flatten shifts
    for org_name, shs in org_shifts.items():
        for s in shs:
            s_copy = dict(s)
            s_copy["organization"] = org_name
            setup_data["shifts"].append(s_copy)

    output_path = r"C:\emptesting\simulation\setup_data.json"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(setup_data, f, indent=2, ensure_ascii=False, default=str)
    print(f"  Saved to {output_path}")

    # ===== Summary =====
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Organizations: {len(setup_data['organizations'])}")
    for o in setup_data["organizations"]:
        print(f"    - {o['name']} (ID: {o['id']}, Admin: {o['admin_email']})")
        print(f"      Departments: {len(o['departments'])}, Leave Types: {len(o['leave_types'])}, Shifts: {len(o['shifts'])}")

    total_created = len(setup_data["employees"])
    print(f"\n  Employees created in this run: {total_created}")
    for org_name in org_employees:
        count = len(org_employees[org_name])
        existing = org_employee_counts.get(org_name, 0)
        print(f"    - {org_name}: {count} new + {existing} existing = {count + existing} total")

    print(f"\n  Total departments: {len(setup_data['departments'])}")
    print(f"  Total leave types: {len(setup_data['leave_types'])}")
    print(f"  Total shifts: {len(setup_data['shifts'])}")
    print(f"\n  Setup data saved to: {output_path}")
    print("  Done!")


if __name__ == "__main__":
    main()
