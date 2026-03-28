import sys, json, urllib.request, urllib.parse, ssl, base64

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE = "https://test-empcloud-api.empcloud.com/api/v1"
ctx = ssl._create_unverified_context()

HEADERS_BASE = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Origin': 'https://test-empcloud.empcloud.com',
    'Referer': 'https://test-empcloud.empcloud.com/',
}

def req(method, url, data=None, extra_headers=None):
    headers = dict(HEADERS_BASE)
    if extra_headers:
        headers.update(extra_headers)
    if data is not None and isinstance(data, dict):
        data = json.dumps(data).encode('utf-8')
        headers['Content-Type'] = 'application/json'
    else:
        data = None
    r = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        resp = urllib.request.urlopen(r, context=ctx, timeout=30)
        body = resp.read().decode('utf-8', errors='replace')
        try:
            return resp.status, json.loads(body)
        except:
            return resp.status, body
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='replace')
        try:
            return e.code, json.loads(body)
        except:
            return e.code, body
    except Exception as e:
        return 0, str(e)

def login():
    status, resp = req('POST', f"{BASE}/auth/login", {
        'email': 'ananya@technova.in', 'password': 'Welcome@123'
    })
    token = resp['data']['tokens']['access_token']
    print(f"Logged in. Token: {token[:60]}...")
    return token

def decode_jwt(token):
    """Decode JWT payload without verification"""
    parts = token.split('.')
    if len(parts) >= 2:
        payload = parts[1]
        padding = 4 - len(payload) % 4
        payload += '=' * padding
        return json.loads(base64.urlsafe_b64decode(payload))
    return {}

def p(method, path, body, token, label=""):
    url = path if path.startswith('http') else f"https://test-empcloud-api.empcloud.com{path}"
    headers = {'Authorization': f'Bearer {token}'} if token else {}
    status, resp = req(method, url, body, headers)
    resp_str = json.dumps(resp, indent=2) if isinstance(resp, dict) else str(resp)
    if len(resp_str) > 800:
        resp_str = resp_str[:800] + "...[truncated]"
    print(f"\n  [{method}] {path[:120]}")
    if label: print(f"  Label: {label}")
    if body: print(f"  Body: {json.dumps(body)[:200]}")
    print(f"  Status: {status}")
    print(f"  Response: {resp_str}")
    return status, resp

