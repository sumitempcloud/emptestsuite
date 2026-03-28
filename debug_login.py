import urllib.request, json, ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

url = "https://test-empcloud-api.empcloud.com/api/v1/auth/login"
data = json.dumps({"email": "ananya@technova.in", "password": "Welcome@123"}).encode()
headers = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0",
    "Origin": "https://test-empcloud.empcloud.com",
}
req = urllib.request.Request(url, data=data, headers=headers, method="POST")
resp = urllib.request.urlopen(req, context=ctx, timeout=30)
body = json.loads(resp.read().decode())
print(json.dumps(body, indent=2, default=str)[:3000])
