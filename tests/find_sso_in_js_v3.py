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
API = 'https://test-empcloud-api.empcloud.com/api/v1'

# Download the main JS bundle
req_html = urllib.request.Request(BASE + '/', headers={'User-Agent': UA})
html = urllib.request.urlopen(req_html, context=ctx).read().decode('utf-8', errors='replace')
js_files = re.findall(r'src="(/assets/[^"]+\.js)"', html)

req_js = urllib.request.Request(BASE + js_files[0], headers={'User-Agent': UA})
js = urllib.request.urlopen(req_js, context=ctx).read().decode('utf-8', errors='replace')

print(f"Bundle: {js_files[0]} ({len(js)//1024}KB)")
print()

# ===========================
# 1. Find the auth store (ha) - it manages tokens
# ===========================
print("=" * 80)
print("1. AUTH STORE (ha) - token management")
print("=" * 80)

# Find the Zustand store creation for auth
for m in re.finditer(r'ha\s*=\s*', js):
    pos = m.start()
    snippet = js[max(0,pos-50):min(len(js),pos+500)]
    if 'token' in snippet.lower() or 'login' in snippet.lower() or 'user' in snippet.lower():
        print(f"\nAuth store at {pos}:")
        print(snippet)
        print("---")

# ===========================
# 2. Find module_slug patterns - these identify modules
# ===========================
print("\n" + "=" * 80)
print("2. MODULE SLUG PATTERNS")
print("=" * 80)

for m in re.finditer(r'module_slug|module\.slug|moduleSlug', js):
    pos = m.start()
    snippet = js[max(0,pos-200):min(len(js),pos+300)]
    print(f"\nmodule_slug at {pos}:")
    print(snippet)
    print("---")

# ===========================
# 3. Find empcloud subdomain URL construction
# ===========================
print("\n" + "=" * 80)
print("3. EMPCLOUD SUBDOMAIN PATTERNS")
print("=" * 80)

for m in re.finditer(r'empcloud|emp-cloud|emp_cloud', js, re.IGNORECASE):
    pos = m.start()
    snippet = js[max(0,pos-200):min(len(js),pos+200)]
    # Skip CSS/i18n noise
    if 'EMP Cloud' in snippet and ('login' in snippet.lower() or 'url' in snippet.lower() or 'http' in snippet.lower()):
        print(f"\nempcloud at {pos}:")
        print(snippet)
        print("---")

# ===========================
# 4. Find the Sidebar/Navigation component that renders module links
# ===========================
print("\n" + "=" * 80)
print("4. SIDEBAR/NAVIGATION COMPONENT")
print("=" * 80)

# The sidebar fetches subscriptions and renders links
for m in re.finditer(r'subscriptions.*queryFn|queryFn.*subscriptions', js):
    pos = m.start()
    snippet = js[max(0,pos-300):min(len(js),pos+500)]
    print(f"\nSubscriptions query at {pos}:")
    print(snippet)
    print("---")

# ===========================
# 5. Find the /modules or /billing page component
# ===========================
print("\n" + "=" * 80)
print("5. MODULES/BILLING PAGE")
print("=" * 80)

for m in re.finditer(r'module.*launch|launch.*module|openModule|activateModule|enableModule', js, re.IGNORECASE):
    pos = m.start()
    snippet = js[max(0,pos-200):min(len(js),pos+300)]
    print(f"\nModule launch at {pos}:")
    print(snippet)
    print("---")

# ===========================
# 6. Find ALL href/to patterns that are dynamic (not just static routes)
# ===========================
print("\n" + "=" * 80)
print("6. DYNAMIC URL/HREF PATTERNS")
print("=" * 80)

# Template literals with URLs
for m in re.finditer(r'`https?://\$\{', js):
    pos = m.start()
    snippet = js[max(0,pos-100):min(len(js),pos+300)]
    print(f"\nTemplate URL at {pos}:")
    print(snippet)
    print("---")

# String concatenation with URLs
for m in re.finditer(r'"https?://"\s*\+|\'https?://\'\s*\+', js):
    pos = m.start()
    snippet = js[max(0,pos-100):min(len(js),pos+300)]
    print(f"\nConcatenated URL at {pos}:")
    print(snippet)
    print("---")

# ===========================
# 7. Find any lazy-loaded chunk files and check them
# ===========================
print("\n" + "=" * 80)
print("7. LAZY-LOADED CHUNK FILES")
print("=" * 80)

chunk_imports = re.findall(r'import\("\./([\w-]+\.js)"\)', js)
vite_chunks = re.findall(r'__vite__mapDeps\.\w+\((\d+)\)', js)
dynamic_imports = re.findall(r'import\(["\']\./([\w.-]+\.js)["\']', js)

# Also look for __vitePreload pattern
preload_chunks = re.findall(r'__vite__mapDeps\((\[[\d,]+\])\)', js)
print(f"Dynamic imports: {dynamic_imports[:20]}")
print(f"Preload chunk arrays: {preload_chunks[:10]}")

# Find the chunk map
chunk_map_match = re.search(r'__vite__mapDeps=\(.*?\[(.*?)\]', js, re.DOTALL)
if chunk_map_match:
    raw = chunk_map_match.group(1)
    chunk_files = re.findall(r'"([^"]+)"', raw)
    print(f"\nChunk map has {len(chunk_files)} entries:")
    for cf in chunk_files:
        print(f"  {cf}")

