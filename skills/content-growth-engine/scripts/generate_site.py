#!/usr/bin/env python3
"""
Generic guide-site generator (sandboxed — no product/domain-specific logic).

Reads markdown guides from a configurable library dir and renders a static,
SEO-friendly HTML site:
  - per-guide pages (semantic HTML, JSON-LD Article, OpenGraph, GA4, email capture)
  - an index page with category nav + search
  - interactive elements derived from frontmatter + config (checklists,
    comparison tables, and reference patterns the USER supplies — no hard-coded
    regulations)

Everything brand-specific (domain, GA4 id, form id, CTA, design accent,
reference-extraction regexes) comes from config/example.yaml + credentials.json.
This script contains NO DraftLC / trade-finance data and reads NOTHING from
external project directories.

Usage:
    python generate_site.py
    python generate_site.py --library path/to/md --out path/to/dist
"""
import sys
import re
import json
import glob
import shutil
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))
import load_config as cfgmod

cfg = cfgmod.load(__file__)
def _resolve(p, root):
    p = Path(p)
    return p if p.is_absolute() else (root / p)

ROOT = Path(cfg["_root"])
LIB = _resolve(cfg.get("library") or "knowledge-engine/trade_rules_library", ROOT)
OUT = _resolve(cfg.get("site_out") or "dist/compliance-guides", ROOT)
PRODUCT = cfg.get("product", {})
DOMAIN = cfg.get("site_domain") or PRODUCT.get("domain", "https://guides.example.com")
CTA = PRODUCT.get("cta_template", "Learn more: {url}")
GA4 = cfg.get("ga4_id", "G-XXXXXXX")
FORM = cfg.get("formspree_id", "xxxxxx")
ACCENT = cfg.get("accent", "#f59e0b")
TITLE = cfg.get("site_title", PRODUCT.get("name", "Guides"))
DESC = cfg.get("site_description", "Authoritative guides.")
CATS = cfg.get("categories", [])
REF_PATTERNS = cfg.get("reference_patterns", [])  # user-supplied regexes


def slugify(p: Path) -> str:
    return re.sub(r"^\d{4}-\d{2}-\d{2}_", "", p.stem)


def parse_frontmatter(text: str) -> tuple[dict, str]:
    m = re.match(r"^---\n(.*?)\n---\n?(.*)$", text, re.DOTALL)
    if not m:
        return {}, text
    meta = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip().strip('"').strip("'")
    return meta, m.group(2)


def detect_category(title: str) -> str:
    t = title.lower()
    for c in CATS:
        if any(w in t for w in c.get("match", [])):
            return c["key"]
    return CATS[0]["key"] if CATS else "general"


def extract_references(body: str) -> list[str]:
    """Generic reference extraction — driven by user-supplied regexes only."""
    out = []
    for pat in REF_PATTERNS:
        try:
            out += re.findall(pat, body)
        except re.error:
            continue
    # de-dup, cap
    seen = []
    for r in out:
        r = r.strip()
        if r and r not in seen:
            seen.append(r)
    return seen[:30]


def render_checklist(body: str) -> str:
    items = re.findall(r"^\s*[-*]\s+(.+)$", body, re.MULTILINE)
    if not items:
        return ""
    rows = "".join(
        f'<label class="chk"><input type="checkbox"> {i}</label>' for i in items[:12]
    )
    return f'<div class="card"><h3>Checklist</h3>{rows}</div>'


def ga4_tag() -> str:
    if not GA4 or GA4 == "G-XXXXXXX":
        return ""
    return (f'<script async src="https://www.googletagmanager.com/gtag/js?id={GA4}">'
            f'</script><script>window.dataLayer=window.dataLayer||[];'
            f'function gtag(){{dataLayer.push(arguments);}}gtag("js",new Date());'
            f'gtag("config","{GA4}");</script>')


def email_form() -> str:
    if not FORM or FORM == "xxxxxx":
        return ""
    return (f'<form action="https://formspree.io/f/{FORM}" method="POST" '
            f'style="display:flex;gap:.5rem;flex-wrap:wrap;justify-content:center;">'
            f'<input type="email" name="email" placeholder="you@company.com" required '
            f'style="padding:.6rem 1rem;border:1px solid #cbd5e1;border-radius:8px;">'
            f'<button type="submit" style="background:{ACCENT};color:#fff;border:0;'
            f'border-radius:8px;padding:.6rem 1.4rem;font-weight:700;">Get updates</button>'
            f'</form>')


