import sys
import re
import urllib.request
import ssl

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Skip SSL verification for test environment
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

BASE = 'https://test-empcloud.empcloud.com'

print("=" * 80)
print("STEP 1: Fetch HTML and find JS bundles")
print("=" * 80)

req_html = urllib.request.Request(BASE + '/', headers={
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
})
html = urllib.request.urlopen(req_html, context=ctx).read().decode('utf-8', errors='replace')

# Find all JS files
js_files = re.findall(r'src="(/assets/[^"]+\.js)"', html)
print(f"Found {len(js_files)} JS files: {js_files}")

# Also look for CSS/other asset patterns
all_assets = re.findall(r'(?:src|href)="(/assets/[^"]+)"', html)
print(f"All assets referenced: {all_assets}")

# SSO patterns to search for
sso_patterns = [
    'sso_token', 'sso/callback', 'sso_url', 'launch_url', 'module_url',
    'openModule', 'launchModule', 'redirectToModule', '/sso/', 'generateSso',
    'ssoToken', 'ssoUrl', 'sso-token', 'sso-url', 'sso_redirect',
    'testpayroll', 'test-recruit', 'test-performance', 'test-rewards',
    'test-exit', 'testlms', 'test-lms', 'test-helpdesk',
    'window.open', 'window.location.href', 'redirect_url',
    'module_launch', 'moduleLaunch', 'launchApp', 'launch_app',
    'cross_domain', 'crossDomain', 'token_transfer', 'tokenTransfer',
    'empcloud.com', '.empcloud.', 'subdomain',
    'payroll.', 'recruit.', 'performance.', 'rewards.', 'exit.',
    'lms.', 'helpdesk.', 'attendance.',
    'navigate_to_module', 'navigateToModule', 'moduleRedirect',
    'auth_token', 'authToken', 'access_token', 'accessToken',
    'jwt', 'JWT', 'bearer', 'Bearer',
    'open(', 'location.assign', 'location.replace',
]

# Additional patterns for URL construction
url_patterns = [
    'https://', 'http://',
    'protocol', 'hostname', 'origin',
    'encodeURIComponent', 'URLSearchParams',
    'redirect', 'callback',
    'module_id', 'moduleId', 'module_code', 'moduleCode',
]

all_patterns = sso_patterns + url_patterns

for js_file in js_files:
    print("\n" + "=" * 80)
    print(f"ANALYZING: {js_file}")
    print("=" * 80)

    url = BASE + js_file
    print(f"Downloading {url}...")
    req_js = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })
    js_content = urllib.request.urlopen(req_js, context=ctx).read().decode('utf-8', errors='replace')
    print(f"File size: {len(js_content)} bytes")

    found_positions = {}

    for pattern in all_patterns:
        idx = 0
        occurrences = []
        while True:
            idx = js_content.find(pattern, idx)
            if idx == -1:
                break
            occurrences.append(idx)
            idx += 1

        if occurrences:
            found_positions[pattern] = occurrences

    # Print findings sorted by position
    if found_positions:
        print(f"\nFound {len(found_positions)} different patterns:")
        for pattern, positions in sorted(found_positions.items(), key=lambda x: x[0]):
            print(f"  '{pattern}': {len(positions)} occurrences")

        # Now print unique code regions (deduplicated by proximity)
        all_regions = []
        for pattern, positions in found_positions.items():
            for pos in positions:
                all_regions.append((pos, pattern))

        all_regions.sort(key=lambda x: x[0])

        # Merge overlapping regions and print
        printed_ranges = []

        # Focus on SSO-specific patterns first
        priority_patterns = [
            'sso_token', 'sso/callback', 'sso_url', 'launch_url', 'module_url',
            'openModule', 'launchModule', 'redirectToModule', '/sso/', 'generateSso',
            'ssoToken', 'ssoUrl', 'sso_redirect', 'moduleLaunch', 'launchApp',
            'module_launch', 'navigate_to_module', 'navigateToModule', 'moduleRedirect',
            'testpayroll', 'test-recruit', 'test-performance', 'test-rewards',
            'test-exit', 'testlms', 'test-lms', 'test-helpdesk',
            'cross_domain', 'crossDomain', 'token_transfer', 'tokenTransfer',
            'empcloud.com', '.empcloud.',
            'payroll.', 'recruit.', 'performance.', 'rewards.', 'exit.',
            'lms.', 'helpdesk.', 'attendance.',
        ]

        print("\n" + "-" * 60)
        print("SSO/MODULE-SPECIFIC PATTERNS (priority):")
        print("-" * 60)

        for pattern in priority_patterns:
            if pattern in found_positions:
                for pos in found_positions[pattern][:5]:  # max 5 per pattern
                    # Check if we already printed a region near this
                    already_printed = False
                    for (ps, pe) in printed_ranges:
                        if ps <= pos <= pe:
                            already_printed = True
                            break

                    if not already_printed:
                        start = max(0, pos - 300)
                        end = min(len(js_content), pos + 300)
                        snippet = js_content[start:end]
                        printed_ranges.append((start, end))
                        print(f'\n>>> FOUND "{pattern}" at position {pos}:')
                        print(snippet)
                        print('---END---')

        # Now print window.open patterns (likely SSO redirect)
        print("\n" + "-" * 60)
        print("WINDOW.OPEN / LOCATION PATTERNS:")
        print("-" * 60)

        for pattern in ['window.open', 'window.location.href', 'location.assign', 'location.replace']:
            if pattern in found_positions:
                for pos in found_positions[pattern][:10]:
                    already_printed = False
                    for (ps, pe) in printed_ranges:
                        if ps <= pos <= pe:
                            already_printed = True
                            break
                    if not already_printed:
                        start = max(0, pos - 300)
                        end = min(len(js_content), pos + 300)
                        snippet = js_content[start:end]
                        printed_ranges.append((start, end))
                        print(f'\n>>> FOUND "{pattern}" at position {pos}:')
                        print(snippet)
                        print('---END---')

