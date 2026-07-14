---
name: content-growth-engine
version: "1.0.0"
description: >
  Autonomous content engine: generate a compliance/domain guide library from LIVE
  regulatory sources, deploy as a static site, capture leads via GA4 + email,
  distribute to LinkedIn/Twitter/Reddit/SO/GitHub via per-platform Telegram bots
  with one-tap "Open & Post" buttons, monitor trending topics, and surface an
  ops dashboard. Reusable across products, services, and industries.
author: DraftLC
license: MIT
user-invocable: true
metadata:
  openclaw:
    tags:
      - content
      - seo
      - telegram
      - distribution
      - static-site
      - growth
    requires:
      env: []
      optionalEnv:
        - CGE_SITE_DOMAIN
        - CGE_TG_APPROVALS
        - CGE_TG_LINKEDIN
        - CGE_TG_TWITTER
        - CGE_TG_REDDIT
        - CGE_TG_QA
        - CGE_GA4_ID
        - CGE_FORMSPREE_ID
        - CGE_INDEXNOW_KEY
        - CGE_GOOGLE_SA_JSON
      bins:
        - python3
        - git
---

# Content Growth Engine

A reusable, parameterized pipeline that turns a body of authoritative source
material (regulatory PDFs, court feeds, official docs, standards) into a
self-driving content + distribution operation. Originally built for DraftLC
(trade-finance LC compliance). This skill is the GENERIC version — product,
domain, categories, and CTA are all supplied via `config/example.yaml`.

## CORE PRINCIPLE — NO LAZY SEEDING

The engine requires REAL, authoritative SOURCES (live scraping / official docs /
court feeds). It does NOT invent content from a synthetic KB. If `sources:` is
empty or missing, the generator MUST refuse to run. Verified implementation over
plausible-looking generated filler.

## When to use

- You have a domain with authoritative source material and want organic reach.
- You want per-platform human-in-the-loop distribution (not fully automated posting
  that risks API bans / ToS violations).
- You want a static, cheap-to-host site with lead capture + analytics.
- You want trending-topic discovery to feed new content.

## Parameter schema (config/example.yaml)

```yaml
product:
  name: "YourProduct"
  domain: "https://guides.yourproduct.com"   # CGE_SITE_DOMAIN override
  cta_template: "YourProduct generates compliant {topic} — so you never face this failure mode."  # honest, topic-specific
sources:                                      # REQUIRED — live/authoritative
  - path: "C:/regulatory/pdfs/*.pdf"
  - rss: "https://example.org/rulings/rss.xml"
  - url: "https://standards-body.org/texts/"
categories:                                  # used for nav + analytics
  - {key: "ucp600", match: ["ucp", "600"]}
  - {key: "disputes", match: ["dispute", "reject"]}
platforms:                                    # which bots to wire
  linkedin: true
  twitter: true
  reddit: true
  qa: true                                    # StackOverflow + GitHub
analytics:
  ga4_id: "G-XXXXXXX"                          # CGE_GA4_ID override
  formspree_id: "xxxxxx"                       # CGE_FORMSPREE_ID override
indexing:
  indexnow_key: "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"  # CGE_INDEXNOW_KEY override
```

Secrets (bot tokens, API keys) are NEVER stored in this skill. They come from
environment variables (CGE_TG_*), or a local gitignored `config/bots.yaml` the
user creates. See references/telegram_setup.md.

## Pipeline

```
sources → guides (static HTML) → deploy (Cloudflare Pages)
   ↓
trending_topics.py (last30days) → queue → new guides
   ↓
extract_platform.py → per-platform drafts → Telegram bot (Open & Post)
   ↓
reply_drafter.py ← user pastes a URL → drafts reply → Telegram bot (Open & Reply)
   ↓
generate_dashboard.py (LOCAL only) → ops visibility
```

## Required tools / skills

- `last30days` skill (installed separately) — trending topic research.
- Python 3.12+, git, a Cloudflare Pages project (or any static host).
- Telegram bots (one per platform) — created by the user.

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/forward_to_telegram.py` | Multi-bot sender with Open & Post / Open & Reply buttons. Reads tokens from env. |
| `scripts/extract_platform.py` | Turns a guide into a LinkedIn/Twitter-ready post (length + CTA from config). |
| `scripts/reply_drafter.py` | Given a post URL/text, drafts a reply with a guide link. |
| `scripts/trending_topics.py` | Wraps last30days, scores coverage vs. existing guides, queues gaps. |
| `scripts/generate_dashboard.py` | Local static ops dashboard (never deployed). |
| `scripts/submit_indexnow.py` | Bulk IndexNow submission. |
| `scripts/submit_google.py` | Google Indexing API submission (service-account JSON via env). |

## Deployment note

The ops dashboard MUST stay local. Do not copy it into the deploy/ output dir.
`generate_dashboard.py` writes to the repo root, not to the published site.

## Verification

- Scan the skill dir for bot tokens / API keys before publishing — must be 0 leaks.
- `python scripts/forward_to_telegram.py --test` should report each bot from env.
- `python scripts/generate_dashboard.py` writes a local HTML, NOT under deploy/.

## Hard rules (from the DraftLC build — keep them here)

1. Ops dashboard is LOCAL ONLY — never deployed to the public site.
2. No secrets in the skill — env vars (CGE_*) or gitignored config/bots.yaml only.
3. Content generation requires live/authoritative `sources:` — refuse if empty.
4. CTA must be honest and topic-specific, never fake "error-checking" claims.
5. Distribution is human-in-the-loop (Open & Post buttons), not silent auto-post.
