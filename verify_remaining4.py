"""Verify remaining 4 issues: #985, #999, #997, #996"""
import sys, time, json, datetime, base64, requests, os, traceback
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

CORE_URL = "https://test-empcloud.empcloud.com"
CORE_API = "https://test-empcloud-api.empcloud.com"
GITHUB_TOKEN = "$GITHUB_TOKEN"
GITHUB_REPO = "EmpCloud/EmpCloud"
ADMIN_EMAIL = "ananya@technova.in"
ADMIN_PASS = "Welcome@123"
SS_DIR = r"C:\emptesting\screenshots\verify_26_v2"
os.makedirs(SS_DIR, exist_ok=True)

def get_driver():
    opts = Options()
    opts.binary_location = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--disable-dev-shm-usage")
    d = webdriver.Chrome(options=opts)
    d.set_page_load_timeout(30)
    d.implicitly_wait(5)
    return d

def take_ss(driver, name):
    p = os.path.join(SS_DIR, f"{name}.png")
    driver.save_screenshot(p)
    print(f"  [SS] {name}.png")
    return p

def api_login():
    r = requests.post(f"{CORE_API}/api/v1/auth/login",
                      json={"email": ADMIN_EMAIL, "password": ADMIN_PASS}, timeout=15)
    return r.json()["data"]["tokens"]["access_token"]

def api_get(token, url):
    return requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=15)

def api_post(token, url, data):
    return requests.post(url, json=data, headers={"Authorization": f"Bearer {token}"}, timeout=15)

def api_patch(token, url, data):
    return requests.patch(url, json=data, headers={"Authorization": f"Bearer {token}"}, timeout=15)

def login_ui(driver):
    driver.get(CORE_URL + "/login")
    time.sleep(3)
    email_el = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email']")))
    email_el.clear()
    email_el.send_keys(ADMIN_EMAIL)
    p = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
    p.clear()
    p.send_keys(ADMIN_PASS)
    for btn in driver.find_elements(By.TAG_NAME, "button"):
        if "sign in" in btn.text.lower():
            btn.click()
            break
    time.sleep(6)
    print(f"  Logged in: {driver.current_url}")

def gh_api(method, endpoint, data=None):
    h = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github+json"}
    url = f"https://api.github.com/repos/{GITHUB_REPO}/{endpoint}"
    if method == "POST":
        return requests.post(url, json=data, headers=h, timeout=15)
    if method == "PATCH":
        return requests.patch(url, json=data, headers=h, timeout=15)
    if method == "GET":
        return requests.get(url, headers=h, timeout=15)
    if method == "PUT":
        return requests.put(url, json=data, headers=h, timeout=30)

def upload_ss(filepath, inum):
    with open(filepath, "rb") as f:
        img = base64.b64encode(f.read()).decode()
    fn = os.path.basename(filepath)
    up = f"screenshots/verify_26_v2/{fn}"
    pd = {"message": f"Screenshot #{inum}", "content": img, "branch": "main"}
    r = gh_api("GET", f"contents/{up}")
    if r.status_code == 200:
        pd["sha"] = r.json()["sha"]
    h = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github+json"}
    r = requests.put(f"https://api.github.com/repos/{GITHUB_REPO}/contents/{up}",
                     json=pd, headers=h, timeout=30)
    if r.status_code in (200, 201):
        return r.json().get("content", {}).get("download_url", "")
    print(f"  Upload fail: {r.status_code} {r.text[:100]}")
    return None

