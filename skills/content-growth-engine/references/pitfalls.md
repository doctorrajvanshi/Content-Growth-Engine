# Content Growth Engine — Pitfalls

## P1: Dashboard must never reach the public site

If `dashboard.html` ever lands in `deploy/` or `dist/<site>/`, removing it is NOT a plain `rm`:
1. Delete from BOTH `deploy/` and `dist/<site>/`.
2. `cd deploy && git rm -f dashboard.html && git commit && git push`.
Cloudflare serves the committed tree; the working-copy `rm` won't un-publish it.

## P2: Banned words in generated guides

Run a post-generation grep for AI-ish words before writing guides to the approvals directory.
These words are banned from all guide content:

```
leverage, transform, reimagine, foster, pivot, perhaps, generally, vital, critical
```

Fix pattern:
```bash
grep -i -n 'leverage\|transform\|reimagine\|foster\|pivot\|perhaps\|generally\|vital\|critical' <file>
```
Replace each instance with a concrete, direct alternative. "Generally" → remove or restate
as a direct claim. "Vital" → "key" or "important". "Critical" → "essential" or "necessary".

**Hotspot: FAQ answers**. "Generally" appears most often in FAQ answers (e.g., "courts have
generally accepted..."). Strip it — state the claim directly: "courts have accepted..."

NOTE: Words appearing in quoted news article titles in Source Notes are still flagged —
rephrase the citation or paraphrase the title.

## P3: Google News RSS false positives

Google News RSS searches for niche trade-finance topics often return irrelevant results.
The relevance filter (matching ≥30% of topic words against the article title) catches most
false positives, but some slip through. Common false-positive patterns:

- **Patent/IP disclaimers** matching "article X disclaimer on reimbursement"
- **Sales tax / social media** matching "electronic document submission"
- **General compliance** matching specific court cases or dispute names
- **Temple/mosque disputes** matching "bombay high court orders"

Always verify the source title is actually about trade finance / LC / guarantee law before
writing a guide. When in doubt, read the article (or at least the first paragraph).

## P4: last30days yt-dlp PATH fix (Windows)

On Windows, yt-dlp may not be on PATH even after install. Fix:
```bash
export PATH="$PATH:$HOME/AppData/Roaming/Python/Python312/Scripts"
```

## P5: Telegram button pre-fill + 4096-char cap
## P5: Telegram button pre-fill + 4096-char cap
Telegram message length cap is 4096 characters. The "Open & Post" buttons use
`https://t.me/share/url?url=...&text=...` — the `text` parameter must be URL-encoded
and the total URL must stay under the cap. `extract_platform.py` enforces this.

## P6: Cloudflare `_redirects` catch-all LOOP (took site down twice)
## P6: Cloudflare `_redirects` catch-all LOOP (took site down — re-confirmed 2026-07-15)
A `_redirects` wildcard `/*` matches the root `/` too. Pointing `/*` at
the site's own homepage — in EITHER form — loops:
  `/*  /  301`                     ← loops
  `/* https://<same-domain>/  301`  ← ALSO loops (this form was
                                        tested 2026-07-15 and still
                                        broke EVERY page incl. homepage:
                                        `net::ERR_TOO_MANY_REDIRECTS`)
Cloudflare does NOT reliably serve the static file before evaluating
`/*`; the wildcard consumes `/` and redirects it to `/` again.

**Do NOT deploy any `/*` catch-all to fix orphaned URLs.** Safe options:
- **(A) Leave 404** — cleanest, nothing breaks. Default choice
  (chosen 2026-07-15).
- **(B) Per-slug map** — only with a real old→new slug
  correspondence file. Heavy; most legacy slugs have no new equivalent.
- **(C) Cloudflare DASHBOARD Bulk Redirects** (NOT the `_redirects`
  file) — "host/path → target" rules without the `/*` root trap.
  Requires manual dashboard work / your Cloudflare login. A single
  dynamic rule or a bulk-redirect CSV (generated from the orphaned
  slug list) goes here.

The ONE `_redirects` rule that IS safe and worth keeping:
```text
# old Cloudflare Pages subdomain → custom domain
https://<project>.pages.dev/*  https://<domain>/:splat  301
```
That domain-level form works because the target is a DIFFERENT host.

Edge cache note: after pushing a broken `_redirects`, the loop persists
~1-5 min from Cloudflare's edge cache even after you revert. Verify
with a DEEP page URL (e.g. `/ucp-600-article-2-...`), not just `/`,
after the wait — a bare `/` check can mask a still-cached loop.

## P7: Gateway wrapper must set env vars explicitly

The tokens (`APPROVAL_BOT_TOKEN` etc.) are NOT in system or user env vars
on some hosts. The gateway's `_run_supervisor.cmd` wrapper MUST include
`set APPROVAL_BOT_TOKEN=<real_token>` before launching Python. Without this,
the gateway falls back to `***` and 404s silently.

Extract the real token from `forward_to_telegram.py`'s `BOT_TOKENS` dict
(it loads from env at import time). The wrapper needs it explicitly because
the Task Scheduler launch context may not inherit the parent's env.

## P8: Playwright persistent context doesn't reliably save session cookies

`launch_persistent_context(PROFILE, ...)` was tested and LinkedIn's session
did NOT persist to the saved profile. The working approach:
`browser.new_context()` + inject cookies from Netscape files via
`context.add_cookies()`. See `references/playwright-readonly-fetch.md`.

## P9: Cron + optional script flags

If a script has `--notify` and you wire it into a cron WITHOUT the flag,
alerts are silently dead. The regulatory monitor ran for an unknown period
with `--notify` missing. Always verify the cron invocation passes the
flags the script expects.

## P10: Listener must be supervised

The platform bot listener (`platform_bot_listener.py`) is an always-on daemon.
If it crashes without a supervisor, inbound messages are lost silently.
Always run under `platform_bot_supervisor.py` (crash-restart + backoff).

## P11: Subagent drafting, not the listener

The listener stays dumb/resilient (no LLM dependency). Drafting runs in a
cron subagent that has model + web tools. Keeps the daemon stable.

## P12: Don't overthink, just execute

When the plan is clear, run the tools, don't narrate. Parallel tool calls
for independent checks. One clear answer, then act.
