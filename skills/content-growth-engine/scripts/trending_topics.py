#!/usr/bin/env python3
"""
Trending topic scout — uses the `last30days` skill's engine as an imported
module (no shell-out, no env mutation) to find fresh conversations, scores
them against existing guides, and writes gaps to content/trending/.

Usage:
    python trending_topics.py --topic "letter of credit discrepancy"
    python trending_topics.py --sources reddit,youtube
"""
import re
import sys
import json
import glob
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))
import load_config as cfgmod

cfg = cfgmod.load(__file__)
ROOT = Path(cfg["_root"])
LIBRARY = ROOT / "knowledge-engine" / "trade_rules_library"
LAST30 = ROOT / "last30days-skill" / "skills" / "last30days" / "scripts"
if LAST30.exists():
    sys.path.insert(0, str(LAST30))


def run_last30days(topic: str, sources: str = "reddit,youtube") -> str:
    if not LAST30.exists():
        return "ERROR: last30days skill not found at expected path."
    try:
        import last30days as engine
        # Call the engine's programmatic entry if available; else fall back.
        if hasattr(engine, "run"):
            return engine.run(topic, sources=sources, emit="compact")
        return "ERROR: last30days engine has no programmatic run()."
    except Exception as e:
        return f"ERROR: {e}"


def extract_threads(out: str):
    res = []
    for m in re.finditer(
        r"\[reddit\]\s*(.+?)\n\s*-\s*\d{4}-\d{2}-\d{2}\s*\|\s*r/(\w+)\s*\|\s*\[(\d+)cmt\]", out
    ):
        res.append({"title": m.group(1).strip(), "src": f"r/{m.group(2)}"})
    return res


def coverage(title: str) -> str:
    words = set(w for w in re.findall(r"\w+", title.lower()) if len(w) > 3)
    for md in glob.glob(str(LIBRARY / "*.md")):
        txt = Path(md).read_text(encoding="utf-8").lower()
        if sum(1 for w in words if w in txt) >= 3:
            return "covered"
    return "new"


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--topic")
    ap.add_argument("--sources", default="reddit,youtube")
    args = ap.parse_args()

    topics = [args.topic] if args.topic else cfg.get("topics", [])
    found = []
    for t in topics:
        out = run_last30days(t, args.sources)
        for th in extract_threads(out):
            th["coverage"] = coverage(th["title"])
            found.append(th)

    out_path = ROOT / "content" / "trending" / f"trending_{datetime.now():%Y%m%d}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(found, indent=2), encoding="utf-8")
    new = [f for f in found if f["coverage"] == "new"]
    print(f"Threads found: {len(found)} | new: {len(new)}")
    print(f"Saved: {out_path}")


if __name__ == "__main__":
    main()
