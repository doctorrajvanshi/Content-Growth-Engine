#!/usr/bin/env python3
"""
replay_dead_letters.py — automated replay of failed Telegram sends.

Scans dead-letter queues written by telegram_gateway.py and
forward_to_telegram.py, re-attempts each POST against the Telegram
Bot API, and on success moves the file to a `replayed/` archive.

Differences handled:
  - Gateway dead-letters use form-encoded `data` (Telegram sendMessage
    with data=).
  - Forwarder dead-letters use JSON `payload` (requests.post json=payload).

Run manually, or via the scheduled cron (every 30 min).
"""
import os
import sys
import json
import time
import shutil

ROOT = os.path.dirname(os.path.abspath(__file__))
# Resolve both dead-letter dirs regardless of where the script lives.
CANDIDATES = [
    os.path.join(ROOT, "dead_letter"),                 # scripts/dead_letter (forwarder)
    os.path.join(ROOT, "telegram_gateway", "dead_letter"),  # if script run from repo root
    os.path.join(os.path.dirname(ROOT), "telegram_gateway", "dead_letter"),  # gateway dead-letter
]
# Ensure the gateway dead-letter dir exists (it is created lazily by the
# gateway only on first failure); create proactively so replay can see it.
for _d in CANDIDATES:
    try:
        os.makedirs(_d, exist_ok=True)
    except Exception:
        pass
DEAD_DIRS = [d for d in CANDIDATES if os.path.isdir(d)]

# Max age before we stop retrying (hours). Old failures are archived without
# retry to avoid replay storms on permanently broken payloads.
MAX_AGE_HOURS = 72

import requests

def replay_file(path):
    """Re-attempt one dead-letter file. Returns 'ok', 'fail', or 'skip'."""
    try:
        rec = json.loads(open(path, encoding="utf-8").read())
    except Exception as e:
        print(f"  ! unreadable {os.path.basename(path)}: {e}")
        return "skip"

    # Age gate
    failed_at = rec.get("failed_at")
    if failed_at:
        try:
            from datetime import datetime, timezone
            ft = datetime.fromisoformat(failed_at.replace("Z", "+00:00"))
            age_h = (datetime.now(timezone.utc) - ft).total_seconds() / 3600
            if age_h > MAX_AGE_HOURS:
                print(f"  ~ too old ({age_h:.0f}h) -> archive w/o retry: {os.path.basename(path)}")
                return "archive"
        except Exception:
            pass

    endpoint = rec.get("endpoint", "sendMessage")
    token = None
    # Gateway records the bot token implicitly via the gateway TOKEN; forwarder
    # does not store the token, so we resolve it from BOT_TOKENS by type.
    desc = rec.get("desc", "")
    if "data" in rec:
        # Gateway format: form-encoded, token embedded in the record.
        token = rec.get("token")
        body = rec["data"]
        post_kwargs = {"data": body}
    elif "payload" in rec:
        # Forwarder format: JSON, per-type token from BOT_TOKENS.
        body = rec["payload"]
        ctype = "guide"
        for k in ("reddit", "qa", "linkedin", "twitter", "guide"):
            if k in desc:
                ctype = k
                break
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                "ft", os.path.join(ROOT, "forward_to_telegram.py"))
            ft = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(ft)
            token = ft.BOT_TOKENS.get(ctype, ft.BOT_TOKENS["guide"])
        except Exception:
            token = None
        post_kwargs = {"json": body}
    else:
        print(f"  ! unknown format: {os.path.basename(path)}")
        return "skip"

    if not token:
        print(f"  ! no token for {os.path.basename(path)}")
        return "skip"

    url = f"https://api.telegram.org/bot{token}/{endpoint}"
    try:
        r = requests.post(url, timeout=15, **post_kwargs)
        if r.status_code == 200 and r.json().get("ok"):
            print(f"  ✓ replayed: {os.path.basename(path)} ({desc})")
            return "ok"
        print(f"  ! still failing ({r.status_code}): {os.path.basename(path)}")
        return "fail"
    except Exception as e:
        print(f"  ! error replaying {os.path.basename(path)}: {e}")
        return "fail"


def main():
    if not DEAD_DIRS:
        print("No dead-letter directories found.")
        return
    print(f"Scanning dead-letter dirs: {len(DEAD_DIRS)}")
    ok = fail = skip = archive = 0
    for d in DEAD_DIRS:
        files = [f for f in os.listdir(d) if f.endswith(".json")]
        if not files:
            continue
        print(f"\n[{d}] {len(files)} pending")
        replay_dir = os.path.join(d, "replayed")
        archive_dir = os.path.join(d, "archived")
        os.makedirs(replay_dir, exist_ok=True)
        os.makedirs(archive_dir, exist_ok=True)
        for f in sorted(files):
            p = os.path.join(d, f)
            res = replay_file(p)
            if res == "ok":
                shutil.move(p, os.path.join(replay_dir, f)); ok += 1
            elif res == "archive":
                shutil.move(p, os.path.join(archive_dir, f)); archive += 1
            elif res == "skip":
                skip += 1
            else:
                fail += 1
    print(f"\nReplay summary: ok={ok} fail={fail} archived={archive} skipped={skip}")


if __name__ == "__main__":
    main()
