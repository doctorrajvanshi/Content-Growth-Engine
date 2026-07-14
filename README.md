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

## Full documentation

The complete README — scripts, secrets model, dependencies, and hard rules —
lives with the skill at
[`skills/content-growth-engine/README.md`](skills/content-growth-engine/README.md).

## Layout

This repo follows the Hermes **tap** layout: the skill lives under
`skills/content-growth-engine/` (not the repo root) so `hermes skills tap add`
discovers it. Install via the commands above rather than cloning manually.
