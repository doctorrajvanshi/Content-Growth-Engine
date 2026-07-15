# Google News RSS — Source Discovery for Held Topics

When a content batch has topics marked `HOLD_NO_SOURCE` (no dossier hits), Google News
RSS can find replacement sources for rewriting.

## RSS URL pattern

```
https://news.google.com/rss/search?q={URL-encoded-query}&hl=en-US&gl=US&ceid=US:en
```

## Python search technique

```python
import urllib.request, urllib.parse, xml.etree.ElementTree as ET

def search_google_news(query, num_results=5):
    encoded = urllib.parse.quote(query)
    url = f"https://news.google.com/rss/search?q={encoded}&hl=en-US&gl=US&ceid=US:en"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = resp.read().decode("utf-8")
    root = ET.fromstring(data)
    results = []
    for item in root.findall(".//item")[:num_results]:
        results.append({
            "title": item.findtext("title", ""),
            "url": item.findtext("link", ""),
            "source_name": (item.find("source").text if item.find("source") is not None else ""),
            "pub_date": item.findtext("pubDate", ""),
        })
    return results
```

## Relevance filter

Match ≥30% of topic words (length > 2) against the article title:

```python
def is_topic_relevant(title, topic):
    title_lower = title.lower()
    topic_words = [w for w in topic.lower().split() if len(w) > 2]
    matches = sum(1 for w in topic_words if w in title_lower)
    return matches / len(topic_words) >= 0.3 if topic_words else False
```

## Fallback: shorten the query

If the full normalized_topic returns 0 results, try the first 3 words:
```python
if not hits and len(topic.split()) > 3:
    hits = search_google_news(" ".join(topic.split()[:3]))
```

## Rate limiting

Add `time.sleep(1)` between searches to avoid Google throttling.

## Redirect URL pitfall

Google News RSS `<link>` tags contain redirect URLs
(`https://news.google.com/rss/articles/CBMi...`), NOT the actual article URLs.
These redirect URLs require JavaScript to follow and will NOT resolve via curl or
`curl -L`. Do not waste time trying to extract real URLs from them.

**Practical approach**: Use the article title + publisher name for source notes.
The title and publisher are reliably extracted from the RSS XML. Source notes
should cite: `"{Title}," {Publisher}, {Date}.` — no URL needed.

## Bash batch search technique

For quick scouting of many topics, bash `for` loops with `curl` + `grep` are
faster than Python scripts:

```bash
for query in \
  "topic+one+keywords" \
  "topic+two+keywords"
do
  echo "=== $query ==="
  curl -s "https://news.google.com/rss/search?q=${query}&hl=en-US&gl=US&ceid=US:en" \
    | grep -oP '<title>.*?</title>' | head -3
  echo "---"
done
```

This extracts titles only (no URLs needed — see redirect URL pitfall above).
Add `sleep 1` between queries to avoid throttling. Use Python only when you need
source names, dates, or deeper extraction.

## Post-write banned word check

After writing all guides, run a grep for banned words across the output directory:
```bash
grep -r -i -E '\b(leverage|transform|reimagine|foster|pivot|perhaps|generally|vital|critical)\b' <output_dir>/
```
Patch any matches before finalizing. Common false triggers: "generally" in FAQ
answers, "critical" in conclusion paragraphs. Replace with concrete alternatives.

## False positive patterns (trade-finance specific)

Watch for these when the topic involves trade finance / LC / guarantee law:
- Patent/IP disclaimers (matching "article X disclaimer")
- Sales tax / social media articles (matching "electronic document submission")
- General compliance articles (matching specific court case names)
- Unrelated court disputes (matching "high court orders")

Verify the source title is actually about the trade-finance domain before writing a guide.

## MT700-field topics — SOURCEABLE LOCALLY (the old "hold & flag" path is WRONG)
Topics of the form `mt700 field <NNx> relationship with UCP 600` or
`mt700 field <NNx> contradicts other fields` (fields 31D, 32B, 39A, 39B,
40A, 41A, 42A, 42C, 43P, 43T, 44A, 44C, 44D, 44E, 44F, 45A,
46A, 47A, 48) returned **0 usable NEWS sources** — Google News indexes
outlets, not SWIFT handbooks. The OLD guidance to "hold and flag for a manual
source drop" is INCORRECT: these are sourceable TODAY from local reference PDFs.

**Local PRIMARY sources (confirmed present on the DraftLC Windows host 2026-07-15):**
- `F:/PD/ucp600.pdf` — official ICC UCP 600 (39 articles). Gives the
  "relationship with UCP 600 articles" half.
- `F:/PD/swift_standards_sr2018.pdf` — SWIFT Standards Category 7
  (Documentary Credits), 367pp, MT700 field specs for ALL 19 fields
  (scope, format, rules, allowed values). Gives the "field spec" + "contradicts
  other fields" half.

**Correct rewrite workflow (proven 2026-07-15 — produced 50 compliant guides):**
1. Extract full text from both PDFs. Use **PyPDF2** — `pdftotext` shell
   pipes break on non-UTF8 bytes (UnicodeDecodeError). PyPDF2 reads them.
2. For each field, slice the SWIFT field-spec block. Regex `Field\s+<NNx>\s*:`
   works for most. NOTE field **42A is spelled `42a`** lowercase with
   sub-options 42A/42D/42M/42P — search `Field\s+42a`, NOT `42A`.
3. Build a `field → UCP 600 article` map, e.g.:
   31D→Art 6 (expiry/place); 32B→Art 14(b)/30/18-19;
   39A/39B→Art 30; 40A→Art 3/6; 41A→Art 6/7-8;
   42A→Art 6/7-8 (drawee); 43P→Art 41(b)/31-33; 43T→Art 41(a)/20-28;
   44A-44F→Art 20-28/14; 45A→Art 14(d)/18; 46A→Art 14/19-28;
   47A→Art 14; 48→Art 36/38.
4. Write a dossier JSON with `field_specs` + `ucp_article_map`.
5. Dispatch rewrite agents fed the dossier inline (field_contexts per batch).
   Agent rule: cite article/field NUMBERS, do NOT reproduce long passages.
6. Gate: ≥600 words, required sections, banned-word grep, dedupe vs active lib.

This is the RIGHT model — real primary sources, no news dependency, no
fabrication. The "hold and flag" path only applies if the local PDFs are
absent on a given host (then keep holding, but prefer copying the PDFs in).
