#!/usr/bin/env python3
"""
Google Indexing API URL Submission Script
==========================================
Submits URLs from the compliance-guides sitemap to Google's Indexing API.

Google's free tier allows 200 URL submissions per day. This script respects
that limit and tracks submission counts.

Usage:
    python submit_google.py                   # Submit all URLs
    python submit_google.py --dry-run         # Preview without submitting
    python submit_google.py --limit 50        # Submit only first 50 URLs
    python submit_google.py --urls URL1 URL2  # Submit specific URLs
"""

import argparse
import json
import os
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    import requests
except ImportError:
    print("[ERROR] 'requests' package required. Install with: pip install requests")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
DEFAULT_SITEMAP = os.environ.get("SITEMAP_PATH", "./dist/compliance-guides/sitemap.xml")
DEFAULT_SERVICE_ACCOUNT = os.environ.get("GOOGLE_SA_JSON", "./service_account.json")
GOOGLE_INDEXING_API = "https://indexing.googleapis.com/v3/urlNotifications:publish"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
MAX_URLS_PER_DAY = 200  # Google free tier limit
SITEMAP_NS = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}


def parse_sitemap(sitemap_path: str) -> list[str]:
    """Extract all <loc> URLs from a sitemap.xml file."""
    tree = ET.parse(sitemap_path)
    root = tree.getroot()
    urls = [loc.text for loc in root.findall(".//s:loc", SITEMAP_NS) if loc.text]
    return urls


def load_service_account(path: str) -> dict:
    """Load and return the Google service account JSON."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_access_token(service_account: dict) -> Optional[str]:
    """
    Exchange a service account's private key for a short-lived OAuth2 access token
    using the JWT assertion flow.
    """
    try:
        from google.oauth2 import service_account as sa_module
        from google.auth.transport.requests import Request as GoogleRequest

        credentials = sa_module.Credentials.from_service_account_info(
            service_account,
            scopes=["https://www.googleapis.com/auth/indexing"],
        )
        credentials.refresh(GoogleRequest())
        token = credentials.token
        if isinstance(token, bytes):
            token = token.decode("utf-8")
        return token
    except ImportError:
        # Fallback: manual JWT construction
        try:
            import base64
            from cryptography.hazmat.primitives import hashes, serialization
            from cryptography.hazmat.primitives.asymmetric import padding

            now = int(time.time())
            header = base64.urlsafe_b64encode(
                json.dumps({"alg": "RS256", "typ": "JWT"}).encode()
            ).rstrip(b"=")
            payload = base64.urlsafe_b64encode(
                json.dumps(
                    {
                        "iss": service_account["client_email"],
                        "scope": "https://www.googleapis.com/auth/indexing",
                        "aud": GOOGLE_TOKEN_URL,
                        "iat": now,
                        "exp": now + 3600,
                    }
                ).encode()
            ).rstrip(b"=")
            signing_input = header + b"." + payload
            key = serialization.load_pem_private_key(
                service_account["private_key"].encode(), password=None
            )
            signature = key.sign(signing_input, padding.PKCS1v15(), hashes.SHA256())
            jwt_token = signing_input + b"." + base64.urlsafe_b64encode(signature).rstrip(b"=")

            resp = requests.post(
                GOOGLE_TOKEN_URL,
                data={
                    "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                    "assertion": jwt_token.decode(),
                },
                timeout=15,
            )
            resp.raise_for_status()
            return resp.json().get("access_token")
        except Exception as e:
            print(f"[ERROR] Could not obtain access token: {e}")
            return None


def submit_url(url: str, access_token: str, dry_run: bool = False) -> dict:
    """Submit a single URL to Google's Indexing API. Returns response dict."""
    payload = {
        "url": url,
        "type": "URL_UPDATED",
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
    }
    if dry_run:
        return {"status": "DRY_RUN", "url": url}

    resp = requests.post(
        GOOGLE_INDEXING_API,
        json=payload,
        headers=headers,
        timeout=30,
    )
    try:
        return resp.json()
    except Exception:
        return {"error": resp.text, "status_code": resp.status_code}


