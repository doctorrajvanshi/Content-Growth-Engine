#!/usr/bin/env python3
"""
Generic platform post extractor.

Turns a guide (markdown or html) into a platform-ready post. Length + CTA +
opening come from config/example.yaml (or env overrides). No hardcoded product
names, domains, or tokens.

Usage:
    python extract_platform.py linkedin guide.md
    python extract_platform.py twitter guide.md
    python extract_platform.py twitter guide.md --limit 5
"""
import os
import re
import sys
import json
import glob
import argparse
from pathlib import Path
from datetime import datetime

CGE_DIR = Path(os.environ.get("CGE_REPO", "."))
CONFIG = CGE_DIR / "config" / "example.yaml"


def load_config():
    if CONFIG.exists():
        try:
            import yaml
            return yaml.safe_load(CONFIG.read_text(encoding="utf-8")) or {}
        except Exception:
            pass
    return {}


cfg = load_config()
DOMAIN = os.environ.get("CGE_SITE_DOMAIN", cfg.get("product", {}).get("domain", "https://guides.example.com"))
CTA = cfg.get("product", {}).get(
    "cta_template", "Explore compliant {topic} guidance at {url}"
)
LIMITS = {"linkedin": 3000, "twitter": 280}


def slugify(md_path: Path) -> str:
    name = md_path.stem
    name = re.sub(r"^\d{4}-\d{2}-\d{2}_", "", name)
    return name


def read_text(md_path: Path) -> str:
    return md_path.read_text(encoding="utf-8")


def extract_title(text: str) -> str:
    m = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    return m.group(1).strip() if m else "Untitled"


def extract_summary(text: str, max_chars: int = 180) -> str:
    # grab first non-heading paragraph
    paras = [p.strip() for p in text.split("\n\n") if p.strip() and not p.startswith("#")]
    if not paras:
        return ""
    s = paras[0]
    s = re.sub(r"[*_`#]", "", s)
    return s[:max_chars].rstrip() + ("…" if len(s) > max_chars else "")


def make_post(platform: str, title: str, summary: str, slug: str) -> str:
    url = f"{DOMAIN}/{slug}"
    topic = title
    if platform == "twitter":
        body = f"{summary}\n\n{CTA.format(topic=topic, url=url)}"
        if len(body) > LIMITS["twitter"]:
            # trim summary
            allowed = LIMITS["twitter"] - len(f"\n\n{CTA.format(topic=topic, url=url)}") - 3
            body = f"{summary[:max(allowed, 50)]}…\n\n{CTA.format(topic=topic, url=url)}"
        return body
    elif platform == "linkedin":
        body = f"{title}\n\n{summary}\n\n{CTA.format(topic=topic, url=url)}"
        return body[:LIMITS["linkedin"]]
    else:
        return f"{title}\n\n{summary}\n\n{url}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("platform", choices=["linkedin", "twitter"])
    ap.add_argument("input", nargs="?", help="markdown file or dir")
    ap.add_argument("--limit", type=int, default=1)
    args = ap.parse_args()

    if args.input and Path(args.input).exists():
        files = [Path(args.input)] if Path(args.input).is_file() else list(Path(args.input).rglob("*.md"))
    else:
        files = sorted(glob.glob(str(CGE_DIR / "knowledge-engine" / "trade_rules_library" / "*.md")))

    files = files[: args.limit]
    out_dir = CGE_DIR / "content" / args.platform
    out_dir.mkdir(parents=True, exist_ok=True)

    for f in files:
        text = read_text(f)
        title = extract_title(text)
        summary = extract_summary(text)
        slug = slugify(f)
        post = make_post(args.platform, title, summary, slug)
        stamp = datetime.now().strftime("%Y-%m-%d")
        out = out_dir / f"{args.platform}_{stamp}_{slug}.txt"
        out.write_text(post, encoding="utf-8")
        print(f"✓ {args.platform} post → {out.name} ({len(post)} chars)")
        print(post[:240])


if __name__ == "__main__":
    main()
