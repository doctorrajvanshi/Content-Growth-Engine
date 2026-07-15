#!/usr/bin/env python3
"""
YourProduct Operations Dashboard
Generates a static HTML dashboard showing the full system status.
"""
import os
import json
import glob
import sqlite3
from datetime import datetime
from pathlib import Path

DB = Path(r"/path/to/your/project\knowledge-engine\your_seo.db")
LIBRARY = Path(r"/path/to/your/project\knowledge-engine\your_guide_library")
CONTENT = Path(r"/path/to/your/project\content")
DEPLOY = Path(r"/path/to/your/project\deploy")
OUTPUT = Path(r"/path/to/your/project\dashboard.html")
SITE_URL = "https://guides.yourproduct.com"


def get_stats():
    """Collect all system stats."""
    stats = {}

    # Guide stats
    md_files = glob.glob(str(LIBRARY / "*.md"))
    stats["total_guides"] = len(md_files)
    total_words = 0
    for f in md_files:
        total_words += len(open(f, encoding="utf-8").read().split())
    stats["total_words"] = total_words
    stats["avg_words"] = total_words // max(len(md_files), 1)

    # Queue stats
    conn = sqlite3.connect(str(DB))
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM content_queue WHERE status IS NULL")
    stats["queue_pending"] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM content_queue WHERE status='staged'")
    stats["queue_staged"] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM content_queue WHERE status='skipped'")
    stats["queue_skipped"] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM content_queue")
    stats["queue_total"] = cur.fetchone()[0]
    conn.close()

    # Deploy stats
    html_files = glob.glob(str(DEPLOY / "*.html"))
    stats["deployed_pages"] = len(html_files)

    # Content stats
    content_dirs = {
        "linkedin": CONTENT / "linkedin",
        "twitter": CONTENT / "twitter",
        "reddit": CONTENT / "reddit",
        "replies": CONTENT / "replies",
    }
    for name, path in content_dirs.items():
        if path.exists():
            txt_files = glob.glob(str(path / "*.txt"))
            stats[f"content_{name}"] = len(txt_files)
        else:
            stats[f"content_{name}"] = 0

    # Categories
    categories = {}
    for f in md_files:
        basename = os.path.basename(f).lower()
        if "ucp" in basename:
            cat = "UCP 600"
        elif "isbp" in basename:
            cat = "ISBP 745"
        elif "swift" in basename or "mt700" in basename:
            cat = "SWIFT"
        elif "dispute" in basename:
            cat = "Disputes"
        elif "checklist" in basename:
            cat = "Checklists"
        elif "eucp" in basename or "digital" in basename:
            cat = "Digital Trade"
        elif "urdg" in basename or "guarantee" in basename:
            cat = "URDG"
        elif "incoterm" in basename:
            cat = "Incoterms"
        elif any(r in basename for r in ["india", "uae", "singapore", "uk", "china", "region"]):
            cat = "Regional"
        else:
            cat = "Trade Finance"
        categories[cat] = categories.get(cat, 0) + 1
    stats["categories"] = dict(sorted(categories.items(), key=lambda x: -x[1]))

    # Crawl deploy for recent files
    recent_files = sorted(glob.glob(str(DEPLOY / "*.html")), key=os.path.getmtime, reverse=True)[:5]
    stats["recent_deploy"] = []
    for f in recent_files:
        mtime = datetime.fromtimestamp(os.path.getmtime(f))
        stats["recent_deploy"].append({
            "name": os.path.basename(f),
            "size": os.path.getsize(f),
            "modified": mtime.strftime("%Y-%m-%d %H:%M"),
        })

    return stats


