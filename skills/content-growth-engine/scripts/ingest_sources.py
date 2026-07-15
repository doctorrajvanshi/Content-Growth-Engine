#!/usr/bin/env python3
"""
Generic source ingestion (sandboxed — no product-specific sources).

Builds a guide library from AUTHORITATIVE sources the USER configures:
  - local markdown/text/PDF files
  - RSS feeds (parsed with stdlib xml.etree)
  - web pages (fetched, headline + lead extracted)

Output: one markdown stub per item into the configured library dir, with
YAML frontmatter. NO hard-coded topics, regulations, or product references.

Usage:
    python ingest_sources.py
"""
import sys
import re
import glob
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.request import Request, urlopen
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))
import load_config as cfgmod

cfg = cfgmod.load(__file__)
ROOT = Path(cfg["_root"])
LIB = Path(cfg.get("library") or (ROOT / "knowledge-engine" / "trade_rules_library"))
SOURCES = cfg.get("sources", [])
LIB.mkdir(parents=True, exist_ok=True)

UA = {"User-Agent": "content-growth-engine/1.0 (+https://github.com/doctorrajvanshi/Content-Growth-Engine)"}


def fetch(url: str, timeout: int = 20) -> str:
    req = Request(url, headers=UA)
    with urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "ignore")


def from_rss(url: str) -> list[tuple[str, str, str]]:
    out = []
    try:
        xml = fetch(url)
        root = ET.fromstring(xml)
        for item in root.iter("item"):
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            desc = (item.findtext("description") or "").strip()
            if title and link:
                out.append((title, link, re.sub(r"<[^>]+>", "", desc)[:400]))
    except Exception as e:
        print(f"  ! RSS failed {url}: {e}")
    return out


def from_local(path_glob: str) -> list[tuple[str, str, str]]:
    out = []
    for f in glob.glob(path_glob):
        p = Path(f)
        text = p.read_text(encoding="utf-8", errors="ignore")
        title = p.stem
        out.append((title, "", text[:400]))
    return out


def write_stub(title: str, link: str, body: str):
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    stamp = datetime.now().strftime("%Y-%m-%d")
    fm = f"---\ntitle: \"{title}\"\nsource: \"{link}\"\n---\n\n{body}\n"
    (LIB / f"{stamp}_{slug}.md").write_text(fm, encoding="utf-8")
    print(f"  ✓ {slug}")


def main():
    if not SOURCES:
        raise SystemExit("✗ No 'sources:' configured. Add RSS/local/url entries to config/example.yaml.")
    total = 0
    for s in SOURCES:
        if isinstance(s, dict):
            if "rss" in s:
                print(f"RSS: {s['rss']}")
                for t, l, b in from_rss(s["rss"]):
                    write_stub(t, l, b); total += 1
            elif "path" in s:
                print(f"Local: {s['path']}")
                for t, l, b in from_local(s["path"]):
                    write_stub(t, l, b); total += 1
            elif "url" in s:
                print(f"URL: {s['url']}")
                try:
                    html = fetch(s["url"])
                    title = re.search(r"<title>(.*?)</title>", html, re.I)
                    t = title.group(1).strip() if title else s["url"]
                    write_stub(t, s["url"], re.sub(r"<[^>]+>", "", html)[:400]); total += 1
                except Exception as e:
                    print(f"  ! url failed {s['url']}: {e}")
        elif isinstance(s, str) and s.startswith("http"):
            # bare url
            print(f"URL: {s}")
            try:
                html = fetch(s)
                title = re.search(r"<title>(.*?)</title>", html, re.I)
                t = title.group(1).strip() if title else s
                write_stub(t, s, re.sub(r"<[^>]+>", "", html)[:400]); total += 1
            except Exception as e:
                print(f"  ! url failed {s}: {e}")
    print(f"✓ Ingested {total} items → {LIB}")


if __name__ == "__main__":
    main()
