#!/usr/bin/env python3
"""
Telegram Forwarder (v2)
Sends content drafts to platform-specific Telegram bots with Open & Post buttons.

Usage:
    python forward_to_telegram.py reddit <filename>    # Forward Reddit draft
    python forward_to_telegram.py qa <filename>        # Forward Q&A draft
    python forward_to_telegram.py linkedin <filename>  # Forward LinkedIn draft
    python forward_to_telegram.py twitter <filename>   # Forward Twitter draft
    python forward_to_telegram.py test                 # Test connectivity
"""
import sys
import os
import re
import json
import hashlib
import requests
import time
from urllib.parse import quote
from datetime import datetime, timezone

# --- Resilient send config (shared with gateway) ---
SEND_MAX_RETRY = 5
SEND_BACKOFF_BASE = 2
SEND_BACKOFF_MAX = 60
DEAD_LETTER_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dead_letter")
os.makedirs(DEAD_LETTER_DIR, exist_ok=True)

def telegram_post(token, endpoint, payload, desc="forward"):
    """Resilient POST to Telegram Bot API with retry + exponential backoff + dead-letter."""
    url = f"https://api.telegram.org/bot{token}/{endpoint}"
    last = None
    for attempt in range(1, SEND_MAX_RETRY + 1):
        try:
            r = requests.post(url, json=payload, timeout=15)
            if r.status_code == 200 and r.json().get("ok"):
                return r
            last = r
            print(f"  ! {desc} HTTP {r.status_code} (attempt {attempt}/{SEND_MAX_RETRY})")
        except Exception as e:
            last = None
            print(f"  ! {desc} exception: {e} (attempt {attempt}/{SEND_MAX_RETRY})")
        if attempt < SEND_MAX_RETRY:
            time.sleep(min(SEND_BACKOFF_BASE * (2 ** (attempt - 1)), SEND_BACKOFF_MAX))
    # dead-letter
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe = re.sub(r"\W+", "_", desc)[:40]
    dlp = os.path.join(DEAD_LETTER_DIR, f"{ts}_{safe}.json")
    try:
        with open(dlp, "w", encoding="utf-8") as fh:
            json.dump({"endpoint": endpoint, "payload": {k: (v[:200] if isinstance(v, str) else v)
                        for k, v in payload.items()}, "desc": desc,
                       "failed_at": datetime.now(timezone.utc).isoformat(),
                       "last_status": getattr(last, "status_code", None)}, fh, indent=2)
        print(f"  ! DEAD-LETTER written: {dlp}")
    except Exception as e:
        print(f"  ! dead-letter write failed: {e}")
    return last

# --- Local-only approval telemetry ---
# (TELEMETRY_PATH is defined below next to APPROVALS_ROOT)

def record_telemetry(event):
    """Append a local-only telemetry event (no external send)."""
    try:
        event["ts"] = datetime.now(timezone.utc).isoformat()
        with open(TELEMETRY_PATH, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"  ! telemetry write failed: {e}")

# Per-type bot tokens
BOT_TOKENS = {
    "reddit": os.environ.get("REDDIT_BOT_TOKEN", "reddit-bot-token-placeholder"),
    "qa": os.environ.get("QA_BOT_TOKEN", "qa-bot-token-placeholder"),
    "linkedin": os.environ.get("LINKEDIN_BOT_TOKEN", "linkedin-bot-token-placeholder"),
    "twitter": os.environ.get("TWITTER_BOT_TOKEN", "twitter-bot-token-placeholder"),
    "guide": os.environ.get("APPROVAL_BOT_TOKEN", "approval-bot-token-placeholder"),
}
}

CHAT_ID = "YOUR_CHAT_ID"
APPROVALS_ROOT = os.path.join(os.path.expanduser("~"), ".hermes", "approvals")
TELEMETRY_PATH = os.path.join(APPROVALS_ROOT, "telemetry.jsonl")
CALLBACK_MAX_BYTES = 64


def pending_map_path(content_type):
    return os.path.join(APPROVALS_ROOT, content_type, ".pending_map.json")


def store_pending_id(content_type, filename):
    """Persist a short callback ID -> filename mapping for copy handlers."""
    fid = hashlib.md5(filename.encode("utf-8")).hexdigest()[:8]
    path = pending_map_path(content_type)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = {}
    if os.path.exists(path):
        try:
            data = json.loads(open(path, encoding="utf-8").read())
        except (OSError, ValueError):
            data = {}
    data[fid] = filename
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
    callback = f"copy_{content_type}_{fid}"
    if len(callback.encode("utf-8")) > CALLBACK_MAX_BYTES:
        raise ValueError(f"callback_data exceeds Telegram limit: {callback}")
    return fid

