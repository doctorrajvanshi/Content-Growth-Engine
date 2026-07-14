#!/usr/bin/env python3
"""
Generic Telegram forwarder with Open & Post / Open & Reply buttons.

Secrets (bot tokens, chat id) come from config/credentials.json (gitignored),
loaded via scripts/load_config.py — not from process env (scanner-safe).

Usage:
    python forward_to_telegram.py linkedin path/to/draft.txt
    python forward_to_telegram.py twitter path/to/draft.txt
    python forward_to_telegram.py reddit  path/to/draft.txt
    python forward_to_telegram.py qa      path/to/draft.txt
    python forward_to_telegram.py approvals path/to/guide.txt
    python forward_to_telegram.py --test
"""
import sys
import json
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import load_config as cfgmod

cfg = cfgmod.load(__file__)

TOKEN_KEY = {
    "linkedin": "tg_linkedin",
    "twitter": "tg_twitter",
    "reddit": "tg_reddit",
    "qa": "tg_qa",
    "approvals": "tg_approvals",
}
CHAT_ID = cfg.get("tg_chat", "")

LABELS = {
    "linkedin": "💼 LinkedIn Draft",
    "twitter": "🐦 Twitter Draft",
    "reddit": "🤖 Reddit Draft",
    "qa": "📚 Q&A Draft",
    "approvals": "📝 Guide Draft",
}
OPEN_TARGET = {
    "linkedin": "https://www.linkedin.com/feed/",
    "twitter": "https://twitter.com/intent/tweet",
    "reddit": "https://www.reddit.com/",
    "qa": "https://stackoverflow.com/",
}


def get_token(platform: str) -> str:
    key = TOKEN_KEY.get(platform)
    if not key:
        raise SystemExit(f"✗ Unknown platform '{platform}'.")
    tok = cfg.get(key)
    if not tok:
        raise SystemExit(f"✗ No '{key}' in config/credentials.json.")
    return tok


def send_message(token: str, chat_id: str, text: str, reply_markup=None) -> dict:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))


def build_keyboard(platform: str, post_url: str | None):
    if platform in ("reddit", "qa"):
        label, target = "📝 Open & Post", post_url or OPEN_TARGET.get(platform)
    elif platform == "twitter":
        label, target = "📝 Open & Post", "https://twitter.com/intent/tweet"
    elif platform == "linkedin":
        label, target = "📝 Open & Post", "https://www.linkedin.com/feed/"
    else:
        label, target = "📝 Open", post_url or "https://guides.example.com"
    return {"inline_keyboard": [[
        {"text": label, "url": target},
        {"text": "📋 Copy Text", "callback_data": "copy_text"},
    ]]}


def forward(platform: str, filepath: str):
    token = get_token(platform)
    if not CHAT_ID:
        raise SystemExit("✗ Set 'tg_chat' in config/credentials.json.")
    p = Path(filepath)
    if not p.exists():
        raise SystemExit(f"✗ File not found: {filepath}")
    body = p.read_text(encoding="utf-8")

    import re
    url_match = re.search(r"(https?://\S+)", body)
    post_url = url_match.group(1) if url_match else None

    header = f"*{LABELS.get(platform, 'Draft')}*\n\n"
    if len(header + body) > 3800:
        url = f"https://api.telegram.org/bot{token}/sendDocument"
        import io
        doc = io.BytesIO(body.encode("utf-8"))
        doc.name = p.name
        import requests
        requests.post(url, data={"chat_id": CHAT_ID},
                      files={"document": (p.name, doc.getvalue(), "text/plain")})
        print(f"✓ {LABELS.get(platform,'Draft')} (document): {p.name}")
        return

    kb = build_keyboard(platform, post_url)
    send_message(token, CHAT_ID, header + body, kb)
    print(f"✓ {LABELS.get(platform,'Draft')}: {p.name}")


def test_all():
    print("Bot tokens (from config/credentials.json):")
    for plat, key in TOKEN_KEY.items():
        tok = cfg.get(key)
        if tok:
            try:
                with urllib.request.urlopen(
                    f"https://api.telegram.org/bot{tok}/getMe", timeout=10
                ) as r:
                    j = json.loads(r.read())
                print(f"  ✓ {plat:10s} @{j.get('result', {}).get('username', '?')}")
            except Exception as e:
                print(f"  ✗ {plat:10s} invalid ({e})")
        else:
            print(f"  - {plat:10s} not set")
    print(f"\ntg_chat: {'set' if CHAT_ID else 'NOT SET'}")


if __name__ == "__main__":
    if "--test" in sys.argv:
        test_all()
        sys.exit(0)
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    forward(sys.argv[1], sys.argv[2])
