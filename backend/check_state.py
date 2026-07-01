"""Check current state of schools and scans."""
import json
import urllib.request
import http.cookiejar

BASE = "http://127.0.0.1:8000/api/v1"

jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))

# Login
login = json.dumps({"email": "admin@scap.paris", "password": "admin2026"}).encode()
req = urllib.request.Request(f"{BASE}/auth/login", data=login, headers={"Content-Type": "application/json"})
opener.open(req)

# Schools
resp = opener.open(urllib.request.Request(f"{BASE}/schools"))
schools = json.loads(resp.read().decode())
print("=== ÉCOLES ===")
for s in schools:
    print(f"  id={s['id']} {s['name']:20s} strategy={s['scraper_strategy']:8s} last_scan={s['last_scanned_at']}")

# Scan runs
print("\n=== SCAN RUNS ===")
resp = opener.open(urllib.request.Request(f"{BASE}/scan-runs"))
runs = json.loads(resp.read().decode())
for r in runs:
    print(f"  id={r.get('id')} school={r.get('school_registry_id')} status={r.get('status')} found={r.get('courses_found')} started={r.get('started_at')} finished={r.get('finished_at')}")
