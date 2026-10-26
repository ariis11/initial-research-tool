#!/usr/bin/env python3
"""index.py -- every analysis file's frontmatter as one table.

Reads research/papers/*.md and writes research/papers/_index.csv, one row per
paper. Regenerable at any time, never hand-edited.

This is the comparison table synthesis is built from. Zotero cannot do this --
it has tags, a free-text Extra field and notes, but no custom fields, no table
view and no query language, so it cannot answer "every paper using
accumulators whose threat model assumes an honest issuer". That question is
the entire point of extraction, which is why the analysis lives in git as
markdown rather than inside the reference manager.

  python3 index.py --papers research/papers
"""
from __future__ import annotations

import argparse, csv, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import common as c

try:
    import yaml
except ImportError:
    print("needs pyyaml:  pip3 install pyyaml", file=sys.stderr)
    raise SystemExit(2)

COLUMNS = ["bibkey", "year", "title", "venue", "venue_type", "peer_reviewed",
           "relevance", "credibility", "contribution_type", "techniques",
           "threat_model", "assumptions", "security_argument", "evaluation",
           "real_deployment", "limitations_stated", "open_problems_stated",
           "leaves_open", "limitations_unstated", "builds_on", "contradicts",
           "chase", "threads", "verified", "verified_date", "zotero_key", "doi"]
FM = re.compile(r"^---\n(.*?)\n---\n", re.S)


def flat(v) -> str:
    if v is None:
        return ""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, list):
        return "; ".join(str(x) for x in v)
    return " ".join(str(v).split())


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--papers", type=Path, required=True)
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()

    files = sorted(p for p in a.papers.glob("*.md") if not p.name.startswith("_"))
    rows, skipped = [], []
    for f in files:
        m = FM.match(f.read_text(encoding="utf-8"))
        if not m:
            skipped.append(f.name); continue
        try:
            fm = yaml.safe_load(m.group(1)) or {}
        except yaml.YAMLError:
            skipped.append(f.name); continue
        fm.setdefault("bibkey", f.stem)
        rows.append({k: flat(fm.get(k)) for k in COLUMNS})

    rows.sort(key=lambda r: (r["relevance"] or "zz", -int(r["year"] or 0)
                             if str(r["year"]).isdigit() else 0))
    out = a.out or (a.papers / "_index.csv")
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS)
        w.writeheader(); w.writerows(rows)

    c.log(f"{len(rows)} papers → {out}")
    if skipped:
        c.log(f"  skipped (no parseable frontmatter): {', '.join(skipped[:5])}")
    verified = sum(1 for r in rows if r["verified"] == "true")
    c.log(f"  verified: {verified}/{len(rows)}")
    if rows:
        for col in ("relevance", "contribution_type", "security_argument"):
            vals = {}
            for r in rows:
                vals[r[col] or "—"] = vals.get(r[col] or "—", 0) + 1
            c.log(f"  {col}: " + ", ".join(f"{k}={v}" for k, v in sorted(vals.items())))
    return 0


if __name__ == "__main__":
    sys.exit(main())
