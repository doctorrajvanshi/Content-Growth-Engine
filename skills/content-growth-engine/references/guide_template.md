# Guide Template — Standard Structure

Every guide follows this structure. Word count: 800-1200 words.

## File naming

`XX_ucp600_<topic-slug>.md` — zero-padded sequential number, topic family prefix,
lowercase hyphenated slug. Example: `01_ucp600_dcw_letter_of_credit_insights.md`.

## Required sections (in order)

```markdown
# {Title}

## Introduction
{2-3 paragraphs: what the document/topic is, why it matters for trade finance,
and a note about the Google News source used for context.}

## Regulatory Framework
{Which rules/laws/standards govern this. Cite specific articles (UCP 600, ISBP 745,
URDG 758, etc.). Explain what each rule requires.}

## Failure Mode Analysis

### Failure Mode 1: {short title}
{What goes wrong, why it matters, how it manifests in practice.}

### Failure Mode 2: {short title}
...

### Failure Mode 3: {short title}
...

### Failure Mode 4: {short title}
...  (optional)

### Failure Mode 5: {short title}
...  (optional)

## Deterministic Resolution Architecture

1. {Step 1 — concrete action}
2. {Step 2 — concrete action}
3. ...
7. {Step 7 — concrete action}

## Conclusion
{2-3 sentences summarizing the key takeaway.}

## FAQ

**{Question 1}?**
{Answer — 1-2 sentences.}

**{Question 2}?**
...

**{Question 3}?**
...

**{Question 4}?**
...

**{Question 5}?**
...

## Source Notes
- Canonical authority: {which rules/laws are the legal basis}.
- Live context: "{Article title}," {Publisher}, {Date}. This is context only, not legal authority.
```

## Style rules

- **Banned words**: leverage, transform, reimagine, foster, pivot, perhaps, generally,
  vital, critical. Replace with concrete alternatives.
- **Source Notes**: All news sources must be marked "This is context only, not legal
  authority." — never present news as legal basis.
- **Failure modes**: Aim for 3-5. Each must describe a distinct failure, not a restatement.
- **Resolution steps**: Aim for 7. Each must be a concrete action, not a general principle.
- **FAQ**: Aim for 5+. Questions should anticipate real practitioner confusion.
- **Tone**: Direct, specific, no hedging. State what the rule IS, not what it "generally" is.
