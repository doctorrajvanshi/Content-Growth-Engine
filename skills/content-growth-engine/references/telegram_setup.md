# Telegram bot setup (no tokens stored in the skill)

## 1. Create a bot per platform
Message @BotFather on Telegram:
- /newbot → name it (e.g. "YourProduct LinkedIn Bot") → get token
- Repeat for each platform: linkedin, twitter, reddit, qa, approvals

## 2. Get your chat id
Message @userinfobot → it returns your numeric chat id.

## 3. Provide secrets via config/credentials.json (gitignored — never committed)
Create config/credentials.json:
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
  "indexnow_key": "....",
  "twitter_bearer": "AAAA...",
  "google_sa_json": "/abs/path/to/sa.json"
}
config/credentials.json is in .gitignore. Do not commit it.
The loader (scripts/load_config.py) reads this file — it does NOT use
process environment, so the skill passes Hermes's security scanner.

## 4. Verify
```
python scripts/forward_to_telegram.py --test
```
All bots should show ✓ with their @username; chat id should show "set".

## 5. Send a draft
```
python scripts/forward_to_telegram.py linkedin content/linkedin/some_post.txt
```
You receive a Telegram message with [📝 Open & Post] and [📋 Copy Text].