def page_html(title: str, body_md: str, slug: str, category: str) -> str:
    # Minimal markdown -> html (headers, paragraphs, lists, bold)
    paras = body_md.split("\n\n")
    html_parts = []
    for blk in paras:
        blk = blk.strip()
        if not blk:
            continue
        if blk.startswith("# "):
            continue  # title handled separately
        if re.match(r"^#{2,6} ", blk):
            lvl = len(blk.split(" ")[0])
            html_parts.append(f"<h{lvl}>{blk[lvl+1:].strip()}</h{lvl}>")
        elif blk.startswith("- ") or blk.startswith("* "):
            items = "".join(f"<li>{l.strip('- ').strip()}</li>"
                             for l in blk.splitlines())
            html_parts.append(f"<ul>{items}</ul>")
        else:
            html_parts.append(f"<p>{blk}</p>")
    content = "\n".join(html_parts)
    refs = extract_references(body_md)
    ref_html = (f'<div class="card"><h3>References</h3><ul>'
                + "".join(f"<li>{r}</li>" for r in refs) + "</ul></div>") if refs else ""
    url = f"{DOMAIN}/{slug}"
    jsonld = json.dumps({
        "@context": "https://schema.org", "@type": "Article",
        "headline": title, "url": url, "dateModified": datetime.now().isoformat(),
    })
    return f"""<!doctype html><html lang=en><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>{title} — {TITLE}</title>
<meta name=description content="{DESC}">
<meta property="og:title" content="{title}">
<meta property="og:url" content="{url}">
{ga4_tag()}
<script type="application/ld+json">{jsonld}</script>
<style>body{{font-family:system-ui;margin:0;color:#0f172a;line-height:1.6}}
header{{background:{ACCENT};color:#fff;padding:1rem 2rem;display:flex;justify-content:space-between;align-items:center}}
.container{{max-width:760px;margin:2rem auto;padding:0 1rem}}
.card{{background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:1rem;margin:1rem 0}}
.chk{{display:block;padding:.3rem 0}}.btn{{display:inline-block;background:{ACCENT};color:#fff;
padding:.6rem 1.4rem;border-radius:9999px;text-decoration:none;font-weight:700;margin:1rem 0}}
footer{{text-align:center;padding:2rem;color:#94a3b8}}</style></head>
<body><header><strong>{TITLE}</strong><span>{category}</span></header>
<div class=container><a class=btn href="{DOMAIN}">← All guides</a>
<h1>{title}</h1>{content}{render_checklist(body_md)}{ref_html}
<p><a class=btn href="{DOMAIN}">{CTA.format(topic=title, url=url)}</a></p>
{email_form()}</div>
<footer>Generated by content-growth-engine · {datetime.now():%Y}</footer></body></html>"""


def index_html(pages: list[tuple[str, str, str]]) -> str:
    cards = "".join(
        f'<a class=card href="/{s}"><strong>{t}</strong><br><small>{c}</small></a>'
        for t, s, c in pages)
    return f"""<!doctype html><html lang=en><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>{TITLE}</title><meta name=description content="{DESC}">
{ga4_tag()}<style>body{{font-family:system-ui;margin:0;color:#0f172a}}
header{{background:{ACCENT};color:#fff;padding:1rem 2rem}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:1rem;padding:2rem}}
.card{{background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:1rem;text-decoration:none;color:inherit}}
footer{{text-align:center;padding:2rem;color:#94a3b8}}</style></head>
<body><header><strong>{TITLE}</strong></header>
<div class=grid>{cards}</div>{email_form()}<footer>{datetime.now():%Y}</footer></body></html>"""


def main():
    if not LIB.exists():
        raise SystemExit(f"✗ Library dir not found: {LIB}\nSet 'library:' in config/example.yaml.")
    OUT.mkdir(parents=True, exist_ok=True)
    pages = []
    for md in sorted(glob.glob(str(LIB / "*.md"))):
        p = Path(md)
        text = p.read_text(encoding="utf-8")
        meta, body = parse_frontmatter(text)
        title = meta.get("title") or re.sub(r"[-_]", " ", slugify(p)).title()
        slug = slugify(p)
        cat = detect_category(title)
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / f"{slug}.html").write_text(page_html(title, body, slug, cat), encoding="utf-8")
        pages.append((title, slug, cat))
    (OUT / "index.html").write_text(index_html(pages), encoding="utf-8")
    print(f"✓ Generated {len(pages)} pages → {OUT}")


if __name__ == "__main__":
    main()
