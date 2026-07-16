# content-growth-engine

A reusable, **parameterized** content + distribution engine. Turn a body of
authoritative source material (regulatory PDFs, court feeds, official docs,
standards) into a self-driving content operation: a static guide site, lead
capture (GA4 + email), per-platform Telegram distribution with one-tap
**Open & Post** buttons, trending-topic discovery, and a local ops dashboard.

Originally built for DraftLC (trade-finance LC compliance); this is the generic
version — product, domain, categories, and CTA are supplied via config.

> **No lazy seeding.** The engine requires REAL, authoritative `sources:`.
> It does NOT invent content from a synthetic KB. Honest CTAs only.

---

## Install

```bash
hermes skills tap add doctorrajvanshi/Content-Growth-Engine
hermes skills install content-growth-engine
```

Or clone-and-copy (equivalent):

```bash
git clone https://github.com/doctorrajvanshi/Content-Growth-Engine.git
cp -r Content-Growth-Engine/skills/content-growth-engine ~/.hermes/skills/
```



## Quick Start (Onboarding)

### Step 1: Install the skill
```bash
hermes skills tap add doctorrajvanshi/Content-Growth-Engine
hermes skills install content-growth-engine
```

### Step 2: Install dependencies
```bash
hermes skills tap add mvanhorn/last30days-skill
hermes skills install last30days
```

### Step 3: Create `.env` (required)
```bash
cp skills/content-growth-engine/.env.example .env
# Edit .env with your real bot tokens from @BotFather
```

**All bot tokens are loaded via `python-dotenv` from `.env`.** No hardcoded fallbacks.
If `.env` is missing, every bot returns HTTP 404 and crons silently fall back
to the approvals bot — a common source of posts appearing in the wrong channel.

### Step 4: Create your config
```bash
mkdir -p config
cp config/example.yaml config/your-config.yaml
# Edit config/your-config.yaml with your product name, domain, categories
```

### Step 4: Create credentials (gitignored)
```bash
# Create config/credentials.json with your bot tokens
# NEVER commit this file — it's in .gitignore
```

### Step 5: Create Telegram bots
1. Message @BotFather on Telegram: /newbot for each platform
2. Get your chat ID from @userinfobot
3. Add tokens to config/credentials.json

### Step 6: Test the pipeline
```bash
# Test bot connectivity
python scripts/forward_to_telegram.py --test

# Test guide generation (with real sources)
python scripts/ingest_sources.py --config config/your-config.yaml

# Test distribution
python scripts/forward_to_telegram.py linkedin content/linkedin/some_post.txt
```

### Step 7: Set up cron jobs
```bash
# Trending topics (daily)
hermes cron create --schedule "0 8 * * *" --prompt "Run trending_topics.py"

# Guide generation (as needed)
hermes cron create --schedule "0 9 * * 1" --prompt "Run ingest_sources.py"
```

## Custom Commands

| Command | Description |
|---------|-------------|
| `python scripts/forward_to_telegram.py --test` | Test all bot connections |
| `python scripts/forward_to_telegram.py <platform> <file>` | Send a draft to a platform bot |
| `python scripts/extract_platform.py <platform> <guide.md>` | Extract a platform-ready post |
| `python scripts/reply_drafter.py <url_or_text>` | Draft a reply to a post |
| `python scripts/trending_topics.py` | Discover trending topics |
| `python scripts/generate_dashboard.py` | Build local ops dashboard |
| `python scripts/submit_indexnow.py` | Submit URLs to IndexNow |
| `python scripts/submit_google.py` | Submit to Google Indexing API |

## Platform Examples

### LinkedIn
```bash
python scripts/extract_platform.py linkedin guides/your-guide.md
python scripts/forward_to_telegram.py linkedin content/linkedin/post.txt
```

### Twitter
```bash
python scripts/extract_platform.py twitter guides/your-guide.md --limit 5
python scripts/forward_to_telegram.py twitter content/twitter/tweet.txt
```

### Reddit
```bash
python scripts/reply_drafter.py "https://reddit.com/r/yoursub/comments/abc123"
python scripts/forward_to_telegram.py reddit content/replies/reply.txt
```

### Dependencies (install last30days)

