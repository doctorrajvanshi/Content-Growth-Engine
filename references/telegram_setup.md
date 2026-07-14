# Telegram bot setup (no tokens stored in the skill)

## 1. Create a bot per platform
Message @BotFather on Telegram:
- /newbot  → name it (e.g. "YourProduct LinkedIn Bot") → get token
- Repeat for each platform: linkedin, twitter, reddit, qa, approvals

## 2. Get your chat id
Message @userinfobot → it returns your numeric chat id.

## 3. Provide secrets (pick ONE — never commit them)

### Option A: environment variables (recommended)
```
export CGE_TG_CHAT="123456789"
export CGE_TG_LINKEDIN="123:AAE..."
export CGE_TG_TWITTER="123:AAE..."
export CGE_TG_REDDIT="123:AAE..."
export CGE_TG_QA="123:AAE..."
export CGE_TG_APPROVALS="123:AAE..."
export CGE_SITE_DOMAIN="https://guides.yourproduct.com"
export CGE_GA4_ID="G-XXXXXXX"
export CGE_FORMSPREE_ID="xxxxxx"
export CGE_INDEXNOW_KEY="...."
export CGE_TWITTER_BEARER="AAAA..."   # optional, for reply fetch
export CGE_GOOGLE_SA_JSON="/path/to/sa.json"
```

### Option B: local gitignored file (config/bots.yaml)
```yaml
CGE_TG_CHAT: "123456789"
CGE_TG_LINKEDIN: "123:AAE..."
CGE_TG_TWITTER: "123:AAE..."
CGE_TG_REDDIT: "123:AAE..."
CGE_TG_QA: "123:AAE..."
CGE_TG_APPROVALS: "123:AAE..."
```
Add `config/bots.yaml` to .gitignore immediately.

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
