# Operational pitfalls & workarounds (from the DraftLC build)

## P1 — Ops dashboard must NOT reach the public site
Symptom: `generate_dashboard.py` output accidentally lands in `deploy/` and gets
pushed to Cloudflare Pages, exposing the full content inventory + cron schedule.

Removal recipe (when it already shipped):
1. Delete the file from BOTH `deploy/` AND `dist/<site>/` (the dist copy silently
   re-syncs on next deploy).
2. `cd deploy && git rm -f dashboard.html && git commit -m "chore: remove dashboard"
   && git push origin main` — a plain `rm` is NOT enough; Cloudflare serves the
   committed tree, not your working copy.
3. After push, wait 20-40s for the Pages build, then verify the URL returns the
   index page (size > 1MB) or 404 — NOT the dashboard HTML.

Guardrail: the skill's `generate_dashboard.py` writes to the repo ROOT, never
`deploy/`. If you ever fork the generator, keep that path.

## P2 — last30days on Windows needs yt-dlp on PATH (not just pip)
The engine gates YouTube on `shutil.which("yt-dlp")`, NOT on the importable module.
`pip install yt-dlp` installs the module but does not put a `yt-dlp` binary on PATH
in a way the subprocess resolves. Fix:
```bash
mkdir -p ~/bin
cat > ~/bin/yt-dlp <<'EOF'
#!/bin/bash
C:/Python312/python.exe -m yt_dlp "$@"
EOF
chmod +x ~/bin/yt-dlp
# then invoke last30days with PATH="$HOME/bin:$PATH" prepended
```
Also keep yt-dlp current: `pip install --upgrade yt-dlp` (stale builds 404 on
YouTube). On Windows only Firefox cookies work for X/Twitter; Chrome/Edge need
FROM_BROWSER=auto.

## P3 — Telegram inline keyboards can't pre-fill cross-app compose
Don't try to embed the post text in the button URL (Twitter intent supports
?text= but LinkedIn/Reddit/SO don't, and long text breaks the 64-byte callback
cap). The working pattern (already in forward_to_telegram.py):
- One button = deep link to the platform's compose/new-post page (Open & Post),
- Second button = `callback_data: copy_text` (Telegram shows the full body in a
  code block for one-tap copy). User copies, then pastes into the opened page.

## P4 — long drafts exceed Telegram's 4096-char message cap
When a guide/draft is > ~3800 chars, send it as a DOCUMENT (sendDocument) instead
of sendMessage, or it is silently truncated. Already handled in
forward_to_telegram.py (text > 3800 → document).
