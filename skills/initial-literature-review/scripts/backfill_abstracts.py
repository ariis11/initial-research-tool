#!/usr/bin/env python3
"""backfill_abstracts.py -- fill missing abstracts after gathering, in bulk.

Added 10 October 2026. WoS Starter returns no abstracts and Scopus search
usually doesn't either, so rows found only there would be screened on their
title. Filling them per query inside gather.py made the whole run hostage to
one provider: that evening OpenAlex answered 429 with Retry-After 16,289 s,
and every WoS query sat out the backoff.

So it's a separate pass, after merge and dedupe:

  1. Semantic Scholar /paper/batch -- 500 ids per request (DOI: or ARXIV:)
  2. OpenAlex by DOI, 50 per request -- skipped cleanly if it is refusing us
  3. --scopus: Scopus Abstract Retrieval by DOI, one request each. Needs
     ELSEVIER_API_KEY and institutional access; quota ~10,000/week, so it goes last and
     only for what the free sources could not fill. On 10 October S2 left 3,773
     DOI-bearing rows empty -- mostly Elsevier/Springer, whose abstracts S2 hides.

Rows that still have no abstract keep an empty one; screening is told to
judge those on the title.

  python3 backfill_abstracts.py --thread <thread>
"""
from __future__ import annotations

import argparse, json, os, sys, time, urllib.error, urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import common as c
from expand import _oa_row, OPENALEX

S2_BATCH = "https://api.semanticscholar.org/graph/v1/paper/batch?fields=abstract,externalIds"


def s2_batch(ids: list[str]) -> list:
    hdrs = {"Content-Type": "application/json", "User-Agent": c.UA,
            **c.auth_headers("api.semanticscholar.org")}
    body = json.dumps({"ids": ids}).encode()
    for attempt in range(4):
        time.sleep(1.1)                       # S2's 1 request/second
        try:
            req = urllib.request.Request(S2_BATCH, data=body, headers=hdrs, method="POST")
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read().decode("utf-8", "replace"))
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504):
                time.sleep(min(10 * 2 ** attempt, 90))
                continue
            raise
    return []


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--thread", type=Path, required=True)
    ap.add_argument("--no-openalex", action="store_true")
    ap.add_argument("--scopus", action="store_true")
    a = ap.parse_args()

    path = a.thread / "candidates.csv"
    rows = c.read_rows(path)
    need = [r for r in rows if not (r.get("abstract") or "").strip()]
    c.log(f"{len(rows):,} rows, {len(need):,} without an abstract")
    start = len(need)

    # 1. Semantic Scholar, by DOI or arXiv id
    keyed = []
    for r in need:
        if d := c.norm_doi(r.get("doi")):
            keyed.append(("DOI:" + d, r))
        elif x := c.norm_arxiv(r.get("arxiv")):
            keyed.append(("ARXIV:" + x, r))
    s2_filled = 0
    for i in range(0, len(keyed), 500):
        chunk = keyed[i:i + 500]
        try:
            res = s2_batch([k for k, _ in chunk])
        except Exception as e:
            c.log(f"  s2 batch {i // 500}: {e!r}"[:160])
            continue
        for (_, r), p in zip(chunk, res):
            if p and (p.get("abstract") or "").strip():
                r["abstract"] = p["abstract"][:4000]
                s2_filled += 1
        c.log(f"  s2 {min(i + 500, len(keyed)):,}/{len(keyed):,} — filled {s2_filled:,}")
        c.write_rows(path, rows)              # checkpoint

    # 2. OpenAlex, by DOI, for what is still missing
    oa_filled = 0
    if not a.no_openalex:
        left = [r for r in need if not r["abstract"] and c.norm_doi(r.get("doi"))]
        for i in range(0, len(left), 50):
            chunk = left[i:i + 50]
            try:
                res = c.get_json(OPENALEX, {"filter": "doi:" + "|".join(c.norm_doi(r["doi"]) for r in chunk),
                                            "per-page": 50, "mailto": c.MAILTO}, tries=2)
            except Exception as e:
                c.log(f"  openalex refusing ({e!r})"[:160] + " — stopping the OpenAlex step")
                break
            by = {}
            for w in res.get("results", []):
                o = _oa_row(w, "")
                if o["doi"] and o["abstract"]:
                    by[o["doi"]] = o["abstract"]
            for r in chunk:
                if (d := c.norm_doi(r["doi"])) in by:
                    r["abstract"] = by[d]
                    oa_filled += 1
        c.write_rows(path, rows)

    # 3. Scopus Abstract Retrieval, one DOI at a time
    sc_filled = 0
    if a.scopus and os.environ.get("ELSEVIER_API_KEY"):
        hdr = {"X-ELS-APIKey": os.environ["ELSEVIER_API_KEY"], "Accept": "application/json"}
        if tok := os.environ.get("ELSEVIER_INSTTOKEN"):
            hdr["X-ELS-Insttoken"] = tok
        left = [r for r in need if not r["abstract"] and c.norm_doi(r.get("doi"))]
        for i, r in enumerate(left, 1):
            try:
                res = c.get_json("https://api.elsevier.com/content/abstract/doi/"
                                 + urllib.request.quote(c.norm_doi(r["doi"]), safe="/"),
                                 {"field": "dc:description"}, headers=hdr, tries=3)
                core = (res.get("abstracts-retrieval-response") or {}).get("coredata") or {}
                if txt := (core.get("dc:description") or "").strip():
                    r["abstract"] = txt[:4000]
                    sc_filled += 1
            except c.HostUnavailable as e:
                c.log(f"  scopus refusing ({e}) — stopping the Scopus step")
                break
            except Exception:
                pass                          # 404 = not in Scopus; normal
            if i % 250 == 0:
                c.log(f"  scopus {i:,}/{len(left):,} — filled {sc_filled:,}")
                c.write_rows(path, rows)
        c.write_rows(path, rows)

    still = sum(1 for r in rows if not (r.get("abstract") or "").strip())
    c.log(f"filled {s2_filled:,} from Semantic Scholar, {oa_filled:,} from OpenAlex, "
          f"{sc_filled:,} from Scopus; "
          f"{still:,} still without an abstract")
    c.write_run(a.thread, "backfill_abstracts", {"missing_before": start,
                "s2_filled": s2_filled, "openalex_filled": oa_filled, "scopus_filled": sc_filled,
                "missing_after": still})
    return 0


if __name__ == "__main__":
    sys.exit(main())
