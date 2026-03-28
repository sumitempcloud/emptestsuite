"""
Fresh E2E Test — Assets, Positions, and Documents
Tests CRUD, business rules, assignments, file validation, and Selenium UI flows.
"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import os
import time
import json
import uuid
import traceback
import requests
import base64
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

# ── Config ──────────────────────────────────────────────────────────────
API_BASE = "https://test-empcloud-api.empcloud.com/api/v1"
UI_BASE = "https://test-empcloud.empcloud.com"
SCREENSHOT_DIR = r"C:\Users\Admin\screenshots\fresh_assets_positions"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

ADMIN_EMAIL = "ananya@technova.in"
ADMIN_PASS = "Welcome@123"
EMP_EMAIL = "priya@technova.in"
EMP_PASS = "Welcome@123"

PREFIX = "fapd_"
step_counter = [0]
results = []
UNIQUE = uuid.uuid4().hex[:6]


# ── Helpers ─────────────────────────────────────────────────────────────
def log(msg):
    print(f"  {msg}")


def record(test_name, status, detail=""):
    results.append({"test": test_name, "status": status, "detail": detail})
    icon = "PASS" if status == "PASS" else ("FAIL" if status == "FAIL" else "WARN")
    print(f"  [{icon}] {test_name}" + (f" -- {detail}" if detail else ""))


def api_login(email, password):
    r = requests.post(f"{API_BASE}/auth/login", json={"email": email, "password": password}, timeout=30)
    if r.status_code == 200:
        data = r.json()
        tokens = data.get("data", {}).get("tokens", {})
        if isinstance(tokens, dict) and tokens.get("access_token"):
            return tokens["access_token"]
    print(f"  Login failed for {email}: {r.status_code} {r.text[:200]}")
    return None


def hdr(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def hdr_multipart(token):
    return {"Authorization": f"Bearer {token}"}


def get_driver():
    opts = Options()
    opts.binary_location = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-extensions")
    opts.add_argument("--ignore-certificate-errors")
    svc = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=svc, options=opts)


def ss(driver, name):
    step_counter[0] += 1
    fname = f"{PREFIX}{step_counter[0]:02d}_{name}.png"
    path = os.path.join(SCREENSHOT_DIR, fname)
    driver.save_screenshot(path)
    log(f"[SS] {fname}")
    return path


def wait_ready(driver, timeout=15):
    time.sleep(2)
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
    except TimeoutException:
        pass
    time.sleep(1)


def selenium_login(driver, email, password):
    driver.get(f"{UI_BASE}/login")
    wait_ready(driver)
    try:
        email_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email'], input[name='email']"))
        )
        email_input.clear()
        email_input.send_keys(email)
        pw_input = driver.find_element(By.CSS_SELECTOR, "input[type='password'], input[name='password']")
        pw_input.clear()
        pw_input.send_keys(password)
        btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        btn.click()
        wait_ready(driver, 20)
        time.sleep(3)
        return True
    except Exception as e:
        log(f"Selenium login failed: {e}")
        return False


def extract_list(resp_json):
    """Extract list from API response (usually at resp.data)."""
    if isinstance(resp_json, list):
        return resp_json
    if isinstance(resp_json, dict):
        data = resp_json.get("data")
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for key in ["items", "results", "assets", "positions", "documents", "categories"]:
                val = data.get(key)
                if isinstance(val, list):
                    return val
    return []


def extract_item(resp_json):
    """Extract single item from response (usually at resp.data)."""
    if isinstance(resp_json, dict):
        data = resp_json.get("data")
        if isinstance(data, dict) and "id" in data:
            return data
        if "id" in resp_json:
            return resp_json
    return resp_json if isinstance(resp_json, dict) else {}


def get_employees(token):
    r = requests.get(f"{API_BASE}/users", headers=hdr(token), timeout=30)
    if r.status_code == 200:
        return extract_list(r.json())
    return []


# ════════════════════════════════════════════════════════════════════════
#                        API TESTS
# ════════════════════════════════════════════════════════════════════════

def run_api_tests():
    print("\n" + "=" * 70)
    print("  SECTION 1: API TESTS -- Assets, Positions, Documents")
    print("=" * 70)

    admin_token = api_login(ADMIN_EMAIL, ADMIN_PASS)
    emp_token = api_login(EMP_EMAIL, EMP_PASS)
    if not admin_token:
        record("API Login (admin)", "FAIL", "Could not login as admin")
        return
    record("API Login (admin)", "PASS")
    if emp_token:
        record("API Login (employee)", "PASS")
    else:
        record("API Login (employee)", "WARN", "Employee login failed, some tests skipped")

    employees = get_employees(admin_token)
    emp_ids = [e["id"] for e in employees if e.get("id")][:5]
    log(f"Found {len(employees)} employees, using IDs: {emp_ids[:3]}")

    # ── ASSETS ──────────────────────────────────────────────────────────
    print("\n--- ASSETS API ---")

    # 1. List assets
    r = requests.get(f"{API_BASE}/assets", headers=hdr(admin_token), timeout=30)
    initial_assets = extract_list(r.json()) if r.status_code == 200 else []
    record("Assets -- List all", "PASS" if r.status_code == 200 else "FAIL",
           f"HTTP {r.status_code}, count={len(initial_assets)}")

    # 2. Asset categories
    r = requests.get(f"{API_BASE}/assets/categories", headers=hdr(admin_token), timeout=30)
    categories = extract_list(r.json()) if r.status_code == 200 else []
    record("Assets -- Get categories", "PASS" if r.status_code == 200 else "FAIL",
           f"HTTP {r.status_code}, count={len(categories)}")
    cat_id = categories[0]["id"] if categories else None

    # 3. Create asset
    serial = f"SN-{UNIQUE}-001"
    asset_payload = {
        "name": f"Test Laptop {UNIQUE}",
        "serial_number": serial,
        "purchase_date": "2025-06-15",
        "warranty_expiry": "2027-06-15",
        "status": "available",
        "condition_status": "new",
        "category_id": cat_id,
        "brand": "Dell",
        "model": "Latitude 5520",
        "description": f"E2E test asset {UNIQUE}"
    }
    r = requests.post(f"{API_BASE}/assets", headers=hdr(admin_token), json=asset_payload, timeout=30)
    created_asset = extract_item(r.json()) if r.status_code in (200, 201) else {}
    asset_id = created_asset.get("id")
    record("Assets -- Create", "PASS" if r.status_code in (200, 201) and asset_id else "FAIL",
           f"HTTP {r.status_code}, id={asset_id}")

    # 4. Get single asset
    if asset_id:
        r = requests.get(f"{API_BASE}/assets/{asset_id}", headers=hdr(admin_token), timeout=30)
        got = extract_item(r.json()) if r.status_code == 200 else {}
        name_ok = UNIQUE in str(got.get("name", ""))
        record("Assets -- Get by ID", "PASS" if r.status_code == 200 and name_ok else "FAIL",
               f"HTTP {r.status_code}, name match={name_ok}")

    # 5. Update asset
    if asset_id:
        update_payload = {"name": f"Updated Laptop {UNIQUE}", "condition_status": "good", "brand": "Lenovo"}
        r = requests.put(f"{API_BASE}/assets/{asset_id}", headers=hdr(admin_token), json=update_payload, timeout=30)
        record("Assets -- Update", "PASS" if r.status_code == 200 else "FAIL", f"HTTP {r.status_code}")
        # Verify update
        if r.status_code == 200:
            r2 = requests.get(f"{API_BASE}/assets/{asset_id}", headers=hdr(admin_token), timeout=30)
            got2 = extract_item(r2.json())
            record("Assets -- Update persisted", "PASS" if "Updated" in str(got2.get("name", "")) else "FAIL",
                   f"name={got2.get('name')}")

    # 6. Duplicate serial number -- should be rejected
    dup_payload = {
        "name": f"Dup Laptop {UNIQUE}",
        "serial_number": serial,  # Same serial
        "status": "available",
        "condition_status": "new"
    }
    r = requests.post(f"{API_BASE}/assets", headers=hdr(admin_token), json=dup_payload, timeout=30)
    if r.status_code in (400, 409, 422):
        record("Assets -- Duplicate serial number rejected", "PASS", f"HTTP {r.status_code}")
    else:
        dup_id = extract_item(r.json()).get("id") if r.status_code in (200, 201) else None
        record("Assets -- Duplicate serial number rejected", "FAIL",
               f"HTTP {r.status_code} -- API accepted duplicate serial number '{serial}'!")
        if dup_id:
            requests.delete(f"{API_BASE}/assets/{dup_id}", headers=hdr(admin_token), timeout=30)

    # 7. Warranty expiry before purchase date -- should be rejected
    bad_warranty = {
        "name": f"Bad Warranty {UNIQUE}",
        "serial_number": f"SN-{UNIQUE}-BAD",
        "purchase_date": "2026-01-01",
        "warranty_expiry": "2025-01-01",
        "status": "available",
        "condition_status": "new"
    }
    r = requests.post(f"{API_BASE}/assets", headers=hdr(admin_token), json=bad_warranty, timeout=30)
    if r.status_code in (400, 422):
        record("Assets -- Warranty before purchase rejected", "PASS", f"HTTP {r.status_code}")
    else:
        bad_id = extract_item(r.json()).get("id") if r.status_code in (200, 201) else None
        record("Assets -- Warranty before purchase rejected", "FAIL",
               f"HTTP {r.status_code} -- accepted warranty_expiry before purchase_date")
        if bad_id:
            requests.delete(f"{API_BASE}/assets/{bad_id}", headers=hdr(admin_token), timeout=30)

    # 8. Assign asset to employee
    assigned_ok = False
    if asset_id and len(emp_ids) >= 1:
        assign_payload = {"assigned_to": emp_ids[0]}
        r = requests.post(f"{API_BASE}/assets/{asset_id}/assign", headers=hdr(admin_token), json=assign_payload, timeout=30)
        assigned_ok = r.status_code in (200, 201)
        record("Assets -- Assign to employee", "PASS" if assigned_ok else "FAIL",
               f"HTTP {r.status_code}, assigned_to={emp_ids[0]}")

    # 9. Double assignment -- same asset to different employee -- MUST be blocked
    if asset_id and len(emp_ids) >= 2 and assigned_ok:
        assign2 = {"assigned_to": emp_ids[1]}
        r = requests.post(f"{API_BASE}/assets/{asset_id}/assign", headers=hdr(admin_token), json=assign2, timeout=30)
        record("Assets -- Double assignment blocked",
               "PASS" if r.status_code in (400, 403, 409, 422) else "FAIL",
               f"HTTP {r.status_code} (expected 400/403/409/422)")

    # 10. Delete assigned asset -- should be blocked
    if asset_id and assigned_ok:
        r = requests.delete(f"{API_BASE}/assets/{asset_id}", headers=hdr(admin_token), timeout=30)
        if r.status_code in (400, 403, 409, 422):
            record("Assets -- Delete assigned asset blocked", "PASS", f"HTTP {r.status_code}")
        else:
            record("Assets -- Delete assigned asset blocked", "FAIL",
                   f"HTTP {r.status_code} -- API allowed deleting assigned asset")

    # 11. Return/unassign asset (POST /assets/:id/return)
    if asset_id and assigned_ok:
        r = requests.post(f"{API_BASE}/assets/{asset_id}/return", headers=hdr(admin_token), json={"notes": "E2E return"}, timeout=30)
        if r.status_code in (200, 201):
            record("Assets -- Return/unassign asset", "PASS", f"HTTP {r.status_code}")
        else:
            record("Assets -- Return/unassign asset", "FAIL",
                   f"HTTP {r.status_code} -- return endpoint error: {r.text[:100]}")

    # 12. Employee view -- my assets
    if emp_token:
        r = requests.get(f"{API_BASE}/assets/my", headers=hdr(emp_token), timeout=30)
        record("Assets -- Employee 'my assets'", "PASS" if r.status_code == 200 else "FAIL",
               f"HTTP {r.status_code}")

    # 13. Create and delete unassigned asset
    serial2 = f"SN-{UNIQUE}-DEL"
    del_payload = {
        "name": f"Deletable Asset {UNIQUE}",
        "serial_number": serial2,
        "purchase_date": "2025-01-01",
        "warranty_expiry": "2027-01-01",
        "status": "available",
        "condition_status": "new"
    }
    r = requests.post(f"{API_BASE}/assets", headers=hdr(admin_token), json=del_payload, timeout=30)
    del_asset_id = extract_item(r.json()).get("id") if r.status_code in (200, 201) else None
    if del_asset_id:
        r = requests.delete(f"{API_BASE}/assets/{del_asset_id}", headers=hdr(admin_token), timeout=30)
        record("Assets -- Delete unassigned asset", "PASS" if r.status_code == 200 else "FAIL",
               f"HTTP {r.status_code}")
    else:
        record("Assets -- Delete unassigned asset", "WARN", "Could not create asset to delete")

    # ── POSITIONS ───────────────────────────────────────────────────────
    print("\n--- POSITIONS API ---")

    # 1. List positions
    r = requests.get(f"{API_BASE}/positions", headers=hdr(admin_token), timeout=30)
    positions = extract_list(r.json()) if r.status_code == 200 else []
    record("Positions -- List all", "PASS" if r.status_code == 200 else "FAIL",
           f"HTTP {r.status_code}, count={len(positions)}")

    # 2. Create position
    # Get department IDs
    dept_r = requests.get(f"{API_BASE}/organizations/me/departments", headers=hdr(admin_token), timeout=30)
    depts = extract_list(dept_r.json()) if dept_r.status_code == 200 else []
    dept_id = depts[0]["id"] if depts else None

    pos_payload = {
        "title": f"QA Engineer {UNIQUE}",
        "code": f"POS-{UNIQUE}",
        "department_id": dept_id,
        "employment_type": "full_time",
        "headcount_budget": 5,
        "headcount_filled": 2,
        "status": "open",
        "job_description": f"E2E test position {UNIQUE}",
        "requirements": "3+ years QA experience",
        "min_salary": 50000,
        "max_salary": 80000,
        "currency": "INR"
    }
    r = requests.post(f"{API_BASE}/positions", headers=hdr(admin_token), json=pos_payload, timeout=30)
    created_pos = extract_item(r.json()) if r.status_code in (200, 201) else {}
    pos_id = created_pos.get("id")
    record("Positions -- Create", "PASS" if r.status_code in (200, 201) and pos_id else "FAIL",
           f"HTTP {r.status_code}, id={pos_id}")

    # 3. Get single position
    if pos_id:
        r = requests.get(f"{API_BASE}/positions/{pos_id}", headers=hdr(admin_token), timeout=30)
        got = extract_item(r.json()) if r.status_code == 200 else {}
        record("Positions -- Get by ID", "PASS" if r.status_code == 200 else "FAIL",
               f"HTTP {r.status_code}, title={got.get('title')}")

    # 4. Update position
    if pos_id:
        update = {"title": f"Senior QA Engineer {UNIQUE}", "headcount_budget": 8}
        r = requests.put(f"{API_BASE}/positions/{pos_id}", headers=hdr(admin_token), json=update, timeout=30)
        record("Positions -- Update", "PASS" if r.status_code == 200 else "FAIL", f"HTTP {r.status_code}")
        # Verify update persisted
        if r.status_code == 200:
            r2 = requests.get(f"{API_BASE}/positions/{pos_id}", headers=hdr(admin_token), timeout=30)
            got2 = extract_item(r2.json())
            record("Positions -- Update persisted", "PASS" if "Senior" in str(got2.get("title", "")) else "FAIL",
                   f"title={got2.get('title')}")

    # 5. Headcount planning -- correct path is /employees/headcount per OpenAPI spec
    r = requests.get(f"{API_BASE}/employees/headcount", headers=hdr(admin_token), timeout=30)
    if r.status_code == 200:
        hc_data = extract_list(r.json())
        record("Positions -- Headcount plan (employees/headcount)", "PASS",
               f"HTTP {r.status_code}, departments={len(hc_data)}")
    else:
        record("Positions -- Headcount plan (employees/headcount)", "FAIL",
               f"HTTP {r.status_code} -- {r.text[:100]}")

    # 6. Vacancy check -- verify headcount_budget vs headcount_filled
    if pos_id:
        r = requests.get(f"{API_BASE}/positions/{pos_id}", headers=hdr(admin_token), timeout=30)
        if r.status_code == 200:
            pos_data = extract_item(r.json())
            budget = pos_data.get("headcount_budget", 0)
            filled = pos_data.get("headcount_filled", 0)
            vacancies = budget - filled if budget and filled is not None else None
            record("Positions -- Vacancy calculation",
                   "PASS" if vacancies is not None and vacancies >= 0 else "WARN",
                   f"budget={budget}, filled={filled}, vacancies={vacancies}")

    # 7. Delete position
    if pos_id:
        r = requests.delete(f"{API_BASE}/positions/{pos_id}", headers=hdr(admin_token), timeout=30)
        record("Positions -- Delete", "PASS" if r.status_code == 200 else "FAIL", f"HTTP {r.status_code}")

    # ── DOCUMENTS ───────────────────────────────────────────────────────
    print("\n--- DOCUMENTS API ---")

    # 1. List documents
    r = requests.get(f"{API_BASE}/documents", headers=hdr(admin_token), timeout=30)
    docs = extract_list(r.json()) if r.status_code == 200 else []
    record("Documents -- List all", "PASS" if r.status_code == 200 else "FAIL",
           f"HTTP {r.status_code}, count={len(docs)}")

    # 2. Document categories
    r = requests.get(f"{API_BASE}/documents/categories", headers=hdr(admin_token), timeout=30)
    doc_cats = extract_list(r.json()) if r.status_code == 200 else []
    record("Documents -- Get categories", "PASS" if r.status_code == 200 else "FAIL",
           f"HTTP {r.status_code}, count={len(doc_cats)}")
    doc_cat_id = doc_cats[0]["id"] if doc_cats else None

    # 3. Create document category
    cat_payload = {"name": f"TestCategory {UNIQUE}", "description": "E2E test category"}
    r = requests.post(f"{API_BASE}/documents/categories", headers=hdr(admin_token), json=cat_payload, timeout=30)
    new_cat = extract_item(r.json()) if r.status_code in (200, 201) else {}
    new_cat_id = new_cat.get("id")
    record("Documents -- Create category", "PASS" if r.status_code in (200, 201) and new_cat_id else "FAIL",
           f"HTTP {r.status_code}, id={new_cat_id}")

    # 4. Upload PDF document (POST /documents/upload with multipart)
    pdf_content = (
        b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
        b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R>>endobj\n"
        b"xref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n"
        b"0000000058 00000 n \n0000000115 00000 n \n"
        b"trailer<</Size 4/Root 1 0 R>>\nstartxref\n190\n%%EOF"
    )
    upload_user_id = str(emp_ids[0]) if emp_ids else ""
    files = {"file": (f"test_{UNIQUE}.pdf", pdf_content, "application/pdf")}
    data = {
        "name": f"Test Doc {UNIQUE}",
        "category_id": str(new_cat_id) if new_cat_id else str(doc_cat_id or ""),
        "user_id": upload_user_id,
    }
    r = requests.post(f"{API_BASE}/documents/upload", headers=hdr_multipart(admin_token),
                      files=files, data=data, timeout=30)
    uploaded_doc = extract_item(r.json()) if r.status_code in (200, 201) else {}
    doc_id = uploaded_doc.get("id")
    record("Documents -- Upload PDF", "PASS" if r.status_code in (200, 201) and doc_id else "FAIL",
           f"HTTP {r.status_code}, id={doc_id}")

    # 5. Get document by ID
    if doc_id:
        r = requests.get(f"{API_BASE}/documents/{doc_id}", headers=hdr(admin_token), timeout=30)
        record("Documents -- Get by ID", "PASS" if r.status_code == 200 else "FAIL", f"HTTP {r.status_code}")

    # 6. Download document
    if doc_id:
        r = requests.get(f"{API_BASE}/documents/{doc_id}/download", headers=hdr(admin_token), timeout=30)
        record("Documents -- Download", "PASS" if r.status_code == 200 else "FAIL", f"HTTP {r.status_code}")

    # 7. Upload .exe file -- MUST be rejected
    exe_content = b"MZ\x90\x00" + b"\x00" * 100
    exe_files = {"file": ("malware.exe", exe_content, "application/x-msdownload")}
    exe_data = {"name": "Malicious File", "category_id": str(doc_cat_id or "")}
    r = requests.post(f"{API_BASE}/documents/upload", headers=hdr_multipart(admin_token),
                      files=exe_files, data=exe_data, timeout=30)
    if r.status_code in (400, 403, 415, 422):
        record("Documents -- Reject .exe upload", "PASS", f"HTTP {r.status_code}")
    else:
        record("Documents -- Reject .exe upload", "FAIL",
               f"HTTP {r.status_code} -- API accepted .exe file upload!")

    # 8. Upload .bat file -- MUST be rejected
    bat_files = {"file": ("script.bat", b"@echo off\nformat C:", "application/x-bat")}
    r = requests.post(f"{API_BASE}/documents/upload", headers=hdr_multipart(admin_token),
                      files=bat_files, data={"name": "Bad script"}, timeout=30)
    blocked = r.status_code in (400, 403, 415, 422)
    record("Documents -- Reject .bat upload", "PASS" if blocked else "FAIL",
           f"HTTP {r.status_code}" + ("" if blocked else " -- .bat file accepted!"))

    # 9. Upload .sh file -- MUST be rejected
    sh_files = {"file": ("script.sh", b"#!/bin/bash\nrm -rf /", "text/x-shellscript")}
    r = requests.post(f"{API_BASE}/documents/upload", headers=hdr_multipart(admin_token),
                      files=sh_files, data={"name": "Bad shell"}, timeout=30)
    blocked = r.status_code in (400, 403, 415, 422)
    record("Documents -- Reject .sh upload", "PASS" if blocked else "FAIL",
           f"HTTP {r.status_code}" + ("" if blocked else " -- .sh file accepted!"))

    # 10. My documents (employee view)
    if emp_token:
        r = requests.get(f"{API_BASE}/documents/my", headers=hdr(emp_token), timeout=30)
        my_docs = extract_list(r.json()) if r.status_code == 200 else []
        record("Documents -- Employee 'my documents'", "PASS" if r.status_code == 200 else "FAIL",
               f"HTTP {r.status_code}, count={len(my_docs)}")

    # 11. Mandatory documents tracking (correct path: /documents/tracking/mandatory)
    r = requests.get(f"{API_BASE}/documents/tracking/mandatory", headers=hdr(admin_token), timeout=30)
    if r.status_code == 200:
        record("Documents -- Mandatory tracking", "PASS", f"HTTP {r.status_code}")
    else:
        record("Documents -- Mandatory tracking", "FAIL",
               f"HTTP {r.status_code} -- {r.text[:100]}")

    # 12. Expiry alerts (correct path: /documents/tracking/expiry)
    r = requests.get(f"{API_BASE}/documents/tracking/expiry", headers=hdr(admin_token), timeout=30)
    if r.status_code == 200:
        expiry_data = extract_list(r.json())
        record("Documents -- Expiry alerts", "PASS", f"HTTP {r.status_code}, count={len(expiry_data)}")
    else:
        record("Documents -- Expiry alerts", "FAIL",
               f"HTTP {r.status_code} -- {r.text[:100]}")

    # 13. Verify document
    if doc_id:
        verify_payloads = [
            {"verification_status": "verified"},
            {"status": "verified"},
            {"is_verified": 1},
        ]
        verified = False
        for vp in verify_payloads:
            r = requests.put(f"{API_BASE}/documents/{doc_id}/verify", headers=hdr(admin_token), json=vp, timeout=30)
            if r.status_code == 200:
                verified = True
                break
        record("Documents -- Verify document", "PASS" if verified else "FAIL",
               f"HTTP {r.status_code}")

    # Cleanup: delete test asset if still exists
    if asset_id:
        requests.delete(f"{API_BASE}/assets/{asset_id}", headers=hdr(admin_token), timeout=30)

    return admin_token, emp_token


# ════════════════════════════════════════════════════════════════════════
#                     SELENIUM UI TESTS
# ════════════════════════════════════════════════════════════════════════

def safe_selenium_test(label, email, password, pages):
    """Run a set of page visits in a fresh driver to avoid ChromeDriver crashes."""
    driver = None
    try:
        driver = get_driver()
        if not selenium_login(driver, email, password):
            record(f"Selenium -- {label} login", "FAIL", "Could not login")
            return
        record(f"Selenium -- {label} login", "PASS")
        ss(driver, f"{label}_dashboard")

        for path, ss_name, keywords in pages:
            try:
                driver.get(f"{UI_BASE}{path}")
                wait_ready(driver)
                time.sleep(3)
                page_text = driver.find_element(By.TAG_NAME, "body").text.lower()
                has_content = any(w in page_text for w in keywords)
                ss(driver, ss_name)
                record(f"Selenium -- {label} {path}",
                       "PASS" if has_content else "WARN",
                       "Has expected content" if has_content else f"Text: {page_text[:80]}")
            except Exception as e:
                record(f"Selenium -- {label} {path}", "FAIL", str(e)[:150])
                # Try to recover with a new driver
                try:
                    driver.quit()
                except:
                    pass
                driver = get_driver()
                selenium_login(driver, email, password)

    except Exception as e:
        record(f"Selenium -- {label} error", "FAIL", str(e)[:200])
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass


def run_selenium_tests():
    print("\n" + "=" * 70)
    print("  SECTION 2: SELENIUM UI TESTS -- Assets, Positions, Documents")
    print("=" * 70)

    # Admin pages
    admin_pages = [
        ("/assets", "admin_assets", ["asset", "serial", "assign", "laptop", "hardware", "inventory"]),
        ("/positions", "admin_positions", ["position", "vacancy", "headcount", "department", "role", "open", "qa"]),
        ("/documents", "admin_documents", ["document", "upload", "category", "file", "pdf"]),
        ("/documents/categories", "admin_doc_categories", ["category", "document", "mandatory"]),
    ]
    safe_selenium_test("Admin", ADMIN_EMAIL, ADMIN_PASS, admin_pages)

    # Employee pages
    emp_pages = [
        ("/assets", "emp_assets", ["asset", "laptop", "assigned"]),
        ("/documents", "emp_documents", ["document", "file", "upload"]),
        ("/documents/my", "emp_my_documents", ["document", "my", "file"]),
    ]
    safe_selenium_test("Employee", EMP_EMAIL, EMP_PASS, emp_pages)


# ════════════════════════════════════════════════════════════════════════
#                        MAIN
# ════════════════════════════════════════════════════════════════════════

def main():
    start = time.time()
    print("\n" + "#" * 70)
    print("  FRESH E2E TEST -- Assets, Positions, Documents")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Unique ID: {UNIQUE}")
    print("#" * 70)

    try:
        run_api_tests()
    except Exception as e:
        print(f"\n  API TESTS CRASHED: {e}")
        traceback.print_exc()

    try:
        run_selenium_tests()
    except Exception as e:
        print(f"\n  SELENIUM TESTS CRASHED: {e}")
        traceback.print_exc()

    # ── Summary ─────────────────────────────────────────────────────────
    elapsed = time.time() - start
    total = len(results)
    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    warned = sum(1 for r in results if r["status"] == "WARN")

    print("\n" + "=" * 70)
    print("  SUMMARY")
    print("=" * 70)
    print(f"  Total: {total} | PASS: {passed} | FAIL: {failed} | WARN: {warned}")
    print(f"  Time: {elapsed:.1f}s")
    print(f"  Screenshots: {SCREENSHOT_DIR}")
    print()

    if failed > 0:
        print("  FAILURES:")
        for r in results:
            if r["status"] == "FAIL":
                print(f"    X  {r['test']} -- {r['detail']}")
        print()

    if warned > 0:
        print("  WARNINGS:")
        for r in results:
            if r["status"] == "WARN":
                print(f"    ?  {r['test']} -- {r['detail']}")
        print()

    # Write results JSON
    results_path = os.path.join(SCREENSHOT_DIR, "results.json")
    with open(results_path, "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "unique_id": UNIQUE,
            "elapsed_seconds": round(elapsed, 1),
            "totals": {"total": total, "pass": passed, "fail": failed, "warn": warned},
            "results": results
        }, f, indent=2)
    print(f"  Results saved: {results_path}")


if __name__ == "__main__":
    main()
