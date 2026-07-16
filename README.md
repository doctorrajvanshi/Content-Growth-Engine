# Content Growth Engine

A reusable, **parameterized** content + distribution engine (built for Hermes).
Turn a body of authoritative source material into a self-driving content
operation: a static guide site, lead capture (GA4 + email), per-platform
Telegram distribution with one-tap **Open & Post** buttons, trending-topic
discovery, and a local ops dashboard.

Originally built for DraftLC (trade-finance LC compliance); this is the generic
version — product, domain, categories, and CTA are supplied via config.

## Install

```bash
hermes skills tap add doctorrajvanshi/Content-Growth-Engine
hermes skills install content-growth-engine
```

Then create a local, gitignored `config/credentials.json` (see the skill's
full README) and fill in `config/example.yaml`.



## What's New (v1.1)

### Bidirectional Reply Bots
Users can now message your Telegram bots with a post URL or topic text, and
get a drafted reply back — cross-referencing your guide library with live
web research when needed.

### Hardened Telegram Transport
Every send point follows a resilience pattern: env-sourced tokens (never
hardcoded), exponential retry (5×, 2s→60s), dead-letter queues with
automated replay, and local-only telemetry.

### Playwright Read-Only URL Fetching
Fetch post/comment context from JS-gated platforms (LinkedIn, Twitter, SO)
using headless Chromium with Netscape cookie injection. Read-only — no
form filling, no clicking compose.

### Dynamic Dashboard
`build_dashboard.py` pulls live stats from your library, cron jobs, and
git history — never stale.

## Secrets & `.env`

All bot tokens are loaded from `.env` via `python-dotenv`. No hardcoded
fallbacks — see `.env.example` for the required variables. After creating
`.env`, restart the Task Scheduler tasks (Admin):
```
schtasks /run /tn "DraftLC Telegram Gateway"
schtasks /run /tn "DraftLC Platform Bot Listener"
```

## Full documentation

The complete README — scripts, secrets model, dependencies, and hard rules —
lives with the skill at
[`skills/content-growth-engine/README.md`](skills/content-growth-engine/README.md).

## Layout

This repo follows the Hermes **tap** layout: the skill lives under
`skills/content-growth-engine/` (not the repo root) so `hermes skills tap add`
discovers it. Install via the commands above rather than cloning manually.
