"""Configure les écoles concurrentes et lance les scans."""

import json
import urllib.error
import urllib.request
from http.cookiejar import CookieJar

BASE_URL = "http://127.0.0.1:8000/api/v1"
SCAN_TIMEOUT = 600  # secondes


def make_opener():
    jar = CookieJar()
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))


def api_request(opener, method, path, data=None, timeout=30):
    url = f"{BASE_URL}{path}"
    headers = {"Content-Type": "application/json"} if data else {}
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with opener.open(req, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())


def main():
    opener = make_opener()

    # 1. Login
    status, body = api_request(
        opener,
        "POST",
        "/auth/login",
        {"email": "admin@scap.paris", "password": "admin2026"},
    )
    if status != 200:
        print(f"Échec login : {status} {body}")
        return
    print("✅ Login admin OK")

    # 2. Corriger Digital Campus → ORSYS
    status, body = api_request(
        opener,
        "PATCH",
        "/schools/1",
        {"name": "ORSYS", "url": "https://www.orsys.fr/", "scraper_strategy": "ORSYS"},
    )
    print(f"📝 École id=1 → ORSYS : {status} {body.get('name', body)}")

    # 3. Corriger ICAN → Demos
    status, body = api_request(
        opener,
        "PATCH",
        "/schools/2",
        {"name": "Demos", "url": "https://www.demos.fr/", "scraper_strategy": "Demos"},
    )
    print(f"📝 École id=2 → Demos : {status} {body.get('name', body)}")

    # 4. Lancer les scans
    for school_id, label in [(1, "ORSYS"), (2, "Demos"), (3, "SCAP"), (4, "Cegos")]:
        print(f"\n🚀 Lancement scan {label} (id={school_id})...")
        try:
            status, body = api_request(
                opener,
                "POST",
                f"/schools/{school_id}/scan",
                timeout=SCAN_TIMEOUT,
            )
            print(f"   → {status}: {json.dumps(body, indent=2, ensure_ascii=False)}")
        except Exception as exc:
            print(f"   → Erreur/timeout pour {label} : {exc}")


if __name__ == "__main__":
    main()
