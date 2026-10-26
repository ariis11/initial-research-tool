#!/usr/bin/env python3
"""merge_shards.py -- fold per-source gather shards into the thread's corpus.

Added 10 October 2026. Gathering one source at a time is slow because each
source has its own rate limit (arXiv: one request per 3 s) and they wait on
each other. Run gather.py once per source, in parallel, each into its own
<thread>/shards/<source>/ -- no two processes write the same file -- then
merge here. Safe to re-run: rows already in candidates.csv (including screened
ones) keep their bands; only new papers are added.

  python3 merge_shards.py --thread <thread> [--only wos,scopus]
"""
from __future__ import annotations

import argparse, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import common as c
from expand import merge_into


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--thread", type=Path, required=True)
    ap.add_argument("--only", default="", help="comma-separated shard names")
    a = ap.parse_args()

    path = a.thread / "candidates.csv"
    corpus = c.read_rows(path) if path.exists() else []
    before = len(corpus)
    only = {s for s in a.only.split(",") if s}
    merged = {}
    for shard in sorted((a.thread / "shards").glob("*/candidates.csv")):
        name = shard.parent.name
        if only and name not in only:
            continue
        rows = c.read_rows(shard)
        n = len(corpus)
        corpus = merge_into(corpus, rows)
        merged[name] = {"rows": len(rows), "new": len(corpus) - n}
        c.log(f"  {name:16s} {len(rows):6,} rows → +{len(corpus) - n:,} new")
        q = shard.parent / "queries.md"
        if q.exists():
            with (a.thread / "queries.md").open("a", encoding="utf-8") as f:
                f.write(f"\n\n<!-- shard: {name} -->\n" + q.read_text(encoding="utf-8"))
    c.write_rows(path, corpus)
    c.log(f"candidates.csv: {before:,} → {len(corpus):,}")
    c.write_run(a.thread, "merge_shards", {"shards": merged, "before": before,
                                           "after": len(corpus)})
    return 0


if __name__ == "__main__":
    sys.exit(main())
