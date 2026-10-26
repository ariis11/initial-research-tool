#!/usr/bin/env python3
"""corpus_report.py -- what is actually in a thread's corpus.

Descriptive only: no judgement, no screening. Its job is to let a human look at
a few thousand rows and decide whether the queries were well chosen, before
anyone spends effort screening them.

  python3 corpus_report.py --thread <thread> --out <thread>/corpus-report.md
"""
from __future__ import annotations

import argparse, json, re, sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import common as c


def bar(n, total, width=28):
    return "█" * max(1, round(width * n / total)) if total and n else ""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--thread", type=Path, required=True)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--top", type=int, default=20)
    a = ap.parse_args()

    rows = c.read_rows(a.thread / "candidates.csv")
    if not rows:
        c.log("no candidates.csv")
        return 2
    n = len(rows)
    L: list[str] = []
    def w(s=""): L.append(s)

    w(f"# Corpus report — {a.thread.resolve().name}")
    w()
    w(f"*Generated {c.now_iso()} from `candidates.csv`. Descriptive only — "
      f"nothing here is a screening decision.*")
    w()
    w(f"**{n:,} distinct papers.**")
    w()

    # ---- provenance ----
    src = Counter()
    for r in rows:
        for s in c.split_list(r["sources"]):
            src[s] += 1
    w("## Where they came from")
    w()
    w("| source | papers | share |")
    w("|---|---:|---|")
    for s, k in src.most_common():
        w(f"| {s} | {k:,} | {bar(k, n)} {100*k//n}% |")
    w()

    # ---- by mode ----
    mode = Counter()
    for r in rows:
        for fb in c.split_list(r["found_by"]):
            parts = fb.split(":")
            if len(parts) >= 2:
                mode[f"{parts[0]}:{parts[1]}"] += 1
    w("## By search mode")
    w()
    w("*`phrase` takes everything a precise query returns. `scoped` and "
      "`relevance` are capped, so their numbers reflect the cap, not the field.*")
    w()
    w("| source:mode | papers |")
    w("|---|---:|")
    for m, k in mode.most_common():
        w(f"| `{m}` | {k:,} |")
    w()

    # ---- overlap: the headline September finding ----
    ns = Counter(len(c.split_list(r["sources"])) or 1 for r in rows)
    single = ns.get(1, 0)
    w("## How many sources found each paper")
    w()
    w("| sources | papers | share |")
    w("|---:|---:|---|")
    for k in sorted(ns):
        w(f"| {k} | {ns[k]:,} | {bar(ns[k], n)} {100*ns[k]//n}% |")
    w()
    w(f"**{100*single//n}% were returned by exactly one source.** The September "
      f"baseline across nine tools was 90%. A lower number here is expected — "
      f"several of these sources index each other — but it is the same warning: "
      f"drop a source and you lose papers nothing else returns.")
    w()

    # ---- years ----
    yrs = Counter()
    for r in rows:
        y = str(r["year"])[:4]
        if y.isdigit() and 1970 <= int(y) <= 2027:
            yrs[int(y)] += 1
    if yrs:
        recent = sum(v for k, v in yrs.items() if k >= 2024)
        w("## By year")
        w()
        for y in sorted(yrs)[-12:]:
            w(f"    {y}  {yrs[y]:5,}  {bar(yrs[y], max(yrs.values()), 40)}")
        w()
        w(f"**{recent:,} papers ({100*recent//n}%) are from 2024 onward.**")
        w()

    # ---- venues ----
    ven = Counter(r["venue"].strip() for r in rows if r["venue"].strip())
    if ven:
        w(f"## Top {a.top} venues")
        w()
        w("| venue | papers |")
        w("|---|---:|")
        for v, k in ven.most_common(a.top):
            w(f"| {v[:66]} | {k:,} |")
        w()

    # ---- which queries actually produced anything ----
    q_hits = Counter()
    for r in rows:
        for fb in c.split_list(r["found_by"]):
            parts = fb.split(":", 2)
            if len(parts) == 3:
                q_hits[parts[2]] += 1
    if q_hits:
        w("## Yield per query")
        w()
        w("*Papers reaching the corpus from each query, across all sources and "
          "modes. A query near zero is either too narrow or the wrong words.*")
        w()
        w("| query | papers |")
        w("|---|---:|")
        for q, k in q_hits.most_common():
            w(f"| {q[:66]} | {k:,} |")
        w()
        dead = [q for q, k in q_hits.items() if k <= 2]
        if dead:
            w(f"**{len(dead)} queries returned 2 papers or fewer:** "
              + ", ".join(f"`{d[:40]}`" for d in dead[:12]))
            w()

    # ---- coverage sanity ----
    w("## Data completeness")
    w()
    for label, test in [("has a DOI", lambda r: bool(r["doi"])),
                        ("has an arXiv ID", lambda r: bool(r["arxiv"])),
                        ("has an abstract", lambda r: len(r["abstract"]) > 80),
                        ("has a venue", lambda r: bool(r["venue"].strip())),
                        ("has a year", lambda r: bool(str(r["year"]).strip())),
                        ("has neither DOI nor arXiv", lambda r: not r["doi"] and not r["arxiv"])]:
        k = sum(1 for r in rows if test(r))
        w(f"- {label}: **{k:,}** ({100*k//n}%)")
    w()
    w("*Abstract coverage matters most: screening is done on title and abstract, "
      "so a row without one cannot be screened properly and has to be fetched or "
      "dropped.*")
    w()

    # ---- runs ----
    runs = sorted((a.thread / "runs").glob("*.json")) if (a.thread / "runs").exists() else []
    if runs:
        w("## Runs")
        w()
        w("| when | script | returned | new |")
        w("|---|---|---:|---:|")
        for f in runs:
            d = json.loads(f.read_text(encoding="utf-8"))
            w(f"| {d.get('at','')} | {d.get('script','')} | "
              f"{d.get('rows_returned', d.get('resolved','—'))} | {d.get('new_rows','—')} |")
        w()

    out = a.out or (a.thread / "corpus-report.md")
    out.write_text("\n".join(L), encoding="utf-8")
    c.log(f"{n:,} papers → {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
