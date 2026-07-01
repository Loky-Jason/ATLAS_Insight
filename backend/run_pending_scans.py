"""Trigger Demos and SCAP scans in the background (fire-and-forget)."""
import json
import urllib.request
import http.cookiejar
import sys

BASE = "http://127.0.0.1:8000/api/v1"

jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))

login = json.dumps({"email": "admin@scap.paris", "password": "admin2026"}).encode()
req = urllib.request.Request(f"{BASE}/auth/login", data=login, headers={"Content-Type": "application/json"})
opener.open(req)

for school_id, label in [(2, "Demos"), (3, "SCAP")]:
    print(f"Déclenchement scan {label} (id={school_id})...", flush=True)
    req = urllib.request.Request(f"{BASE}/schools/{school_id}/scan", method="POST")
    try:
        resp = opener.open(req, timeout=600)
        print(f"  {label}: {resp.read().decode()}", flush=True)
    except Exception as exc:
        print(f"  {label} erreur: {exc}", flush=True)
    print("---", flush=True)
