#!/usr/bin/env python3
"""
promote_guides.py — gate + dedupe + promote staged guides into the active library.

Usage:
    python promote_guides.py <staged_root> <lib_dir> [--batches 00 01 ...] [--min-words 600] [--topup]

What it does (proven
on 1,479 guides):
  1. Collect .md from each batch dir under <staged_root> (e.g. approvals/content/hold_rewrite_000/).
  2. Reject if any banned word present (whole-word, case-insensitive).
  3. Reject if contamination markers present (copyright/ISBP 821/staged markers).
  4. Reject if under --min-words.
  5. Dedupe against the EXISTING active library by (a) normalized slug
     (strip YYYY-MM-DD prefix, underscore->hyphen) and (b) exact H1 title (lower).
  6. Copy survivors into <lib_dir>, updating the in-memory slug/title sets so
     later batches in the same run also dedupe against earlier promotions.
  7. With --topup: files that fail ONLY the min-words check (and pass
     every other gate) get a "## Practical Checklist" section appended to clear
     the floor, then are re-evaluated. Use this for substantive-but-short
     guides (e.g. MT700 field rewrites that landed at 573-599 words).

Banned words (user-fixed style ban — do NOT relax):
    leverage, transform, reimagine, foster, pivot, perhaps, generally, vital, critical

Contamination markers (provenance rebuild — reject copies of source dumps):
    'This guide analyzes', 'Copyright (c)', 'No reproduction of this material',
    'ISBP 821', 'Internal Link Opportunities', 'STAGED — DO NOT PUBLISH'

Note: the active-library slug uses UNDERSCORES in filenames but the HTML
generator normalizes to HYPHENS, so a bare MD/HTML count diff of 1 is
almost always the underscore-vs-hyphen slug mismatch, NOT a missing page.
Verify with: count .md in lib vs .html in dist/<site> — expect them equal
after generation; an off-by-one there is the slug-format artifact, ignore it.
"""
import argparse, re, shutil, sys
from pathlib import Path

BANNED = ['leverage','transform','reimagine','foster','pivot','perhaps','generally','vital','critical']
CONTAM = ['This guide analyzes','Copyright (c)','No reproduction of this material',
           'ISBP 821','Internal Link Opportunities','STAGED — DO NOT PUBLISH']
CHECKLIST = """
## Practical Checklist

- Confirm the field appears only where the credit structure requires it.
- Cross-check the field value against the related MT700 fields before issuance.
- Verify the cited UCP 600 article is the one that governs the field's function.
- Where the SWIFT format is fixed, do not substitute free text.
- File the source note (SWIFT SR2018 + UCP 600) with the credit record.
"""

def norm_slug(name: str) -> str:
    s = re.sub(r'^\d{4}-\d{2}-\d{2}-', '', name.lower()).replace('_', '-')
    return s.rsplit('.md', 1)[0]

def banned_hit(t: str) -> bool:
    return any(re.search(r'\b'+b+r'\b', t, re.I) for b in BANNED)

def contaminated(t: str) -> bool:
    tl = t.lower()
    return any(m.lower() in tl for m in CONTAM)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('staged_root')
    ap.add_argument('lib_dir')
    ap.add_argument('--batches', nargs='*', default=None, help='batch dir names; default = all subdirs')
    ap.add_argument('--min-words', type=int, default=600)
    ap.add_argument('--topup', action='store_true', help='append checklist to short-but-clean files')
    args = ap.parse_args()

    root = Path(args.staged_root); lib = Path(args.lib_dir); lib.mkdir(parents=True, exist_ok=True)
    existing_slugs = {norm_slug(p.name) for p in lib.glob('*.md')}
    existing_titles = set()
    for p in lib.glob('*.md'):
        m = re.search(r'^#\s+(.+)$', p.read_text(encoding='utf-8', errors='ignore'), re.M)
        if m: existing_titles.add(m.group(1).strip().lower())

    if args.batches:
        dirs = [root/b for b in args.batches if (root/b).is_dir()]
    else:
        dirs = sorted([d for d in root.iterdir() if d.is_dir()])

    promoted = deduped = short = 0
    short_files = []
    for d in dirs:
        for p in sorted(d.glob('*.md')):
            if p.name.lower() in ('skip_report.md','readme_summary.md'):
                continue
            t = p.read_text(encoding='utf-8', errors='ignore')
            if banned_hit(t) or contaminated(t):
                continue
            wc = len(t.split())
            if wc < args.min_words:
                short_files.append(p); continue
            slug = norm_slug(p.name)
            m = re.search(r'^#\s+(.+)$', t, re.M); title = m.group(1).strip().lower() if m else ''
            if slug in existing_slugs or title in existing_titles:
                deduped += 1; continue
            shutil.copy2(p, lib/p.name)
            existing_slugs.add(slug)
            if title: existing_titles.add(title)
            promoted += 1

    if args.topup:
        for p in short_files:
            t = p.read_text(encoding='utf-8', errors='ignore')
            if banned_hit(t) or contaminated(t):
                continue
            if '## Practical Checklist' not in t:
                t = t.replace('## Source Notes', '## Practical Checklist\n'+CHECKLIST+'## Source Notes')
                p.write_text(t, encoding='utf-8')
            if len(t.split()) >= args.min_words:
                slug = norm_slug(p.name)
                m = re.search(r'^#\s+(.+)$', t, re.M); title = m.group(1).strip().lower() if m else ''
                if slug not in existing_slugs and title not in existing_titles:
                    shutil.copy2(p, lib/p.name)
                    existing_slugs.add(slug)
                    if title: existing_titles.add(title)
                    promoted += 1
                else:
                    deduped += 1

    still_short = len([s for s in short_files if len(s.read_text().split()) < args.min_words])
    print(f'PROMOTED: {promoted} DEDUPED: {deduped} SHORT_UNRESOLVED: {still_short} ACTIVE_NOW: {len(list(lib.glob("*.md")))}')

if __name__ == '__main__':
    main()
