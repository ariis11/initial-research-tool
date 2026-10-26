#!/usr/bin/env python3
"""screen.py -- the human/agent handoff for Gate B.

Three modes, matching how screening actually works:

  --emit    write the unscreened rows out in batches for the agent to judge
  --apply   take the agent's decisions back in and record them
  --audit   draw the random sample a human actually reads

Four bands, and the audit rates are the point of the design:

  1 Core        clearly in         accepted    10% sampled
  2 Probable    in, weaker reason  accepted    25% sampled
  3 Borderline  genuinely unsure   HUMAN ALL  100% sampled
  4 Out         not relevant       rejected     5% sampled

Band 4 is sampled deliberately although it is the tempting one to skip: a
wrongly INCLUDED paper costs ten minutes later, a wrongly EXCLUDED one is
invisible forever, and recall is the entire reason this method exists.

If band 3 comes back as a large share of the corpus that is a signal the
thread definition is too vague -- go back to Gate A rather than grinding
through it. --stats says so out loud.
"""
from __future__ import annotations

import argparse, json, random, re, sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import common as c

BANDS = {"1": "core", "2": "probable", "3": "borderline", "4": "out"}
AUDIT_RATE = {"1": 0.10, "2": 0.25, "3": 1.00, "4": 0.05}
ACCEPTED = {"1", "2"}
BORDERLINE_SHARE_WARN = 0.25


def unscreened(rows):
    return [r for r in rows if not (r.get("band") or "").strip()]


def select(rows, match, exclude):
    """Narrow which unscreened rows to work on.

    Screening a whole corpus in one go is often the wrong shape: a first pass
    wants the papers where the thread's vocabularies actually meet, because if
    the criteria are wrong that subset will show it for a fraction of the
    effort.
    """
    out = rows
    for pat in (match or []):          # every --match must hit: AND, not OR
        rx = re.compile(pat, re.I)
        out = [r for r in out if rx.search(f"{r['title']} {r['abstract'][:900]}")]
    for pat in (exclude or []):
        rx = re.compile(pat, re.I)
        out = [r for r in out if not rx.search(f"{r['title']} {r['abstract'][:900]}")]
    return out


def relevance_terms(thread: Path) -> list[tuple[re.Pattern, int]]:
    """The thread's own ordering terms, from thread.md.

    A fenced ```relevance block, one `<weight> <regex>` per line:

        4 ai agent|agentic|llm agent
        3 revocation|provenance

    Without one, every word of four letters or more in the ```queries block
    counts 1. Topic words never live in this script: they belong to the
    thread, and a list tuned to one thesis orders everyone else's corpus by
    that thesis.
    """
    out = []
    body = c.thread_block(thread, "relevance")
    if body:
        for ln in body.splitlines():
            ln = ln.strip()
            if not ln or ln.startswith("#"):
                continue
            w, _, pat = ln.partition(" ")
            try:
                out.append((re.compile(pat.strip(), re.I), int(w)))
            except (ValueError, re.error) as e:
                c.log(f"  thread.md relevance line ignored ({e}): {ln}")
        if out:
            return out
    words = set()
    for q in (c.thread_block(thread, "queries") or "").splitlines():
        if q.strip() and not q.strip().startswith("#"):
            words |= {w for w in re.findall(r"[a-z0-9]{4,}", q.lower())
                      if w not in c.STOPWORDS}
    return [(re.compile(rf"\b{re.escape(w)}", re.I), 1) for w in sorted(words)]


def relevance_hint(r, terms) -> int:
    """Rough ordering only -- NOT a filter. Every row still gets screened.

    Screening in a sensible order means the yield per batch is informative:
    if band 1 dries up after N batches, that is measured evidence about the
    rest of the corpus rather than an assumption about it. Nothing is dropped
    on the strength of this score.
    """
    txt = f"{r.get('title','')} {r.get('abstract','')[:600]}"
    score = sum(w for rx, w in terms if rx.search(txt))
    y = str(r.get("year", ""))[:4]
    if y.isdigit():
        this_year = int(c.now_iso()[:4])
        score += 3 if int(y) >= this_year - 1 else (1 if int(y) >= this_year - 3 else 0)
    return score


def cmd_emit(rows, a):
    todo = select(unscreened(rows), a.match, a.exclude)
    if a.order == "relevance":
        terms = relevance_terms(a.thread)
        todo.sort(key=lambda r: relevance_hint(r, terms), reverse=True)
    if not todo:
        c.log("nothing unscreened.")
        return 0
    out = a.out or (a.thread / "screening")
    out.mkdir(parents=True, exist_ok=True)
    for f in out.glob("batch-*.json"):
        f.unlink()
    n = 0
    for i in range(0, len(todo), a.batch_size):
        chunk = todo[i:i + a.batch_size]
        payload = {
            "instructions": (
                "Assign each paper a band and a one-line reason, from title, "
                "abstract and venue only. 1=core (clearly in), 2=probable (in, "
                "weaker reason), 3=borderline (genuinely unsure -- a human will "
                "decide), 4=out (not relevant). Judge against the criteria in "
                "thread.md, not against your own sense of what is interesting. "
                "Use 3 when genuinely torn; do not use it to avoid deciding. "
                "Return [{\"bibkey\":..., \"band\":\"1\", \"reason\":\"...\"}]."),
            "papers": [{"bibkey": r["bibkey"], "title": r["title"],
                        "year": r["year"], "venue": r["venue"],
                        "abstract": (r["abstract"] or "")[:900]} for r in chunk],
        }
        (out / f"batch-{i // a.batch_size + 1:03d}.json").write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        n += 1
    c.log(f"{len(todo)} unscreened rows → {n} batches in {out}")
    c.log(f"criteria: {a.thread / 'thread.md'}")
    return 0


