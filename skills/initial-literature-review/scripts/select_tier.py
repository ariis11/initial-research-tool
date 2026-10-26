#!/usr/bin/env python3
"""select_tier.py -- mark tier A (read in full, goes to Zotero) by area rules.

Added 11 October 2026 for phd-field, after the owner's rule: **everything in
Zotero is read in full; nothing is in Zotero that has not been.** Tier A is the
review proper; tier B stays in candidates.csv and is cited from there.

Rules, agreed 11 October:
  * band 1 only, near-duplicates (reason says "duplicate of") excluded
  * areas taken WHOLE:  --whole  "C1 C2 C3"
  * areas taken IN PART: --partial "N1 N2" --keep "<regex>" -- only papers whose
    title/abstract match --keep, plus the --top N most-cited per area
  * rows already tier A stay tier A

This is a SELECTION rule, not screening: every row here was already judged
relevant by a screener. The keyword filter only decides which relevant papers
of the attack/benchmark-heavy areas get the expensive full read.

  python3 select_tier.py --thread <thread> [--dry-run]
"""
from __future__ import annotations

import argparse, re, sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import common as c
from select_sample import AREA, citations

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--thread", type=Path, required=True)
    ap.add_argument("--whole", required=True, help='area codes taken whole, e.g. "C1 C2 C3"')
    ap.add_argument("--partial", default="", help="area codes taken only where --keep matches")
    ap.add_argument("--keep", help="regex over title+abstract that selects papers from --partial areas")
    ap.add_argument("--top", type=int, default=10)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    whole, partial = set(a.whole.split()), set(a.partial.split())
    if partial and not a.keep:
        ap.error("--partial needs --keep, the regex that decides which of their papers to take")
    keep = re.compile(a.keep, re.I) if a.keep else None

    path = a.thread / "candidates.csv"
    rows = c.read_rows(path)
    area = lambda r: (AREA.match(r.get("reason") or "") or [None, "??"])[1]
    band1 = [r for r in rows if r.get("band") == "1"
             and not re.search(r"duplicate of", r.get("reason") or "", re.I)]

    cites = citations([r for r in band1 if area(r) in partial])
    chosen, why = set(), {}
    for r in band1:
        ar = area(r)
        if r.get("tier") == "A":
            chosen.add(r["bibkey"]); why[r["bibkey"]] = r.get("tier_reason") or "already tier A"
        elif ar in whole:
            chosen.add(r["bibkey"]); why[r["bibkey"]] = f"tier A: whole area {ar}"
        elif ar in partial and keep.search(f"{r['title']} {r.get('abstract', '')}"):
            chosen.add(r["bibkey"]); why[r["bibkey"]] = f"tier A: {ar}, touches authority"
    for ar in partial:
        pool = sorted((r for r in band1 if area(r) == ar and r["bibkey"] not in chosen),
                      key=lambda r: cites.get(r["bibkey"], 0), reverse=True)[:a.top]
        for r in pool:
            chosen.add(r["bibkey"]); why[r["bibkey"]] = f"tier A: {ar}, top-{a.top} cited"

    new = 0
    for r in rows:
        if r.get("band") not in ("1", "2"):
            continue
        if r["bibkey"] in chosen:
            new += r.get("tier") != "A"
            r["tier"], r["tier_reason"], r["tiered_by"] = "A", why[r["bibkey"]], "select_tier.py"
        elif r.get("tier") != "A":
            r["tier"], r["tier_reason"], r["tiered_by"] = "B", "accepted, not tier A", "select_tier.py"

    per = Counter(area(r) for r in rows if r["bibkey"] in chosen)
    c.log(f"tier A: {len(chosen)} ({new} new) — " + ", ".join(f"{k} {v}" for k, v in sorted(per.items())))
    if a.dry_run:
        return 0
    c.write_rows(path, rows)
    c.write_run(a.thread, "select_tier", {"whole": sorted(whole), "partial": sorted(partial),
                                          "top": a.top, "tier_a": len(chosen), "new": new,
                                          "per_area": dict(per)})
    return 0


if __name__ == "__main__":
    sys.exit(main())
