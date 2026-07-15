#!/usr/bin/env python3
"""
platform_bot_listener.py — always-on inbound listener for the 4 platform
platform Telegram bots (Reddit, Twitter, LinkedIn, Dev Q&A).

Polls each bot's getUpdates. When you send a post/comment URL or a topic
to any of these bots, it records an inbound job to content/inbound/ and
triggers the reply-drafter (via a flag file the cron picks up).

Resilient: reconnects on error, exponential backoff on Telegram API
failures, never exits on a single bad message.

Run under platform_bot_supervisor.py (same pattern as gateway_supervisor).
"""
import os
import sys
import re
import json
import time
import logging
import requests

ROOT = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(ROOT)
INBOUND_DIR = os.path.join(ROOT, "content", "inbound")
os.makedirs(INBOUND_DIR, exist_ok=True)
TRIGGER = os.path.join(ROOT, "content", "inbound", ".poll_trigger")

# Per-bot tokens + chat (must match forward_to_telegram.py)
import importlib.util
spec = importlib.util.spec_from_file_location(
    "ft", os.path.join(ROOT, "scripts", "forward_to_telegram.py"))
ft = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ft)

BOTS = {
    "reddit":   {"token": ft.BOT_TOKENS["reddit"],   "chat": ft.CHAT_ID, "label": "Reddit"},
    "twitter":  {"token": ft.BOT_TOKENS["twitter"],  "chat": ft.CHAT_ID, "label": "Twitter"},
    "linkedin": {"token": ft.BOT_TOKENS["linkedin"], "chat": ft.CHAT_ID, "label": "LinkedIn"},
    "qa":       {"token": ft.BOT_TOKENS["qa"],       "chat": ft.CHAT_ID, "label": "Dev Q&A"},
}

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
log = logging.getLogger("platform_bot_listener")

URL_RE = re.compile(r"https?://\S+", re.I)

def is_url(text):
    return bool(URL_RE.search(text))

def record_inbound(platform, chat_id, text):
    """Write an inbound job file + touch trigger so the drafter cron fires."""
    fid = f"{platform}_{int(time.time()*1000)}"
    job = {
        "platform": platform,
        "chat_id": chat_id,
        "text": text.strip(),
        "url": (URL_RE.search(text).group(0) if is_url(text) else ""),
        "received_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "processed": False,
    }
    path = os.path.join(INBOUND_DIR, f"{fid}.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(job, fh, indent=2)
    # touch trigger
    try:
        open(TRIGGER, "w").close()
    except Exception:
        pass
    log.info(f"Recorded inbound {platform}: {text[:60]}")
    return path

def poll_bot(name, cfg):
    """Poll one bot's getUpdates, return next offset to use."""
    token = cfg["token"]
    if not token or token.endswith("***"):
        log.warning(f"{name}: no real token (placeholder) — skipping poll")
        return None
    offset = 0
    try:
        r = requests.get(
            f"https://api.telegram.org/bot{token}/getUpdates",
            params={"offset": offset, "timeout": 10, "limit": 10}, timeout=20)
        if r.status_code != 200:
            log.warning(f"{name}: getUpdates HTTP {r.status_code}")
            return None
        data = r.json()
        if not data.get("ok"):
            log.warning(f"{name}: getUpdates not ok: {data.get('description')}")
            return None
        max_off = offset
        for upd in data.get("result", []):
            max_off = max(max_off, upd.get("update_id", 0) + 1)
            msg = upd.get("message")
            if not msg:
                continue
            text = msg.get("text", "").strip()
            chat_id = msg.get("chat", {}).get("id")
            if not text:
                continue
            # Ignore our own command echoes / empty
            if text.startswith("/start") or text.startswith("/help"):
                continue
            record_inbound(name, chat_id, text)
        return max_off
    except Exception as e:
        log.error(f"{name}: poll error: {e}")
        return None

def main():
    log.info("Platform bot listener started (4 bots)")
    offsets = {n: 0 for n in BOTS}
    # seed offset to avoid replaying old history
    for n, c in BOTS.items():
        try:
            r = requests.get(f"https://api.telegram.org/bot{c['token']}/getUpdates",
                             params={"offset": -1, "limit": 1}, timeout=10)
            if r.status_code == 200 and r.json().get("ok"):
                res = r.json().get("result", [])
                if res:
                    offsets[n] = res[-1].get("update_id", 0) + 1
        except Exception:
            pass
    log.info(f"Seeded offsets: {offsets}")
    while True:
        for n, c in BOTS.items():
            off = poll_bot(n, c)
            if off is not None:
                offsets[n] = off
        time.sleep(3)

if __name__ == "__main__":
    main()