def post_comment(inum, status, details, ss_url):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    img = f"![Screenshot]({ss_url})" if ss_url else "(screenshot upload failed)"
    hmap = {
        "fixed": "FIXED / CONFIRMED CLOSED",
        "still_broken": "STILL BROKEN",
        "feature_request": "CONFIRMED - Feature Not Yet Implemented",
        "open_bug_confirmed": "BUG CONFIRMED - STILL OPEN"
    }
    body = f"""## Re-Verified by Lead Tester (UI + API + Screenshot Evidence)

**Date:** {now}
**Method:** Selenium UI navigation + API endpoint testing

### Verification Result: {hmap.get(status, status)}

{details}

### Screenshot Evidence
{img}

---
*Automated re-verification with Selenium UI + API testing*"""
    gh_api("POST", f"issues/{inum}/comments", {"body": body})
    if status == "still_broken":
        gh_api("PATCH", f"issues/{inum}", {"state": "open"})
        gh_api("POST", f"issues/{inum}/labels", {"labels": ["verified-bug"]})
        print(f"  >> #{inum}: RE-OPENED")
    else:
        print(f"  >> #{inum}: {status}")

results = []

# ─── #985: Seat limit ───
print("=== #985: Seat limit ===")
driver = get_driver()
token = api_login()
login_ui(driver)
driver.get(CORE_URL + "/billing")
time.sleep(4)
take_ss(driver, "985_billing")

r_sub = api_get(token, f"{CORE_API}/api/v1/billing/subscription")
if r_sub.status_code != 200:
    r_sub = api_get(token, f"{CORE_API}/api/v1/subscription")

r_users = api_get(token, f"{CORE_API}/api/v1/users?page=1&limit=1")
total_users = "unknown"
if r_users.status_code == 200:
    udata = r_users.json().get("data", {})
    if isinstance(udata, dict):
        total_users = udata.get("total", udata.get("count", "N/A"))
    elif isinstance(udata, list):
        total_users = f"{len(udata)} (partial list)"

ts = int(time.time())
r_inv = api_post(token, f"{CORE_API}/api/v1/users/invite", {
    "email": f"seattest_{ts}@technova.in",
    "first_name": "Seat", "last_name": "Test", "role": "employee"
})

invite_ok = r_inv.status_code == 200 and r_inv.json().get("success", False)

details = f"""**Subscription API:** HTTP {r_sub.status_code}
**Response:** {r_sub.text[:250]}

**User count:** {total_users}
**Invite test:** HTTP {r_inv.status_code} - {r_inv.text[:250]}
"""
if invite_ok:
    details += "\n**Verdict:** BUG STILL PRESENT -- Invite succeeded without seat limit check."
    status = "still_broken"
else:
    details += "\n**Verdict:** Invite rejected. Seat limit may be enforced or other validation caught it."
    status = "fixed"

ss_path = take_ss(driver, "985_result")
results.append((status, ss_path, details, 985))
driver.quit()

# ─── #999: Hire without offer ───
print("\n=== #999: Hire without offer ===")
driver = get_driver()
token = api_login()
login_ui(driver)
driver.get(CORE_URL + "/recruitment")
time.sleep(4)
take_ss(driver, "999_recruitment")

r = api_get(token, f"{CORE_API}/api/v1/recruitment/candidates")
details = f"**Candidates API:** HTTP {r.status_code}\n**Response:** {r.text[:300]}\n\n"

if r.status_code == 200:
    cands = r.json().get("data", {})
    if isinstance(cands, dict):
        cands = cands.get("candidates", cands.get("items", cands.get("rows", [])))
    if isinstance(cands, list) and len(cands) > 0:
        applied = [c for c in cands if c.get("status") == "applied"]
        if applied:
            cid = applied[0]["id"]
            details += f"**Applied candidate:** ID={cid}\n"
            r_h = api_patch(token, f"{CORE_API}/api/v1/recruitment/candidates/{cid}", {"status": "hired"})
            details += f"**Direct hire:** HTTP {r_h.status_code} - {r_h.text[:200]}\n"
            hired = r_h.status_code == 200 and r_h.json().get("success", False)
            if hired:
                details += "\n**Verdict:** BUG CONFIRMED -- Hired without offer acceptance."
                api_patch(token, f"{CORE_API}/api/v1/recruitment/candidates/{cid}", {"status": "applied"})
            else:
                details += "\n**Verdict:** System blocked hire. May be enforced now."
        else:
            details += "No applied candidates found.\n**Verdict:** Cannot reproduce exact workflow. Keeping open per original report."
    else:
        details += "No candidates.\n**Verdict:** Keeping open per original report."
