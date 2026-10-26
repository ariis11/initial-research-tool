#!/usr/bin/env python3
"""wos.py -- Web of Science through the Starter API.

Added 10 October 2026, when the WoS Starter key arrived (Expanded and Journals
API keys were NOT granted). What Starter gives, and what it doesn't:

  gives   search over the WoS Core Collection (TS = title+abstract+keywords),
          DOI, source title, ISSN, year, document type, WoS times-cited
          (Institutional Member plan only), the WoS UID
  doesn't ABSTRACTS. Starter has none. Rows found only by WoS get their abstract
          from OpenAlex by DOI, one request per 50 DOIs. A row with neither a
          DOI nor an OpenAlex abstract stays abstract-less and is screened on
          its title -- recorded, not hidden.
  doesn't THE INDEX EDITION (SCIE / SSCI / ESCI). /journals answers "is this
          journal in WoS", not "in which citation index". That question
          (PoPETs and p. 71.2.2) still needs the Master Journal List by hand:
          https://mjl.clarivate.com

Three uses:

  1. a gather source  -- gather.py --sources ...,wos
  2. corpus coverage  -- which accepted papers are WoS-indexed, and how cited.
                         That is the defence's own criterion (p. 71.2.2), so it
                         is measured, not inferred from venue names.
  3. journal check    -- is a target venue in WoS at all

Quota (Clarivate, checked 10 Oct): Free Trial 1 req/s, 50/day, no times-cited.
Institutional Member 5 req/s, 5,000/day, times-cited included. 50 records per
page, so a 300-row query costs 6 requests. Key in ~/.ilr-env as
WOS_STARTER_API_KEY.

  python3 wos.py journal --issn 2299-0984
  python3 wos.py search --query "indirect prompt injection" --limit 50
  python3 wos.py coverage --thread research/threads/my-topic
"""
from __future__ import annotations

import argparse, csv, os, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import common as c
from expand import _oa_row, OPENALEX

BASE = "https://api.clarivate.com/apis/wos-starter/v1"
PAGE = 50
# Our own spacing, so the Free Trial's 1 req/s is honoured too. Set
# WOS_STARTER_RPS=5 on the Institutional plan.
_GAP = 1.0 / max(float(os.environ.get("WOS_STARTER_RPS", "1")), 0.1)
_last = 0.0


def _headers() -> dict:
    key = (os.environ.get("WOS_STARTER_API_KEY") or "").strip()
    if not key:
        raise RuntimeError("WOS_STARTER_API_KEY not set — see ~/.ilr-env")
    return {"X-ApiKey": key}


def _get(path: str, params: dict) -> dict:
    global _last
    wait = _GAP - (time.time() - _last)
    if wait > 0:
        time.sleep(wait)
    _last = time.time()
    return c.get_json(f"{BASE}{path}", params, headers=_headers())


def _g(d: dict, *keys, default=None):
    """The JSON is camelCase; the Python client's docs are snake_case. Accept both."""
    for k in keys:
        if isinstance(d, dict) and k in d:
            return d[k]
    return default


def _ts(q: str, mode: str) -> str:
    # Words in TS are ANDed by default. Quotes inside the query would break the
    # phrase, so they are dropped.
    q = q.replace('"', " ").strip()
    return f'TS=("{q}")' if mode == "phrase" else f"TS=({q})"


def _times_cited(hit: dict) -> str:
    for cit in _g(hit, "citations", default=[]) or []:
        if _g(cit, "db") == "WOS":
            return str(_g(cit, "count", default=""))
    return ""


def _row(hit: dict, found_by: str) -> dict:
    src = _g(hit, "source", default={}) or {}
    ids = _g(hit, "identifiers", default={}) or {}
    names = _g(hit, "names", default={}) or {}
    authors = [_g(a, "displayName", "display_name", "wosStandard", default="")
               for a in (_g(names, "authors", default=[]) or [])]
    doi = c.norm_doi(_g(ids, "doi"))
    uid = _g(hit, "uid", default="")
    return {**c.blank_row(),
            "title": _g(hit, "title", default="") or "",
            "authors": c.join_list(authors),
            "year": _g(src, "publishYear", "publish_year", default="") or "",
            "venue": _g(src, "sourceTitle", "source_title", default="") or "",
            "venue_type": c.join_list(_g(hit, "types", default=[]) or []),
            "doi": doi,
            "url": f"https://doi.org/{doi}" if doi else
                   f"https://www.webofscience.com/wos/woscc/full-record/{uid}",
            "abstract": "",
            "sources": "wos", "found_by": found_by,
            "first_seen": c.now_iso()}


def fill_abstracts(rows: list[dict]) -> int:
    """WoS Starter has no abstracts. Fetch them from OpenAlex by DOI, 50 at a time."""
    need = [r for r in rows if r.get("doi") and not r.get("abstract")]
    filled = 0
    for i in range(0, len(need), 50):
        chunk = need[i:i + 50]
        try:
            res = c.get_json(OPENALEX, {"filter": "doi:" + "|".join(r["doi"] for r in chunk),
                                        "per-page": 50, "mailto": c.MAILTO})
        except Exception as e:                       # abstracts are a bonus, not a gate
            c.log(f"  openalex abstract fill failed: {e!r}"[:160])
            continue
        by_doi = {}
        for w in res.get("results", []):
            oa = _oa_row(w, "")
            if oa["doi"] and oa["abstract"]:
                by_doi[oa["doi"]] = oa["abstract"]
        for r in chunk:
            if r["doi"] in by_doi:
                r["abstract"] = by_doi[r["doi"]]
                filled += 1
    return filled