def cmd_apply(rows, a):
    decisions = []
    for p in a.apply:
        data = json.loads(Path(p).read_text(encoding="utf-8"))
        decisions += data if isinstance(data, list) else data.get("decisions", [])
    by_key = {r["bibkey"]: r for r in rows}
    applied, unknown, bad = 0, [], []
    for d in decisions:
        key, band = d.get("bibkey"), str(d.get("band", "")).strip()
        if key not in by_key:
            unknown.append(key); continue
        if band not in BANDS:
            bad.append((key, band)); continue
        r = by_key[key]
        r["band"], r["reason"] = band, (d.get("reason") or "").strip()
        r["screened_by"] = a.by
        r["screened_at"] = c.now_iso()
        applied += 1
    c.log(f"applied {applied} decisions")
    if unknown:
        c.log(f"  {len(unknown)} unknown bibkeys, ignored (first: {unknown[:3]})")
    if bad:
        c.log(f"  {len(bad)} invalid bands, ignored (first: {bad[:3]})")
    if not a.dry_run:
        c.write_rows(a.thread / "candidates.csv", rows)
        c.write_run(a.thread, "screen-apply", {"applied": applied,
                    "unknown": len(unknown), "invalid": len(bad), "by": a.by})
    return 0


def cmd_audit(rows, a):
    rnd = random.Random(a.seed)
    screened = [r for r in rows if (r.get("band") or "") in BANDS]
    if not screened:
        c.log("nothing screened yet.")
        return 2
    sample = []
    for band in BANDS:
        pool = [r for r in screened if r["band"] == band]
        if not pool:
            continue
        k = len(pool) if AUDIT_RATE[band] >= 1.0 else max(1, round(len(pool) * AUDIT_RATE[band]))
        sample += rnd.sample(pool, min(k, len(pool)))
    sample.sort(key=lambda r: (r["band"], r["title"]))
    for r in sample:
        r["screened_by"] = r.get("screened_by") or ""
    path = a.thread / "audit.csv"
    if not a.dry_run:
        c.write_rows(path, sample)
        c.write_run(a.thread, "screen-audit",
                    {"seed": a.seed, "sampled": len(sample),
                     "rates": AUDIT_RATE,
                     "per_band": dict(Counter(r["band"] for r in sample))})
    c.log(f"audit sample: {len(sample)} of {len(screened)} screened → {path}")
    for band in BANDS:
        n = sum(1 for r in sample if r["band"] == band)
        tot = sum(1 for r in screened if r["band"] == band)
        if tot:
            c.log(f"  band {band} {BANDS[band]:11s} {n:5d} of {tot:5d}"
                  f"  ({int(AUDIT_RATE[band]*100)}%)")
    c.log("\nRead audit.csv. For each row: does the reason hold? Overturn in the")
    c.log("band column, then re-run --apply. Band 4 rows matter most — a paper")
    c.log("wrongly dropped is invisible from here on.")
    return 0


def cmd_stats(rows, a):
    counts = Counter((r.get("band") or "unscreened") for r in rows)
    total = len(rows)
    c.log(f"{total} rows")
    for band in list(BANDS) + ["unscreened"]:
        n = counts.get(band, 0)
        if n:
            label = BANDS.get(band, "unscreened")
            c.log(f"  {band:10s} {label:11s} {n:6d}  ({100*n//max(total,1)}%)")
    scr = sum(counts.get(b, 0) for b in BANDS)
    acc = sum(counts.get(b, 0) for b in ACCEPTED)
    c.log(f"\nscreened {scr} · accepted {acc} · to ingest {acc}")
    if scr:
        share = counts.get("3", 0) / scr
        if share > BORDERLINE_SHARE_WARN:
            c.log(f"\n  WARNING: borderline is {share:.0%} of screened rows.")
            c.log("  That is a vague thread definition, not a pile of work.")
            c.log("  Go back to Gate A and sharpen the in/out criteria.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--thread", type=Path, required=True)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--emit", action="store_true")
    g.add_argument("--apply", action="append", metavar="FILE")
    g.add_argument("--audit", action="store_true")
    g.add_argument("--stats", action="store_true")
    ap.add_argument("--batch-size", type=int, default=60)
    ap.add_argument("--order", choices=["relevance", "none"], default="relevance",
                    help="batch ordering; 'relevance' makes per-batch yield "
                         "informative. It never drops a row.")
    ap.add_argument("--match", action="append", default=[],
                    help="only emit rows matching this regex; repeatable, ALL must match")
    ap.add_argument("--exclude", action="append", default=[],
                    help="skip rows matching this regex; repeatable")
    ap.add_argument("--out", type=Path)
    ap.add_argument("--by", default="agent")
    ap.add_argument("--seed", type=int, default=20260923, help="audit sample seed, for reproducibility")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    rows = c.read_rows(a.thread / "candidates.csv")
    if not rows:
        c.log(f"no candidates.csv in {a.thread}")
        return 2
    if a.emit:
        return cmd_emit(rows, a)
    if a.apply:
        return cmd_apply(rows, a)
    if a.audit:
        return cmd_audit(rows, a)
    return cmd_stats(rows, a)


if __name__ == "__main__":
    sys.exit(main())
