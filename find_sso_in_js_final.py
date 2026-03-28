import sys
import re
import json
import urllib.request
import ssl

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
BASE = 'https://test-empcloud.empcloud.com'

# Download the DashboardPage chunk
chunk_url = f'{BASE}/assets/DashboardPage-C3qd1jjb.js'
req = urllib.request.Request(chunk_url, headers={'User-Agent': UA})
chunk_js = urllib.request.urlopen(req, context=ctx).read().decode('utf-8', errors='replace')

print(f"DashboardPage chunk: {len(chunk_js)} bytes")
print()

# Find all SSO-related code with full context
print("=" * 80)
print("SSO URL GENERATION CODE")
print("=" * 80)

# The key pattern: base_url + sso_token
for m in re.finditer(r'sso_token', chunk_js):
    pos = m.start()
    # Get a large context window
    start = max(0, pos - 500)
    end = min(len(chunk_js), pos + 500)
    print(f"\nsso_token at position {pos}:")
    print(chunk_js[start:end])
    print("\n" + "-" * 60)

# Find the module URL map (b variable)
print("\n" + "=" * 80)
print("MODULE BASE_URL MAP CONSTRUCTION")
print("=" * 80)

for m in re.finditer(r'base_url', chunk_js):
    pos = m.start()
    start = max(0, pos - 300)
    end = min(len(chunk_js), pos + 300)
    print(f"\nbase_url at position {pos}:")
    print(chunk_js[start:end])
    print("\n" + "-" * 60)

# Find moduleUrl references in the component
print("\n" + "=" * 80)
print("moduleUrl PROP USAGE")
print("=" * 80)

for m in re.finditer(r'moduleUrl', chunk_js):
    pos = m.start()
    start = max(0, pos - 200)
    end = min(len(chunk_js), pos + 300)
    print(f"\nmoduleUrl at position {pos}:")
    print(chunk_js[start:end])
    print("\n" + "-" * 60)

# Find the "launch" link rendering
print("\n" + "=" * 80)
print("LAUNCH LINK RENDERING")
print("=" * 80)

for m in re.finditer(r'launch|Launch', chunk_js):
    pos = m.start()
    start = max(0, pos - 300)
    end = min(len(chunk_js), pos + 300)
    print(f"\nlaunch at position {pos}:")
    print(chunk_js[start:end])
    print("\n" + "-" * 60)

# Find the ModulesPage subscription/SSO code
print("\n" + "=" * 80)
print("MODULES PAGE - SSO CODE")
print("=" * 80)

mod_url = f'{BASE}/assets/ModulesPage-CCqW7Cm_.js'
req2 = urllib.request.Request(mod_url, headers={'User-Agent': UA})
mod_js = urllib.request.urlopen(req2, context=ctx).read().decode('utf-8', errors='replace')

# Search for SSO/token/URL patterns
for pat in ['sso', 'token', 'base_url', 'module_url', 'href', 'window.open', 'target.*blank']:
    for m2 in re.finditer(pat, mod_js):
        pos = m2.start()
        start = max(0, pos - 200)
        end = min(len(mod_js), pos + 300)
        snippet = mod_js[start:end]
        if 'sso' in snippet.lower() or 'token' in snippet.lower() or 'url' in snippet.lower():
            print(f"\n[ModulesPage] '{pat}' at {pos}:")
            print(snippet)
            print("-" * 60)
            break

# Now fetch the API to see module base_urls
print("\n" + "=" * 80)
print("API: Module definitions with base_url")
print("=" * 80)

API = 'https://test-empcloud-api.empcloud.com/api/v1'
login_data = json.dumps({
    "email": "ananya@technova.in",
    "password": "Welcome@123"
}).encode()

req_login = urllib.request.Request(
    f'{API}/auth/login',
    data=login_data,
    headers={'Content-Type': 'application/json', 'User-Agent': UA},
    method='POST'
)

resp = urllib.request.urlopen(req_login, context=ctx)
login_resp = json.loads(resp.read().decode())
token = login_resp['data']['tokens']['access_token']
print(f"Logged in. Token: {token[:40]}...")

# Get subscriptions
for ep in ['/subscriptions', '/modules']:
    try:
        req_api = urllib.request.Request(f'{API}{ep}', headers={
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
            'User-Agent': UA
        })
        resp_api = urllib.request.urlopen(req_api, context=ctx)
        data = json.loads(resp_api.read().decode())
        print(f"\nGET {ep}:")
        print(json.dumps(data, indent=2, default=str)[:5000])
    except Exception as e:
        code = getattr(e, 'code', str(e))
        try:
            body = e.read().decode()[:500]
        except:
            body = ''
        print(f"GET {ep} -> {code}: {body}")

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print("""
The SSO URL is generated in the DashboardPage-C3qd1jjb.js chunk.

The pattern is:
  v = r != null && r.base_url
      ? `${r.base_url}?sso_token=${encodeURIComponent(I.getState().accessToken || "")}`
      : null;

Where:
- r = module definition from the modules API (contains base_url)
- I = the auth store (ha/zustand) which holds accessToken
- The SSO URL = module.base_url + "?sso_token=" + encodeURIComponent(accessToken)
""")
