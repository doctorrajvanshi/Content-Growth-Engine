#!/usr/bin/env python3
"""
Local ops dashboard generator.
Writes to the REPO ROOT (e.g. <repo>/dashboard.html) — NEVER to deploy/ or dist/.
No secrets, no network, no process-env reads.

Usage:
    python generate_dashboard.py
"""
import json
import glob
import sqlite3
from datetime import datetime
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent))
import load_config as cfgmod

cfg = cfgmod.load(__file__)
ROOT = Path(cfg["_root"])
LIBRARY = ROOT / "knowledge-engine" / "trade_rules_library"
CONTENT = ROOT / "content"
DB = ROOT / "knowledge-engine" / "seo.db"
OUTPUT = ROOT / "dashboard.html"          # LOCAL ONLY — do not deploy


def stats():
    s = {}
    mds = glob.glob(str(LIBRARY / "*.md"))
    s["guides"] = len(mds)
    s["words"] = sum(len(Path(f).read_text(encoding="utf-8").split()) for f in mds)
    for plat in ("linkedin", "twitter", "reddit", "replies"):
        d = CONTENT / plat
        s[f"content_{plat}"] = len(glob.glob(str(d / "*.txt"))) if d.exists() else 0
    cats = {}
    for c in cfg.get("categories", []):
        key, match = c["key"], c["match"]
        cats[key] = sum(1 for f in mds if any(m in Path(f).stem.lower() for m in match))
    s["categories"] = cats
    if DB.exists():
        try:
            con = sqlite3.connect(str(DB))
            s["queue_total"] = con.execute("SELECT COUNT(*) FROM content_queue").fetchone()[0]
            s["queue_pending"] = con.execute(
                "SELECT COUNT(*) FROM content_queue WHERE status IS NULL").fetchone()[0]
            con.close()
        except Exception:
            s["queue_total"] = s["queue_pending"] = 0
    return s


def render(s):
    cats = "".join(f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in s["categories"].items())
    return f"""<!doctype html><html><head><meta charset=utf-8>
<title>Ops Dashboard</title><style>body{{font-family:system-ui;margin:2rem;color:#0f172a}}
h1{{font-size:1.5rem}}.card{{background:#fff;border:1px solid #e2e8f0;border-radius:12px;
padding:1rem;margin:.5rem;display:inline-block;min-width:140px}}
.n{{font-size:1.6rem;font-weight:800;color:#f59e0b}}table{{border-collapse:collapse;width:100%}}
td,th{{text-align:left;padding:.4rem;border-bottom:1px solid #f1f5f9;font-size:.85rem}}</style>
</head><body><h1>Content Growth Engine — Ops Dashboard</h1>
<p>Generated {datetime.now():%Y-%m-%d %H:%M}</p>
<div>
<div class=card><div class=n>{s['guides']:,}</div>Guides</div>
<div class=card><div class=n>{s['words']:,}</div>Words</div>
<div class=card><div class=n>{s.get('queue_pending',0):,}</div>Queue pending</div>
</div>
<h2>Content pipeline</h2>
<table><tr><th>Platform</th><th>Drafts</th></tr>
<tr><td>LinkedIn</td><td>{s['content_linkedin']:,}</td></tr>
<tr><td>Twitter</td><td>{s['content_twitter']:,}</td></tr>
<tr><td>Reddit</td><td>{s['content_reddit']}</td></tr>
<tr><td>Replies</td><td>{s['content_replies']}</td></tr></table>
<h2>Categories</h2><table>{cats}</table>
<p style=color:#94a3b8>Local-only dashboard. Not deployed to the public site.</p>
</body></html>"""


if __name__ == "__main__":
    s = stats()
    OUTPUT.write_text(render(s), encoding="utf-8")
    print(f"Dashboard written locally: {OUTPUT} ({len(s['categories'])} categories)")
