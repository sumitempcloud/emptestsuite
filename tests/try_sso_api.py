"""
EmpCloud SSO Token Generation via OAuth2 PKCE Flow

Discovered SSO Flow:
1. Login to dashboard API -> get access_token + refresh_token
2. Use access_token to call /oauth/authorize with PKCE + target module client_id
3. Get auth code from redirect
4. Exchange auth code for module-scoped access_token via /oauth/token

OIDC Discovery: https://test-empcloud-api.empcloud.com/.well-known/openid-configuration
"""
import sys, json, urllib.request, urllib.parse, ssl, base64, hashlib, os

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE = "https://test-empcloud-api.empcloud.com"
ctx = ssl._create_unverified_context()

COMMON_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Origin': 'https://test-empcloud.empcloud.com',
    'Referer': 'https://test-empcloud.empcloud.com/',
}

def http_request(method, url, data=None, extra_headers=None, follow_redirects=True):
    headers = dict(COMMON_HEADERS)
    if extra_headers:
        headers.update(extra_headers)
    raw_data = None
    if data is not None and isinstance(data, dict):
        raw_data = json.dumps(data).encode('utf-8')
        headers['Content-Type'] = 'application/json'
    elif data is not None and isinstance(data, str):
        raw_data = data.encode('utf-8')
        headers['Content-Type'] = 'application/x-www-form-urlencoded'
    r = urllib.request.Request(url, data=raw_data, headers=headers, method=method)

    handlers = [urllib.request.HTTPSHandler(context=ctx)]
    if not follow_redirects:
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, hdrs, newurl):
                return None
        handlers.insert(0, NoRedirect)
    opener = urllib.request.build_opener(*handlers)
    try:
        resp = opener.open(r, timeout=30)
        body = resp.read().decode('utf-8', errors='replace')
        loc = resp.headers.get('Location', '')
        try:
            return resp.status, json.loads(body), loc
        except:
            return resp.status, body, loc
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='replace')
        loc = e.headers.get('Location', '') if hasattr(e, 'headers') else ''
        try:
            return e.code, json.loads(body), loc
        except:
            return e.code, body, loc
    except Exception as e:
        return 0, str(e), ''

def decode_jwt(token):
    parts = token.split('.')
    if len(parts) >= 2:
        payload = parts[1]
        payload += '=' * (4 - len(payload) % 4)
        return json.loads(base64.urlsafe_b64decode(payload))
    return {}


