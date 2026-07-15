#!/usr/bin/env python3
"""
fetch_url_context.py — fetch and extract readable text from a social/post URL.

STRICTLY READ-ONLY. Uses Playwright (headless Chromium) to render JS-gated
pages (Reddit, Twitter/X, LinkedIn, StackOverflow, generic). It only ever
READS page text (inner_text / text_content). It never fills inputs, clicks
compose buttons, or submits forms. Safe for use with a logged-in test profile.

Session cookies are loaded from .pw_cookies/<platform>_cookies.txt (Netscape
format) in READ-ONLY mode — cookies are loaded into the context, never
modified or written back.

Usage:
    python fetch_url_context.py <url>
    python fetch_url_context.py <url>  # cookies auto-loaded from .pw_cookies/
"""
import sys
import os
import re
import json
import time

# Optional Netscape cookie jars (one per platform), filled by the user.
COOKIE_DIR = os.environ.get("PLAYWRIGHT_COOKIE_DIR", os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", ".pw_cookies"))
COOKIE_FILES = {
    "reddit.com":      os.path.join(COOKIE_DIR, "reddit_cookies.txt"),
    "twitter.com":     os.path.join(COOKIE_DIR, "twitter_cookies.txt"),
    "x.com":           os.path.join(COOKIE_DIR, "twitter_cookies.txt"),
    "linkedin.com":    os.path.join(COOKIE_DIR, "linkedin_cookies.txt"),
    "stackoverflow.com": os.path.join(COOKIE_DIR, "stackoverflow_cookies.txt"),
}


def load_netscape_cookies(context, host):
    """Read a Netscape-format cookies.txt for the host and add to context.
    READ-ONLY: cookies are loaded, never modified or written back."""
    path = COOKIE_FILES.get(host)
    if not path or not os.path.exists(path):
        return 0
    cookies = []
    for line in open(path, encoding="utf-8", errors="ignore"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 7:
            continue
        domain, _, path_, secure, expiry, name, value = parts[:7]
        cookies.append({
            "name": name, "value": value, "domain": domain.lstrip("."),
            "path": path_ or "/", "secure": secure.lower() == "true",
            "expires": int(expiry) if expiry.isdigit() else None,
        })
    if cookies:
        try:
            context.add_cookies(cookies)
        except Exception as e:
            print(f"  ! cookie load warn ({host}): {e}")
    return len(cookies)

# Read-only selectors per platform (grab the post/thread body)
SELECTORS = {
    "reddit.com":      ["shreddit-post", "div[data-testid='post-container']", "article"],
    "twitter.com":     ["article", "div[data-testid='tweetText']"],
    "x.com":           ["article", "div[data-testid='tweetText']"],
    "linkedin.com":    ["div.feed-shared-update-v2", "article"],
    "stackoverflow.com":["div.question", "div.answer"],
}

def extract_with_playwright(url):
    """Render the page headlessly and return its text. READ-ONLY."""
    from playwright.sync_api import sync_playwright
    from urllib.parse import urlparse
    host = urlparse(url).netloc.lower().replace("www.", "")

    text_parts = []
    title = ""
    author = ""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = browser.new_context()
        # Inject user-provided session cookies (read-only) for this host
        n = load_netscape_cookies(context, host)
        page = context.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(2000)  # let JS hydrate

        title = page.title()
        # Try platform-specific selectors first
        for sel in SELECTORS.get(host, []):
            try:
                nodes = page.query_selector_all(sel)
                if nodes:
                    for n in nodes[:5]:
                        t = n.inner_text()
                        if t:
                            text_parts.append(t)
                    break
            except Exception:
                continue
        # Fallback: whole body
        if not text_parts:
            try:
                text_parts.append(page.inner_text("body"))
            except Exception:
                pass
        # Try to find an author handle
        try:
            a = page.query_selector("a[href*='/user/'], a[href*='/profile/'], span[dir='auto'][title]")
            if a:
                author = a.inner_text()
        except Exception:
            pass
        browser.close()

    text = "\n\n".join(p for p in text_parts if p).strip()

    # Detect bot-wall / challenge pages so callers can fall back to paste-text
    block_markers = [
        "blocked by network security",
        "just a moment",
        "performing security verification",
        "verify you are human",
        "are you a robot",
        "enable javascript and cookies to continue",
    ]
    is_blocked = any(m in text.lower() for m in block_markers)
    # Login page with no feed content also means session didn't persist
    looks_logged_out = ("sign in" in text.lower() and "join now" in text.lower())

    return {
        "title": title,
        "text": "" if (is_blocked or looks_logged_out) else text[:8000],
        "author": author.strip(),
        "url": url,
        "site": host,
        "method": "playwright",
        "blocked": is_blocked,
        "logged_out": looks_logged_out,
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: fetch_url_context.py <url>")
        sys.exit(1)
    url = sys.argv[1]
    if not url.startswith("http"):
        print(json.dumps({"error": "not a url"}))
        sys.exit(1)
    try:
        ctx = extract_with_playwright(url)
    except Exception as e:
        # Fallback to the old HTTP method if Playwright fails
        ctx = _http_fallback(url)
        if ctx is None:
            print(json.dumps({"error": f"fetch failed: {e}"}))
            sys.exit(1)
    print(json.dumps(ctx, ensure_ascii=False)[:5000])


def _http_fallback(url):
    """Last-resort plain HTTP fetch (no JS)."""
    import requests
    from urllib.parse import urlparse
    try:
        r = requests.get(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 Chrome/120 Safari/537.36"}, timeout=20)
        if r.status_code != 200:
            return None
        html = r.text
        html = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.I | re.S)
        html = re.sub(r"<style[^>]*>.*?</style>", " ", html, flags=re.I | re.S)
        html = re.sub(r"<[^>]+>", " ", html)
        html = re.sub(r"&[a-z]+;", " ", html)
        html = re.sub(r"\s+", " ", html).strip()
        return {"title": "", "text": html[:6000], "author": "",
                "url": url, "site": urlparse(url).netloc, "method": "http"}
    except Exception:
        return None


if __name__ == "__main__":
    main()
