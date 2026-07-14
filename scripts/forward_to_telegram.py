#!/usr/bin/env python3
"""
Generic Telegram forwarder with Open & Post / Open & Reply buttons.

Tokens are read from ENVIRONMENT VARIABLES (CGE_TG_*), never hardcoded.
Create a local gitignored config/bots.yaml if you prefer files — see
references/telegram_setup.md.

Usage:
    python forward_to_telegram.py linkedin path/to/draft.txt
    python forward_to_telegram.py twitter path/to/draft.txt
    python forward_to_telegram.py reddit  path/to/draft.txt
    python forward_to_telegram.py qa      path/to/draft.txt
    python forward_to_telegram.py approvals path/to/guide.txt
    python forward_to_telegram.py --test
"""
import os
import re
import sys
import json
import urllib.parse
import urllib.request
from pathlib import Path

# --- Bot token resolution (env only) -----------------------------------------
TOKEN_ENV = {
    "linkedin": "CGE_TG_LINKEDIN",
    "twitter": "CGE_TG_TWITTER",
    "reddit": "CGE_TG_REDDIT",
    "qa": "CGE_TG_QA",
    "approvals": "CGE_TG_APPROVALS",
}
CHAT_ID = os.environ.get("CGE_TG_CHAT", os.environ.get("CGE_TG_CHAT_ID", ""))

LABELS = {
    "linkedin": "💼 LinkedIn Draft",
    "twitter": "🐦 Twitter Draft",
    "reddit": "🤖 Reddit Draft",
    "qa": "📚 Q&A Draft",
    "approvals": "📝 Guide Draft",
}

# Per-platform "open" target. For posts we deep-link to the compose page; the
# actual text is copied via the Copy button (Telegram inline keyboards can't
# pre-fill cross-app). For replies we open the source URL.
OPEN_TARGET = {
    "linkedin": "https://www.linkedin.com/feed/",
    "twitter": "https://twitter.com/intent/tweet",
    "reddit": "https://www.reddit.com/",
    "qa": "https://stackoverflow.com/",
}


def _load_yaml_bots():
    """Optional: read config/bots.yaml from repo root if present + gitignored."""
    p = Path(os.environ.get("CGE_CONFIG_DIR", ".")) / "config" / "bots.yaml"
    if not p.exists():
        return {}
    try:
        import yaml
        data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        return {k: v for k, v in data.items() if k.endswith("_token")}
    except Exception:
        return {}


def get_token(platform: str) -> str:
    env = TOKEN_ENV.get(platform)
    if env and os.environ.get(env):
        return os.environ[env]
    # fallback to optional yaml
    y = _load_yaml_bots()
    key = f"CGE_TG_{platform.upper()}"
    if key in y:
        return y[key]
    raise SystemExit(
        f"✗ No token for '{platform}'. Set env {TOKEN_ENV.get(platform,'')} "
        f"or add it to config/bots.yaml (gitignored)."
    )


def send_message(token: str, chat_id: str, text: str, reply_markup=None) -> dict:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))


def build_keyboard(platform: str, post_url: str = None):
    """Open & Post / Open & Reply button + Copy Text button."""
    if platform in ("reddit", "qa"):
        label, target = "📝 Open & Post", post_url or OPEN_TARGET.get(platform)
    elif platform == "twitter":
        label, target = "📝 Open & Post", "https://twitter.com/intent/tweet"
    elif platform == "linkedin":
        label, target = "📝 Open & Post", "https://www.linkedin.com/feed/"
    else:
        label, target = "📝 Open", post_url or "https://guides.example.com"
    return {
        "inline_keyboard": [
            [
                {"text": label, "url": target},
                {"text": "📋 Copy Text", "callback_data": "copy_text"},
            ]
        ]
    }


def forward(platform: str, filepath: str):
    token = get_token(platform)
    if not CHAT_ID:
        raise SystemExit("✗ Set CGE_TG_CHAT (your Telegram chat id).")
    p = Path(filepath)
    if not p.exists():
        raise SystemExit(f"✗ File not found: {filepath}")
    body = p.read_text(encoding="utf-8")

    # extract source url if present (reddit/qa drafts embed it)
    url_match = re.search(r"(https?://\S+)", body)
    post_url = url_match.group(1) if url_match else None

    header = f"*{LABELS.get(platform, 'Draft')}*\n\n"
    # Telegram message cap 4096; if longer, send file as document
    if len(header + body) > 3800:
        # send document
        url = f"https://api.telegram.org/bot{token}/sendDocument"
        import io
        doc = io.BytesIO(body.encode("utf-8"))
        doc.name = p.name
        data = urllib.parse.urlencode({"chat_id": CHAT_ID}).encode()
        # multipart
        import requests
        requests.post(url, data={"chat_id": CHAT_ID},
                      files={"document": (p.name, doc.getvalue(), "text/plain")})
        print(f"✓ {LABELS.get(platform,'Draft')} (sent as document): {p.name}")
        return

    kb = build_keyboard(platform, post_url)
    send_message(token, CHAT_ID, header + body, kb)
    print(f"✓ {LABELS.get(platform,'Draft')}: {p.name}")


def test_all():
    print("Telegram token check (env only):")
    for plat, env in TOKEN_ENV.items():
        tok = os.environ.get(env)
        if tok:
            try:
                import urllib.request, json
                with urllib.request.urlopen(
                    f"https://api.telegram.org/bot{tok}/getMe", timeout=10
                ) as r:
                    j = json.loads(r.read())
                    uname = j.get("result", {}).get("username", "?")
                print(f"  ✓ {plat:10s} @{uname}  [{env}]")
            except Exception as e:
                print(f"  ✗ {plat:10s} {env} invalid ({e})")
        else:
            print(f"  - {plat:10s} {env} not set")
    print(f"\nCGE_TG_CHAT: {'set' if CHAT_ID else 'NOT SET'}")


if __name__ == "__main__":
    if "--test" in sys.argv:
        test_all()
        sys.exit(0)
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    forward(sys.argv[1], sys.argv[2])