# STEP 2: Also check for chunk/lazy-loaded JS files
print("\n" + "=" * 80)
print("STEP 2: Look for chunk files")
print("=" * 80)

# Check if there are chunk references in the main JS
for js_file in js_files:
    url = BASE + js_file
    req_js2 = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })
    js_content = urllib.request.urlopen(req_js2, context=ctx).read().decode('utf-8', errors='replace')

    # Find chunk file references
    chunks = re.findall(r'["\'](/assets/[^"\']+\.js)["\']', js_content)
    chunk_refs = re.findall(r'["\']([\w-]+)-[a-f0-9]+\.js["\']', js_content)

    if chunks:
        print(f"Direct chunk references in {js_file}: {chunks[:20]}")
    if chunk_refs:
        print(f"Chunk name patterns: {chunk_refs[:20]}")

# STEP 3: Try listing the assets directory
print("\n" + "=" * 80)
print("STEP 3: Search for SSO in API login response")
print("=" * 80)

import json

# Login to get token and check for SSO info
login_data = json.dumps({
    "email": "ananya@technova.in",
    "password": "Welcome@123"
}).encode()

req = urllib.request.Request(
    'https://test-empcloud-api.empcloud.com/api/v1/login',
    data=login_data,
    headers={'Content-Type': 'application/json'},
    method='POST'
)

try:
    resp = urllib.request.urlopen(req, context=ctx)
    login_resp = json.loads(resp.read().decode())
    token = login_resp.get('data', {}).get('token', '')

    # Check for SSO-related keys in login response
    print("Login response keys:", list(login_resp.get('data', {}).keys()))

    # Check for module URLs or SSO config
    for key in login_resp.get('data', {}):
        val = login_resp['data'][key]
        val_str = str(val).lower()
        if any(k in val_str for k in ['sso', 'url', 'module', 'redirect', 'token', 'domain']):
            print(f"  {key}: {val}")

    # Try fetching SSO-specific endpoints
    sso_endpoints = [
        '/api/v1/sso/generate',
        '/api/v1/sso/token',
        '/api/v1/sso/config',
        '/api/v1/modules',
        '/api/v1/modules/urls',
        '/api/v1/module/list',
        '/api/v1/app/modules',
        '/api/v1/dashboard/modules',
        '/api/v1/user/modules',
        '/api/v1/settings/modules',
        '/api/v1/tenant/modules',
        '/api/v1/subscription/modules',
    ]

    for ep in sso_endpoints:
        try:
            req2 = urllib.request.Request(
                f'https://test-empcloud-api.empcloud.com{ep}',
                headers={
                    'Authorization': f'Bearer {token}',
                    'Content-Type': 'application/json'
                }
            )
            resp2 = urllib.request.urlopen(req2, context=ctx)
            data = json.loads(resp2.read().decode())
            print(f"\n{ep} -> SUCCESS")
            # Print abbreviated response
            resp_str = json.dumps(data, indent=2)
            if len(resp_str) > 2000:
                print(resp_str[:2000] + "\n... (truncated)")
            else:
                print(resp_str)
        except Exception as e:
            status = getattr(e, 'code', str(e))
            print(f"{ep} -> {status}")

except Exception as e:
    print(f"Login failed: {e}")

print("\n" + "=" * 80)
print("DONE")
print("=" * 80)
