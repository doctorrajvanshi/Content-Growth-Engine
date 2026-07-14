#!/usr/bin/env python3
"""
Google Indexing API submission. Service-account JSON is passed via env
(CGE_GOOGLE_SA_JSON = path to file, or the JSON itself). No hardcoded creds.

Usage:
    python submit_google.py                 # submit up to 200 html in deploy/
    CGE_GOOGLE_SA_JSON=sa.json python submit_google.py
"""
import os
import sys
import glob
import json
from pathlib import Path

CGE_DIR = Path(os.environ.get("CGE_REPO", "."))
HOST = os.environ.get("CGE_SITE_DOMAIN", "").rstrip("/")
SA_ENV = os.environ.get("CGE_GOOGLE_SA_JSON", "")
DEPLOY = CGE_DIR / "deploy"
SCOPES = ["https://www.googleapis.com/auth/indexing"]


def get_creds():
    raw = SA_ENV
    if raw.startswith("{"):
        data = json.loads(raw)
    elif Path(raw).exists():
        data = json.loads(Path(raw).read_text())
    else:
        raise SystemExit("✗ Set CGE_GOOGLE_SA_JSON to JSON or a file path.")
    try:
        from google.oauth2 import service_account
        return service_account.Credentials.from_service_account_info(data, scopes=SCOPES)
    except ImportError:
        raise SystemExit("✗ pip install google-auth requests")


def main():
    if not HOST:
        raise SystemExit("✗ Set CGE_SITE_DOMAIN.")
    creds = get_creds()
    from google.auth.transport.requests import AuthorizedSession
    session = AuthorizedSession(creds)
    urls = []
    for html in glob.glob(str(DEPLOY / "*.html")):
        slug = Path(html).stem
        if slug in ("index", "dashboard", "404"):
            continue
        urls.append(f"{HOST}/{slug}")
    urls = urls[:200]  # free-tier daily quota
    ok = 0
    for u in urls:
        r = session.post(
            "https://indexing.googleapis.com/v3/urlNotifications:publish",
            json={"url": u, "type": "URL_UPDATED"})
        if r.status_code in (200, 429):
            ok += 1
    print(f"Google: submitted {ok}/{len(urls)} (200=ok, 429=quota)")


if __name__ == "__main__":
    main()