# ===========================
# 8. Download and search chunk files for SSO
# ===========================
print("\n" + "=" * 80)
print("8. SEARCHING CHUNK FILES FOR SSO")
print("=" * 80)

if chunk_map_match:
    for cf in chunk_files:
        if not cf.endswith('.js'):
            continue
        try:
            chunk_url = f'{BASE}/assets/{cf}'
            req_c = urllib.request.Request(chunk_url, headers={'User-Agent': UA})
            chunk_js = urllib.request.urlopen(req_c, context=ctx).read().decode('utf-8', errors='replace')

            # Search for SSO-related content
            sso_found = False
            for pat in ['sso', 'SSO', 'module_url', 'moduleUrl', 'launch', 'redirect_url',
                        'token=', 'access_token', 'empcloud.com', 'subdomain',
                        'window.open', 'window.location']:
                if pat in chunk_js:
                    if not sso_found:
                        print(f"\n{'='*40}")
                        print(f"CHUNK: {cf} ({len(chunk_js)} bytes)")
                        print(f"{'='*40}")
                        sso_found = True

                    for match in re.finditer(re.escape(pat), chunk_js):
                        pos = match.start()
                        snippet = chunk_js[max(0,pos-200):min(len(chunk_js),pos+200)]
                        print(f'\n  Found "{pat}" at {pos}:')
                        print(f"  {snippet}")
                        print("  ---")
                        break  # Just first occurrence per pattern per chunk

            if not sso_found and len(chunk_js) > 100:
                # Check if it has any URL-related content
                if 'http' in chunk_js and ('url' in chunk_js.lower() or 'redirect' in chunk_js.lower()):
                    print(f"  {cf}: has http+url patterns but no SSO keywords")
        except Exception as e:
            pass

# ===========================
# 9. API: Check login response and module endpoints
# ===========================
print("\n" + "=" * 80)
print("9. API: LOGIN AND MODULE ENDPOINTS")
print("=" * 80)

login_data = json.dumps({
    "email": "ananya@technova.in",
    "password": "Welcome@123"
}).encode()

req = urllib.request.Request(
    f'{API}/login',
    data=login_data,
    headers={'Content-Type': 'application/json', 'User-Agent': UA},
    method='POST'
)

try:
    resp = urllib.request.urlopen(req, context=ctx)
    login_resp = json.loads(resp.read().decode())
    token = login_resp.get('data', {}).get('token', '')
    print("Login OK")

    # Print full login response
    print("\nFull login response:")
    print(json.dumps(login_resp, indent=2, default=str)[:3000])

    # Check subscriptions endpoint (the sidebar uses it)
    for ep in ['/subscriptions', '/subscribed-modules', '/modules', '/tenant/modules',
               '/dashboard', '/company/settings', '/company/modules']:
        try:
            req2 = urllib.request.Request(f'{API}{ep}', headers={
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json',
                'User-Agent': UA
            })
            resp2 = urllib.request.urlopen(req2, context=ctx)
            data = json.loads(resp2.read().decode())
            resp_str = json.dumps(data, indent=2, default=str)
            print(f"\n{'='*40}")
            print(f"GET {ep} -> OK")
            print(f"{'='*40}")
            if len(resp_str) > 3000:
                print(resp_str[:3000] + "\n...(truncated)")
            else:
                print(resp_str)
        except Exception as e:
            code = getattr(e, 'code', str(e))
            if str(code) not in ['404', '405']:
                print(f"GET {ep} -> {code}")

    # Try SSO generation via POST
    for ep in ['/sso/generate', '/sso/token', '/auth/sso', '/auth/token/module']:
        for payload in [
            {"module": "payroll"},
            {"module_slug": "emp-payroll"},
            {"target_url": "https://testpayroll.empcloud.com"},
        ]:
            try:
                post_data = json.dumps(payload).encode()
                req3 = urllib.request.Request(f'{API}{ep}', data=post_data, headers={
                    'Authorization': f'Bearer {token}',
                    'Content-Type': 'application/json',
                    'User-Agent': UA
                }, method='POST')
                resp3 = urllib.request.urlopen(req3, context=ctx)
                data = json.loads(resp3.read().decode())
                print(f"\nPOST {ep} ({payload}) -> OK:")
                print(json.dumps(data, indent=2, default=str)[:2000])
            except:
                pass

except Exception as e:
    print(f"Login failed: {e}")
    try:
        body = e.read().decode() if hasattr(e, 'read') else ''
        print(f"Body: {body[:500]}")
    except:
        pass

# ===========================
# 10. Search for the "ha" store definition more broadly
# ===========================
print("\n" + "=" * 80)
print("10. AUTH STORE DEFINITION (broader search)")
print("=" * 80)

# Look for setTokens, logout, accessToken in context
for pat in ['setTokens', 'setUser', 'accessToken.*refresh', 'refreshToken', 'login.*token',
            'oauth/token', 'client_id.*empcloud']:
    for m in re.finditer(pat, js):
        pos = m.start()
        snippet = js[max(0,pos-300):min(len(js),pos+500)]
        print(f'\n>>> "{pat}" at {pos}:')
        print(snippet)
        print("---")
        break  # first match only

print("\n" + "=" * 80)
print("DONE")
print("=" * 80)
