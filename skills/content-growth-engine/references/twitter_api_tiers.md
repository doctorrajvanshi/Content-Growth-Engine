# Twitter / X API tiers (verified 2026-07)

Decides whether Twitter *monitoring/search* is possible on a given budget. Posting
via the "Open & Post" human-in-the-loop flow works on any tier (you paste into the
composer) — this only affects the *automated search/reply* path.

| Tier | Cost | Search/recent | Posting |
|------|------|---------------|----------|
| Free | $0 | NOT available | 1,500 tweets/month |
| Basic | $100/mo | 10,000/mo | yes |
| Pro | $5,000/mo | 100,000/mo | yes |

## Implications for this skill

- The Free tier CANNOT search — do not call the search endpoint on Free; it
  returns "credits depleted" / 403. Search = paid tier.
- Twitter *monitoring* (finding conversations to engage with) needs either Basic
  ($100/mo) OR the manual fallback: user searches twitter.com, copies the tweet
  URL/text, runs `python scripts/reply_drafter.py twitter "<url or text>"`, bot
  drafts a reply with a guide link, sends to Telegram with Open & Reply.
- By design acceptable: distribution is human-in-the-loop (hard rule #5). Cron
  tweets still flow daily; only auto-discovery of others' tweets is gated behind
  Basic.

## Bearer token
If Basic is purchased: save the Bearer token to a gitignored file (config/bots.yaml
or CGE_TWITTER_BEARER env). reply_drafter.py reads CGE_TWITTER_BEARER to enrich a
pasted tweet ID with the author's text; without it, the bot still drafts from the
text you paste.