def main():
    parser = argparse.ArgumentParser(
        description="Submit compliance guide URLs to Google Indexing API"
    )
    parser.add_argument(
        "--sitemap",
        default=DEFAULT_SITEMAP,
        help=f"Path to sitemap.xml (default: {DEFAULT_SITEMAP})",
    )
    parser.add_argument(
        "--service-account",
        default=DEFAULT_SERVICE_ACCOUNT,
        help=f"Path to Google service account JSON (default: {DEFAULT_SERVICE_ACCOUNT})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview URLs without submitting to Google",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=MAX_URLS_PER_DAY,
        help=f"Max URLs to submit (default: {MAX_URLS_PER_DAY} = free tier daily limit)",
    )
    parser.add_argument(
        "--urls",
        nargs="*",
        help="Submit specific URLs instead of reading from sitemap",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.25,
        help="Delay between requests in seconds (default: 0.25)",
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
    print(f"Google Indexing API — URL Submission")
    print(f"{'=' * 60}")
    print(f"  Sitemap:       {args.sitemap}")
    print(f"  Total URLs:    {total_urls}")
    print(f"  Submit limit:  {submit_count} (daily free tier: {MAX_URLS_PER_DAY})")
    print(f"  Dry run:       {args.dry_run}")
    print(f"{'=' * 60}")

    # --- Authenticate (skip in dry-run) ---
    access_token = None
    if not args.dry_run:
        sa_path = args.service_account
        if not os.path.isfile(sa_path):
            print()
            print("[SETUP REQUIRED] Google service account JSON not found.")
            print(f"  Expected at: {sa_path}")
            print()
            print("  To configure:")
            print("  1. Create a Google Cloud project with Indexing API enabled")
            print("  2. Create a service account and download the JSON key")
            print("  3. Place the JSON at the path above, or pass --service-account PATH")
            print("  4. Add the service account email as an owner in Google Search Console")
            print()
            print("  Without credentials, use --dry-run to preview what would be submitted.")
            sys.exit(1)

        try:
            sa = load_service_account(sa_path)
        except (json.JSONDecodeError, OSError) as e:
            print(f"[ERROR] Could not read service account JSON: {e}")
            sys.exit(1)

        access_token = get_access_token(sa)
        if not access_token:
            print("[ERROR] Failed to obtain access token. Check service account credentials.")
            sys.exit(1)
        print("  Auth:          OK (service account token obtained)")

    print()

    # --- Submit ---
    success_count = 0
    error_count = 0
    errors = []

    for i, url in enumerate(urls[:submit_count], 1):
        try:
            result = submit_url(url, access_token or "", dry_run=args.dry_run)
            status = result.get("urlNotificationMetadata", {}).get(
                "latestUpdate", {}
            ).get("status") or result.get("status", "UNKNOWN")

            if args.dry_run:
                print(f"  [{i}/{submit_count}] DRY RUN: {url}")
                success_count += 1
            elif "error" in result:
                error_count += 1
                errors.append((url, result["error"]))
                print(f"  [{i}/{submit_count}] ERROR: {url}")
                print(f"         {result['error']}")
            else:
                success_count += 1
                if i % 10 == 0 or i == submit_count:
                    print(f"  [{i}/{submit_count}] Submitted OK — {url[:70]}...")

            # Rate-limit: small delay between requests
            if not args.dry_run and i < submit_count:
                time.sleep(args.delay)

        except requests.exceptions.Timeout:
            error_count += 1
            errors.append((url, "Timeout"))
            print(f"  [{i}/{submit_count}] TIMEOUT: {url}")
        except requests.exceptions.ConnectionError as e:
            error_count += 1
            errors.append((url, f"Connection error: {e}"))
            print(f"  [{i}/{submit_count}] CONNECTION ERROR: {url}")
            print(f"         {e}")
            # Don't spam retries on connection failures
            if error_count > 3:
                print()
                print("[ABORT] Multiple connection failures. Aborting to avoid spam.")
                break
        except Exception as e:
            error_count += 1
            errors.append((url, str(e)))
            print(f"  [{i}/{submit_count}] UNEXPECTED ERROR: {url}")
            print(f"         {e}")

    # --- Summary ---
    print()
    print(f"{'=' * 60}")
    print(f"  Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Success:   {success_count}")
    print(f"  Errors:    {error_count}")
    if errors:
        print()
        print("  Error details:")
        for url, err in errors[:10]:
            print(f"    {url}")
            print(f"      → {err}")
        if len(errors) > 10:
            print(f"    ... and {len(errors) - 10} more")
    print(f"{'=' * 60}")

    sys.exit(1 if error_count > 0 and success_count == 0 else 0)


if __name__ == "__main__":
    main()
