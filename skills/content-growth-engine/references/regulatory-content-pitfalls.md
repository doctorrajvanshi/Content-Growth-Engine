# Regulatory Content Pitfalls

## 1. NEVER Fabricate Citations (CRITICAL)

When generating content for domain experts in regulated industries (trade finance,
law, healthcare, finance), NEVER invent:
- Article numbers (e.g., "UCP 600 Article 20(b)")
- Section references (e.g., "ISBP 745 paragraph 12")
- Legal citations (e.g., "PSD2 Article 97")
- Regulatory deadlines or effective dates
- Specific dollar thresholds from regulations

**If you don't know the exact reference, say so explicitly:**
- ❌ "UCP 600 Article 20(b) allows carrier-arranged transshipment"
- ✅ "UCP 600 has specific rules on transshipment (I'd need to verify the exact article number)"

**Why this matters:** A fabricated citation from a credentialed expert
(CDCS, CTFP, etc.) is worse than no citation. The audience will verify it,
and when they find it's wrong, ALL your content loses credibility.

**Source:** User caught fabricated UCP 600 Article 20(b) reference in a
LinkedIn post draft. The article number was wrong. This was during a
personal branding content creation session (Jul 2026).

## 2. Stale Export Data

Platform data exports (LinkedIn CSV, Instagram JSON, Facebook data download)
may not reflect current profile state. Examples:
- Certifications shown as expired in export but current on live profile
- Bio text changed since export date
- Handle/username changed after export

**Rule:** Always cross-reference export data against live profiles before
making claims about current status.

## 3. LinkedIn Technical Limitations

LinkedIn is fully client-side rendered (React). Consequences:
- curl/HTTP requests return empty HTML shells
- Cookie injection via browser_console is blocked by Hermes security
- Voyager API requires CSRF tokens and is partially deprecated (410 errors)
- Best approaches: data exports (CSV), or credential login via browser_type

## 4. Content Accuracy Checklist

Before publishing any content with regulatory references:
- [ ] All article/section numbers verified against primary source
- [ ] All dollar amounts and thresholds confirmed
- [ ] All dates and deadlines checked
- [ ] All organization names spelled correctly
- [ ] All certification names and issuing bodies accurate
- [ ] No fabricated metrics ("trusted by 50,000+ teams")
- [ ] No generic claims without evidence
