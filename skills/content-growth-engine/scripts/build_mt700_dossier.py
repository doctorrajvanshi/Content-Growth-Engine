"""Build an MT700 source dossier from local reference PDFs.

Why: MT700 field-reference topics (fields 31D-48) are NOT sourceable
via Google News (news outlets don't publish SWIFT field handbooks). The
real primary sources are local PDFs:
  - UCP 600 official text        (e.g. F:/PD/ucp600.pdf)
  - SWIFT SR2018 Category 7        (e.g. F:/PD/swift_standards_sr2018.pdf)
This script extracts per-field specs + a field->UCP-article map into one
JSON dossier that rewrite agents consume inline.

Usage:
  python scripts/build_mt700_dossier.py \
      --ucp "F:/PD/ucp600.pdf" \
      --swift "F:/PD/swift_standards_sr2018.pdf" \
      --out mt700_source_dossier.json

Pitfalls discovered 2026-07-15:
  - Use PyPDF2, NOT `pdftotext` shell pipes (break on non-UTF8 bytes).
  - Field 42A is spelled `42a` (lowercase) with sub-options 42A/42D/
    42M/42P. Search `Field\\s+42a`, not `42A`.
"""
import argparse, json, re, sys
from pathlib import Path

try:
    import PyPDF2
except ImportError:
    sys.exit("PyPDF2 required: pip install pypdf")

FIELDS = ["31D", "32B", "39A", "39B", "40A", "41A", "42A",
          "42C", "43P", "43T", "44A", "44C", "44D", "44E",
          "44F", "45A", "46A", "47A", "48"]

# field -> UCP 600 article(s) it maps to (for "relationship with UCP" topics)
UCP_MAP = {
    "31D": "Article 6 (Expiry date and place for presentation)",
    "32B": "Article 14(b) / Art 30 (Tolerance) / Art 18-19 (Currency)",
    "39A": "Article 30 (Tolerance in credit amount, quantity, unit prices)",
    "39B": "Article 30 (Maximum / not exceeding tolerance)",
    "40A": "Article 3 (Form of credit / availability) / Art 6",
    "41A": "Article 6 (Availability and expiry) / Art 7-8",
    "42A": "Article 6 (Availability) / Art 7 (Issuing bank undertaking)",
    "42C": "Article 6 (Availability) / Art 10 / Art 7-8",
    "43P": "Article 41(b) (Partial shipments) / Art 31-33",
    "43T": "Article 41(a) (Transhipment) / Art 20-28",
    "44A": "Article 20-28 (Transport routing) / Art 14",
    "44C": "Article 33 (Hours of presentation) / Art 14",
    "44D": "Article 14(j) (Place of taking in charge / dispatch)",
    "44E": "Article 20-28 (Port of loading / airport of departure)",
    "44F": "Article 20-28 (Port of discharge / destination)",
    "45A": "Article 14(d) (Goods description) / Art 18",
    "46A": "Article 14 (Documents required) / Art 19-28",
    "47A": "Article 14 (Additional conditions)",
    "48": "Article 36 (Transferable credits) / Art 38",
}


def extract(pdf_path: str) -> str:
    rd = PyPDF2.PdfReader(pdf_path)
    return "\n".join((pg.extract_text() or "") for pg in rd.pages)


def field_spec(swift_text: str, field: str) -> str:
    # 42A is stored lowercase as 42a with sub-options
    token = "42a" if field == "42A" else field
    pat = re.compile(rf"Field\s+{token}\s*:\s*(.+?)"
                       r"(?=\n\s*(?:Field\s+\d|\Z))", re.S)
    m = pat.search(swift_text)
    if not m:
        # fallback: bare ":42A:" style
        m = re.search(rf":?\s*{re.escape(field)}\b[^\n]{{0,200}}\n"
                       rf"((?:.{{0,400}}\n){{0,8}}", swift_text)
    if not m:
        return ""
    return re.sub(r"\s+", " ", m.group(1))[:1200].strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ucp", required=True, help="path to UCP 600 PDF")
    ap.add_argument("--swift", required=True, help="path to SWIFT SR2018 Category 7 PDF")
    ap.add_argument("--out", default="mt700_source_dossier.json")
    a = ap.parse_args()

    ucp = extract(a.ucp)
    swift = extract(a.swift)
    print(f"UCP text: {len(ucp):,} chars; SWIFT text: {len(swift):,} chars")

    field_specs = {f: field_spec(swift, f) for f in FIELDS}
    thin = [f for f in FIELDS if len(field_specs[f]) < 100]
    print(f"Field specs extracted: {len(FIELDS) - len(thin)}/{len(FIELDS)}"
          + (f"  THIN: {thin}" if thin else ""))

    dossier = {
        "ucp_text": ucp,
        "swift_text": swift,
        "field_specs": field_specs,
        "ucp_article_map": UCP_MAP,
    }
    Path(a.out).write_text(json.dumps(dossier, indent=1), encoding="utf-8")
    print(f"Wrote {a.out}")


if __name__ == "__main__":
    main()
