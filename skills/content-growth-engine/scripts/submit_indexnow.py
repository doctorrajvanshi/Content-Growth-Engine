#!/usr/bin/env python3
"""
Bulk IndexNow submission. Key + host come from config/credentials.json (via
load_config). No process-env reads.

Usage:
    python submit_indexnow.py
    python submit_indexnow.py --file urls.txt
"""
import sys
import json
import glob
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import load_config as cfgmod

cfg = cfgmod.load(__file__)
ROOT = Path(cfg["_root"])
KEY = cfg.get("indexnow_key", "")
HOST = (cfg.get("site_domain") or cfg.get("product", {}).get("domain", "")).rstrip("/")
DEPLOY = ROOT / "deploy"


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
        raise SystemExit("✗ Set 'indexnow_key' and 'site_domain' in config.")
    if "--file" in sys.argv:
        urls = Path(sys.argv[sys.argv.index("--file") + 1]).read_text().splitlines()
    else:
        urls = collect_urls()
    if not urls:
        print("No URLs to submit.")
        return
    keyloc = f"{HOST}/{KEY}.txt"
    body = json.dumps({"host": HOST.split("//")[-1], "key": KEY,
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