# Platform-specific URLs
PLATFORM_URLS = {
    "twitter": {
        "compose": "https://twitter.com/intent/tweet",
        "thread": "https://twitter.com/compose/tweet",
    },
    "linkedin": {
        "share": "https://www.linkedin.com/feed/share-offsite/",
        "post": "https://www.linkedin.com/feed/",
    },
    "twitter_reply": {
        "reply": "https://twitter.com/intent/tweet",  
    },
    "reddit": {
        "submit": "https://www.reddit.com/submit",
    },
    "qa": {
        "stackoverflow": "https://stackoverflow.com/questions",
    },
}

# Content type labels
TYPE_LABELS = {
    "reddit": "🤖 Reddit Draft",
    "qa": "📚 Q&A Draft",
    "linkedin": "💼 LinkedIn Draft",
    "twitter": "🐦 Twitter Draft",
    "twitter_reply": "🐦 Twitter Reply",
}


def build_post_url(content_type, text, url=None, title=None):
    """Build the platform's compose/submit URL."""
    if content_type == "twitter":
        # Twitter intent URL (opens compose with pre-filled text)
        tweet = text.split("\n\n---")[0].strip()  # First tweet if thread
        if len(tweet) > 280:
            tweet = tweet[:277] + "..."
        return f"https://twitter.com/intent/tweet?text={quote(tweet)}"

    if content_type == "linkedin":
        if url:
            return f"https://www.linkedin.com/feed/share-offsite/?url={quote(url)}"
        return "https://www.linkedin.com/feed/"

    if content_type == "reddit":
        if url:
            # If it's a Reddit post URL, open the comment page
            return url
        return "https://www.reddit.com/r/tradeFinance/submit"

    if content_type == "qa":
        if url:
            return url
        return "https://stackoverflow.com/questions"

    return ""


def send_message(text, content_type="guide", buttons=None):
    """Send message with optional inline keyboard buttons (resilient)."""
    token = BOT_TOKENS.get(content_type, BOT_TOKENS["guide"])

    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "disable_web_page_preview": True,
    }

    if buttons:
        payload["reply_markup"] = json.dumps({
            "inline_keyboard": buttons,
        })

    r = telegram_post(token, "sendMessage", payload, desc=f"forward:{content_type}")
    ok = r is not None and r.status_code == 200 and r.json().get("ok")
    record_telemetry({"event": "forward", "type": content_type, "ok": bool(ok),
                       "title": (text.split("\n", 1)[0][:100])})
    return ok


def forward_file(filepath, content_type):
    """Forward a draft file to Telegram with Open & Post button."""
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        return False

    label = TYPE_LABELS.get(content_type, "📄 Draft")
    filename = os.path.basename(filepath)
    content = open(filepath, encoding="utf-8").read()

    # Load metadata
    meta_path = filepath.rsplit(".", 1)[0] + ".json"
    meta = {}
    if os.path.exists(meta_path):
        meta = json.loads(open(meta_path, encoding="utf-8").read())

    title = meta.get("title", filename)[:100]
    url = meta.get("url", meta.get("guide_url", ""))
    post_url = build_post_url(content_type, content, url, title)

    # Format message
    msg = f"<b>{label}</b>\n\n"

    if content_type == "twitter":
        msg += f"<b>Tweet:</b>\n<code>{content[:280]}</code>\n\n"
        if len(content) > 280:
            msg += f"({len(content)} chars — may need trimming)\n\n"
    elif content_type == "linkedin":
        msg += f"<b>Post:</b>\n{content[:500]}\n\n"
        if len(content) > 500:
            msg += f"... ({len(content)} chars total)\n\n"
    else:
        msg += f"{content[:1000]}\n\n"
        if len(content) > 1000:
            msg += f"... ({len(content)} chars total)\n\n"

    if url:
        msg += f"<b>Source:</b> {url}\n"

    # Build buttons
    buttons = []
    if post_url:
        buttons.append([{"text": "📝 Open & Post", "url": post_url}])
    # Short hash callback; the filename is resolved through the pending map.
    fid = store_pending_id(content_type, filename)
    buttons.append([{"text": "📋 Copy Text", "callback_data": f"copy_{content_type}_{fid}"}])

    ok = send_message(msg, content_type=content_type, buttons=buttons)
    print(f"{'✓' if ok else '✗'} {label}: {title[:50]}")
    return ok


def test_connection():
    """Test all bot connections."""
    for name, token in BOT_TOKENS.items():
        r = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=10)
        if r.status_code == 200:
            bot = r.json().get("result", {})
            print(f"✓ @{bot.get('username'):30s} {bot.get('first_name')}")
        else:
            print(f"✗ {name}: ERROR {r.status_code}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Forward drafts to Telegram")
    parser.add_argument("type", nargs="?", help="Content type (reddit/qa/linkedin/twitter)")
    parser.add_argument("filename", nargs="?", help="File to forward")
    parser.add_argument("--test", action="store_true", help="Test connectivity")
    args = parser.parse_args()

    if args.test:
        print("Bot connections:")
        test_connection()
        return

    if not args.type or not args.filename:
        parser.print_help()
        return

    forward_file(args.filename, args.type)


if __name__ == "__main__":
    main()
