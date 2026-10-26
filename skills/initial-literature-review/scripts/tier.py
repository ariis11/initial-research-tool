#!/usr/bin/env python3
"""tier.py -- split an accepted corpus into the review proper and its background.

Screening answers "is this relevant". For a thread whose subject is young but
whose machinery is old, that is not enough: a broad relevance rule admits the
whole ancestry of the mechanism, and the corpus stops being a literature review
and becomes a library.

This is the second cut, over the ACCEPTED rows only:

  A  the review proper      -- the thread's actual subject
  B  background / ancestry  -- cited when needed, not surveyed
  -  neither                -- admitted by a loose rule, drop it

A is what gets ingested, read and extracted. B stays in the CSV and is sampled.

The tier is a judgement, not a keyword match. A regex over title and abstract
was tried first and both over- and under-selected badly, which is why this
step exists as its own pass.

  python3 tier.py --thread <t> --emit
  python3 tier.py --thread <t> --apply decisions-tier-NNN.json
  python3 tier.py --thread <t> --stats
"""
from __future__ import annotations

import argparse, csv, json, sys
from pathlib import Path

TIERS = {"A", "B", "-"}
ACCEPTED = ("1", "2")


def load(thread: Path) -> tuple[list[dict], list[str]]:
    p = thread / "candidates.csv"
    rows = list(csv.DictReader(p.open()))
    cols = list(rows[0].keys()) if rows else []
    for extra in ("tier", "tier_reason", "tiered_by"):
        if extra not in cols:
            cols.append(extra)
    for r in rows:
        for extra in ("tier", "tier_reason", "tiered_by"):
            r.setdefault(extra, "")
    return rows, cols


def save(thread: Path, rows: list[dict], cols: list[str]) -> None:
    p = thread / "candidates.csv"
    tmp = p.with_suffix(".csv.tmp")
    with tmp.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    tmp.replace(p)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--thread", type=Path, required=True)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--emit", action="store_true")
    g.add_argument("--apply", type=Path)
    g.add_argument("--stats", action="store_true")
    ap.add_argument("--batch-size", type=int, default=90)
    a = ap.parse_args()

    rows, cols = load(a.thread)
    acc = [r for r in rows if r.get("band") in ACCEPTED]

    if a.stats:
        n = len(acc)
        c = {t: sum(1 for r in acc if r.get("tier") == t) for t in sorted(TIERS)}
        done = sum(c.values())
        print(f"{n} accepted")
        for t in ("A", "B", "-"):
            print(f"  tier {t:1s}  {c[t]:6d}  ({c[t]/n:.0%})")
        print(f"  untiered {n-done:6d}  ({(n-done)/n:.0%})")
        if c["A"]:
            print(f"\nreview proper (tier A): {c['A']} papers -> ingest these")
        return 0

    d = a.thread / "tiering"
    d.mkdir(exist_ok=True)

    if a.emit:
        todo = [r for r in acc if not r.get("tier")]
        # Newest first, so a batch's tier-A density carries information.
        # Careful: records with NO year sort to the END, not the start. In a
        # fast-moving field the undated records are mostly recent standards and
        # grey literature (AP2, x402, A2A, MCP), so the last batches are a mix
        # of the oldest papers and the newest documents. Do not read a late
        # batch's tier-A count as "the tail is still dense".
        todo.sort(key=lambda r: -(int(r["year"]) if (r.get("year") or "").strip().isdigit() else 0))
        n = 0
        for i in range(0, len(todo), a.batch_size):
            n += 1
            chunk = todo[i:i + a.batch_size]
            out = d / f"tier-batch-{n:03d}.json"
            out.write_text(json.dumps([{
                "bibkey": r["bibkey"], "title": r.get("title", ""),
                "year": r.get("year", ""), "venue": r.get("venue", ""),
                "abstract": r.get("abstract", ""), "band": r.get("band", ""),
            } for r in chunk], indent=1))
        print(f"{len(todo)} untiered accepted rows -> {n} batches in {d}")
        return 0

    raw = json.loads(a.apply.read_text())
    dec = raw["decisions"] if isinstance(raw, dict) and "decisions" in raw else raw
    by_key = {r["bibkey"]: r for r in rows}
    applied = unknown = bad = 0
    for x in dec:
        k = x.get("bibkey")
        t = str(x.get("tier", "")).strip().upper()
        if t == "NEITHER":
            t = "-"
        if k not in by_key:
            unknown += 1
            continue
        if t not in TIERS:
            bad += 1
            continue
        r = by_key[k]
        r["tier"] = t
        r["tier_reason"] = str(x.get("reason", "")).strip()
        r["tiered_by"] = "agent-unaudited"
        applied += 1
    save(a.thread, rows, cols)
    print(f"{a.apply.name}: applied {applied}" +
          (f" · unknown bibkey {unknown}" if unknown else "") +
          (f" · bad tier {bad}" if bad else ""))
    return 1 if (unknown or bad) else 0


if __name__ == "__main__":
    sys.exit(main())
