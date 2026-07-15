#!/usr/bin/env python3
"""
IndexNow URL Submission Script
================================
Submits compliance guide URLs to the IndexNow API for instant
indexing across Bing, Yandex, Naver, Seznam, and other IndexNow participants.

IndexNow supports bulk submission of up to 10,000 URLs per request.

Usage:
    python submit_indexnow.py                   # Submit all URLs
    python submit_indexnow.py --dry-run         # Preview without submitting
    python submit_indexnow.py --limit 500       # Submit only first 500 URLs
"""

import argparse
import json
import os
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

try:
    import requests
except ImportError:
    print("[ERROR] 'requests' package required. Install with: pip install requests")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
DEFAULT_SITEMAP = os.environ.get("SITEMAP_PATH", "./dist/compliance-guides/sitemap.xml")
DEFAULT_KEY_FILE = os.environ.get("INDEXNOW_KEY_FILE", "./indexnow_key.txt")
INDEXNOW_ENDPOINT = "https://api.indexnow.org/indexnow"
DOMAIN = os.environ.get("SITE_DOMAIN", "guides.yourproduct.com")
SITEMAP_NS = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
MAX_BULK_URLS = 10_000  # IndexNow API limit per request


def parse_sitemap(sitemap_path: str) -> list[str]:
    """Extract all <loc> URLs from a sitemap.xml file."""
    tree = ET.parse(sitemap_path)
    root = tree.getroot()
    urls = [loc.text for loc in root.findall(".//s:loc", SITEMAP_NS) if loc.text]
    return urls


def load_api_key(key_path: str) -> str:
    """Load the IndexNow API key from a text file."""
    with open(key_path, "r", encoding="utf-8") as f:
        return f.read().strip()


