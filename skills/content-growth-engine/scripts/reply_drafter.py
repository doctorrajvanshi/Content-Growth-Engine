#!/usr/bin/env python3
"""
Reply Drafter
Processes a tweet/post URL and drafts a reply with guide links.

Usage:
    python reply_drafter.py twitter "https://twitter.com/user/status/123"
    python reply_drafter.py twitter "Tweet text to reply to"
    python reply_drafter.py linkedin "https://linkedin.com/feed/update/..."
    python reply_drafter.py linkedin "LinkedIn post text to reply to"
"""
import os
import re
import sys
import json
import glob
import hashlib
import subprocess
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

try:
    import requests
except ImportError:
    print("requests not installed")
    sys.exit(1)

KB_DIR = Path(os.environ.get("GUIDE_LIBRARY_DIR", "./knowledge-engine/trade_rules_library"))
GUIDES_URL = os.environ.get("SITE_URL", "https://guides.yourproduct.com")
TOKEN_FILE = Path(os.environ.get("TWITTER_BEARER_FILE", "./twitter_bearer_token.txt"))

# Reply templates
TEMPLATES = {
    "twitter": {
        "question": "Good question. {insight}\n\nDetailed breakdown:\n{guide_url}",
        "default": "{insight}\n\n{guide_url}",
    },
    "linkedin": {
        "question": "Great point. {insight}\n\nI wrote a detailed analysis here:\n{guide_url}",
        "default": "{insight}\n\nFull guide:\n{guide_url}",
    },
}


def get_tweet_text(tweet_id):
    """Fetch tweet text via Twitter API (if token available)."""
    token_file = TOKEN_FILE
    if not token_file.exists():
        return None

    token = token_file.read_text(encoding="utf-8").strip()
    headers = {"Authorization": f"Bearer {token}"}

    try:
        r = requests.get(
            f"https://api.twitter.com/2/tweets/{tweet_id}",
            headers=headers,
            params={"tweet.fields": "text,author_id", "expansions": "author_id",
                    "user.fields": "username"},
            timeout=10,
        )
        if r.status_code == 200:
            data = r.json()
            tweet = data.get("data", {})
            users = {u["id"]: u for u in data.get("includes", {}).get("users", [])}
            author = users.get(tweet.get("author_id"), {})
            return {
                "text": tweet.get("text", ""),
                "author": author.get("username", "unknown"),
                "url": f"https://twitter.com/{author.get('username', 'i')}/status/{tweet_id}",
            }
    except:
        pass
    return None


def search_kb(query, max_results=3):
    """Search KB for relevant guides."""
    results = []
    query_words = [w for w in re.findall(r'\w+', query.lower()) if len(w) > 3]

    for md_file in glob.glob(str(KB_DIR / "*.md")):
        try:
            text = open(md_file, encoding="utf-8").read().lower()
            score = sum(1 for w in query_words if w in text)
            if score >= 2:
                filename = os.path.basename(md_file)
                title_match = re.search(r"^#\s+(.+)$", open(md_file, encoding="utf-8").read(), re.MULTILINE)
                slug = re.sub(r"^\d{4}-\d{2}-\d{2}_", "", filename.replace(".md", ""))
                slug = slug.replace("_", "-")  # site uses hyphens, not underscores
                results.append({
                    "file": md_file,
                    "title": title_match.group(1) if title_match else filename,
                    "slug": slug,
                    "guide_url": f"{GUIDES_URL}/{slug}",
                    "score": score,
                })
        except:
            pass

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:max_results]


def extract_insight(kb_results):
    """Extract insight from KB."""
    if not kb_results:
        return "Based on UCP 600 and ISBP 745 standards, this is a common compliance scenario."

    text = open(kb_results[0]["file"], encoding="utf-8").read()

    # Try failure mode
    failure = re.search(r"##\s*Failure Mode 1.*?\n\n(.+?)(?=\n##|\Z)", text, re.DOTALL)
    if failure:
        sentences = re.split(r"(?<=[.!?])\s+", failure.group(1).strip())
        return " ".join(sentences[:2])

    # Try resolution
    resolution = re.search(r"##\s*Deterministic Resolution.*?\n\n(.+?)(?=\n##|\Z)", text, re.DOTALL)
    if resolution:
        steps = re.findall(r"\d+\.\s*\*\*(.+?)\*\*", resolution.group(1))
        if steps:
            return steps[0].strip()

    # Try introduction
    intro = re.search(r"##\s*Introduction.*?\n\n(.+?)(?=\n##|\Z)", text, re.DOTALL)
    if intro:
        sentences = re.split(r"(?<=[.!?])\s+", intro.group(1).strip())
        return " ".join(sentences[:2])

    return "This is a well-documented compliance scenario."


