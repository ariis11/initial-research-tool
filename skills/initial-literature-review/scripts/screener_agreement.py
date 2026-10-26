#!/usr/bin/env python3
"""screener_agreement.py -- how reproducible is a screening decision?

screener_consistency.py infers disagreement INDIRECTLY, from steps in the
acceptance rate at the boundary between two screeners' ranges. That is a proxy,
and proxies have been wrong twice in this project already: venue quality judged
from journal names, and PDF coverage judged from `get fulltext`. Both gave
confident wrong answers where a direct check gave the right one.

This script is the direct check. Give it the same batches banded twice by two
independent screeners and it reports how often they actually agreed, plus
Cohen's kappa, which discounts the agreement you would get by chance alone.

Two numbers matter, and they are not interchangeable:

  accept/reject  -- does the paper enter the corpus at all (bands 1+2 vs 3+4).
                    This is the decision the rest of the pipeline depends on.
  exact band     -- did they pick the SAME band. Only this one justifies
                    quoting a band-1 count as if it meant something.

Kappa reading, by the usual convention: <0.20 slight, 0.21-0.40 fair,
0.41-0.60 moderate, 0.61-0.80 substantial, >0.80 almost perfect. A corpus
whose accept/reject kappa is below 0.61 has a screening step that another
person re-running it would not reproduce, and the write-up has to say so.

  python3 screener_agreement.py --a <dir-or-files> --b <dir-or-files>
"""
from __future__ import annotations

import argparse, collections, json, math, re, sys
from pathlib import Path

ACCEPT = (1, 2)


def load(paths: list[Path]) -> dict[str, dict[str, int]]:
    """-> {batch: {bibkey: band}}. Accepts a bare list or {"decisions": [...]}."""
    out: dict[str, dict[str, int]] = {}
    for p in paths:
        try:
            raw = json.loads(p.read_text())
        except json.JSONDecodeError as e:
            print(f"  ! {p.name} does not parse: {e}", file=sys.stderr)
            continue
        rows = raw["decisions"] if isinstance(raw, dict) and "decisions" in raw else raw
        m = re.search(r"(\d{3})", p.name)
        if not m:
            print(f"  ! {p.name} has no batch number in its name", file=sys.stderr)
            continue
        bands = {}
        for r in rows:
            try:
                bands[r["bibkey"]] = int(r["band"])
            except (KeyError, TypeError, ValueError):
                print(f"  ! {p.name}: unreadable row {r!r}", file=sys.stderr)
        out.setdefault(m.group(1), {}).update(bands)
    return out


def expand(spec: list[str], pattern: str) -> list[Path]:
    paths: list[Path] = []
    for s in spec:
        p = Path(s)
        paths.extend(sorted(p.glob(pattern)) if p.is_dir() else [p])
    return paths


def kappa(pairs: list[tuple[int, int]], collapse) -> tuple[float, float]:
    """-> (observed agreement, Cohen's kappa) after mapping bands through collapse."""
    n = len(pairs)
    if not n:
        return float("nan"), float("nan")
    A = [collapse(x) for x, _ in pairs]
    B = [collapse(y) for _, y in pairs]
    po = sum(a == b for a, b in zip(A, B)) / n
    labels = set(A) | set(B)
    pe = sum((A.count(l) / n) * (B.count(l) / n) for l in labels)
    # pe == 1 means both screeners used a single label throughout; kappa is
    # undefined there, and reporting 0 would read as "no better than chance"
    # when in fact the two agreed on everything.
    return po, float("nan") if math.isclose(pe, 1.0) else (po - pe) / (1 - pe)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--a", nargs="+", required=True, help="first screener: dir or files")
    ap.add_argument("--b", nargs="+", required=True, help="second screener: dir or files")
    ap.add_argument("--pattern-a", default="decisions-*.json")
    ap.add_argument("--pattern-b", default="*screener-B*.json")
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()

    A = load(expand(args.a, args.pattern_a))
    B = load(expand(args.b, args.pattern_b))
    shared_batches = sorted(set(A) & set(B))
    if not shared_batches:
        print("no batch was screened by both; nothing to compare", file=sys.stderr)
        return 1

    L: list[str] = []
    def say(s: str = "") -> None:
        print(s)
        L.append(s)

    say("# Screener agreement")
    say()
    say(f"Batches screened twice: {', '.join(shared_batches)}")
    say()

    all_pairs: list[tuple[int, int]] = []
    say("| batch | n | exact | accept/reject | kappa (acc/rej) |")
    say("|---|---:|---:|---:|---:|")
    for b in shared_batches:
        keys = sorted(set(A[b]) & set(B[b]))
        pairs = [(A[b][k], B[b][k]) for k in keys]
        all_pairs += pairs
        ex, _ = kappa(pairs, lambda v: v)
        ar, k = kappa(pairs, lambda v: v in ACCEPT)
        say(f"| {b} | {len(pairs)} | {ex:.0%} | {ar:.0%} | {k:.2f} |")

    n = len(all_pairs)
    ex, exk = kappa(all_pairs, lambda v: v)
    ar, ark = kappa(all_pairs, lambda v: v in ACCEPT)
    say()
    say(f"**Pooled, n = {n}**")
    say()
    say(f"- exact band agreement: {ex:.0%} (kappa {exk:.2f})")
    say(f"- accept/reject agreement: {ar:.0%} (kappa {ark:.2f})")
    rA = sum(x in ACCEPT for x, _ in all_pairs) / n
    rB = sum(y in ACCEPT for _, y in all_pairs) / n
    say(f"- acceptance rate: screener A {rA:.0%}, screener B {rB:.0%}")
    say()

    say("Where they diverged:")
    say()
    say("| A | B | n | share of all |")
    say("|---:|---:|---:|---:|")
    m = collections.Counter(p for p in all_pairs if p[0] != p[1])
    for (x, y), count in sorted(m.items(), key=lambda kv: -kv[1]):
        say(f"| {x} | {y} | {count} | {count / n:.1%} |")
    say()

    verdict = ("reproducible" if ark >= 0.61 else
               "NOT reproducible to the usual standard")
    say(f"Verdict on accept/reject: kappa {ark:.2f} -- {verdict}.")
    if exk < 0.61:
        say()
        say(f"Verdict on the exact band: kappa {exk:.2f}. Band counts taken "
            f"from a single screener are not a stable property of the corpus "
            f"and should not be quoted as one.")

    if args.out:
        args.out.write_text("\n".join(L) + "\n")
        print(f"\nwritten: {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
