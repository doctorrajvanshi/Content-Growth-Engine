#!/usr/bin/env python3
"""
Trending Topic Scraper
Uses last30days to find trending trade finance topics for new guides.

Usage:
    python trending_topics.py                    # Search all sources
    python trending_topics.py --sources reddit,youtube
    python trending_topics.py --topic "UCP 600"  # Specific topic
"""
import os
import re
import sys
import json
import glob
import subprocess
from datetime import datetime
from pathlib import Path

SKILL_DIR = Path(os.environ.get("LAST30DAYS_DIR", "~/.hermes/skills/last30days"))
SCRIPT = SKILL_DIR / "scripts" / "last30days.py"
OUTPUT = Path(os.environ.get("TRENDING_DIR", "./content/trending"))
KB_DIR = Path(os.environ.get("GUIDE_LIBRARY_DIR", "./knowledge-engine/trade_rules_library"))
QUEUE_DB = Path(os.environ.get("SEO_DB_PATH", "./knowledge-engine/seo.db"))

# Topics to search
DEFAULT_TOPICS = [
    "letter of credit compliance",
    "UCP 600 discrepancy",
    "trade finance documentary credit",
    "LC document presentation",
    "bill of lading discrepancy",
    "SWIFT MT700 fields",
    "trade finance compliance 2026",
    "export documentary collection",
    "bank guarantee URDG",
    "LC amendment process",
]


def run_last30days(topic, sources="reddit,youtube"):
    """Run last30days and return results."""
    cmd = [
        "C:/Python312/python.exe",
        str(SCRIPT),
        topic,
        f"--search={sources}",
        "--emit=compact",
    ]

    env = os.environ.copy()
    env["PATH"] = os.path.join(os.path.expanduser("~"), "bin") + ";" + env.get("PATH", "")

    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120, env=env)
        return r.stdout + r.stderr
    except subprocess.TimeoutExpired:
        return "TIMEOUT"
    except Exception as e:
        return f"ERROR: {e}"


def extract_relevant_topics(output):
    """Extract relevant discussion topics from last30days output."""
    topics = []

    # Find Reddit threads
    reddit_matches = re.findall(
        r"\[reddit\]\s*(.+?)\n\s*-\s*\d{4}-\d{2}-\d{2}\s*\|\s*r/(\w+)\s*\|\s*\[(\d+)cmt\]",
        output
    )
    for title, sub, comments in reddit_matches:
        topics.append({
            "title": title.strip(),
            "source": f"r/{sub}",
            "comments": int(comments),
            "type": "reddit",
        })

    # Find YouTube videos
    yt_matches = re.findall(
        r"\[youtube\]\s*(.+?)\n\s*-\s*\d{4}-\d{2}-\d{2}\s*\|\s*([\w\s]+?)\s*\|\s*\[(\d+)\s*views\]",
        output
    )
    for title, channel, views in yt_matches:
        topics.append({
            "title": title.strip(),
            "source": channel.strip(),
            "views": int(views),
            "type": "youtube",
        })

    # Find HN posts
    hn_matches = re.findall(
        r"\[hn\]\s*(.+?)\n\s*-\s*\d{4}-\d{2}-\d{2}\s*\|\s*score:\s*(\d+)",
        output
    )
    for title, score in hn_matches:
        topics.append({
            "title": title.strip(),
            "source": "Hacker News",
            "score": int(score),
            "type": "hn",
        })

    return topics


def score_topic(title, kb_files):
    """Score how well-covered a topic is in the KB."""
    title_words = set(w.lower() for w in re.findall(r'\w+', title) if len(w) > 3)

    for kb_file in kb_files:
        text = open(kb_file, encoding="utf-8").read().lower()
        matches = sum(1 for w in title_words if w in text)
        if matches >= 3:
            return "covered"
        elif matches >= 1:
            return "partial"

    return "new"


def add_to_queue(topic, source, topic_type):
    """Add a trending topic to the content queue."""
    import sqlite3

    db = sqlite3.connect(str(QUEUE_DB))
    cur = db.cursor()

    # Check if already in queue
    cur.execute("SELECT COUNT(*) FROM content_queue WHERE topic = ?", (topic,))
    if cur.fetchone()[0] > 0:
        db.close()
        return False

    # Add to queue
    cur.execute(
        "INSERT INTO content_queue (topic, query, content_type, priority, created_at, status) VALUES (?, ?, ?, ?, ?, NULL)",
        (topic, f"trending:{source}", "content", 9, datetime.now().isoformat(timespec="seconds"))
    )
    db.commit()
    db.close()
    return True


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Find trending trade finance topics")
    parser.add_argument("--sources", default="reddit,youtube", help="Sources to search")
    parser.add_argument("--topic", help="Specific topic to search")
    parser.add_argument("--dry-run", action="store_true", help="Don't add to queue")
    parser.add_argument("--limit", type=int, default=0, help="Max topics per search")
    args = parser.parse_args()

    OUTPUT.mkdir(parents=True, exist_ok=True)

    # Get existing KB files for coverage check
    kb_files = glob.glob(str(KB_DIR / "*.md"))

    topics_to_search = [args.topic] if args.topic else DEFAULT_TOPICS
    all_topics = []
    new_count = 0

    for topic in topics_to_search:
        print(f"\nSearching: {topic}")
        output = run_last30days(topic, args.sources)

        if output == "TIMEOUT":
            print("  Timeout — skipping")
            continue

        topics = extract_relevant_topics(output)
        print(f"  Found: {len(topics)} discussions")

        for t in topics[:10]:
            coverage = score_topic(t["title"], kb_files)
            t["coverage"] = coverage

            if not args.dry_run and coverage == "new":
                added = add_to_queue(t["title"], t["source"], t["type"])
                if added:
                    new_count += 1
                    print(f"    + NEW: {t['title'][:60]} ({t['source']})")
                else:
                    print(f"    = EXISTS: {t['title'][:60]}")
            elif coverage == "partial":
                print(f"    ~ PARTIAL: {t['title'][:60]}")
            else:
                print(f"    ✓ COVERED: {t['title'][:60]}")

            all_topics.append(t)

    # Save results
    results_path = OUTPUT / f"trending_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    results = {
        "timestamp": datetime.now().isoformat(),
        "sources": args.sources,
        "topics_searched": len(topics_to_search),
        "total_discussions": len(all_topics),
        "new_topics_added": new_count,
        "topics": all_topics[:50],
    }
    results_path.write_text(json.dumps(results, indent=2), encoding="utf-8")

    print(f"\n{'='*60}")
    print(f"Done: {len(all_topics)} discussions found, {new_count} new topics added to queue")
    print(f"Results: {results_path}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
