#!/usr/bin/env python3
"""screener_consistency.py -- did the screeners agree with each other?

When screening is split across several agents, the band rates they produce are
only comparable if they applied the criteria the same way. One agent in this
run reported changing its own band-1 rule partway through, so this is not a
hypothetical worry.

The corpus was emitted in descending order of expected relevance, so the
acceptance rate (bands 1+2) should fall SMOOTHLY. A sharp step exactly at a
boundary between two agents' ranges is evidence of disagreement between
screeners rather than a real change in the corpus.

Method: compare the jump in acceptance rate at each boundary against the
distribution of jumps between adjacent batches *inside* a single agent's
range. A boundary jump far outside that spread is flagged.

  python3 screener_consistency.py --thread <thread> --boundaries 15,30,45,60,61,76,91,106,126,137
"""
from __future__ import annotations

import argparse, glob, json, re, statistics, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import common as c


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--thread", type=Path, required=True)
    ap.add_argument("--boundaries", required=True,
                    help="last batch number of each screener's range")
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()

    d = a.thread / "screening"
    rates: dict[int, float] = {}
    counts: dict[int, dict] = {}
    for f in sorted(d.glob("decisions-*.json")):
        n = int(re.search(r"(\d+)", f.name).group(1))
        rows = json.loads(f.read_text())
        if not rows:
            continue
        acc = sum(1 for r in rows if str(r.get("band")) in ("1", "2"))
        rates[n] = acc / len(rows)
        counts[n] = {b: sum(1 for r in rows if str(r.get("band")) == b)
                     for b in "1234"}
    if not rates:
        c.log("no decisions files yet")
        return 2

    nums = sorted(rates)
    bounds = {int(x) for x in a.boundaries.split(",") if x.strip()}
    inside, at_bound = [], []
    for prev, nxt in zip(nums, nums[1:]):
        if nxt != prev + 1:
            continue
        jump = abs(rates[nxt] - rates[prev])
        (at_bound if prev in bounds else inside).append((prev, nxt, jump))

    typical = statistics.median(j for _, _, j in inside) if inside else 0.0
    spread = statistics.pstdev([j for _, _, j in inside]) if len(inside) > 1 else 0.0
    threshold = typical + 3 * spread

    L = [f"# Screener consistency — {a.thread.resolve().name}", "",
         f"*Generated {c.now_iso()}. {len(rates)} batches with decisions.*", "",
         f"- median jump in acceptance rate between adjacent batches **inside** one screener's range: **{typical:.1%}**",
         f"- spread (sd): {spread:.1%}",
         f"- flag threshold (median + 3sd): **{threshold:.1%}**", "",
         "## Jumps at screener boundaries", "",
         "| boundary | before | after | jump | verdict |", "|---|---:|---:|---:|---|"]
    flagged = []
    for prev, nxt, jump in at_bound:
        bad = jump > threshold
        if bad:
            flagged.append((prev, nxt, jump))
        L.append(f"| {prev} → {nxt} | {rates[prev]:.0%} | {rates[nxt]:.0%} | "
                 f"{jump:.0%} | {'**CHECK**' if bad else 'ok'} |")
    L += ["", "## Acceptance rate by batch", "",
          "*Should fall smoothly if the ordering worked and the screeners agreed.*", "",
          "| batch | accepted | 1 | 2 | 3 | 4 |", "|---:|---:|---:|---:|---:|---:|"]
    for n in nums:
        cc = counts[n]
        L.append(f"| {n} | {rates[n]:.0%} | {cc['1']} | {cc['2']} | {cc['3']} | {cc['4']} |")

    out = a.out or (a.thread / "screener-consistency.md")
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    c.log(f"median within-range jump {typical:.1%} · threshold {threshold:.1%}")
    if flagged:
        c.log(f"FLAGGED {len(flagged)} boundary/boundaries:")
        for p, n, j in flagged:
            c.log(f"  {p} → {n}: {rates[p]:.0%} → {rates[n]:.0%} (jump {j:.0%})")
    else:
        c.log("no boundary jump stands out — screeners look consistent")
    c.log(f"→ {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
