import sys, json, urllib.request, urllib.parse, ssl, base64

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE = "https://test-empcloud-api.empcloud.com"
ctx = ssl._create_unverified_context()

HEADERS_BASE = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Origin': 'https://test-empcloud.empcloud.com',
    'Referer': 'https://test-empcloud.empcloud.com/',
}

def req(method, url, data=None, extra_headers=None, follow_redirects=False):
    headers = dict(HEADERS_BASE)
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
    try:
        if not follow_redirects:
            class NoRedirect(urllib.request.HTTPRedirectHandler):
                def redirect_request(self, req, fp, code, msg, headers, newurl):
                    return None
            opener = urllib.request.build_opener(NoRedirect, urllib.request.HTTPSHandler(context=ctx))
        else:
            opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx))
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

def login():
    status, resp, _ = req('POST', f"{BASE}/api/v1/auth/login", {
        'email': 'ananya@technova.in', 'password': 'Welcome@123'
    })
    tokens = resp['data']['tokens']
    print(f"Logged in. access_token: {tokens['access_token'][:60]}...")
    print(f"  refresh_token: {tokens['refresh_token']}")
    print(f"  id_token: {tokens.get('id_token', 'N/A')[:80]}...")
    return tokens

def p(label, method, url, data=None, extra_headers=None):
    status, resp, loc = req(method, url, data, extra_headers)
    resp_str = json.dumps(resp, indent=2) if isinstance(resp, dict) else str(resp)
    if len(resp_str) > 1200:
        resp_str = resp_str[:1200] + "...[truncated]"
    print(f"\n  [{method}] {url[:150]}")
    print(f"  Label: {label}")
    if data: print(f"  Data: {str(data)[:300]}")
    print(f"  Status: {status}")
    if loc: print(f"  Location: {loc}")
    print(f"  Response: {resp_str}")
    return status, resp, loc