def main():
    token = login()
    jwt_payload = decode_jwt(token)
    print(f"\nJWT payload: {json.dumps(jwt_payload, indent=2)}")

    # =====================================================
    # KEY FINDING: /sso/callback returns SPA HTML (client-side routing)
    # The SSO is handled client-side. The JWT from login IS the SSO token.
    # Let's test the module APIs directly with the dashboard JWT.
    # =====================================================

    print("\n" + "=" * 80)
    print("PART 1: Test module APIs directly with dashboard JWT")
    print("=" * 80)

    # Module API bases from the modules list
    module_apis = {
        'payroll': 'https://testpayroll-api.empcloud.com',
        'recruit': 'https://testrecruit-api.empcloud.com',
        'performance': 'https://testperformance-api.empcloud.com',
        'leave': 'https://testleave-api.empcloud.com',
        'attendance': 'https://testattendance-api.empcloud.com',
        'expense': 'https://testexpense-api.empcloud.com',
        'helpdesk': 'https://testhelpdesk-api.empcloud.com',
    }

    for name, base_url in module_apis.items():
        print(f"\n--- Module: {name} ({base_url}) ---")
        # Try common authenticated endpoints
        for path in ['/api/v1/me', '/api/v1/dashboard', '/api/v1/auth/verify', '/api/v1/auth/me']:
            p('GET', f'{base_url}{path}', None, token, f"{name} - {path}")

    # =====================================================
    # PART 2: Test payroll SSO callback API endpoint
    # We got 500 on /api/auth/sso - let's try variations
    # =====================================================
    print("\n" + "=" * 80)
    print("PART 2: Payroll module SSO API endpoints")
    print("=" * 80)

    payroll_api = 'https://testpayroll-api.empcloud.com'
    payroll_fe = 'https://testpayroll.empcloud.com'

    sso_paths = [
        ('POST', f'{payroll_api}/api/v1/auth/sso', {'token': token}),
        ('POST', f'{payroll_api}/api/v1/auth/sso', {'sso_token': token}),
        ('POST', f'{payroll_api}/api/v1/auth/sso', {'access_token': token}),
        ('POST', f'{payroll_api}/api/v1/auth/sso/callback', {'token': token}),
        ('POST', f'{payroll_api}/api/v1/auth/sso/callback', {'sso_token': token}),
        ('POST', f'{payroll_api}/api/v1/auth/sso/verify', {'token': token}),
        ('POST', f'{payroll_api}/api/v1/auth/sso/login', {'token': token}),
        ('POST', f'{payroll_api}/api/v1/auth/login', {'sso_token': token}),
        ('POST', f'{payroll_api}/api/v1/auth/token', {'token': token}),
        ('POST', f'{payroll_api}/api/v1/auth/exchange', {'token': token}),
        ('GET', f'{payroll_api}/api/v1/auth/sso/callback?sso_token={token[:50]}', None),
        ('GET', f'{payroll_api}/api/v1/auth/sso/callback?token={token[:50]}', None),
        # Try the full token
        ('POST', f'{payroll_api}/api/auth/sso', {'token': token}),
        ('POST', f'{payroll_api}/api/auth/sso', {'sso_token': token}),
        ('POST', f'{payroll_api}/auth/sso', {'token': token}),
        ('POST', f'{payroll_api}/sso/callback', {'token': token}),
        ('POST', f'{payroll_api}/sso/callback', {'sso_token': token}),
    ]
    for m, url, b in sso_paths:
        p(m, url, b, None, "Payroll SSO")

    # Also try with auth header
    for path in ['/api/v1/auth/sso', '/api/auth/sso', '/api/v1/auth/sso/callback']:
        p('POST', f'{payroll_api}{path}', {}, token, "Payroll SSO with Bearer token")
        p('GET', f'{payroll_api}{path}', None, token, "Payroll SSO with Bearer token")

    # =====================================================
    # PART 3: Try the OIDC / well-known endpoints
    # =====================================================
    print("\n" + "=" * 80)
    print("PART 3: OIDC / well-known discovery")
    print("=" * 80)

    oidc_paths = [
        f'{BASE}/../.well-known/openid-configuration',
        'https://test-empcloud-api.empcloud.com/.well-known/openid-configuration',
        'https://test-empcloud-api.empcloud.com/.well-known/oauth-authorization-server',
        f'{BASE}/auth/.well-known/openid-configuration',
        f'{BASE}/oidc/.well-known/openid-configuration',
    ]
    for url in oidc_paths:
        p('GET', url, None, token, "OIDC discovery")

    # =====================================================
    # PART 4: Try /auth/sso with module_id from the modules list
    # =====================================================
    print("\n" + "=" * 80)
    print("PART 4: Dashboard API - SSO with module_id (real IDs)")
    print("=" * 80)

    # Module IDs from the modules list response:
    # 11=biometrics, 2=monitor, 9=exit, 4=field, 5=helpdesk, 6=lms,
    # 10=payroll, 7=performance, 8=recruitment, 3=selfservice, 1=attendance
    real_ids = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
    for mid in real_ids:
        p('POST', f'/api/v1/modules/{mid}/sso/generate', {}, token, f"module_id={mid}")
        p('POST', f'/api/v1/modules/{mid}/token', {}, token, f"module_id={mid}")
        p('GET', f'/api/v1/modules/{mid}/redirect', None, token, f"module_id={mid}")

    # =====================================================
    # PART 5: Try subscription-based launch with real subscription IDs
    # =====================================================
    print("\n" + "=" * 80)
    print("PART 5: Subscription-based launch (real IDs from response)")
    print("=" * 80)

    # Real subscription IDs from subscriptions response: 29, 23, 22, etc.
    sub_ids = [22, 23, 24, 25, 26, 27, 28, 29]
    for sid in sub_ids:
        p('POST', f'/api/v1/subscriptions/{sid}/launch', {}, token, f"sub_id={sid}")
        p('GET', f'/api/v1/subscriptions/{sid}/launch', None, token, f"sub_id={sid}")
        p('POST', f'/api/v1/subscriptions/{sid}/sso', {}, token, f"sub_id={sid}")
        p('GET', f'/api/v1/subscriptions/{sid}/sso', None, token, f"sub_id={sid}")
        p('POST', f'/api/v1/subscriptions/{sid}/sso/generate', {}, token, f"sub_id={sid}")

    # =====================================================
    # PART 6: Try alternate paths at dashboard API
    # =====================================================
    print("\n" + "=" * 80)
    print("PART 6: Other possible SSO paths on dashboard API")
    print("=" * 80)

    alt_paths = [
        ('POST', '/api/v1/launch', {'module_id': 10}),
        ('POST', '/api/v1/launch', {'module_slug': 'emp-payroll'}),
        ('POST', '/api/v1/auth/launch', {'module_id': 10}),
        ('POST', '/api/v1/auth/launch', {'module_slug': 'emp-payroll'}),
        ('POST', '/api/v1/auth/redirect', {'module_id': 10}),
        ('GET', '/api/v1/auth/redirect?module_id=10', None),
        ('POST', '/api/v1/sso', {'module_id': 10}),
        ('POST', '/api/v1/sso', {'module_slug': 'emp-payroll'}),
        ('POST', '/api/v1/connect', {'module_id': 10}),
        ('POST', '/api/v1/modules/launch', {'module_id': 10}),
        ('POST', '/api/v1/modules/sso/generate', {'module_id': 10}),
        ('GET', '/api/v1/modules/10/access', None),
        ('GET', '/api/v1/modules/10/url', None),
    ]
    for m, path, b in alt_paths:
        p(m, path, b, token)

    print("\n" + "=" * 80)
    print("DONE")
    print("=" * 80)

if __name__ == '__main__':
    main()
