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

## P7: ALL scripts must load `.env` via python-dotenv

Tokens live in `.env` at project root — never hardcoded in source. But
Task Scheduler processes and cron subagents don't automatically see `.env`.
Every script that reads tokens MUST call `load_dotenv()` at startup:

```python
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")
```

**Without this:** running processes miss tokens set after launch, cron
subagents get empty env vars, and sends silently fail (or fall back to
the wrong bot). Real bug: LinkedIn posts appeared in approvals bot because
the cron subagent's `notify_linkedin_bot.py` had an empty `LINKEDIN_BOT_TOKEN`,
returned 404, and the subagent silently routed through approvals instead.

**Install:** `python -m pip install python-dotenv` (usually pre-installed).

**After setting tokens in `.env`:** restart both Task Scheduler tasks:
```bash
schtasks /run /tn "DraftLC Telegram Gateway"      # Admin
schtasks /run /tn "DraftLC Platform Bot Listener"  # Admin
```

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

## P13: Content extraction needs multi-level fallbacks

`extract_twitter.py` originally only looked for `## Failure Mode` headings
(hook) and `## Deterministic Resolution` numbered steps (key point). Guides
without these exact sections produced bare-title tweets with no substance.

**Fix:** always have 3+ fallback sources per extracted field:

| Field | Fallback chain |
|---|---|
| Hook | Failure Mode heading → Introduction → Key Rule / Regulatory Framework → first bold sentence → first substantive paragraph |
| Key point | Resolution steps → Compliance Requirement / Control section → first Verify/Check/Ensure step |

**Rule:** if a content extractor only has1-2 sources for a field, it WILL
produce thin/empty output for guides that don't match the expected structure.
Guide structures vary — always have fallbacks.

P13. **Bot tokens MUST be in .env** — all scripts now use `python-dotenv`
    to load from `.env`. No hardcoded fallbacks. If you forget to create
    `.env`, every bot will fail silently (HTTP 404) and the cron subagent
    will fall back to the approvals bot. After creating `.env`, restart
    both Task Scheduler tasks:
    ```
    schtasks /run /tn "DraftLC Telegram Gateway"     # Admin
    schtasks /run /tn "DraftLC Platform Bot Listener" # Admin
    ```

P14. **Verify bot tokens after any token rotation** — if a bot token
    changes (BotFather regeneration, bot deletion/recreation), update
    `.env` and restart both tasks. Test with:
    ```bash
    python scripts/forward_to_telegram.py --test
    ```
    This prints all 5 bots and their connection status.

P15. **Thin tweets: use multi-level fallback** — `extract_twitter.py`
    now has 5-level hook fallback (Failure Mode → Introduction →
    Key Rule → Bold sentence → First paragraph) and 3-level key point
    fallback (Deterministic Resolution → Compliance Requirement →
    Verify/Check step). Guides without `## Failure Mode` or
    `## Deterministic Resolution` sections still produce substantive
    tweets.

P16. **Cron subagent fallback to approvals bot** — when a platform bot
    token is invalid, the cron subagent may silently fall back to the
    approvals bot instead of failing loudly. This causes LinkedIn posts
    to appear in the approvals channel instead of the LinkedIn bot.
    Always verify bot tokens after deployment with `--test`.
