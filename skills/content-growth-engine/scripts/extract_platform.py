#!/usr/bin/env python3
"""
Generic platform post extractor.

Turns a guide (markdown) into a platform-ready post. Length + CTA + domain come
from config/example.yaml + config/credentials.json (loaded via load_config).
No env-var reads, no hardcoded product names.

Usage:
    python extract_platform.py linkedin guide.md
    python extract_platform.py twitter guide.md --limit 5
"""
import re
import sys
import glob
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))
import load_config as cfgmod

cfg = cfgmod.load(__file__)
DOMAIN = cfg.get("site_domain") or cfg.get("product", {}).get("domain", "https://guides.example.com")
CTA = cfg.get("product", {}).get(
    "cta_template", "Explore compliant {topic} guidance at {url}"
)
LIMITS = {"linkedin": 3000, "twitter": 280}
ROOT = Path(cfg["_root"])


def slugify(md_path: Path) -> str:
    return re.sub(r"^\d{4}-\d{2}-\d{2}_", "", md_path.stem)


def extract_title(text: str) -> str:
    m = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    return m.group(1).strip() if m else "Untitled"


def extract_summary(text: str, max_chars: int = 180) -> str:
    paras = [p.strip() for p in text.split("\n\n") if p.strip() and not p.startswith("#")]
    if not paras:
        return ""
    s = re.sub(r"[*_`#]", "", paras[0])
    return s[:max_chars].rstrip() + ("…" if len(s) > max_chars else "")


def make_post(platform: str, title: str, summary: str, slug: str) -> str:
    url = f"{DOMAIN}/{slug}"
    topic = title
    if platform == "twitter":
        body = f"{summary}\n\n{CTA.format(topic=topic, url=url)}"
        if len(body) > LIMITS["twitter"]:
            allowed = LIMITS["twitter"] - len(f"\n\n{CTA.format(topic=topic, url=url)}") - 3
            body = f"{summary[:max(allowed, 50)]}…\n\n{CTA.format(topic=topic, url=url)}"
        return body
    if platform == "linkedin":
        return f"{title}\n\n{summary}\n\n{CTA.format(topic=topic, url=url)}"[:LIMITS["linkedin"]]
    return f"{title}\n\n{summary}\n\n{url}"


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("platform", choices=["linkedin", "twitter"])
    ap.add_argument("input", nargs="?", help="markdown file or dir")
    ap.add_argument("--limit", type=int, default=1)
    args = ap.parse_args()

    if args.input and Path(args.input).exists():
        files = [Path(args.input)] if Path(args.input).is_file() else list(Path(args.input).rglob("*.md"))
    else:
        files = sorted(glob.glob(str(ROOT / "knowledge-engine" / "trade_rules_library" / "*.md")))

    files = files[: args.limit]
    out_dir = ROOT / "content" / args.platform
    out_dir.mkdir(parents=True, exist_ok=True)
    for f in files:
        text = f.read_text(encoding="utf-8")
        post = make_post(args.platform, extract_title(text), extract_summary(text), slugify(f))
        stamp = datetime.now().strftime("%Y-%m-%d")
        out = out_dir / f"{args.platform}_{stamp}_{slugify(f)}.txt"
        out.write_text(post, encoding="utf-8")
        print(f"✓ {args.platform} post → {out.name} ({len(post)} chars)")
        print(post[:240])


if __name__ == "__main__":
    main()