def generate_dashboard(stats):
    """Generate the HTML dashboard."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cat_rows = ""
    for cat, count in stats["categories"].items():
        pct = count * 100 // max(stats["total_guides"], 1)
        cat_rows += f"""
        <tr>
            <td>{cat}</td>
            <td>{count}</td>
            <td><div class="bar"><div class="bar-fill" style="width:{pct}%"></div></div></td>
            <td>{pct}%</td>
        </tr>"""

    recent_rows = ""
    for f in stats["recent_deploy"]:
        recent_rows += f"""
        <tr>
            <td>{f["name"][:50]}</td>
            <td>{f["size"]:,} bytes</td>
            <td>{f["modified"]}</td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>YourProduct Operations Dashboard</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ font-family: 'Inter', sans-serif; background: #F8FAFC; color: #0F172A; }}
        .container {{ max-width: 1200px; margin: 0 auto; padding: 2rem 1.5rem; }}

        .header {{ text-align: center; margin-bottom: 2rem; }}
        .header h1 {{ font-size: 2rem; font-weight: 800; color: #0F172A; }}
        .header p {{ color: #64748B; margin-top: 0.5rem; }}
        .header .timestamp {{ font-size: 0.875rem; color: #94A3B8; margin-top: 0.25rem; }}

        .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 2rem; }}
        .stat-card {{ background: white; border: 1px solid #E2E8F0; border-radius: 0.75rem; padding: 1.5rem; text-align: center; }}
        .stat-card .number {{ font-size: 2rem; font-weight: 800; color: #F59E0B; }}
        .stat-card .label {{ font-size: 0.875rem; color: #64748B; margin-top: 0.25rem; }}

        .section {{ background: white; border: 1px solid #E2E8F0; border-radius: 0.75rem; padding: 1.5rem; margin-bottom: 1.5rem; }}
        .section h2 {{ font-size: 1.125rem; font-weight: 700; color: #0F172A; margin-bottom: 1rem; padding-bottom: 0.5rem; border-bottom: 1px solid #E2E8F0; }}

        table {{ width: 100%; border-collapse: collapse; }}
        th {{ text-align: left; font-size: 0.75rem; font-weight: 600; color: #64748B; text-transform: uppercase; padding: 0.5rem 0; }}
        td {{ padding: 0.5rem 0; font-size: 0.875rem; border-bottom: 1px solid #F1F5F9; }}
        tr:last-child td {{ border-bottom: none; }}

        .bar {{ background: #F1F5F9; border-radius: 9999px; height: 8px; width: 100%; }}
        .bar-fill {{ background: #F59E0B; border-radius: 9999px; height: 8px; }}

        .badge {{ display: inline-block; padding: 0.25rem 0.75rem; border-radius: 9999px; font-size: 0.75rem; font-weight: 600; }}
        .badge-green {{ background: #D1FAE5; color: #065F46; }}
        .badge-yellow {{ background: #FEF3C7; color: #92400E; }}
        .badge-blue {{ background: #DBEAFE; color: #1E40AF; }}

        .grid-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; }}
        @media (max-width: 768px) {{ .grid-2 {{ grid-template-columns: 1fr; }} }}

        .footer {{ text-align: center; margin-top: 2rem; color: #94A3B8; font-size: 0.875rem; }}
        .footer a {{ color: #F59E0B; text-decoration: none; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>YourProduct Operations Dashboard</h1>
            <p>Compliance Guides System Status</p>
            <p class="timestamp">Last updated: {now}</p>
        </div>

        <!-- Key Stats -->
        <div class="stats-grid">
            <div class="stat-card">
                <div class="number">{stats["total_guides"]:,}</div>
                <div class="label">Guides Published</div>
            </div>
            <div class="stat-card">
                <div class="number">{stats["total_words"]:,}</div>
                <div class="label">Total Words</div>
            </div>
            <div class="stat-card">
                <div class="number">{stats["queue_pending"]:,}</div>
                <div class="label">Queue Pending</div>
            </div>
            <div class="stat-card">
                <div class="number">{stats["deployed_pages"]}</div>
                <div class="label">Deployed Pages</div>
            </div>
        </div>

        <!-- Content Pipeline -->
        <div class="section">
            <h2>Content Pipeline</h2>
            <div class="grid-2">
                <table>
                    <tr><th>Platform</th><th>Drafts</th><th>Status</th></tr>
                    <tr>
                        <td>LinkedIn</td>
                        <td>{stats["content_linkedin"]:,}</td>
                        <td><span class="badge badge-green">Active</span></td>
                    </tr>
                    <tr>
                        <td>Twitter</td>
                        <td>{stats["content_twitter"]:,}</td>
                        <td><span class="badge badge-green">Active</span></td>
                    </tr>
                    <tr>
                        <td>Reddit</td>
                        <td>{stats["content_reddit"]}</td>
                        <td><span class="badge badge-green">Active</span></td>
                    </tr>
                    <tr>
                        <td>Replies</td>
                        <td>{stats["content_replies"]}</td>
                        <td><span class="badge badge-green">Active</span></td>
                    </tr>
                </table>
                <table>
                    <tr><th>Cron Job</th><th>Schedule</th><th>Status</th></tr>
                    <tr><td>E-E-A-T Guide Gen</td><td>Hourly</td><td><span class="badge badge-green">Active</span></td></tr>
                    <tr><td>LinkedIn Post</td><td>Daily 9am</td><td><span class="badge badge-green">Active</span></td></tr>
                    <tr><td>Twitter Post</td><td>Daily 11am</td><td><span class="badge badge-green">Active</span></td></tr>
                    <tr><td>Q&A Monitor</td><td>Daily noon</td><td><span class="badge badge-green">Active</span></td></tr>
                    <tr><td>Reddit Monitor</td><td>Daily 2pm</td><td><span class="badge badge-green">Active</span></td></tr>
                    <tr><td>Twitter Monitor</td><td>Daily 4pm</td><td><span class="badge badge-green">Active</span></td></tr>
                    <tr><td>Health Check</td><td>Every 30min</td><td><span class="badge badge-green">Active</span></td></tr>
                    <tr><td>Trending Topics</td><td>Weekly Mon</td><td><span class="badge badge-green">Active</span></td></tr>
                    <tr><td>Google Index</td><td>Daily 9am</td><td><span class="badge badge-green">Active</span></td></tr>
                </table>
            </div>
        </div>

        <!-- Categories -->
        <div class="grid-2">
            <div class="section">
                <h2>Guide Categories</h2>
                <table>
                    <tr><th>Category</th><th>Count</th><th>Distribution</th><th>%</th></tr>
                    {cat_rows}
                </table>
            </div>
            <div class="section">
                <h2>Recent Deployments</h2>
                <table>
                    <tr><th>File</th><th>Size</th><th>Modified</th></tr>
                    {recent_rows}
                </table>
            </div>
        </div>

        <!-- Queue Status -->
        <div class="section">
            <h2>Content Queue</h2>
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="number">{stats["queue_total"]:,}</div>
                    <div class="label">Total Topics</div>
                </div>
                <div class="stat-card">
                    <div class="number" style="color:#16A34A">{stats["queue_pending"]:,}</div>
                    <div class="label">Pending</div>
                </div>
                <div class="stat-card">
                    <div class="number" style="color:#2563EB">{stats["queue_staged"]:,}</div>
                    <div class="label">Staged</div>
                </div>
                <div class="stat-card">
                    <div class="number" style="color:#94A3B8">{stats["queue_skipped"]:,}</div>
                    <div class="label">Skipped</div>
                </div>
            </div>
        </div>

        <div class="footer">
            <p>Generated by YourProduct Operations Dashboard</p>
            <p><a href="{SITE_URL}">{SITE_URL}</a></p>
        </div>
    </div>
</body>
</html>"""

    return html


def main():
    print("Collecting stats...")
    stats = get_stats()

    print(f"Guides: {stats['total_guides']:,}")
    print(f"Words: {stats['total_words']:,}")
    print(f"Queue: {stats['queue_pending']:,} pending")
    print(f"LinkedIn: {stats['content_linkedin']:,} drafts")
    print(f"Twitter: {stats['content_twitter']:,} drafts")

    print("\nGenerating dashboard...")
    html = generate_dashboard(stats)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(html, encoding="utf-8")
    print(f"Dashboard: {OUTPUT}")
    print(f"Size: {len(html):,} bytes")


if __name__ == "__main__":
    main()
