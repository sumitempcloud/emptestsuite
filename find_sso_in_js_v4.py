import sys
import re
import json
import urllib.request
import ssl

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
BASE = 'https://test-empcloud.empcloud.com'
API_BASE = 'https://test-empcloud-api.empcloud.com'

# ===========================
# 1. Download and fully print key chunk files
# ===========================
print("=" * 80)
print("1. KEY CHUNK FILES - ModulesPage, BillingPage, LoginPage, DashboardPage")
print("=" * 80)

key_chunks = [
    'ModulesPage-CCqW7Cm_.js',
    'BillingPage-BIK6Hjgo.js',
    'LoginPage-jOKZ1-Go.js',
    'DashboardPage-C3qd1jjb.js',
    'SettingsPage-Cz-1xlBw.js',
]

for chunk_name in key_chunks:
    try:
        url = f'{BASE}/assets/{chunk_name}'
        req = urllib.request.Request(url, headers={'User-Agent': UA})
        chunk_js = urllib.request.urlopen(req, context=ctx).read().decode('utf-8', errors='replace')
        print(f"\n{'='*60}")
        print(f"CHUNK: {chunk_name} ({len(chunk_js)} bytes)")
        print(f"{'='*60}")
        # Print full content if under 10K, otherwise first 5K + any SSO patterns
        if len(chunk_js) < 15000:
            print(chunk_js)
        else:
            print("FIRST 5000 chars:")
            print(chunk_js[:5000])
            print("\n... searching for key patterns ...")
            for pat in ['sso', 'SSO', 'token', 'url', 'href', 'redirect', 'launch',
                        'module', 'window.open', 'window.location', 'empcloud',
                        'subscribe', 'activate', 'enable']:
                for m in re.finditer(pat, chunk_js, re.IGNORECASE):
                    pos = m.start()
                    snippet = chunk_js[max(0,pos-150):min(len(chunk_js),pos+250)]
                    print(f'\n>>> "{pat}" at {pos}:')
                    print(snippet)
                    print("---")
                    break  # first per pattern
    except Exception as e:
        print(f"Failed to download {chunk_name}: {e}")

# ===========================
# 2. Login via correct API endpoint and check subscriptions
# ===========================
print("\n" + "=" * 80)
print("2. API: Login and check subscriptions/modules")
print("=" * 80)

# Try different login endpoints
login_endpoints = [
    f'{API_BASE}/api/v1/auth/login',
    f'{API_BASE}/api/v1/auth/signin',
    f'{API_BASE}/api/v1/users/login',
    f'{API_BASE}/api/v1/session',
    f'{API_BASE}/api/v1/oauth/token',
    f'{API_BASE}/oauth/token',
    f'{API_BASE}/api/auth/login',
]

token = None

# First try OAuth token endpoint (since the JS uses oauth/token for refresh)
try:
    oauth_data = urllib.request.urlencode({
        'grant_type': 'password',
        'username': 'ananya@technova.in',
        'password': 'Welcome@123',
        'client_id': 'empcloud-dashboard'
    }).encode()
    req = urllib.request.Request(
        f'{API_BASE}/oauth/token',
        data=oauth_data,
        headers={'Content-Type': 'application/x-www-form-urlencoded', 'User-Agent': UA},
        method='POST'
    )
    resp = urllib.request.urlopen(req, context=ctx)
    data = json.loads(resp.read().decode())
    print(f"OAuth token endpoint OK:")
    print(json.dumps(data, indent=2, default=str)[:2000])
    token = data.get('access_token', '')
except Exception as e:
    code = getattr(e, 'code', '')
    try:
        body = e.read().decode() if hasattr(e, 'read') else ''
    except:
        body = ''
    print(f"OAuth token: {code} - {body[:500]}")

# Also try JSON login
for login_ep in login_endpoints:
    if token:
        break
    try:
        login_data = json.dumps({
            "email": "ananya@technova.in",
            "password": "Welcome@123"
        }).encode()
        req = urllib.request.Request(
            login_ep,
            data=login_data,
            headers={'Content-Type': 'application/json', 'User-Agent': UA},
            method='POST'
        )
        resp = urllib.request.urlopen(req, context=ctx)
        data = json.loads(resp.read().decode())
        print(f"\n{login_ep} -> OK:")
        print(json.dumps(data, indent=2, default=str)[:2000])
        token = data.get('data', {}).get('token', '') or data.get('access_token', '') or data.get('token', '')
    except Exception as e:
        code = getattr(e, 'code', '')
        print(f"{login_ep} -> {code}")

if token:
    print(f"\nToken obtained: {token[:40]}...")

    # Check subscriptions
    for ep in ['/api/v1/subscriptions', '/api/v1/modules', '/api/v1/billing',
               '/api/v1/marketplace', '/api/v1/dashboard']:
        try:
            req2 = urllib.request.Request(f'{API_BASE}{ep}', headers={
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json',
                'User-Agent': UA
            })
            resp2 = urllib.request.urlopen(req2, context=ctx)
            data = json.loads(resp2.read().decode())
            resp_str = json.dumps(data, indent=2, default=str)
            print(f"\nGET {ep} -> OK:")
            if len(resp_str) > 4000:
                print(resp_str[:4000] + "\n...(truncated)")
            else:
                print(resp_str)
        except Exception as e:
            code = getattr(e, 'code', '')
            if str(code) not in ['404']:
                print(f"GET {ep} -> {code}")

# ===========================
# 3. Search main bundle for the area around "/modules" and "/billing" route handlers
# ===========================
print("\n" + "=" * 80)
print("3. ROUTE HANDLER CONTEXT FOR /modules AND /billing")
print("=" * 80)

req_html = urllib.request.Request(BASE + '/', headers={'User-Agent': UA})
html = urllib.request.urlopen(req_html, context=ctx).read().decode('utf-8', errors='replace')
js_files = re.findall(r'src="(/assets/[^"]+\.js)"', html)

req_js = urllib.request.Request(BASE + js_files[0], headers={'User-Agent': UA})
js = urllib.request.urlopen(req_js, context=ctx).read().decode('utf-8', errors='replace')

# Find route definitions for /modules and /billing
for m in re.finditer(r'/modules|/billing|ModulesPage|BillingPage', js):
    pos = m.start()
    snippet = js[max(0,pos-200):min(len(js),pos+400)]
    print(f"\n>>> at {pos}:")
    print(snippet)
    print("---")

print("\n" + "=" * 80)
print("DONE")
print("=" * 80)
