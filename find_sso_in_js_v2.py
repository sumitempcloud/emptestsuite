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

# ============================
# PART 1: Deep JS analysis
# ============================
print("=" * 80)
print("PART 1: Deep search in JS bundle")
print("=" * 80)

req_html = urllib.request.Request(BASE + '/', headers={'User-Agent': UA})
html = urllib.request.urlopen(req_html, context=ctx).read().decode('utf-8', errors='replace')
js_files = re.findall(r'src="(/assets/[^"]+\.js)"', html)

for js_file in js_files:
    req_js = urllib.request.Request(BASE + js_file, headers={'User-Agent': UA})
    js = urllib.request.urlopen(req_js, context=ctx).read().decode('utf-8', errors='replace')
    print(f"Bundle: {js_file} ({len(js)//1024}KB)")

    # Search for module/app navigation patterns more broadly
    # Look for any URL that contains subdomain patterns
    patterns_extended = [
        # Module-specific subdomains
        r'test[\w-]*\.empcloud\.com',
        r'[\w]+\.empcloud\.com',
        # Token in URL
        r'token=["\']',
        r'\?token=',
        r'[&?]token',
        # SSO explicit
        r'sso',
        r'SSO',
        # Module switching
        r'switchModule',
        r'launchModule',
        r'moduleUrl',
        r'module_url',
        r'moduleLink',
        r'moduleHref',
        r'openApp',
        r'launchApp',
        # Navigation to external
        r'navigate.*external',
        r'external.*url',
        r'externalUrl',
        r'externalLink',
        r'openExternal',
        # Subscription / module config
        r'subscri',
        r'module.*config',
        r'module.*setting',
        # Zustand store patterns
        r'create.*store',
        r'useStore',
        r'getState',
    ]

    for pat in patterns_extended:
        for m in re.finditer(pat, js, re.IGNORECASE):
            pos = m.start()
            start = max(0, pos - 200)
            end = min(len(js), pos + 200)
            snippet = js[start:end]
            # Skip very generic matches (like React internals)
            if 'unstable_' in snippet or 'sortIndex' in snippet:
                continue
            # Only print unique/relevant ones
            if any(k in snippet.lower() for k in ['empcloud', 'module', 'sso', 'launch', 'redirect', 'navigate', 'token', 'subscri', 'app_url', 'base_url']):
                print(f'\n>>> Pattern "{pat}" at {pos}:')
                print(snippet)
                print('---')

    # Also search for string literals containing URLs
    print("\n" + "-" * 60)
    print("URL STRING LITERALS:")
    print("-" * 60)
    for m in re.finditer(r'["\'](https?://[^"\']+)["\']', js):
        url = m.group(1)
        if 'localhost' in url:
            continue
        print(f"  URL: {url}")

    # Search for route definitions that might map to modules
    print("\n" + "-" * 60)
    print("ROUTE/PATH DEFINITIONS (sampling):")
    print("-" * 60)
    for m in re.finditer(r'path:\s*["\']([^"\']+)["\']', js):
        path = m.group(1)
        print(f"  path: {path}")

    # Search for store definitions related to auth/modules
    print("\n" + "-" * 60)
    print("AUTH/MODULE STORE PATTERNS:")
    print("-" * 60)
    for keyword in ['token', 'auth', 'module', 'sso', 'app', 'navigation']:
        for m in re.finditer(rf'{keyword}\w*:\s*(?:function|=>|\()', js, re.IGNORECASE):
            pos = m.start()
            start = max(0, pos - 100)
            end = min(len(js), pos + 300)
            snippet = js[start:end]
            if any(k in snippet.lower() for k in ['empcloud', 'module', 'sso', 'launch', 'redirect', 'token', 'url']):
                print(f'\n>>> Store/function "{keyword}" at {pos}:')
                print(snippet)
                print('---')

# ============================
# PART 2: API - Login and check modules/SSO
# ============================
print("\n" + "=" * 80)
print("PART 2: API calls for SSO/module info")
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
    print(f"Login successful. Token: {token[:30]}...")

    # Print full login response structure
    print("\nFull login response:")
    print(json.dumps(login_resp, indent=2, default=str)[:5000])

    # Try many module/SSO endpoints
    endpoints = [
        '/sso/generate', '/sso/token', '/sso/config', '/sso/url',
        '/modules', '/modules/list', '/modules/urls', '/modules/config',
        '/module/list', '/module/urls',
        '/app/modules', '/app/config',
        '/dashboard/modules', '/dashboard/config', '/dashboard/apps',
        '/user/modules', '/user/apps',
        '/settings/modules', '/settings/apps',
        '/tenant/modules', '/tenant/config', '/tenant/apps',
        '/subscription/modules', '/subscription/list', '/subscription/apps',
        '/subscribed-modules', '/subscribed-apps',
        '/marketplace/modules', '/marketplace/subscribed',
        '/navigation', '/navigation/modules', '/nav/modules',
        '/sidebar', '/menu',
        '/company/modules', '/company/apps',
    ]

    for ep in endpoints:
        full_ep = f'{API}{ep}'
        try:
            req2 = urllib.request.Request(full_ep, headers={
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json',
                'User-Agent': UA
            })
            resp2 = urllib.request.urlopen(req2, context=ctx)
            data = json.loads(resp2.read().decode())
            resp_str = json.dumps(data, indent=2, default=str)
            print(f"\n{'='*60}")
            print(f"SUCCESS: {ep}")
            print('='*60)
            if len(resp_str) > 3000:
                print(resp_str[:3000] + "\n... (truncated)")
            else:
                print(resp_str)
        except Exception as e:
            code = getattr(e, 'code', '')
            if code and code != 404 and code != 405:
                print(f"{ep} -> HTTP {code}")

    # Also try POST for SSO generation
    for ep in ['/sso/generate', '/sso/token', '/sso/create']:
        try:
            post_data = json.dumps({"module": "payroll"}).encode()
            req3 = urllib.request.Request(f'{API}{ep}', data=post_data, headers={
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json',
                'User-Agent': UA
            }, method='POST')
            resp3 = urllib.request.urlopen(req3, context=ctx)
            data = json.loads(resp3.read().decode())
            print(f"\nPOST {ep} -> SUCCESS:")
            print(json.dumps(data, indent=2, default=str)[:2000])
        except Exception as e:
            code = getattr(e, 'code', '')
            if code and code != 404:
                try:
                    body = e.read().decode() if hasattr(e, 'read') else ''
                    print(f"POST {ep} -> HTTP {code}: {body[:500]}")
                except:
                    print(f"POST {ep} -> HTTP {code}")

except Exception as e:
    print(f"Login failed: {e}")
    try:
        body = e.read().decode() if hasattr(e, 'read') else ''
        print(f"Response body: {body[:1000]}")
    except:
        pass

print("\n" + "=" * 80)
print("DONE")
print("=" * 80)
