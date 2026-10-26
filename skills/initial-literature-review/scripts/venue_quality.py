#!/usr/bin/env python3
"""venue_quality.py -- how good are the venues this corpus actually sits in?

Screening records a `credibility` judgement, and until now that judgement was
a guess from the venue's NAME. On the agent-identity thread that produced
"77 of 407 look peer-reviewed, 4 look strong" -- defensible as an impression,
not as evidence.

This asks Scopus instead. For every distinct venue it retrieves CiteScore, SJR
and SNIP, so a claim like "only N papers are in a Q1 venue" can be checked
rather than asserted.

Needs ELSEVIER_API_KEY and an entitled IP (see check_access.py).

  python3 venue_quality.py --thread <thread> --out <thread>/venue-quality.md
"""
from __future__ import annotations

import argparse, os, re, sys, time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import common as c

SERIAL = "https://api.elsevier.com/content/serial/title"
GREY = re.compile(r"arxiv|zenodo|ssrn|preprint|figshare|osf\b|research square|"
                  r"working draft|press release|tech\. rep|internet-draft|biorxiv|www",
                  re.I)


def headers() -> dict:
    key = os.environ.get("ELSEVIER_API_KEY")
    if not key:
        raise SystemExit("ELSEVIER_API_KEY not set — source ~/.ilr-env first")
    h = {"X-ELS-APIKey": key, "Accept": "application/json"}
    if tok := os.environ.get("ELSEVIER_INSTTOKEN"):
        h["X-ELS-Insttoken"] = tok
    return h


def first(d: dict, key: str):
    """SJRList/SNIPList nest the number one level deeper than you expect."""
    v = d.get(key) or {}
    inner = list(v.values())[0] if v else []
    return inner[0].get("$") if inner else None


def lookup(title: str, h: dict) -> dict | None:
    try:
        r = c.get_json(SERIAL, {"title": title[:120], "count": 1}, headers=h, tries=3)
    except Exception:
        return None
    e = ((r.get("serial-metadata-response") or {}).get("entry") or [])
    if not e or e[0].get("error"):
        return None
    x = e[0]
    return {
        "scopus_title": x.get("dc:title") or "",
        "publisher": x.get("dc:publisher") or "",
        "citescore": (x.get("citeScoreYearInfoList") or {}).get("citeScoreCurrentMetric"),
        "sjr": first(x, "SJRList"),
        "snip": first(x, "SNIPList"),
        "subjects": "; ".join((s.get("$") or "")[:34] for s in (x.get("subject-area") or [])[:3]),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--thread", type=Path, required=True)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--min-papers", type=int, default=1,
                    help="only look up venues holding at least this many papers")
    ap.add_argument("--sleep", type=float, default=0.3)
    a = ap.parse_args()

    rows = [r for r in c.read_rows(a.thread / "candidates.csv")
            if r.get("band") in ("1", "2")]
    venues = Counter(r["venue"].strip() for r in rows if r["venue"].strip())
    checkable = [(v, n) for v, n in venues.most_common()
                 if n >= a.min_papers and not GREY.search(v)]
    c.log(f"{len(rows)} accepted · {len(venues)} distinct venues · "
          f"{len(checkable)} worth asking Scopus about\n")

    h, found, results = headers(), 0, []
    for i, (v, n) in enumerate(checkable, 1):
        info = lookup(v, h)
        if info:
            found += 1
            results.append({"venue": v, "papers": n, **info})
            c.log(f"  [{i}/{len(checkable)}] {v[:44]:46s} CiteScore={info['citescore']} SJR={info['sjr']}")
        else:
            results.append({"venue": v, "papers": n, "scopus_title": "", "publisher": "",
                            "citescore": None, "sjr": None, "snip": None, "subjects": ""})
            c.log(f"  [{i}/{len(checkable)}] {v[:44]:46s} not in Scopus")
        time.sleep(a.sleep)

    def num(x):
        try:
            return float(x)
        except (TypeError, ValueError):
            return -1.0

    results.sort(key=lambda r: (-num(r["citescore"]), -r["papers"]))
    indexed = [r for r in results if r["citescore"] is not None]
    papers_indexed = sum(r["papers"] for r in indexed)
    grey_papers = sum(n for v, n in venues.items() if GREY.search(v))
    no_venue = sum(1 for r in rows if not r["venue"].strip())

    L = [f"# Venue quality — {a.thread.resolve().name}", "",
         f"*Generated {c.now_iso()} from Scopus. Replaces a judgement made from venue",
         "names with CiteScore, SJR and SNIP, which are checkable.*", "",
         f"- accepted papers: **{len(rows)}**",
         f"- in a venue Scopus indexes: **{papers_indexed}** ({100*papers_indexed//max(len(rows),1)}%)",
         f"- in preprint servers or grey literature: **{grey_papers}**",
         f"- with no venue recorded at all: **{no_venue}**", "",
         "## Venues Scopus indexes", "",
         "| venue | papers | CiteScore | SJR | SNIP | subject areas |",
         "|---|---:|---:|---:|---:|---|"]
    for r in indexed:
        L.append(f"| {r['venue'][:52]} | {r['papers']} | {r['citescore']} | "
                 f"{r['sjr'] or '—'} | {r['snip'] or '—'} | {r['subjects'][:46]} |")
    missing = [r for r in results if r["citescore"] is None]
    if missing:
        L += ["", f"## Not found in Scopus ({len(missing)})", "",
              "*Either genuinely unindexed, or named differently there. "
              "A venue here is not necessarily weak, but it is not evidenced.*", "",
              "| venue | papers |", "|---|---:|"]
        for r in missing:
            L.append(f"| {r['venue'][:62]} | {r['papers']} |")
    out = a.out or (a.thread / "venue-quality.md")
    out.write_text("\n".join(L) + "\n", encoding="utf-8")

    c.log(f"\n{found}/{len(checkable)} venues found in Scopus")
    c.log(f"{papers_indexed} of {len(rows)} accepted papers sit in an indexed venue")
    c.write_run(a.thread, "venue-quality", {"accepted": len(rows),
                "distinct_venues": len(venues), "checked": len(checkable),
                "found_in_scopus": found, "papers_in_indexed_venue": papers_indexed,
                "grey_papers": grey_papers, "no_venue": no_venue})
    c.log(f"→ {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