def submit_to_indexnow(
    api_key: str,
    urls: list[str],
    dry_run: bool = False,
    domain: str = DOMAIN,
) -> dict:
    """
    Submit a batch of URLs to IndexNow.
    IndexNow accepts up to 10,000 URLs per request.
    """
    if dry_run:
        return {
            "status": "DRY_RUN",
            "url_count": len(urls),
            "urls": urls[:10],
        }

    payload = {
        "host": domain,
        "key": api_key,
        "keyLocation": f"https://{domain}/{api_key}.txt",
        "urlList": urls,
    }

    headers = {"Content-Type": "application/json; charset=utf-8"}

    resp = requests.post(
        INDEXNOW_ENDPOINT,
        json=payload,
        headers=headers,
        timeout=60,
    )

    result = {
        "status_code": resp.status_code,
        "url_count": len(urls),
    }

    # IndexNow returns 200 for accepted, 202 for queued, 400/403/422 for errors
    if resp.status_code in (200, 202):
        result["accepted"] = True
    else:
        result["accepted"] = False
        try:
            result["body"] = resp.json()
        except Exception:
            result["body"] = resp.text

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Submit compliance guide URLs to IndexNow API"
    )
    parser.add_argument(
        "--sitemap",
        default=DEFAULT_SITEMAP,
        help=f"Path to sitemap.xml (default: {DEFAULT_SITEMAP})",
    )
    parser.add_argument(
        "--key-file",
        default=DEFAULT_KEY_FILE,
        help=f"Path to file containing the IndexNow API key (default: {DEFAULT_KEY_FILE})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview URLs without submitting to IndexNow",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=MAX_BULK_URLS,
        help=f"Max URLs to submit (default: {MAX_BULK_URLS} = IndexNow API limit)",
    )
    parser.add_argument(
        "--urls",
        nargs="*",
        help="Submit specific URLs instead of reading from sitemap",
    )
    parser.add_argument(
        "--domain",
        default=DOMAIN,
        help=f"Domain to report to IndexNow (default: yourproject.pages.dev)",
    )
    args = parser.parse_args()

    # --- Load URLs ---
    if args.urls:
        urls = args.urls
    else:
        sitemap_path = args.sitemap
        if not os.path.isfile(sitemap_path):
            print(f"[ERROR] Sitemap not found: {sitemap_path}")
            print("  Ensure the compliance guides build has produced the sitemap.")
            sys.exit(1)
        urls = parse_sitemap(sitemap_path)

    total_urls = len(urls)
    submit_count = min(len(urls), args.limit)

    print(f"{'=' * 60}")
    print(f"IndexNow — URL Submission")
    print(f"{'=' * 60}")
    print(f"  Sitemap:       {args.sitemap}")
    print(f"  Domain:        {DOMAIN}")
    print(f"  Total URLs:    {total_urls}")
    print(f"  Submit count:  {submit_count} (max per request: {MAX_BULK_URLS})")
    print(f"  Dry run:       {args.dry_run}")
    print(f"{'=' * 60}")

    # --- Load API key (skip in dry-run) ---
    api_key = None
    if not args.dry_run:
        key_path = args.key_file
        if not os.path.isfile(key_path):
            print()
            print("[SETUP REQUIRED] IndexNow API key not found.")
            print(f"  Expected at: {key_path}")
            print()
            print("  To configure:")
            print("  1. Generate a random key string (e.g., openssl rand -hex 16)")
            print("  2. Save it to a file at the path above")
            print(f"  3. Host the key file at: https://{DOMAIN}/<your-key>.txt")
            print("     (This proves you own the domain)")
            print("  4. Register at https://www.indexnow.org if needed")
            print()
            print("  Without credentials, use --dry-run to preview submissions.")
            sys.exit(1)

        try:
            api_key = load_api_key(key_path)
        except OSError as e:
            print(f"[ERROR] Could not read API key file: {e}")
            sys.exit(1)

        if not api_key:
            print("[ERROR] API key file is empty.")
            sys.exit(1)

        print(f"  API key:       {api_key[:8]}...{api_key[-4:]} (loaded)")

    print()

    # --- Submit in batches ---
    urls_to_submit = urls[:submit_count]
    batches = []
    for i in range(0, len(urls_to_submit), MAX_BULK_URLS):
        batches.append(urls_to_submit[i : i + MAX_BULK_URLS])

    total_success = 0
    total_errors = 0

    for batch_idx, batch in enumerate(batches, 1):
        batch_start = (batch_idx - 1) * MAX_BULK_URLS + 1
        batch_end = min(batch_idx * MAX_BULK_URLS, submit_count)
        print(f"  Batch {batch_idx}/{len(batches)}: URLs {batch_start}–{batch_end} ({len(batch)} URLs)")

        try:
            result = submit_to_indexnow(api_key or "", batch, dry_run=args.dry_run, domain=args.domain)

            if args.dry_run:
                print(f"    DRY RUN — Would submit {len(batch)} URLs to {DOMAIN}")
                for u in batch[:5]:
                    print(f"      {u}")
                if len(batch) > 5:
                    print(f"      ... and {len(batch) - 5} more")
                total_success += len(batch)
            elif result.get("accepted") or result.get("status_code") in (200, 202):
                print(f"    ✓ Accepted (HTTP {result['status_code']})")
                total_success += len(batch)
            else:
                status = result.get("status_code", "?")
                body = result.get("body", "No response body")
                print(f"    ✗ Rejected (HTTP {status})")
                if isinstance(body, dict):
                    print(f"      {json.dumps(body, indent=6)}")
                else:
                    print(f"      {str(body)[:200]}")
                total_errors += len(batch)

        except requests.exceptions.Timeout:
            print(f"    ✗ Timeout submitting batch")
            total_errors += len(batch)
        except requests.exceptions.ConnectionError as e:
            print(f"    ✗ Connection error: {e}")
            total_errors += len(batch)
        except Exception as e:
            print(f"    ✗ Unexpected error: {e}")
            total_errors += len(batch)

    # --- Summary ---
    print()
    print(f"{'=' * 60}")
    print(f"  Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Accepted:  {total_success} URLs")
    print(f"  Errors:    {total_errors} URLs")
    if not args.dry_run:
        print()
        print("  IndexNow participants (Bing, Yandex, Naver, etc.) will be notified.")
        print("  First-time submissions may take minutes to hours to process.")
    print(f"{'=' * 60}")

    sys.exit(1 if total_errors > 0 and total_success == 0 else 0)


if __name__ == "__main__":
    main()