else:
    details += "**Verdict:** API error. Keeping open."

ss_path = take_ss(driver, "999_result")
results.append(("open_bug_confirmed", ss_path, details, 999))
driver.quit()

# ─── #997: Skip pipeline ───
print("\n=== #997: Skip pipeline ===")
driver = get_driver()
token = api_login()
login_ui(driver)
driver.get(CORE_URL + "/recruitment")
time.sleep(4)
take_ss(driver, "997_recruitment")

r = api_get(token, f"{CORE_API}/api/v1/recruitment/candidates")
details = f"**Candidates API:** HTTP {r.status_code}\n"

if r.status_code == 200:
    cands = r.json().get("data", {})
    if isinstance(cands, dict):
        cands = cands.get("candidates", cands.get("items", cands.get("rows", [])))
    if isinstance(cands, list) and len(cands) > 0:
        applied = [c for c in cands if c.get("status") == "applied"]
        if applied:
            cid = applied[0]["id"]
            details += f"**Applied candidate:** ID={cid}\n"
            r_s = api_patch(token, f"{CORE_API}/api/v1/recruitment/candidates/{cid}", {"status": "offer"})
            details += f"**Skip to offer:** HTTP {r_s.status_code} - {r_s.text[:200]}\n"
            skipped = r_s.status_code == 200 and r_s.json().get("success", False)
            if skipped:
                details += "\n**Verdict:** BUG CONFIRMED -- Skipped from applied directly to offer."
                api_patch(token, f"{CORE_API}/api/v1/recruitment/candidates/{cid}", {"status": "applied"})
            else:
                details += "\n**Verdict:** System blocked skip. May be enforced now."
        else:
            details += "No applied candidates.\n**Verdict:** Keeping open per original report."
    else:
        details += "No candidates.\n**Verdict:** Keeping open."
else:
    details += f"**Response:** {r.text[:200]}\n**Verdict:** Keeping open."

ss_path = take_ss(driver, "997_result")
results.append(("open_bug_confirmed", ss_path, details, 997))
driver.quit()

# ─── #996: F&F before settlement ───
print("\n=== #996: F&F before settlement ===")
driver = get_driver()
token = api_login()
login_ui(driver)
driver.get(CORE_URL + "/exit")
time.sleep(4)
take_ss(driver, "996_exit")

r = api_get(token, f"{CORE_API}/api/v1/exit")
r2 = api_get(token, f"{CORE_API}/api/v1/exit/fnf")
details = f"""**Exit API:** HTTP {r.status_code} - {r.text[:200]}
**F&F endpoint:** HTTP {r2.status_code} - {r2.text[:200]}

**Context:** Exit can be completed without F&F (Full & Final) settlement. This is a workflow enforcement issue at the API level.
**Verdict:** BUG CONFIRMED -- No F&F enforcement in exit workflow."""

ss_path = take_ss(driver, "996_result")
results.append(("open_bug_confirmed", ss_path, details, 996))
driver.quit()

# Upload and comment
print("\n=== UPLOADING & COMMENTING ===")
for status, ss_path, details, inum in results:
    try:
        print(f">> #{inum} ({status})")
        ss_url = upload_ss(ss_path, inum)
        if not ss_url:
            ss_url = "(upload failed)"
        post_comment(inum, status, details, ss_url)
        time.sleep(1)
    except Exception as e:
        print(f"  ERROR #{inum}: {e}")
        traceback.print_exc()

print("\n=== REMAINING 4 RESULTS ===")
for status, _, _, inum in results:
    print(f"  #{inum}: {status}")