def search(q: str, limit: int, mode: str = "scoped"):
    """gather.py source. Same contract as the others: -> (rows, total available)."""
    rows, page, total = [], 1, None
    while len(rows) < limit:
        r = _get("/documents", {"q": _ts(q, mode), "db": "WOS", "limit": PAGE, "page": page})
        meta = _g(r, "metadata", default={}) or {}
        if total is None:
            total = _g(meta, "total")
        hits = _g(r, "hits", default=[]) or []
        if not hits:
            break
        rows += [_row(h, f"wos:{mode}:{q}") for h in hits]
        if len(hits) < PAGE:
            break
        page += 1
    rows = rows[:limit]
    # Off for long runs: when OpenAlex is refusing us, every query would wait
    # out its backoff here. backfill_abstracts.py does the same job afterwards.
    if os.environ.get("WOS_FILL_ABSTRACTS", "1") != "0":
        fill_abstracts(rows)
    return rows, total


# ───────────────────────────── CLI ──────────────────────────────────────────

def cmd_journal(a) -> int:
    r = _get("/journals", {"issn": a.issn})
    hits = _g(r, "hits", default=[]) or []
    if not hits:
        print(f"{a.issn}: NOT in Web of Science (per Starter /journals).")
        print("Edition (SCIE/ESCI) is not available through Starter — check https://mjl.clarivate.com")
        return 1
    for j in hits:
        print(f"{a.issn}: IN Web of Science — {_g(j, 'name')} "
              f"(ISSN {_g(j, 'issn')}, eISSN {_g(j, 'eIssn', 'e_issn')})")
        for ln in _g(j, "links", default=[]) or []:
            print(f"   {_g(ln, 'type', default='')}: {_g(ln, 'url', default='')}")
    print("Edition (SCIE/ESCI) is not available through Starter — check https://mjl.clarivate.com")
    return 0


def cmd_search(a) -> int:
    for mode in ("phrase", "scoped"):
        rows, total = search(a.query, a.limit, mode)
        print(f"{mode:7s} total {total}  taken {len(rows)}  "
              f"with abstract {sum(1 for r in rows if r['abstract'])}")
        for r in rows[:5]:
            print(f"   {r['year']}  {r['title'][:90]}  [{r['venue'][:40]}]")
    return 0


def cmd_coverage(a) -> int:
    """Which accepted papers in a thread are WoS-indexed. Writes wos-coverage.csv.

    One request per DOI, joined with OR in groups of 20 to stay inside the quota:
    17 requests per 340 DOIs instead of 340.
    """
    rows = c.read_rows(a.thread / "candidates.csv")
    keep = [r for r in rows if r.get("band") in set(a.bands.split(","))
            and (not a.tier or r.get("tier") == a.tier) and r.get("doi")]
    c.log(f"{len(keep)} rows with a DOI in bands {a.bands}"
          + (f", tier {a.tier}" if a.tier else ""))
    found: dict[str, dict] = {}
    for i in range(0, len(keep), 20):
        chunk = [r["doi"] for r in keep[i:i + 20]]
        q = "DO=(" + " OR ".join(f'"{d}"' for d in chunk) + ")"
        try:
            r = _get("/documents", {"q": q, "db": "WOS", "limit": PAGE})
        except Exception as e:
            c.log(f"  chunk {i // 20}: {e!r}"[:160])
            continue
        for h in _g(r, "hits", default=[]) or []:
            d = c.norm_doi(_g(_g(h, "identifiers", default={}) or {}, "doi"))
            if d:
                found[d] = h
    out = a.thread / "wos-coverage.csv"
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["bibkey", "doi", "in_wos", "wos_uid", "wos_times_cited",
                    "wos_source", "wos_types", "venue_ours"])
        for r in keep:
            h = found.get(r["doi"])
            w.writerow([r["bibkey"], r["doi"], "yes" if h else "no",
                        _g(h, "uid", default="") if h else "",
                        _times_cited(h) if h else "",
                        (_g(_g(h, "source", default={}) or {}, "sourceTitle", default="") if h else ""),
                        c.join_list(_g(h, "types", default=[]) or []) if h else "",
                        r.get("venue", "")])
    n = sum(1 for r in keep if r["doi"] in found)
    c.log(f"{n} of {len(keep)} in WoS Core Collection → {out}")
    c.write_run(a.thread, "wos-coverage", {"bands": a.bands, "tier": a.tier,
                                           "checked": len(keep), "in_wos": n})
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    j = sub.add_parser("journal"); j.add_argument("--issn", required=True)
    s = sub.add_parser("search"); s.add_argument("--query", required=True)
    s.add_argument("--limit", type=int, default=50)
    v = sub.add_parser("coverage"); v.add_argument("--thread", type=Path, required=True)
    v.add_argument("--bands", default="1,2"); v.add_argument("--tier", default="")
    a = ap.parse_args()
    return {"journal": cmd_journal, "search": cmd_search, "coverage": cmd_coverage}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
