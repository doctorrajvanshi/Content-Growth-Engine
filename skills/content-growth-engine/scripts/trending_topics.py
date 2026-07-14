#!/usr/bin/env python3
"""
Trending topic scout — wraps the `last30days` skill to find fresh conversations,
scores them against existing guides, and queues gaps for generation.

Sources/topics come from config/example.yaml `sources` + a `topics` list, or CLI.
No hardcoded domain content.

Usage:
    python trending_topics.py --topic "letter of credit discrepancy"
    python trending_topics.py --sources reddit,youtube
"""
import os
import re
import sys
import json
import glob
import subprocess
import argparse
from pathlib import Path
from datetime import datetime

CGE_DIR = Path(os.environ.get("CGE_REPO", "."))
SKILL = CGE_DIR / "last30days-skill" / "skills" / "last30days" / "scripts" / "last30days.py"
LIBRARY = CGE_DIR / "knowledge-engine" / "trade_rules_library"
CFG = CGE_DIR / "config" / "example.yaml"


def load_cfg():
    if CFG.exists():
        try:
            import yaml
            return yaml.safe_load(CFG.read_text(encoding="utf-8")) or {}
        except Exception:
            return {}
    return {}


def run_last30days(topic: str, sources: str = "reddit,youtube") -> str:
    if not SKILL.exists():
        return "ERROR: last30days skill not found at expected path."
    cmd = ["python3", str(SKILL), topic, f"--search={sources}", "--emit=compact"]
    env = os.environ.copy()
    env["PATH"] = str(Path.home() / "bin") + os.pathsep + env.get("PATH", "")
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=120, env=env).stdout
    except Exception as e:
        return f"ERROR: {e}"


def extract_threads(out: str):
    res = []
    for m in re.finditer(r"\[reddit\]\s*(.+?)\n\s*-\s*\d{4}-\d{2}-\d{2}\s*\|\s*r/(\w+)\s*\|\s*\[(\d+)cmt\]", out):
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
    ap = argparse.ArgumentParser()
    ap.add_argument("--topic")
    ap.add_argument("--sources", default="reddit,youtube")
    ap.add_argument("--topics-file", default=None)
    args = ap.parse_args()

    cfg = load_cfg()
    topics = [args.topic] if args.topic else cfg.get("topics", [])
    if args.topics_file and Path(args.topics_file).exists():
        topics += Path(args.topics_file).read_text(encoding="utf-8").read_text().splitlines()

    found = []
    for t in topics:
        out = run_last30days(t, args.sources)
        for th in extract_threads(out):
            th["coverage"] = coverage(th["title"])
            found.append(th)

    out_path = CGE_DIR / "content" / "trending" / f"trending_{datetime.now():%Y%m%d}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(found, indent=2), encoding="utf-8")
    new = [f for f in found if f["coverage"] == "new"]
    print(f"Threads found: {len(found)} | new: {len(new)}")
    print(f"Saved: {out_path}")


if __name__ == "__main__":
    main()