def main():
    tokens = login()
    access_token = tokens['access_token']
    refresh_token = tokens['refresh_token']
    id_token = tokens.get('id_token', '')
    auth_h = {'Authorization': f'Bearer {access_token}'}

    # =====================================================
    # OIDC discovery gave us:
    # authorization_endpoint: /oauth/authorize
    # token_endpoint: /oauth/token
    # userinfo_endpoint: /oauth/userinfo
    # revocation_endpoint: /oauth/revoke
    # introspection_endpoint: /oauth/introspect
    # jwks_uri: /oauth/jwks
    # =====================================================

    print("\n" + "=" * 80)
    print("PART 1: OAuth endpoints from OIDC discovery")
    print("=" * 80)

    # Get JWKS
    p("JWKS", 'GET', f'{BASE}/oauth/jwks')

    # Userinfo
    p("Userinfo with token", 'GET', f'{BASE}/oauth/userinfo', extra_headers=auth_h)

    # Introspect
    p("Introspect token", 'POST', f'{BASE}/oauth/introspect',
      f'token={access_token}', auth_h)

    # =====================================================
    # PART 2: OAuth authorize - this is likely the SSO flow
    # The frontend redirects here to get an auth code for a module
    # =====================================================
    print("\n" + "=" * 80)
    print("PART 2: OAuth /authorize endpoint (SSO flow)")
    print("=" * 80)

    # Module frontend URLs from the modules list:
    module_urls = {
        'emp-payroll': 'https://testpayroll.empcloud.com',
        'emp-selfservice': 'https://test-selfservice.empcloud.com',
        'emp-monitor': 'https://test-empmonitor.empcloud.com',
        'emp-exit': 'https://test-exit.empcloud.com',
        'emp-helpdesk': 'https://test-helpdesk.empcloud.com',
        'emp-lms': 'https://test-lms.empcloud.com',
        'emp-performance': 'https://test-performance.empcloud.com',
        'emp-recruitment': 'https://test-recruitment.empcloud.com',
        'emp-attendance': 'https://test-attendance.empcloud.com',
    }

    # Try authorize with various client_ids and redirect_uris
    for slug, fe_url in module_urls.items():
        for callback_path in ['/sso/callback', '/auth/callback', '/callback']:
            redirect_uri = f'{fe_url}{callback_path}'
            params = urllib.parse.urlencode({
                'client_id': slug,
                'redirect_uri': redirect_uri,
                'response_type': 'code',
                'scope': 'openid profile email',
            })
            # Without auth - should redirect to login
            status, resp, loc = p(f"authorize {slug} (no auth)",
                'GET', f'{BASE}/oauth/authorize?{params}')

            # With auth - should redirect with code
            status, resp, loc = p(f"authorize {slug} (with auth)",
                'GET', f'{BASE}/oauth/authorize?{params}', extra_headers=auth_h)

            if loc and ('code=' in loc or 'token=' in loc or 'sso_token=' in loc):
                print(f"\n  *** SUCCESS! Got redirect with auth code/token ***")
                print(f"  *** Location: {loc} ***")

            # Only try the first callback path if we get useful results
            if status in [200, 302, 301]:
                break

    # =====================================================
    # PART 3: OAuth token endpoint - exchange code for token
    # =====================================================
    print("\n" + "=" * 80)
    print("PART 3: OAuth /token endpoint variations")
    print("=" * 80)

    # Try client_credentials grant for modules
    for slug in ['emp-payroll', 'emp-selfservice', 'emp-attendance']:
        p(f"client_credentials {slug}", 'POST', f'{BASE}/oauth/token',
          f'grant_type=client_credentials&client_id={slug}&scope=openid')

    # Try exchanging access_token for module token
    p("token exchange", 'POST', f'{BASE}/oauth/token',
      f'grant_type=urn:ietf:params:oauth:grant-type:token-exchange&subject_token={access_token}&subject_token_type=urn:ietf:params:oauth:token-type:access_token&audience=emp-payroll')

    # Try refresh_token grant
    p("refresh_token grant", 'POST', f'{BASE}/oauth/token',
      f'grant_type=refresh_token&refresh_token={refresh_token}')

    # =====================================================
    # PART 4: Try authorize with response_type=token (implicit)
    # =====================================================
    print("\n" + "=" * 80)
    print("PART 4: Implicit flow (response_type=token)")
    print("=" * 80)

    for slug, fe_url in list(module_urls.items())[:3]:
        redirect_uri = f'{fe_url}/sso/callback'
        params = urllib.parse.urlencode({
            'client_id': slug,
            'redirect_uri': redirect_uri,
            'response_type': 'token',
            'scope': 'openid profile email',
        })
        p(f"implicit {slug}", 'GET', f'{BASE}/oauth/authorize?{params}',
          extra_headers=auth_h)

    # =====================================================
    # PART 5: Try POST to authorize (consent form submission)
    # =====================================================
    print("\n" + "=" * 80)
    print("PART 5: POST to /oauth/authorize")
    print("=" * 80)

    for slug in ['emp-payroll', 'emp-selfservice']:
        fe_url = module_urls[slug]
        p(f"POST authorize {slug}", 'POST', f'{BASE}/oauth/authorize', {
            'client_id': slug,
            'redirect_uri': f'{fe_url}/sso/callback',
            'response_type': 'code',
            'scope': 'openid profile email',
            'consent': 'allow',
        }, auth_h)

        # form-encoded variant
        p(f"POST authorize {slug} (form)", 'POST', f'{BASE}/oauth/authorize',
          f'client_id={slug}&redirect_uri={urllib.parse.quote(fe_url + "/sso/callback")}&response_type=code&scope=openid+profile+email',
          auth_h)

    # =====================================================
    # PART 6: Try sending JWT directly to payroll API auth/sso
    # The 500 errors suggest the endpoint exists but crashes
    # =====================================================
    print("\n" + "=" * 80)
    print("PART 6: Payroll API auth/sso with various token formats")
    print("=" * 80)

    payroll_api = 'https://testpayroll-api.empcloud.com'

    # Try with id_token instead of access_token
    if id_token:
        p("id_token in body", 'POST', f'{payroll_api}/api/v1/auth/sso',
          {'token': id_token})
        p("id_token in body (sso_token)", 'POST', f'{payroll_api}/api/v1/auth/sso',
          {'sso_token': id_token})
        p("id_token as Bearer", 'GET', f'{payroll_api}/api/v1/auth/sso',
          extra_headers={'Authorization': f'Bearer {id_token}'})

    # Try just Bearer access_token on payroll dashboard
    p("payroll dashboard", 'GET', f'{payroll_api}/api/v1/dashboard',
      extra_headers=auth_h)
    p("payroll employees", 'GET', f'{payroll_api}/api/v1/employees',
      extra_headers=auth_h)
    p("payroll salary", 'GET', f'{payroll_api}/api/v1/salary-structures',
      extra_headers=auth_h)

    # =====================================================
    # PART 7: Check if /oauth/authorize with cookie works
    # (the real SSO flow might use session cookies)
    # =====================================================
    print("\n" + "=" * 80)
    print("PART 7: JWKS and token verification")
    print("=" * 80)

    p("JWKS keys", 'GET', f'{BASE}/oauth/jwks')

    # Try to verify if payroll validates against same JWKS
    p("payroll JWKS", 'GET', f'{payroll_api}/oauth/jwks')
    p("payroll well-known", 'GET', f'{payroll_api}/.well-known/openid-configuration')

    print("\n" + "=" * 80)
    print("DONE - All OAuth/OIDC endpoints tested")
    print("=" * 80)

if __name__ == '__main__':
    main()