`trending_topics.py` uses the [`last30days`](https://github.com/mvanhorn/last30days-skill)
skill to pull live conversations. It is **not vendored** (it's 18 MB with
API-key-dependent backends). Install it from its canonical public repo via
Hermes — the proper "install from original repo" path:

```bash
hermes skills tap add mvanhorn/last30days-skill
hermes skills install last30days
```

Or run the resolver, which prints those commands if the skill is missing:

```bash
python deps/install_deps.py
```

`trending_topics.py` auto-detects last30days at `~/.hermes/skills/last30days`.
If you skip this, trending discovery is disabled but everything else works.

> `last30days` may need API keys (e.g. `SCRAPECREATORS_API_KEY`) for some
> sources — see its own README. Those are set in the consumer's environment,
> outside this skill.

### Secrets are file-based (scanner-clean)

This skill reads secrets from a **gitignored** `config/credentials.json` via
`scripts/load_config.py` — NOT from process environment and NOT from the code.
That avoids the pattern Hermes's security scanner flags as exfiltration, so
`hermes skills install` passes without a `--force` override.

Create `config/credentials.json` (gitignored — never commit it):

```json
{
  "tg_chat": "123456789",
  "tg_linkedin": "123:AAE...",
  "tg_twitter": "123:AAE...",
  "tg_reddit": "123:AAE...",
  "tg_qa": "123:AAE...",
  "tg_approvals": "123:AAE...",
  "site_domain": "https://guides.yourproduct.com",
  "ga4_id": "G-XXXXXXX",
  "formspree_id": "xxxxxx",
  "indexnow_key": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "twitter_bearer": "AAAA...",
  "google_sa_json": "/abs/path/to/sa.json"
}
```

Non-secret parameters live in `config/example.yaml`:

```yaml
product:
  name: "YourProduct"
  domain: "https://guides.yourproduct.com"
  cta_template: "YourProduct handles compliant {topic} — so you never face this failure mode. {url}"
sources:                 # REQUIRED — live/authoritative
  - path: "C:/regulatory/pdfs/*.pdf"
  - rss: "https://example.org/rulings/rss.xml"
categories:
  - {key: "core", match: ["core", "standard"]}
platforms:
  linkedin: true
  twitter: true
  reddit: true
  qa: true
analytics:
  ga4_id: "G-XXXXXXX"
  formspree_id: "xxxxxx"
indexing:
  indexnow_key: "xxxx"
```

---

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/load_config.py` | Reads `credentials.json` + `example.yaml` (file-based, no env). Fails loudly on bad YAML. |
| `scripts/ingest_sources.py` | Builds a guide library from configured RSS/local/URL sources (no hard-coded topics). |
| `scripts/generate_site.py` | Renders the markdown library into a static, SEO HTML site (GA4/form/CTA/design from config). |
| `scripts/forward_to_telegram.py` | Multi-bot sender with Open & Post / Open & Reply buttons. |
| `scripts/extract_platform.py` | Guide → LinkedIn/Twitter post (length + CTA from config). |
| `scripts/reply_drafter.py` | URL/text → drafted reply with a guide link. |
| `scripts/trending_topics.py` | Wraps `last30days` skill, scores coverage, queues gaps. |
| `scripts/generate_dashboard.py` | **Local** ops dashboard (repo root, never deployed). |
| `scripts/submit_indexnow.py` | Bulk IndexNow submission. |
| `scripts/submit_google.py` | Google Indexing API submission (SA path from config). |

---

## Typical flow

```
sources → guides (static HTML) → deploy (Cloudflare Pages)
   ↓
trending_topics.py (last30days) → queue → new guides
   ↓
extract_platform.py → per-platform drafts → Telegram bot (Open & Post)
   ↓
reply_drafter.py ← paste a URL → drafts reply → Telegram bot (Open & Reply)
   ↓
generate_dashboard.py (LOCAL only) → ops visibility
```

### Verify bots

```bash
python scripts/forward_to_telegram.py --test
```

### Send a draft

```bash
python scripts/forward_to_telegram.py linkedin content/linkedin/some_post.txt
```

You get a Telegram message with **[📝 Open & Post]** and **[📋 Copy Text]**.

---

## Hard rules

1. Ops dashboard is **LOCAL ONLY** — never deployed to the public site.
2. No secrets in the skill — `config/credentials.json` (gitignored) only.
3. Generation requires live/authoritative `sources:` — refuse if empty.
4. CTA must be honest and topic-specific, never fake "error-checking" claims.
5. Distribution is human-in-the-loop (Open & Post), not silent auto-post.
