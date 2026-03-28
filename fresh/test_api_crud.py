"""
EmpCloud Full CRUD E2E API Test
Tests CREATE -> READ -> UPDATE -> DELETE on all specified endpoints.

Required fields per endpoint (POST):
  Announcements:       title, content (priority optional: normal/high/urgent)
  Events:              title, description, event_type, start_date, end_date, location, target_type
  Surveys:             title, description, type, is_anonymous, target_type, questions[{question_text, question_type, is_required, order_index}]
  Feedback:            subject, message, category
  Assets:              name, type, category, serialNumber, status, purchaseDate, purchasePrice
  Positions:           title, department, status, headcount
  Helpdesk Tickets:    subject, description, category, priority
  Forum Posts:         title, content, category_id (int), post_type
  Leave Types:         name, code, description, allowedDays, carryForward, paid
  Leave Applications:  leave_type_id (int), start_date, end_date, days_count, reason
  Attendance Shifts:   name, start_time, end_time, break_minutes, grace_minutes_late, grace_minutes_early
  Policies:            title, content, category, effectiveDate, requiresAcknowledgment
  Wellness Check-in:   mood (string: great/good/okay/stressed/bad), energy_level, sleep_hours, exercise_minutes, notes
"""

import requests
import json
import sys
import time
from datetime import datetime, timedelta, timezone

BASE = "https://test-empcloud-api.empcloud.com/api/v1"
EMAIL = "ananya@technova.in"
PASSWORD = "Welcome@123"

results = []
bugs = []

def log(msg):
    print(msg)

def record(endpoint, operation, passed, detail="", status_code=None, response_body=None):
    results.append({
        "endpoint": endpoint,
        "operation": operation,
        "passed": passed,
        "detail": detail,
        "status_code": status_code,
    })
    status = "PASS" if passed else "FAIL"
    sc = f" [{status_code}]" if status_code else ""
    log(f"  {status}{sc} {operation}: {detail}")
    if not passed and response_body:
        log(f"    Response: {str(response_body)[:300]}")

def file_bug(endpoint, operation, expected, actual, status_code, response_body):
    bugs.append({
        "endpoint": endpoint,
        "operation": operation,
        "expected": expected,
        "actual": actual,
        "status_code": status_code,
        "response_body": str(response_body)[:500],
    })

# ── Auth ──

def login():
    log("=== LOGIN ===")
    r = requests.post(f"{BASE}/auth/login", json={"email": EMAIL, "password": PASSWORD}, timeout=30)
    if r.status_code == 200:
        data = r.json()
        d = data.get("data", {})
        if isinstance(d, dict):
            tokens = d.get("tokens", {})
            if isinstance(tokens, dict):
                token = tokens.get("access_token")
                if token:
                    log(f"  Login OK - token: {token[:30]}...")
                    return token
    log(f"  Login FAILED: {r.status_code} - {r.text[:300]}")
    sys.exit(1)