def main():
    # =====================================================
    # STEP 1: Login to dashboard
    # =====================================================
    print("=" * 80)
    print("STEP 1: Login to EmpCloud Dashboard API")
    print("=" * 80)
    status, resp, _ = http_request('POST', f"{BASE}/api/v1/auth/login", {
        'email': 'ananya@technova.in', 'password': 'Welcome@123'
    })
    if status != 200 or not resp.get('success'):
        print(f"  LOGIN FAILED! Status: {status}")
        print(f"  Response: {json.dumps(resp, indent=2)[:500]}")
        return
    tokens = resp['data']['tokens']
    dashboard_token = tokens['access_token']
    refresh_token = tokens['refresh_token']
    print(f"  Login successful!")
    print(f"  Dashboard access_token: {dashboard_token[:80]}...")
    print(f"  Refresh token: {refresh_token}")
    print(f"  JWT claims: {json.dumps(decode_jwt(dashboard_token), indent=2)}")

    auth_h = {'Authorization': f'Bearer {dashboard_token}'}

    # =====================================================
    # STEP 2: OIDC Discovery
    # =====================================================
    print("\n" + "=" * 80)
    print("STEP 2: OIDC Discovery")
    print("=" * 80)
    status, oidc, _ = http_request('GET', f"{BASE}/.well-known/openid-configuration")
    print(f"  Status: {status}")
    print(f"  OIDC Config: {json.dumps(oidc, indent=2)}")

    # =====================================================
    # STEP 3: Get JWKS
    # =====================================================
    print("\n" + "=" * 80)
    print("STEP 3: JWKS (signing keys)")
    print("=" * 80)
    status, jwks, _ = http_request('GET', f"{BASE}/oauth/jwks")
    print(f"  Status: {status}")
    print(f"  JWKS: {json.dumps(jwks, indent=2)}")

    # =====================================================
    # STEP 4: Userinfo
    # =====================================================
    print("\n" + "=" * 80)
    print("STEP 4: OAuth Userinfo")
    print("=" * 80)
    status, userinfo, _ = http_request('GET', f"{BASE}/oauth/userinfo", extra_headers=auth_h)
    print(f"  Status: {status}")
    print(f"  Userinfo: {json.dumps(userinfo, indent=2)}")

    # =====================================================
    # STEP 5: Get module list
    # =====================================================
    print("\n" + "=" * 80)
    print("STEP 5: Available modules")
    print("=" * 80)
    status, modules_resp, _ = http_request('GET', f"{BASE}/api/v1/modules", extra_headers=auth_h)
    if status == 200 and isinstance(modules_resp, dict):
        modules = modules_resp.get('data', [])
        for m in modules:
            print(f"  Module ID={m['id']}: {m['name']} (slug={m['slug']}, base_url={m.get('base_url', 'N/A')})")
    else:
        print(f"  Status: {status}")

    # =====================================================
    # STEP 6: OAuth Authorize + PKCE for each module
    # =====================================================
    print("\n" + "=" * 80)
    print("STEP 6: Generate SSO tokens via OAuth2 PKCE flow for ALL modules")
    print("=" * 80)

    # Module client_ids and their possible redirect URIs
    module_configs = {}
    if status == 200:
        for m in modules:
            slug = m['slug']
            base_url = m.get('base_url', '')
            if base_url:
                module_configs[slug] = [
                    f"{base_url}/auth/callback",
                    f"{base_url}/callback",
                    f"{base_url}/sso/callback",
                ]

    # Add dashboard itself
    module_configs['empcloud-dashboard'] = [
        'https://test-empcloud.empcloud.com/auth/callback',
        'https://test-empcloud.empcloud.com/callback',
    ]

    sso_results = {}

    for client_id, redirect_uris in module_configs.items():
        print(f"\n--- Module: {client_id} ---")

        # Generate fresh PKCE for each module
        code_verifier = base64.urlsafe_b64encode(os.urandom(32)).rstrip(b'=').decode()
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode()).digest()
        ).rstrip(b'=').decode()

        auth_code = None
        used_redirect = None

        for redirect_uri in redirect_uris:
            params = urllib.parse.urlencode({
                'client_id': client_id,
                'redirect_uri': redirect_uri,
                'response_type': 'code',
                'scope': 'openid profile email',
                'code_challenge': code_challenge,
                'code_challenge_method': 'S256',
                'state': 'sso_test',
            })

            status, resp, location = http_request(
                'GET', f"{BASE}/oauth/authorize?{params}",
                extra_headers=auth_h, follow_redirects=False
            )

            print(f"  Authorize redirect_uri={redirect_uri}")
            print(f"    Status: {status}")
            if location:
                print(f"    Location: {location[:200]}")

            if status == 302 and location:
                parsed = urllib.parse.urlparse(location)
                qs = urllib.parse.parse_qs(parsed.query)
                auth_code = qs.get('code', [None])[0]
                used_redirect = redirect_uri
                if auth_code:
                    print(f"    AUTH CODE: {auth_code}")
                    break
            else:
                resp_str = json.dumps(resp, indent=2) if isinstance(resp, dict) else str(resp)
                print(f"    Response: {resp_str[:300]}")

        if not auth_code:
            print(f"  FAILED: No valid redirect_uri found for {client_id}")
            sso_results[client_id] = {'status': 'FAILED', 'error': 'No valid redirect_uri'}
            continue

        # Exchange auth code for tokens
        print(f"\n  Exchanging code for tokens...")
        form_data = urllib.parse.urlencode({
            'grant_type': 'authorization_code',
            'code': auth_code,
            'redirect_uri': used_redirect,
            'client_id': client_id,
            'code_verifier': code_verifier,
        })

        status, token_resp, _ = http_request('POST', f"{BASE}/oauth/token", form_data)
        print(f"    Token exchange status: {status}")

        if status == 200 and isinstance(token_resp, dict):
            module_token = token_resp.get('access_token', '')
            module_refresh = token_resp.get('refresh_token', '')
            module_id_token = token_resp.get('id_token', '')

            claims = decode_jwt(module_token)
            id_claims = decode_jwt(module_id_token) if module_id_token else {}

            print(f"    ACCESS TOKEN: {module_token[:100]}...")
            print(f"    REFRESH TOKEN: {module_refresh}")
            print(f"    ID TOKEN: {module_id_token[:100]}..." if module_id_token else "    ID TOKEN: N/A")
            print(f"    Token expires_in: {token_resp.get('expires_in')}s")
            print(f"    Token scope: {token_resp.get('scope')}")
            print(f"    JWT claims: client_id={claims.get('client_id')}, sub={claims.get('sub')}, role={claims.get('role')}")
            print(f"    ID Token audience: {id_claims.get('aud')}")

            sso_results[client_id] = {
                'status': 'SUCCESS',
                'access_token': module_token,
                'refresh_token': module_refresh,
                'id_token': module_id_token,
                'redirect_uri': used_redirect,
                'expires_in': token_resp.get('expires_in'),
                'claims': claims,
            }

            # Construct SSO callback URL (what the frontend would redirect to)
            sso_url = f"{used_redirect}?code={auth_code}&state=sso_test"
            print(f"    SSO Callback URL: {sso_url}")
        else:
            resp_str = json.dumps(token_resp, indent=2) if isinstance(token_resp, dict) else str(token_resp)
            print(f"    TOKEN EXCHANGE FAILED: {resp_str[:400]}")
            sso_results[client_id] = {'status': 'TOKEN_EXCHANGE_FAILED', 'error': resp_str[:200]}

    # =====================================================
    # STEP 7: Test module API with SSO token
    # =====================================================
    print("\n" + "=" * 80)
    print("STEP 7: Test module APIs with SSO tokens")
    print("=" * 80)

    payroll_api = 'https://testpayroll-api.empcloud.com'
    if 'emp-payroll' in sso_results and sso_results['emp-payroll']['status'] == 'SUCCESS':
        payroll_token = sso_results['emp-payroll']['access_token']
        payroll_auth = {'Authorization': f'Bearer {payroll_token}'}
        endpoints = ['/api/v1/dashboard', '/api/v1/me', '/api/v1/auth/me',
                     '/api/v1/employees', '/api/v1/salary-structures', '/health']
        for ep in endpoints:
            status, resp, _ = http_request('GET', f'{payroll_api}{ep}', extra_headers=payroll_auth)
            resp_str = json.dumps(resp, indent=2) if isinstance(resp, dict) else str(resp)
            print(f"  [payroll] {ep} -> Status: {status}")
            print(f"    Response: {resp_str[:400]}")

    # =====================================================
    # STEP 8: Refresh token exchange (get new token for dashboard)
    # =====================================================
    print("\n" + "=" * 80)
    print("STEP 8: Refresh token exchange")
    print("=" * 80)

    form_data = urllib.parse.urlencode({
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token,
        'client_id': 'empcloud-dashboard',
    })
    status, resp, _ = http_request('POST', f"{BASE}/oauth/token", form_data)
    print(f"  Dashboard refresh status: {status}")
    if status == 200 and isinstance(resp, dict):
        new_token = resp.get('access_token', '')
        claims = decode_jwt(new_token)
        print(f"  New access_token: {new_token[:80]}...")
        print(f"  Claims: client_id={claims.get('client_id')}, sub={claims.get('sub')}")

    # Also try payroll refresh
    if 'emp-payroll' in sso_results and sso_results['emp-payroll']['status'] == 'SUCCESS':
        payroll_refresh = sso_results['emp-payroll']['refresh_token']
        form_data = urllib.parse.urlencode({
            'grant_type': 'refresh_token',
            'refresh_token': payroll_refresh,
            'client_id': 'emp-payroll',
        })
        status, resp, _ = http_request('POST', f"{BASE}/oauth/token", form_data)
        print(f"\n  Payroll refresh status: {status}")
        if status == 200 and isinstance(resp, dict):
            new_token = resp.get('access_token', '')
            claims = decode_jwt(new_token)
            print(f"  New payroll access_token: {new_token[:80]}...")
            print(f"  Claims: client_id={claims.get('client_id')}, sub={claims.get('sub')}")

    # =====================================================
    # SUMMARY
    # =====================================================
    print("\n" + "=" * 80)
    print("SUMMARY: SSO Token Generation Results")
    print("=" * 80)
    for client_id, result in sso_results.items():
        status = result['status']
        if status == 'SUCCESS':
            claims = result.get('claims', {})
            print(f"  {client_id}: SUCCESS")
            print(f"    redirect_uri: {result['redirect_uri']}")
            print(f"    client_id in JWT: {claims.get('client_id')}")
            print(f"    expires_in: {result['expires_in']}s")
            print(f"    access_token: {result['access_token'][:60]}...")
        else:
            print(f"  {client_id}: {status} - {result.get('error', 'unknown')}")

    # Save results
    with open('sso_token_results.json', 'w') as f:
        # Don't save full tokens to file for security
        summary = {}
        for k, v in sso_results.items():
            summary[k] = {
                'status': v['status'],
                'redirect_uri': v.get('redirect_uri'),
                'expires_in': v.get('expires_in'),
                'client_id_in_jwt': v.get('claims', {}).get('client_id'),
            }
        json.dump(summary, f, indent=2)
    print("\n  Results saved to sso_token_results.json")

    print("\n" + "=" * 80)
    print("DONE")
    print("=" * 80)

if __name__ == '__main__':
    main()
