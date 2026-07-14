#!/usr/bin/env python3
"""
Bulk IndexNow submission. Key + host come from env (CGE_INDEXNOW_KEY, CGE_SITE_DOMAIN).
No hardcoded values.

Usage:
    python submit_indexnow.py                    # submit all html in deploy/
    python submit_indexnow.py --file urls.txt
"""
import os
import sys
import glob
import json
import urllib.request
from pathlib import Path

CGE_DIR = Path(os.environ.get("CGE_REPO", "."))
KEY = os.environ.get("CGE_INDEXNOW_KEY", "")
HOST = os.environ.get("CGE_SITE_DOMAIN", "").rstrip("/")
DEPLOY = CGE_DIR / "deploy"


def collect_urls():
    urls = []
    for html in glob.glob(str(DEPLOY / "*.html")):
        slug = Path(html).stem
        if slug in ("index", "dashboard", "404"):
            continue
        urls.append(f"{HOST}/{slug}")
    return urls


def main():
    if not KEY or not HOST:
        raise SystemExit("✗ Set CGE_INDEXNOW_KEY and CGE_SITE_DOMAIN.")
    if "--file" in sys.argv:
        urls = Path(sys.argv[sys.argv.index("--file") + 1]).read_text().splitlines()
    else:
        urls = collect_urls()
    if not urls:
        print("No URLs to submit.")
        return
    keyloc = f"{HOST}/{KEY}.txt"
    body = json.dumps({"host": HOST.split('//')[-1], "key": KEY,
                       "keyLocation": keyloc, "urlList": urls}).encode()
    req = urllib.request.Request(
        "https://api.indexnow.org/indexnow", data=body,
        headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            print(f"IndexNow: {r.status} — {len(urls)} URLs")
    except urllib.error.HTTPError as e:
        print(f"IndexNow error {e.code}: {e.read().decode()[:200]}")


if __name__ == "__main__":
    main()
