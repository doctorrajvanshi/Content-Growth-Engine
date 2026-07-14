#!/usr/bin/env python3
"""
Generic reply drafter.

Given a post URL or raw text, draft a reply that links to the most relevant
local guide. Pure local logic + optional Twitter API fetch (token from env).
No hardcoded product/domain.

Usage:
    python reply_drafter.py twitter "https://twitter.com/u/status/123"
    python reply_drafter.py twitter "what happens if documents are late?"
    python reply_drafter.py linkedin "https://linkedin.com/feed/update/..."
    python reply_drafter.py linkedin "Our bank rejected the certificate..."
"""
import os
import re
import sys
import json
import glob
import urllib.parse
from pathlib import Path

CGE_DIR = Path(os.environ.get("CGE_REPO", "."))
DOMAIN = os.environ.get("CGE_SITE_DOMAIN", "https://guides.example.com")
LIBRARY = CGE_DIR / "knowledge-engine" / "trade_rules_library"
TOKEN_ENV = "CGE_TWITTER_BEARER"


def get_tweet(tweet_id: str):
    tok = os.environ.get(TOKEN_ENV, "")
    if not tok:
        return None
    try:
        import urllib.request
        url = f"https://api.twitter.com/2/tweets/{tweet_id}?tweet.fields=text,author_id&expansions=author_id&user.fields=username"
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {tok}"})
        with urllib.request.urlopen(req, timeout=10) as r:
            j = json.loads(r.read())
        tw = j.get("data", {})
        users = {u["id"]: u for u in j.get("includes", {}).get("users", [])}
        a = users.get(tw.get("author_id"), {})
        return {"text": tw.get("text", ""), "author": a.get("username", "i"),
                "url": f"https://twitter.com/{a.get('username','i')}/status/{tweet_id}"}
    except Exception:
        return None


def search_guides(query: str, max_n: int = 1):
    words = [w for w in re.findall(r"\w+", query.lower()) if len(w) > 3]
    scored = []
    for md in glob.glob(str(LIBRARY / "*.md")):
        txt = Path(md).read_text(encoding="utf-8").lower()
        score = sum(1 for w in words if w in txt)
        if score >= 2:
            slug = re.sub(r"^\d{4}-\d{2}-\d{2}_", "", Path(md).stem)
            scored.append((score, slug, md))
    scored.sort(reverse=True)
    return scored[:max_n]


def draft(text: str, platform: str) -> str:
    hits = search_guides(text)
    if hits:
        slug = hits[0][1]
        url = f"{DOMAIN}/{slug}"
        # grab one insight sentence from the guide
        body = Path(hits[0][2]).read_text(encoding="utf-8")
        insight = re.split(r"(?<=[.!?])\s+", re.sub(r"[#*_`]", "", body))[2:4]
        insight = " ".join(insight)[:180]
        reply = f"Good question. {insight}\n\nDetailed guidance: {url}"
    else:
        reply = f"Related guidance: {DOMAIN}"
    if platform == "twitter" and len(reply) > 280:
        reply = reply[:277] + "…"
    return reply


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    platform, inp = sys.argv[1], sys.argv[2]
    text, url = inp, None
    if inp.startswith("http"):
        url = inp
        m = re.search(r"/status/(\d+)", inp)
        if m and platform == "twitter":
            tw = get_tweet(m.group(1))
            if tw:
                text = tw["text"]
    reply = draft(text, platform)
    print(reply)
    # forward to telegram
    sys.path.insert(0, str(Path(__file__).parent))
    import forward_to_telegram as ft
    out_dir = CGE_DIR / "content" / "replies"
    out_dir.mkdir(parents=True, exist_ok=True)
    tmp = out_dir / f"reply_{platform}_{abs(hash(text)) % 100000}.txt"
    tmp.write_text(reply, encoding="utf-8")
    ft.forward(platform, str(tmp))


if __name__ == "__main__":
    main()
