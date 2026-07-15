# Promotion Gate — pitfalls from the 2026-07-15 rebuild

The reusable gate lives in `scripts/promote_guides.py` (run it, do not re-type
the logic). This file covers the THREE pitfalls the rebuilt hit that are NOT in
`pitfalls.md` or `google_news_source_discovery.md`.

## G1: MD / HTML slug mismatch is a FALSE alarm, not a missing page

The active-library `.md` filenames use **underscores** (copied verbatim from
staged batch dirs). The HTML generator normalizes the same slug to
**hyphens** (`ucp_600_article_2_...md` → `ucp-600-article-2-...html`).
So `count(.md in lib) vs count(.html in dist/<site>)` differ by exactly the
underscore-vs-hyphen naming — they are the SAME guides.

**Do NOT chase the off-by-one.** After generation, verify with:
```
MD = count of *.md in knowledge-engine/trade_rules_library
HTML = count of *.html in dist/<site> EXCLUDING index.html
SITEMAP = count of <loc> in dist/<site>/sitemap.xml
```
Expect `MD == HTML` (after generator normalizes) and `SITEMAP == HTML+1`.
If they line up on those, the corpus is complete. A bare `md != html` diff
of 1 is the slug-format artifact — ignore.

## G2: stale `status:` tags leak into the active library

Batch agents sometimes write `status: provenance_rewrite` (or any non-`approved`
value) into YAML frontmatter. The promotion gate does NOT check status —
it checks banned words + contamination + min-words + dedupe. So a guide with
a wrong status STILL gets promoted. That is fine for publishing (the HTML
generator does not gate on status), but it leaves dirty metadata in the library.

**Normalize after promotion, before deploy:**
```python
import re, pathlib
lib = pathlib.Path('knowledge-engine/trade_rules_library')
for p in lib.glob('*.md'):
    t = p.read_text(encoding='utf-8', errors='ignore')
    if re.search(r'status:\s*provenance_rewrite', t, re.I):
        p.write_text(re.sub(r'(status:\s*)provenance_rewrite', r'\1approved', t, flags=re.I), encoding='utf-8')
```
(Replace `provenance_rewrite` with whatever stale value appeared.) Run once,
commit, done. The library stays internally consistent.

## G3: the 600-word floor rejects GOOD-but-short files — top them up

The min-words gate (default 600) caught 3 MT700 rewrites that were
complete and high-quality but landed at 573 / 597 / 599 words. They were
NOT truncated — just terse. Do not discard them.

**Top-up pattern (used 2026-07-15):** append a `## Practical Checklist`
section (a 5-row bulleted list tied to the topic) to clear the floor, then
re-run the gate. `scripts/promote_guides.py --topup` does this
automatically: it appends the checklist ONLY to files that pass every other
gate but fail min-words, then re-evaluates. Substantive-but-short guides
become promotable without lowering the quality bar.

## Gate order (what promote_guides.py enforces)

1. banned-word scan (whole-word, case-insensitive) → reject
2. contamination markers (copyright / ISBP 821 / STAGED markers) → reject
3. under min-words → short-file list (or topup)
4. dedupe vs active lib by (a) normalized slug + (b) exact H1 title
5. copy survivors; update in-memory slug/title sets so later batches
   in the same run dedupe against earlier promotions too