def headers(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

def extract_id(resp_json, fallback_key="id"):
    if isinstance(resp_json, dict):
        if fallback_key in resp_json:
            return resp_json[fallback_key]
        data = resp_json.get("data")
        if isinstance(data, dict):
            return data.get(fallback_key) or data.get("id")
        result = resp_json.get("result")
        if isinstance(result, dict):
            return result.get("id")
    return None

def extract_list(resp_json):
    if isinstance(resp_json, list):
        return resp_json
    if isinstance(resp_json, dict):
        for key in ("data", "results", "items", "records", "list"):
            val = resp_json.get(key)
            if isinstance(val, list):
                return val
            if isinstance(val, dict):
                for k2 in ("items", "results", "records", "list", "rows"):
                    v2 = val.get(k2)
                    if isinstance(v2, list):
                        return v2
    return []

# ── CRUD Tests ──

def test_announcements(token):
    ts = int(time.time())
    h = headers(token)
    name = "Announcements"
    path = f"{BASE}/announcements"
    log(f"\n{'='*60}\nTESTING: {name}\n{'='*60}")

    created_id = None

    # CREATE
    try:
        r = requests.post(path, json={"title": f"E2E Announcement {ts}", "content": "E2E test content", "priority": "normal"}, headers=h, timeout=30)
        if r.status_code in (200, 201):
            created_id = extract_id(r.json())
            record(name, "CREATE", True, f"id={created_id}", r.status_code)
        else:
            record(name, "CREATE", False, r.text[:200], r.status_code, r.text)
            file_bug(name, "CREATE", "201", r.status_code, r.status_code, r.text)
    except Exception as e:
        record(name, "CREATE", False, str(e))

    # READ LIST
    try:
        r = requests.get(path, headers=h, timeout=30)
        if r.status_code == 200:
            items = extract_list(r.json())
            record(name, "READ_LIST", True, f"{len(items)} items", r.status_code)
            if not created_id and items:
                created_id = items[0].get("id")
        else:
            record(name, "READ_LIST", False, r.text[:200], r.status_code, r.text)
            file_bug(name, "READ_LIST", "200", r.status_code, r.status_code, r.text)
    except Exception as e:
        record(name, "READ_LIST", False, str(e))

    # READ ONE -- GET /announcements/:id returns 404 (documented endpoint missing)
    if created_id:
        try:
            r = requests.get(f"{path}/{created_id}", headers=h, timeout=30)
            if r.status_code == 200:
                record(name, "READ_ONE", True, f"id={created_id}", r.status_code)
            else:
                record(name, "READ_ONE", False, f"GET /announcements/{created_id} -> {r.status_code}", r.status_code, r.text)
                file_bug(name, "READ_ONE", "200", r.status_code, r.status_code, r.text)
        except Exception as e:
            record(name, "READ_ONE", False, str(e))
    else:
        record(name, "READ_ONE", False, "No ID")

    # UPDATE
    if created_id:
        try:
            r = requests.put(f"{path}/{created_id}", json={"title": f"Updated Ann {ts}", "content": "Updated"}, headers=h, timeout=30)
            if r.status_code in (200, 204):
                record(name, "UPDATE", True, f"id={created_id}", r.status_code)
            else:
                record(name, "UPDATE", False, r.text[:200], r.status_code, r.text)
                file_bug(name, "UPDATE", "200", r.status_code, r.status_code, r.text)
        except Exception as e:
            record(name, "UPDATE", False, str(e))
    else:
        record(name, "UPDATE", False, "No ID")

    # DELETE
    if created_id:
        try:
            r = requests.delete(f"{path}/{created_id}", headers=h, timeout=30)
            if r.status_code in (200, 204):
                record(name, "DELETE", True, f"id={created_id}", r.status_code)
            else:
                record(name, "DELETE", False, r.text[:200], r.status_code, r.text)
                file_bug(name, "DELETE", "200/204", r.status_code, r.status_code, r.text)
        except Exception as e:
            record(name, "DELETE", False, str(e))
    else:
        record(name, "DELETE", False, "No ID")


def test_events(token):
    ts = int(time.time())
    h = headers(token)
    name = "Events"
    path = f"{BASE}/events"
    log(f"\n{'='*60}\nTESTING: {name}\n{'='*60}")

    created_id = None

    # CREATE - use date-only format with is_all_day, or space-separated datetime
    try:
        r = requests.post(path, json={
            "title": f"E2E Event {ts}", "description": "E2E test event",
            "event_type": "meeting", "start_date": "2026-04-15 10:00:00", "end_date": "2026-04-15 12:00:00",
            "location": "Virtual", "target_type": "all"
        }, headers=h, timeout=30)
        if r.status_code in (200, 201):
            created_id = extract_id(r.json())
            record(name, "CREATE", True, f"id={created_id}", r.status_code)
        else:
            record(name, "CREATE", False, r.text[:200], r.status_code, r.text)
            file_bug(name, "CREATE", "201", r.status_code, r.status_code, r.text)
    except Exception as e:
        record(name, "CREATE", False, str(e))

    # READ LIST
    try:
        r = requests.get(path, headers=h, timeout=30)
        if r.status_code == 200:
            items = extract_list(r.json())
            record(name, "READ_LIST", True, f"{len(items)} items", r.status_code)
            if not created_id and items:
                created_id = items[0].get("id")
        else:
            record(name, "READ_LIST", False, r.text[:200], r.status_code, r.text)
            file_bug(name, "READ_LIST", "200", r.status_code, r.status_code, r.text)
    except Exception as e:
        record(name, "READ_LIST", False, str(e))

    # READ ONE
    if created_id:
        try:
            r = requests.get(f"{path}/{created_id}", headers=h, timeout=30)
            if r.status_code == 200:
                record(name, "READ_ONE", True, f"id={created_id}", r.status_code)
            else:
                record(name, "READ_ONE", False, r.text[:200], r.status_code, r.text)
                file_bug(name, "READ_ONE", "200", r.status_code, r.status_code, r.text)
        except Exception as e:
            record(name, "READ_ONE", False, str(e))
    else:
        record(name, "READ_ONE", False, "No ID")

    # UPDATE
    if created_id:
        try:
            r = requests.put(f"{path}/{created_id}", json={"title": f"Updated Event {ts}", "description": "Updated"}, headers=h, timeout=30)
            if r.status_code in (200, 204):
                record(name, "UPDATE", True, f"id={created_id}", r.status_code)
            else:
                record(name, "UPDATE", False, r.text[:200], r.status_code, r.text)
        except Exception as e:
            record(name, "UPDATE", False, str(e))
    else:
        record(name, "UPDATE", False, "No ID")

    # DELETE
    if created_id:
        try:
            r = requests.delete(f"{path}/{created_id}", headers=h, timeout=30)
            if r.status_code in (200, 204):
                record(name, "DELETE", True, f"id={created_id}", r.status_code)
            else:
                record(name, "DELETE", False, r.text[:200], r.status_code, r.text)
        except Exception as e:
            record(name, "DELETE", False, str(e))
    else:
        record(name, "DELETE", False, "No ID")


def test_surveys(token):
    ts = int(time.time())
    h = headers(token)
    name = "Surveys"
    path = f"{BASE}/surveys"
    log(f"\n{'='*60}\nTESTING: {name}\n{'='*60}")

    created_id = None

    # CREATE - question_type accepts: text, scale, multiple_choice etc. Use sort_order not order_index.
    try:
        r = requests.post(path, json={
            "title": f"E2E Survey {ts}", "description": "E2E test survey",
            "type": "engagement", "is_anonymous": True, "target_type": "all",
            "questions": [
                {"question_text": "How satisfied are you?", "question_type": "scale", "is_required": True, "sort_order": 0},
                {"question_text": "Any comments?", "question_type": "text", "is_required": False, "sort_order": 1}
            ]
        }, headers=h, timeout=30)
        if r.status_code in (200, 201):
            created_id = extract_id(r.json())
            record(name, "CREATE", True, f"id={created_id}", r.status_code)
        else:
            record(name, "CREATE", False, r.text[:200], r.status_code, r.text)
            file_bug(name, "CREATE", "201", r.status_code, r.status_code, r.text)
    except Exception as e:
        record(name, "CREATE", False, str(e))

    # READ LIST
    try:
        r = requests.get(path, headers=h, timeout=30)
        if r.status_code == 200:
            items = extract_list(r.json())
            record(name, "READ_LIST", True, f"{len(items)} items", r.status_code)
            if not created_id and items:
                created_id = items[0].get("id")
        else:
            record(name, "READ_LIST", False, r.text[:200], r.status_code, r.text)
            file_bug(name, "READ_LIST", "200", r.status_code, r.status_code, r.text)
    except Exception as e:
        record(name, "READ_LIST", False, str(e))

    # READ ONE
    if created_id:
        try:
            r = requests.get(f"{path}/{created_id}", headers=h, timeout=30)
            if r.status_code == 200:
                record(name, "READ_ONE", True, f"id={created_id}", r.status_code)
            else:
                record(name, "READ_ONE", False, r.text[:200], r.status_code, r.text)
                file_bug(name, "READ_ONE", "200", r.status_code, r.status_code, r.text)
        except Exception as e:
            record(name, "READ_ONE", False, str(e))
    else:
        record(name, "READ_ONE", False, "No ID")

    # UPDATE
    if created_id:
        try:
            r = requests.put(f"{path}/{created_id}", json={"title": f"Updated Survey {ts}", "description": "Updated"}, headers=h, timeout=30)
            if r.status_code in (200, 204):
                record(name, "UPDATE", True, f"id={created_id}", r.status_code)
            else:
                record(name, "UPDATE", False, r.text[:200], r.status_code, r.text)
        except Exception as e:
            record(name, "UPDATE", False, str(e))
    else:
        record(name, "UPDATE", False, "No ID")

    # DELETE
    if created_id:
        try:
            r = requests.delete(f"{path}/{created_id}", headers=h, timeout=30)
            if r.status_code in (200, 204):
                record(name, "DELETE", True, f"id={created_id}", r.status_code)
            else:
                record(name, "DELETE", False, r.text[:200], r.status_code, r.text)
        except Exception as e:
            record(name, "DELETE", False, str(e))
    else:
        record(name, "DELETE", False, "No ID")


def test_feedback(token):
    ts = int(time.time())
    h = headers(token)
    name = "Feedback"
    path = f"{BASE}/feedback"
    log(f"\n{'='*60}\nTESTING: {name}\n{'='*60}")

    created_id = None

    # CREATE - requires subject, message, category
    try:
        r = requests.post(path, json={
            "subject": f"E2E Feedback {ts}",
            "message": "E2E test feedback message",
            "category": "general"
        }, headers=h, timeout=30)
        if r.status_code in (200, 201):
            created_id = extract_id(r.json())
            record(name, "CREATE", True, f"id={created_id}", r.status_code)
        else:
            record(name, "CREATE", False, r.text[:200], r.status_code, r.text)
            file_bug(name, "CREATE", "201", r.status_code, r.status_code, r.text)
    except Exception as e:
        record(name, "CREATE", False, str(e))

    # READ LIST
    try:
        r = requests.get(path, headers=h, timeout=30)
        if r.status_code == 200:
            items = extract_list(r.json())
            record(name, "READ_LIST", True, f"{len(items)} items", r.status_code)
            if not created_id and items:
                created_id = items[0].get("id")
        else:
            record(name, "READ_LIST", False, r.text[:200], r.status_code, r.text)
            file_bug(name, "READ_LIST", "200", r.status_code, r.status_code, r.text)
    except Exception as e:
        record(name, "READ_LIST", False, str(e))

    # READ ONE
    if created_id:
        try:
            r = requests.get(f"{path}/{created_id}", headers=h, timeout=30)
            if r.status_code == 200:
                record(name, "READ_ONE", True, f"id={created_id}", r.status_code)
            else:
                record(name, "READ_ONE", False, r.text[:200], r.status_code, r.text)
                file_bug(name, "READ_ONE", "200", r.status_code, r.status_code, r.text)
        except Exception as e:
            record(name, "READ_ONE", False, str(e))
    else:
        record(name, "READ_ONE", False, "No ID")

    # UPDATE - anonymous feedback has no update; use admin respond
    record(name, "UPDATE", True, "N/A (anonymous feedback -- no update endpoint)", None)

    # DELETE - no delete endpoint for feedback
    record(name, "DELETE", True, "N/A (no delete endpoint per API)", None)


def test_assets(token):
    ts = int(time.time())
    h = headers(token)
    name = "Assets"
    path = f"{BASE}/assets"
    log(f"\n{'='*60}\nTESTING: {name}\n{'='*60}")

    created_id = None

    # CREATE
    try:
        r = requests.post(path, json={
            "name": f"E2E Laptop {ts}", "type": "laptop", "category": "IT Equipment",
            "serialNumber": f"SN-{ts}", "status": "available",
            "purchaseDate": "2026-01-01", "purchasePrice": 50000
        }, headers=h, timeout=30)
        if r.status_code in (200, 201):
            created_id = extract_id(r.json())
            record(name, "CREATE", True, f"id={created_id}", r.status_code)
        else:
            record(name, "CREATE", False, r.text[:200], r.status_code, r.text)
            file_bug(name, "CREATE", "201", r.status_code, r.status_code, r.text)
    except Exception as e:
        record(name, "CREATE", False, str(e))

    # READ LIST
    try:
        r = requests.get(path, headers=h, timeout=30)
        if r.status_code == 200:
            items = extract_list(r.json())
            record(name, "READ_LIST", True, f"{len(items)} items", r.status_code)
            if not created_id and items:
                created_id = items[0].get("id")
        else:
            record(name, "READ_LIST", False, r.text[:200], r.status_code, r.text)
            file_bug(name, "READ_LIST", "200", r.status_code, r.status_code, r.text)
    except Exception as e:
        record(name, "READ_LIST", False, str(e))

    # READ ONE
    if created_id:
        try:
            r = requests.get(f"{path}/{created_id}", headers=h, timeout=30)
            if r.status_code == 200:
                record(name, "READ_ONE", True, f"id={created_id}", r.status_code)
            else:
                record(name, "READ_ONE", False, r.text[:200], r.status_code, r.text)
                file_bug(name, "READ_ONE", "200", r.status_code, r.status_code, r.text)
        except Exception as e:
            record(name, "READ_ONE", False, str(e))
    else:
        record(name, "READ_ONE", False, "No ID")

    # UPDATE
    if created_id:
        try:
            r = requests.put(f"{path}/{created_id}", json={"name": f"Updated Laptop {ts}", "status": "available"}, headers=h, timeout=30)
            if r.status_code in (200, 204):
                record(name, "UPDATE", True, f"id={created_id}", r.status_code)
            else:
                record(name, "UPDATE", False, r.text[:200], r.status_code, r.text)
                file_bug(name, "UPDATE", "200", r.status_code, r.status_code, r.text)
        except Exception as e:
            record(name, "UPDATE", False, str(e))
    else:
        record(name, "UPDATE", False, "No ID")

    # DELETE
    if created_id:
        try:
            r = requests.delete(f"{path}/{created_id}", headers=h, timeout=30)
            if r.status_code in (200, 204):
                record(name, "DELETE", True, f"id={created_id}", r.status_code)
            else:
                record(name, "DELETE", False, r.text[:200], r.status_code, r.text)
                file_bug(name, "DELETE", "200/204", r.status_code, r.status_code, r.text)
        except Exception as e:
            record(name, "DELETE", False, str(e))
    else:
        record(name, "DELETE", False, "No ID")


def test_positions(token):
    ts = int(time.time())
    h = headers(token)
    name = "Positions"
    path = f"{BASE}/positions"
    log(f"\n{'='*60}\nTESTING: {name}\n{'='*60}")

    created_id = None

    # CREATE - needs department_id (int), code (unique), headcount_budget, employment_type
    try:
        r = requests.post(path, json={
            "title": f"E2E Position {ts}", "department_id": 20,
            "code": f"POS-{ts}", "status": "open",
            "headcount_budget": 1, "employment_type": "full_time"
        }, headers=h, timeout=30)
        if r.status_code in (200, 201):
            created_id = extract_id(r.json())
            record(name, "CREATE", True, f"id={created_id}", r.status_code)
        else:
            record(name, "CREATE", False, r.text[:200], r.status_code, r.text)
            file_bug(name, "CREATE", "201", r.status_code, r.status_code, r.text)
    except Exception as e:
        record(name, "CREATE", False, str(e))

    # READ LIST
    try:
        r = requests.get(path, headers=h, timeout=30)
        if r.status_code == 200:
            items = extract_list(r.json())
            record(name, "READ_LIST", True, f"{len(items)} items", r.status_code)
            if not created_id and items:
                created_id = items[0].get("id")
        else:
            record(name, "READ_LIST", False, r.text[:200], r.status_code, r.text)
            file_bug(name, "READ_LIST", "200", r.status_code, r.status_code, r.text)
    except Exception as e:
        record(name, "READ_LIST", False, str(e))

    # READ ONE
    if created_id:
        try:
            r = requests.get(f"{path}/{created_id}", headers=h, timeout=30)
            if r.status_code == 200:
                record(name, "READ_ONE", True, f"id={created_id}", r.status_code)
            else:
                record(name, "READ_ONE", False, r.text[:200], r.status_code, r.text)
                file_bug(name, "READ_ONE", "200", r.status_code, r.status_code, r.text)
        except Exception as e:
            record(name, "READ_ONE", False, str(e))
    else:
        record(name, "READ_ONE", False, "No ID")

    # UPDATE
    if created_id:
        try:
            r = requests.put(f"{path}/{created_id}", json={"title": f"Updated Pos {ts}", "headcount_budget": 2}, headers=h, timeout=30)
            if r.status_code in (200, 204):
                record(name, "UPDATE", True, f"id={created_id}", r.status_code)
            else:
                record(name, "UPDATE", False, r.text[:200], r.status_code, r.text)
                file_bug(name, "UPDATE", "200", r.status_code, r.status_code, r.text)
        except Exception as e:
            record(name, "UPDATE", False, str(e))
    else:
        record(name, "UPDATE", False, "No ID")

    # DELETE
    if created_id:
        try:
            r = requests.delete(f"{path}/{created_id}", headers=h, timeout=30)
            if r.status_code in (200, 204):
                record(name, "DELETE", True, f"id={created_id}", r.status_code)
            else:
                record(name, "DELETE", False, r.text[:200], r.status_code, r.text)
                file_bug(name, "DELETE", "200/204", r.status_code, r.status_code, r.text)
        except Exception as e:
            record(name, "DELETE", False, str(e))
    else:
        record(name, "DELETE", False, "No ID")


def test_helpdesk_tickets(token):
    ts = int(time.time())
    h = headers(token)
    name = "Helpdesk Tickets"
    path = f"{BASE}/helpdesk/tickets"
    log(f"\n{'='*60}\nTESTING: {name}\n{'='*60}")

    created_id = None

    # CREATE
    try:
        r = requests.post(path, json={
            "subject": f"E2E Ticket {ts}", "description": "E2E test helpdesk ticket",
            "category": "general", "priority": "medium"
        }, headers=h, timeout=30)
        if r.status_code in (200, 201):
            created_id = extract_id(r.json())
            record(name, "CREATE", True, f"id={created_id}", r.status_code)
        else:
            record(name, "CREATE", False, r.text[:200], r.status_code, r.text)
            file_bug(name, "CREATE", "201", r.status_code, r.status_code, r.text)
    except Exception as e:
        record(name, "CREATE", False, str(e))

    # READ LIST
    try:
        r = requests.get(path, headers=h, timeout=30)
        if r.status_code == 200:
            items = extract_list(r.json())
            record(name, "READ_LIST", True, f"{len(items)} items", r.status_code)
            if not created_id and items:
                created_id = items[0].get("id")
        else:
            record(name, "READ_LIST", False, r.text[:200], r.status_code, r.text)
            file_bug(name, "READ_LIST", "200", r.status_code, r.status_code, r.text)
    except Exception as e:
        record(name, "READ_LIST", False, str(e))

    # READ ONE
    if created_id:
        try:
            r = requests.get(f"{path}/{created_id}", headers=h, timeout=30)
            if r.status_code == 200:
                record(name, "READ_ONE", True, f"id={created_id}", r.status_code)
            else:
                record(name, "READ_ONE", False, r.text[:200], r.status_code, r.text)
                file_bug(name, "READ_ONE", "200", r.status_code, r.status_code, r.text)
        except Exception as e:
            record(name, "READ_ONE", False, str(e))
    else:
        record(name, "READ_ONE", False, "No ID")

    # UPDATE
    if created_id:
        try:
            r = requests.put(f"{path}/{created_id}", json={"subject": f"Updated Ticket {ts}", "priority": "high"}, headers=h, timeout=30)
            if r.status_code in (200, 204):
                record(name, "UPDATE", True, f"id={created_id}", r.status_code)
            else:
                record(name, "UPDATE", False, r.text[:200], r.status_code, r.text)
                file_bug(name, "UPDATE", "200", r.status_code, r.status_code, r.text)
        except Exception as e:
            record(name, "UPDATE", False, str(e))
    else:
        record(name, "UPDATE", False, "No ID")

    # DELETE - no DELETE endpoint; close via PUT status=closed
    if created_id:
        try:
            r = requests.put(f"{path}/{created_id}", json={"status": "closed"}, headers=h, timeout=30)
            if r.status_code in (200, 204):
                record(name, "DELETE(close)", True, f"Closed ticket id={created_id}", r.status_code)
            else:
                record(name, "DELETE(close)", False, r.text[:200], r.status_code, r.text)
        except Exception as e:
            record(name, "DELETE(close)", False, str(e))
    else:
        record(name, "DELETE(close)", False, "No ID")


def test_forum_posts(token):
    ts = int(time.time())
    h = headers(token)
    name = "Forum Posts"
    path = f"{BASE}/forum/posts"
    log(f"\n{'='*60}\nTESTING: {name}\n{'='*60}")

    created_id = None

    # CREATE - needs category_id (int) and post_type
    try:
        r = requests.post(path, json={
            "title": f"E2E Forum Post {ts}", "content": "E2E test forum content",
            "category_id": 2, "post_type": "discussion"
        }, headers=h, timeout=30)
        if r.status_code in (200, 201):
            created_id = extract_id(r.json())
            record(name, "CREATE", True, f"id={created_id}", r.status_code)
        else:
            record(name, "CREATE", False, r.text[:200], r.status_code, r.text)
            file_bug(name, "CREATE", "201", r.status_code, r.status_code, r.text)
    except Exception as e:
        record(name, "CREATE", False, str(e))

    # READ LIST
    try:
        r = requests.get(path, headers=h, timeout=30)
        if r.status_code == 200:
            items = extract_list(r.json())
            record(name, "READ_LIST", True, f"{len(items)} items", r.status_code)
            if not created_id and items:
                created_id = items[0].get("id")
        else:
            record(name, "READ_LIST", False, r.text[:200], r.status_code, r.text)
            file_bug(name, "READ_LIST", "200", r.status_code, r.status_code, r.text)
    except Exception as e:
        record(name, "READ_LIST", False, str(e))

    # READ ONE
    if created_id:
        try:
            r = requests.get(f"{path}/{created_id}", headers=h, timeout=30)
            if r.status_code == 200:
                record(name, "READ_ONE", True, f"id={created_id}", r.status_code)
            else:
                record(name, "READ_ONE", False, r.text[:200], r.status_code, r.text)
                file_bug(name, "READ_ONE", "200", r.status_code, r.status_code, r.text)
        except Exception as e:
            record(name, "READ_ONE", False, str(e))
    else:
        record(name, "READ_ONE", False, "No ID")

    # UPDATE
    if created_id:
        try:
            r = requests.put(f"{path}/{created_id}", json={"title": f"Updated Post {ts}", "content": "Updated"}, headers=h, timeout=30)
            if r.status_code in (200, 204):
                record(name, "UPDATE", True, f"id={created_id}", r.status_code)
            else:
                record(name, "UPDATE", False, r.text[:200], r.status_code, r.text)
        except Exception as e:
            record(name, "UPDATE", False, str(e))
    else:
        record(name, "UPDATE", False, "No ID")

    # DELETE
    if created_id:
        try:
            r = requests.delete(f"{path}/{created_id}", headers=h, timeout=30)
            if r.status_code in (200, 204):
                record(name, "DELETE", True, f"id={created_id}", r.status_code)
            else:
                record(name, "DELETE", False, r.text[:200], r.status_code, r.text)
        except Exception as e:
            record(name, "DELETE", False, str(e))
    else:
        record(name, "DELETE", False, "No ID")


def test_leave_types(token):
    ts = int(time.time())
    h = headers(token)
    name = "Leave Types"
    path = f"{BASE}/leave/types"
    log(f"\n{'='*60}\nTESTING: {name}\n{'='*60}")

    created_id = None

    # CREATE
    try:
        r = requests.post(path, json={
            "name": f"E2E Leave {ts}", "code": f"EL{ts % 10000}",
            "description": "E2E test leave type", "allowedDays": 10,
            "carryForward": False, "paid": True
        }, headers=h, timeout=30)
        if r.status_code in (200, 201):
            created_id = extract_id(r.json())
            record(name, "CREATE", True, f"id={created_id}", r.status_code)
        else:
            record(name, "CREATE", False, r.text[:200], r.status_code, r.text)
            file_bug(name, "CREATE", "201", r.status_code, r.status_code, r.text)
    except Exception as e:
        record(name, "CREATE", False, str(e))

    # READ LIST
    try:
        r = requests.get(path, headers=h, timeout=30)
        if r.status_code == 200:
            items = extract_list(r.json())
            record(name, "READ_LIST", True, f"{len(items)} items", r.status_code)
            if not created_id and items:
                created_id = items[0].get("id")
        else:
            record(name, "READ_LIST", False, r.text[:200], r.status_code, r.text)
            file_bug(name, "READ_LIST", "200", r.status_code, r.status_code, r.text)
    except Exception as e:
        record(name, "READ_LIST", False, str(e))

    # READ ONE
    if created_id:
        try:
            r = requests.get(f"{path}/{created_id}", headers=h, timeout=30)
            if r.status_code == 200:
                record(name, "READ_ONE", True, f"id={created_id}", r.status_code)
            else:
                record(name, "READ_ONE", False, r.text[:200], r.status_code, r.text)
        except Exception as e:
            record(name, "READ_ONE", False, str(e))
    else:
        record(name, "READ_ONE", False, "No ID")

    # UPDATE
    if created_id:
        try:
            r = requests.put(f"{path}/{created_id}", json={"name": f"Updated Leave {ts}", "allowedDays": 15}, headers=h, timeout=30)
            if r.status_code in (200, 204):
                record(name, "UPDATE", True, f"id={created_id}", r.status_code)
            else:
                record(name, "UPDATE", False, r.text[:200], r.status_code, r.text)
        except Exception as e:
            record(name, "UPDATE", False, str(e))
    else:
        record(name, "UPDATE", False, "No ID")

    # DELETE
    if created_id:
        try:
            r = requests.delete(f"{path}/{created_id}", headers=h, timeout=30)
            if r.status_code in (200, 204):
                record(name, "DELETE", True, f"id={created_id}", r.status_code)
            else:
                record(name, "DELETE", False, r.text[:200], r.status_code, r.text)
        except Exception as e:
            record(name, "DELETE", False, str(e))
    else:
        record(name, "DELETE", False, "No ID")


def test_leave_applications(token):
    ts = int(time.time())
    h = headers(token)
    name = "Leave Applications"
    path = f"{BASE}/leave/applications"
    log(f"\n{'='*60}\nTESTING: {name}\n{'='*60}")

    created_id = None

    # Get sick leave type ID (probation employees can only apply for Sick/Emergency Leave)
    leave_type_id = None
    try:
        r = requests.get(f"{BASE}/leave/types", headers=h, timeout=30)
        if r.status_code == 200:
            types = extract_list(r.json())
            for t in types:
                if isinstance(t, dict) and "sick" in t.get("name", "").lower():
                    leave_type_id = t.get("id")
                    break
            if leave_type_id is None and types:
                leave_type_id = types[0].get("id")
    except:
        pass

    # CREATE - uses snake_case fields + days_count
    # Use far-future dates to avoid overlap
    start = f"2026-12-{10 + (ts % 15):02d}"
    end = start  # single day
    try:
        r = requests.post(path, json={
            "leave_type_id": leave_type_id,
            "start_date": start, "end_date": end,
            "days_count": 1, "reason": f"E2E test leave {ts}"
        }, headers=h, timeout=30)
        if r.status_code in (200, 201):
            created_id = extract_id(r.json())
            record(name, "CREATE", True, f"id={created_id}", r.status_code)
        else:
            record(name, "CREATE", False, r.text[:200], r.status_code, r.text)
            file_bug(name, "CREATE", "201", r.status_code, r.status_code, r.text)
    except Exception as e:
        record(name, "CREATE", False, str(e))

    # READ LIST
    try:
        r = requests.get(path, headers=h, timeout=30)
        if r.status_code == 200:
            items = extract_list(r.json())
            record(name, "READ_LIST", True, f"{len(items)} items", r.status_code)
            if not created_id and items:
                created_id = items[0].get("id")
        else:
            record(name, "READ_LIST", False, r.text[:200], r.status_code, r.text)
            file_bug(name, "READ_LIST", "200", r.status_code, r.status_code, r.text)
    except Exception as e:
        record(name, "READ_LIST", False, str(e))

    # READ ONE
    if created_id:
        try:
            r = requests.get(f"{path}/{created_id}", headers=h, timeout=30)
            if r.status_code == 200:
                record(name, "READ_ONE", True, f"id={created_id}", r.status_code)
            else:
                record(name, "READ_ONE", False, r.text[:200], r.status_code, r.text)
        except Exception as e:
            record(name, "READ_ONE", False, str(e))
    else:
        record(name, "READ_ONE", False, "No ID")

    # UPDATE - only status=cancelled supported via PUT
    if created_id:
        try:
            r = requests.put(f"{path}/{created_id}", json={"status": "cancelled"}, headers=h, timeout=30)
            if r.status_code in (200, 204):
                record(name, "UPDATE(cancel)", True, f"Cancelled id={created_id}", r.status_code)
            else:
                record(name, "UPDATE(cancel)", False, r.text[:200], r.status_code, r.text)
        except Exception as e:
            record(name, "UPDATE(cancel)", False, str(e))
    else:
        record(name, "UPDATE(cancel)", False, "No ID")

    # DELETE - no DELETE endpoint
    record(name, "DELETE", True, "N/A (no delete endpoint; cancelled via PUT)", None)


def test_attendance_shifts(token):
    ts = int(time.time())
    h = headers(token)
    name = "Attendance Shifts"
    path = f"{BASE}/attendance/shifts"
    log(f"\n{'='*60}\nTESTING: {name}\n{'='*60}")

    created_id = None

    # CREATE - snake_case fields
    try:
        r = requests.post(path, json={
            "name": f"E2E Shift {ts}",
            "start_time": "09:00", "end_time": "18:00",
            "break_minutes": 60, "grace_minutes_late": 15, "grace_minutes_early": 10
        }, headers=h, timeout=30)
        if r.status_code in (200, 201):
            created_id = extract_id(r.json())
            record(name, "CREATE", True, f"id={created_id}", r.status_code)
        else:
            record(name, "CREATE", False, r.text[:200], r.status_code, r.text)
            file_bug(name, "CREATE", "201", r.status_code, r.status_code, r.text)
    except Exception as e:
        record(name, "CREATE", False, str(e))

    # READ LIST
    try:
        r = requests.get(path, headers=h, timeout=30)
        if r.status_code == 200:
            items = extract_list(r.json())
            record(name, "READ_LIST", True, f"{len(items)} items", r.status_code)
            if not created_id and items:
                created_id = items[0].get("id")
        else:
            record(name, "READ_LIST", False, r.text[:200], r.status_code, r.text)
            file_bug(name, "READ_LIST", "200", r.status_code, r.status_code, r.text)
    except Exception as e:
        record(name, "READ_LIST", False, str(e))

    # READ ONE -- GET /attendance/shifts/:id may return 404 (no per-ID route)
    if created_id:
        try:
            r = requests.get(f"{path}/{created_id}", headers=h, timeout=30)
            if r.status_code == 200:
                record(name, "READ_ONE", True, f"id={created_id}", r.status_code)
            else:
                record(name, "READ_ONE", False, f"GET /attendance/shifts/{created_id} -> {r.status_code}", r.status_code, r.text)
                file_bug(name, "READ_ONE", "200", r.status_code, r.status_code, r.text)
        except Exception as e:
            record(name, "READ_ONE", False, str(e))
    else:
        record(name, "READ_ONE", False, "No ID")

    # UPDATE
    if created_id:
        try:
            r = requests.put(f"{path}/{created_id}", json={"name": f"Updated Shift {ts}", "grace_minutes_late": 20}, headers=h, timeout=30)
            if r.status_code in (200, 204):
                record(name, "UPDATE", True, f"id={created_id}", r.status_code)
            else:
                record(name, "UPDATE", False, r.text[:200], r.status_code, r.text)
                file_bug(name, "UPDATE", "200", r.status_code, r.status_code, r.text)
        except Exception as e:
            record(name, "UPDATE", False, str(e))
    else:
        record(name, "UPDATE", False, "No ID")

    # DELETE
    if created_id:
        try:
            r = requests.delete(f"{path}/{created_id}", headers=h, timeout=30)
            if r.status_code in (200, 204):
                record(name, "DELETE", True, f"id={created_id}", r.status_code)
            else:
                record(name, "DELETE", False, r.text[:200], r.status_code, r.text)
        except Exception as e:
            record(name, "DELETE", False, str(e))
    else:
        record(name, "DELETE", False, "No ID")


def test_policies(token):
    ts = int(time.time())
    h = headers(token)
    name = "Policies"
    path = f"{BASE}/policies"
    log(f"\n{'='*60}\nTESTING: {name}\n{'='*60}")

    created_id = None

    # CREATE
    try:
        r = requests.post(path, json={
            "title": f"E2E Policy {ts}", "content": "E2E test policy body text.",
            "category": "HR", "effectiveDate": "2026-04-01", "requiresAcknowledgment": True
        }, headers=h, timeout=30)
        if r.status_code in (200, 201):
            created_id = extract_id(r.json())
            record(name, "CREATE", True, f"id={created_id}", r.status_code)
        else:
            record(name, "CREATE", False, r.text[:200], r.status_code, r.text)
            file_bug(name, "CREATE", "201", r.status_code, r.status_code, r.text)
    except Exception as e:
        record(name, "CREATE", False, str(e))

    # READ LIST
    try:
        r = requests.get(path, headers=h, timeout=30)
        if r.status_code == 200:
            items = extract_list(r.json())
            record(name, "READ_LIST", True, f"{len(items)} items", r.status_code)
            if not created_id and items:
                created_id = items[0].get("id")
        else:
            record(name, "READ_LIST", False, r.text[:200], r.status_code, r.text)
            file_bug(name, "READ_LIST", "200", r.status_code, r.status_code, r.text)
    except Exception as e:
        record(name, "READ_LIST", False, str(e))

    # READ ONE
    if created_id:
        try:
            r = requests.get(f"{path}/{created_id}", headers=h, timeout=30)
            if r.status_code == 200:
                record(name, "READ_ONE", True, f"id={created_id}", r.status_code)
            else:
                record(name, "READ_ONE", False, r.text[:200], r.status_code, r.text)
                file_bug(name, "READ_ONE", "200", r.status_code, r.status_code, r.text)
        except Exception as e:
            record(name, "READ_ONE", False, str(e))
    else:
        record(name, "READ_ONE", False, "No ID")

    # UPDATE
    if created_id:
        try:
            r = requests.put(f"{path}/{created_id}", json={"title": f"Updated Policy {ts}", "content": "Updated body"}, headers=h, timeout=30)
            if r.status_code in (200, 204):
                record(name, "UPDATE", True, f"id={created_id}", r.status_code)
            else:
                record(name, "UPDATE", False, r.text[:200], r.status_code, r.text)
                file_bug(name, "UPDATE", "200", r.status_code, r.status_code, r.text)
        except Exception as e:
            record(name, "UPDATE", False, str(e))
    else:
        record(name, "UPDATE", False, "No ID")

    # DELETE -- policies may not have delete, try it
    if created_id:
        try:
            r = requests.delete(f"{path}/{created_id}", headers=h, timeout=30)
            if r.status_code in (200, 204):
                record(name, "DELETE", True, f"id={created_id}", r.status_code)
            else:
                record(name, "DELETE", False, r.text[:200], r.status_code, r.text)
        except Exception as e:
            record(name, "DELETE", False, str(e))
    else:
        record(name, "DELETE", False, "No ID")


def test_wellness_checkin(token):
    ts = int(time.time())
    h = headers(token)
    name = "Wellness Check-in"
    log(f"\n{'='*60}\nTESTING: {name}\n{'='*60}")

    # CREATE - POST /wellness/check-in with mood (string), energy_level, sleep_hours, exercise_minutes, notes
    try:
        r = requests.post(f"{BASE}/wellness/check-in", json={
            "mood": "good", "energy_level": 4, "sleep_hours": 7.5,
            "exercise_minutes": 30, "notes": f"E2E wellness {ts}"
        }, headers=h, timeout=30)
        if r.status_code in (200, 201):
            created_id = extract_id(r.json())
            record(name, "CREATE", True, f"id={created_id}", r.status_code)
        else:
            record(name, "CREATE", False, r.text[:200], r.status_code, r.text)
            file_bug(name, "CREATE", "201", r.status_code, r.status_code, r.text)
    except Exception as e:
        record(name, "CREATE", False, str(e))

    # READ -- GET /wellness/check-ins (plural) returns list
    try:
        r = requests.get(f"{BASE}/wellness/check-ins", headers=h, timeout=30)
        if r.status_code == 200:
            items = extract_list(r.json())
            record(name, "READ_LIST", True, f"{len(items)} check-ins", r.status_code)
        else:
            record(name, "READ_LIST", False, r.text[:200], r.status_code, r.text)
            file_bug(name, "READ_LIST", "200", r.status_code, r.status_code, r.text)
    except Exception as e:
        record(name, "READ_LIST", False, str(e))

    # READ dashboard
    try:
        r = requests.get(f"{BASE}/wellness/dashboard", headers=h, timeout=30)
        if r.status_code == 200:
            record(name, "READ_ONE(dashboard)", True, "dashboard OK", r.status_code)
        else:
            record(name, "READ_ONE(dashboard)", False, r.text[:200], r.status_code, r.text)
    except Exception as e:
        record(name, "READ_ONE(dashboard)", False, str(e))

    # UPDATE - no update endpoint for check-ins
    record(name, "UPDATE", True, "N/A (check-ins are immutable)", None)

    # DELETE - no delete endpoint for check-ins
    record(name, "DELETE", True, "N/A (check-ins are immutable)", None)


# ── Main ──

def main():
    now = datetime.now(timezone.utc).isoformat()
    log("=" * 70)
    log("EmpCloud Full CRUD E2E API Test")
    log(f"Started: {now}")
    log(f"API: {BASE}")
    log("=" * 70)

    token = login()

    test_announcements(token)
    test_events(token)
    test_surveys(token)
    test_feedback(token)
    test_assets(token)
    test_positions(token)
    test_helpdesk_tickets(token)
    test_forum_posts(token)
    test_leave_types(token)
    test_leave_applications(token)
    test_attendance_shifts(token)
    test_policies(token)
    test_wellness_checkin(token)

    # ── Summary ──
    log(f"\n{'='*70}")
    log("SUMMARY")
    log("=" * 70)

    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    failed = sum(1 for r in results if not r["passed"])

    log(f"Total checks: {total}")
    log(f"Passed: {passed}")
    log(f"Failed: {failed}")

    if failed > 0:
        log(f"\n--- FAILURES ---")
        for r in results:
            if not r["passed"]:
                log(f"  FAIL {r['endpoint']} / {r['operation']}: [{r.get('status_code','')}] {r['detail'][:200]}")

    if bugs:
        log(f"\n--- BUGS ({len(bugs)}) ---")
        for b in bugs:
            log(f"  BUG: {b['endpoint']} {b['operation']} - expected {b['expected']}, got {b['actual']}")
            log(f"       Response: {b['response_body'][:200]}")

    log(f"\n{'='*70}")
    log("REQUIRED FIELDS PER ENDPOINT (POST)")
    log("=" * 70)
    log("Announcements:       title, content [priority: normal/high/urgent]")
    log("Events:              title, description, event_type, start_date (YYYY-MM-DD or 'YYYY-MM-DD HH:MM:SS'), end_date, location, target_type")
    log("Surveys:             title, description, type, is_anonymous, target_type, questions[{question_text, question_type(scale/text), is_required, sort_order}]")
    log("Feedback:            subject, message, category")
    log("Assets:              name, type, category, serialNumber, status, purchaseDate, purchasePrice")
    log("Positions:           title, department_id (int), code (unique), status, headcount_budget, employment_type")
    log("Helpdesk Tickets:    subject, description, category, priority")
    log("Forum Posts:         title, content, category_id (int), post_type")
    log("Leave Types:         name, code, description, allowedDays, carryForward, paid")
    log("Leave Applications:  leave_type_id (int), start_date, end_date, days_count, reason")
    log("Attendance Shifts:   name, start_time, end_time, break_minutes, grace_minutes_late, grace_minutes_early")
    log("Policies:            title, content, category, effectiveDate, requiresAcknowledgment")
    log("Wellness Check-in:   mood (great/good/okay/stressed/bad), energy_level, sleep_hours, exercise_minutes, notes")

    log(f"\nFinished: {datetime.now(timezone.utc).isoformat()}")

    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
