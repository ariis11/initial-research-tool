#!/usr/bin/env python3
"""subtract.py -- drop from one thread what another thread already accepted.

Added 10 October 2026 for the phd-gaps thread, which covers what the
agent-identity pass left out. Re-screening the 4,329 papers that pass already
accepted would cost days and add nothing, so they are removed before screening.

Only ACCEPTED rows are subtracted (bands 1-2 by default). Rejected rows are
kept on purpose: the other thread rejected many papers for being outside ITS
scope -- prompt injection, runtime monitoring -- which is exactly what the new
thread is about.

Matched by DOI, then arXiv ID, then title slug -- the same order as dedupe.py.
Removed rows go to <thread>/prior-overlap.csv, so the subtraction can be
checked and undone.

  python3 subtract.py --thread research/threads/follow-up \\
                      --prior  research/threads/my-topic
"""
from __future__ import annotations

import argparse, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import common as c


def keys(r: dict) -> set[str]:
    out = set()
    if d := c.norm_doi(r.get("doi")):
        out.add("doi:" + d)
    if x := c.norm_arxiv(r.get("arxiv")):
        out.add("arxiv:" + x)
    if t := c.title_slug(r.get("title") or ""):
        out.add("title:" + t)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--thread", type=Path, required=True)
    ap.add_argument("--prior", type=Path, required=True)
    ap.add_argument("--bands", default="1,2", help="prior bands counted as accepted")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    bands = set(a.bands.split(","))
    prior = [r for r in c.read_rows(a.prior / "candidates.csv") if r.get("band") in bands]
    seen = set().union(*(keys(r) for r in prior)) if prior else set()
    rows = c.read_rows(a.thread / "candidates.csv")
    keep, gone = [], []
    for r in rows:
        (gone if keys(r) & seen else keep).append(r)
    c.log(f"prior accepted: {len(prior):,} · this thread: {len(rows):,} → "
          f"keep {len(keep):,}, subtract {len(gone):,}")
    if a.dry_run:
        return 0
    if gone:
        overlap = a.thread / "prior-overlap.csv"
        c.write_rows(overlap, c.read_rows(overlap) + gone if overlap.exists() else gone)
    c.write_rows(a.thread / "candidates.csv", keep)
    c.write_run(a.thread, "subtract", {"prior": str(a.prior), "bands": sorted(bands),
                                       "prior_accepted": len(prior), "before": len(rows),
                                       "kept": len(keep), "subtracted": len(gone)})
    return 0


if __name__ == "__main__":
    sys.exit(main())
