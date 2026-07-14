#!/usr/bin/env python3
"""
Google Indexing API submission. Service-account JSON path comes from
config/credentials.json ('google_sa_json'). No os.environ.

Usage:
    python submit_google.py
"""
import sys
import glob
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import load_config as cfgmod

cfg = cfgmod.load(__file__)
ROOT = Path(cfg["_root"])
HOST = (cfg.get("site_domain") or cfg.get("product", {}).get("domain", "")).rstrip("/")
SA_PATH = cfg.get("google_sa_json", "")
DEPLOY = ROOT / "deploy"
SCOPES = ["https://www.googleapis.com/auth/indexing"]


def main():
    if not HOST:
        raise SystemExit("✗ Set 'site_domain' in config.")
    if not SA_PATH or not Path(SA_PATH).exists():
        raise SystemExit("✗ Set 'google_sa_json' (path to service-account file) in config.")
    try:
        from google.oauth2 import service_account
        from google.auth.transport.requests import AuthorizedSession
    except ImportError:
        raise SystemExit("✗ missing google-auth / requests — install in your venv first")
    creds = service_account.Credentials.from_service_account_file(SA_PATH, scopes=SCOPES)
    session = AuthorizedSession(creds)
    urls = []
    for html in glob.glob(str(DEPLOY / "*.html")):
        slug = Path(html).stem
        if slug in ("index", "dashboard", "404"):
            continue
        urls.append(f"{HOST}/{slug}")
    urls = urls[:200]
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