def draft_reply(text, platform, url=None):
    """Draft a reply based on input text."""
    kb_results = search_kb(text)
    insight = extract_insight(kb_results)
    guide_url = kb_results[0]["guide_url"] if kb_results else GUIDES_URL

    # Determine if it's a question
    is_question = "?" in text or any(w in text.lower() for w in ["how", "what", "why", "help"])
    template_key = "question" if is_question else "default"
    template = TEMPLATES.get(platform, TEMPLATES["twitter"])[template_key]

    reply = template.format(insight=insight, guide_url=guide_url)

    # Platform-specific length limits
    if platform == "twitter" and len(reply) > 280:
        reply = reply[:277] + "..."

    return reply, kb_results


def send_to_telegram(text, platform, original_url=None, reply_url=None):
    """Send draft to Telegram with Open & Reply button."""
    # Build the reply URL (where user will post)
    if platform == "twitter":
        post_url = f"https://twitter.com/intent/tweet?text={quote(text[:280])}"
        label = "🐦 Twitter Reply"
    elif platform == "linkedin":
        post_url = original_url or "https://www.linkedin.com/feed/"
        label = "💼 LinkedIn Reply"
    else:
        post_url = ""
        label = "📝 Draft Reply"

    # Forward via forward_to_telegram.py
    # Create a temp file with the reply
temp_dir = Path(os.environ.get("REPLIES_DIR", "./content/replies"))
    temp_dir.mkdir(parents=True, exist_ok=True)

    slug = hashlib.md5(text[:100].encode()).hexdigest()[:8]
    temp_file = temp_dir / f"reply_{platform}_{slug}.txt"
    temp_file.write_text(text, encoding="utf-8")

    meta_file = temp_dir / f"reply_{platform}_{slug}.json"
    meta = {
        "platform": platform,
        "original_url": original_url or "",
        "reply_url": post_url,
        "drafted_at": datetime.now().isoformat(timespec="seconds"),
    }
    meta_file.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    # Send via forward_to_telegram.py
    script = os.path.join(os.path.dirname(__file__), "forward_to_telegram.py")
    try:
        subprocess.run(
            ["C:/Python312/python.exe", script, platform, str(temp_file)],
            capture_output=True, timeout=30
        )
        print(f"✓ Sent to Telegram: {label}")
        print(f"  Reply URL: {post_url[:80]}")
    except Exception as e:
        print(f"✗ Failed to send: {e}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Draft replies to social posts")
    parser.add_argument("platform", choices=["twitter", "linkedin"], help="Platform")
    parser.add_argument("input", help="URL or text to reply to")
    args = parser.parse_args()

    text = args.input
    url = None

    # Check if input is a URL
    if text.startswith("http"):
        url = text
        # Try to extract tweet ID
        tweet_match = re.search(r"/status/(\d+)", text)
        if tweet_match and args.platform == "twitter":
            tweet_id = tweet_match.group(1)
            tweet_data = get_tweet_text(tweet_id)
            if tweet_data:
                text = tweet_data["text"]
                print(f"Fetched tweet from @{tweet_data['author']}: {text[:80]}")
            else:
                print("Couldn't fetch tweet (no API access). Using URL as context.")
                text = f"Trade finance compliance question about: {url}"

    print(f"\nDrafting {args.platform} reply...")
    reply, kb_results = draft_reply(text, args.platform, url)

    print(f"\n{'='*50}")
    print(f"REPLY:")
    print(f"{'='*50}")
    print(reply)
    print(f"{'='*50}")
    if kb_results:
        print(f"\nKB source: {kb_results[0]['title'][:60]}")
        print(f"Guide: {kb_results[0]['guide_url']}")

    # Send to Telegram
    send_to_telegram(reply, args.platform, url)


if __name__ == "__main__":
    main()
