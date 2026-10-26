#!/usr/bin/env python3
"""gather.py -- keyword search across every open source, in explicit modes.

Capping results measures how well a tool RANKS, not what it HOLDS, and ranking
is the thing that fails -- a ~1,000-citation foundational paper sat outside the
top 50 of five of six tools searching its exact topic. So the aim is to take
everything a query returns rather than a top-N slice.

But "take everything" is only meaningful if the query is precise enough that
"everything" is a finite set. Measured 23 September on "AI agent identity":

    arxiv     all:AI agent identity          199,738     <- words, matched apart
    arxiv     all:"AI agent identity"              4     <- the same query, quoted
    openalex  search=                        212,360     <- incl. full text
    openalex  title_and_abstract.search        5,932
    openalex  title_and_abstract "phrase"        103
    crossref  query.bibliographic          1,172,217     <- no strict mode exists

A 50,000x difference on arXiv between the same words quoted and unquoted. Top-N
of a 200,000-row fuzzy match is not coverage, it is a sample of a ranking.

So every source runs in EXPLICIT MODES and each is logged separately:

  phrase     exact phrase, title+abstract. Small and precise -- TAKE EVERYTHING.
  scoped     the words, title+abstract only. Broader -- capped by --limit.
  relevance  the source offers no strict mode; this is its top-N ranking, and
             it is labelled as such rather than pretending to be coverage.

This is what the September finding asked for: "we searched OpenAlex for X" is
not a reproducible statement without the mode.

  python3 gather.py --thread research/threads/my-topic
  python3 gather.py --query "delegated authorization autonomous agents" --dry-run
"""
from __future__ import annotations

import argparse, os, re, sys, time
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import common as c
from expand import merge_into, _oa_row, _s2_row, OPENALEX, S2, S2_FIELDS

CROSSREF = "https://api.crossref.org/works"
SCOPUS = "https://api.elsevier.com/content/search/scopus"
ARXIV = "http://export.arxiv.org/api/query"
DBLP = "https://dblp.org/search/publ/api"
EPRINT = "https://eprint.iacr.org/search"


def openalex(q: str, limit: int, mode: str = "scoped"):
    term = f'"{q}"' if mode == "phrase" else q
    filt = f"title_and_abstract.search:{term}"
    rows, cursor, total = [], "*", None
    while len(rows) < limit:
        r = c.get_json(OPENALEX, {"filter": filt, "per-page": 200, "cursor": cursor,
                                  "mailto": c.MAILTO})
        meta = r.get("meta") or {}
        if total is None:
            total = meta.get("count")
        batch = r.get("results", [])
        if not batch:
            break
        rows += [_oa_row(w, f"openalex:{mode}:{q}") for w in batch]
        cursor = meta.get("next_cursor")
        if not cursor:
            break
    return rows[:limit], total


def semanticscholar(q: str, limit: int, mode: str = "relevance"):
    headers = {"x-api-key": os.environ["S2_API_KEY"]} if os.environ.get("S2_API_KEY") else {}
    rows, token, total = [], None, None
    while len(rows) < limit:
        params = {"query": q, "fields": S2_FIELDS, "limit": 100}
        if token:
            params["token"] = token
        r = c.get_json(f"{S2}/search/bulk", params, headers=headers, tries=4)
        if total is None:
            total = r.get("total")
        data = r.get("data") or []
        if not data:
            break
        rows += [_s2_row(p, f"semanticscholar:{mode}:{q}") for p in data]
        token = r.get("token")
        if not token:
            break
    return rows[:limit], total


def scopus(q: str, limit: int, mode: str = "scoped"):
    """Elsevier Scopus. Needs ELSEVIER_API_KEY and a subscribing institution's
    IP (or an insttoken) -- the key alone is not enough.

    Added 3 October on the evidence that mattered: 75% of this corpus came from
    exactly ONE source, so a new index adds unique papers rather than repeats.
    Abstract coverage was never the argument.
    """
    key = os.environ.get("ELSEVIER_API_KEY")
    if not key:
        raise RuntimeError("ELSEVIER_API_KEY not set — see ~/.ilr-env")
    headers = {"X-ELS-APIKey": key, "Accept": "application/json"}
    if tok := os.environ.get("ELSEVIER_INSTTOKEN"):
        headers["X-ELS-Insttoken"] = tok
    term = f'TITLE-ABS-KEY("{q}")' if mode == "phrase" else f"TITLE-ABS-KEY({q})"
    rows, start, total = [], 0, None
    while len(rows) < limit:
        r = c.get_json(SCOPUS, {"query": term, "count": 25, "start": start},
                       headers=headers)
        res = r.get("search-results") or {}
        if total is None:
            try:
                total = int(res.get("opensearch:totalResults") or 0)
            except (TypeError, ValueError):
                total = None
        entries = res.get("entry") or []
        if not entries or entries[0].get("error"):
            break
        for e in entries:
            doi = c.norm_doi(e.get("prism:doi"))
            rows.append({**c.blank_row(),
                "title": e.get("dc:title") or "",
                "authors": c.join_list([e.get("dc:creator") or ""]),
                "year": (e.get("prism:coverDate") or "")[:4],
                "venue": e.get("prism:publicationName") or "",
                "venue_type": e.get("subtypeDescription") or "",
                "doi": doi,
                "url": f"https://doi.org/{doi}" if doi else (e.get("prism:url") or ""),
                "abstract": (e.get("dc:description") or "")[:4000],
                "sources": "scopus", "found_by": f"scopus:{mode}:{q}",
                "first_seen": c.now_iso()})
        start += len(entries)
        if len(entries) < 25:
            break
    return rows[:limit], total


def crossref(q: str, limit: int, mode: str = "relevance"):
    rows, cursor, total = [], "*", None
    while len(rows) < limit:
        r = c.get_json(CROSSREF, {"query.bibliographic": q, "rows": 100,
                                  "cursor": cursor, "mailto": c.MAILTO})
        msg = r.get("message", {})
        if total is None:
            total = msg.get("total-results")
        items = msg.get("items", [])
        if not items:
            break
        for it in items:
            rows.append({**c.blank_row(),
                "title": (it.get("title") or [""])[0],
                "authors": c.join_list([f"{a.get('family','')}, {a.get('given','')}".strip(", ")
                                        for a in (it.get("author") or [])]),
                "year": ((it.get("issued") or {}).get("date-parts") or [[None]])[0][0] or "",
                "venue": (it.get("container-title") or [""])[0],
                "venue_type": it.get("type") or "",
                "doi": c.norm_doi(it.get("DOI")), "url": it.get("URL") or "",
                "abstract": re.sub(r"<[^>]+>", "", it.get("abstract") or "")[:4000],
                "sources": "crossref", "found_by": f"crossref:{mode}:{q}",
                "first_seen": c.now_iso()})
        cursor = msg.get("next-cursor")
        if not cursor:
            break
    return rows[:limit], total


def arxiv(q: str, limit: int, mode: str = "phrase"):
    """arXiv blocked us for hours during September testing. One request per
    three seconds is their stated rate; we honour it."""
    ns = {"a": "http://www.w3.org/2005/Atom",
          "o": "http://a9.com/-/spec/opensearch/1.1/"}
    rows, start, total = [], 0, None
    while len(rows) < limit:
        sq = f'all:"{q}"' if mode == "phrase" else f"abs:{q}"
        txt = c.get_text(ARXIV, {"search_query": sq, "start": start,
                                 "max_results": 100})
        root = ET.fromstring(txt)
        if total is None:
            tr = root.findtext("o:totalResults", "", ns)
            total = int(tr) if str(tr).isdigit() else None
        entries = root.findall("a:entry", ns)
        if not entries:
            break
        for e in entries:
            aid = (e.findtext("a:id", "", ns) or "")
            rows.append({**c.blank_row(),
                "title": " ".join((e.findtext("a:title", "", ns) or "").split()),
                "authors": c.join_list([a.findtext("a:name", "", ns) for a in e.findall("a:author", ns)]),
                "year": (e.findtext("a:published", "", ns) or "")[:4],
                "venue": "arXiv", "venue_type": "preprint",
                "doi": c.norm_doi(e.findtext("a:doi", "", ns)),
                "arxiv": c.norm_arxiv(aid), "url": aid,
                "abstract": " ".join((e.findtext("a:summary", "", ns) or "").split())[:4000],
                "sources": "arxiv", "found_by": f"arxiv:{mode}:{q}",
                "first_seen": c.now_iso()})
        start += len(entries)
        if len(entries) < 100:
            break
        time.sleep(3)
    return rows[:limit], total


def eprint(q: str, limit: int, mode: str = "relevance"):
    """IACR ePrint is invisible to nearly every AI tool, which is exactly why
    it matters -- the cryptography literature lives here, and free abstract
    coverage collapses to 56% on Springer LNCS material without it. There is
    no API, so the search page is parsed. Structural, so it will break when
    they restyle: the selftest covers it."""
    rows, total = [], None
    try:
        html = c.get_text(EPRINT, {"q": q})
    except c.HttpError:
        return rows, None
    if m := re.search(r"(\d[\d,]*)\s+results", html):
        total = int(m.group(1).replace(",", ""))
    # Each result is one <div class="mb-4"> holding the paper link, a <strong>
    # title and an italic author list.
    for block in re.split(r'<div class="mb-4">', html)[1:]:
        m_id = re.search(r'href="/(\d{4}/\d+)"', block)
        m_ti = re.search(r"<strong>(.*?)</strong>", block, re.S)
        if not (m_id and m_ti):
            continue
        num = m_id.group(1)
        title = " ".join(re.sub(r"<[^>]+>", "", m_ti.group(1)).split())
        m_au = re.search(r'class="fst-italic">(.*?)</span>', block, re.S)
        authors = ""
        if m_au:
            raw = " ".join(re.sub(r"<[^>]+>", "", m_au.group(1)).split())
            authors = c.join_list([a.strip() for a in raw.split(",")])
        rows.append({**c.blank_row(), "title": title, "authors": authors,
                     "year": num[:4], "venue": "IACR ePrint", "venue_type": "preprint",
                     "url": f"https://eprint.iacr.org/{num}",
                     "sources": "eprint", "found_by": f"eprint:{mode}:{q}",
                     "first_seen": c.now_iso()})
        if len(rows) >= limit:
            break
    return rows, total


def dblp(q: str, limit: int) -> list[dict]:
    """DBLP sits behind an anti-bot challenge, confirmed again on 23 September.
    We do not attempt to defeat it -- that is a deliberate access control, and
    circumventing it is both impolite and the kind of thing that gets the whole
    university IP range blocked. DBLP stays a MANUAL source, used by hand at
    Gate C for venue verification, where it is genuinely good."""
    raise RuntimeError(
        "DBLP is behind an anti-bot wall and is not scripted by design. "
        "Search it by hand at https://dblp.org/search and note results in queries.md.")


# DBLP is deliberately absent from the default set -- see its docstring.
def wos(q: str, limit: int, mode: str = "scoped"):
    """Web of Science Core Collection via the Starter API -- see wos.py.
    Not in the default set until the key's plan (50/day trial vs 5,000/day
    institutional) is confirmed; pass --sources ...,wos to use it."""
    import wos as _wos
    return _wos.search(q, limit, mode)


SOURCES = {"openalex": openalex, "semanticscholar": semanticscholar,
           "crossref": crossref, "arxiv": arxiv, "eprint": eprint,
           "scopus": scopus, "dblp": dblp, "wos": wos}
# Crossref stays out of the default set: measured at 10% precision on the
# agent-identity thread, because this field's words mean other things in
# chemistry and medicine. Scopus replaces it as the broad index.
# Scopus is only defaulted in when a key is configured; otherwise every query
# would log the same "no key" failure. A thread can name its own set in a
# fenced ```sources block in thread.md, and --sources overrides both.
DEFAULT_SOURCES = ["openalex", "semanticscholar", "arxiv", "eprint"] + (
    ["scopus"] if os.environ.get("ELSEVIER_API_KEY") else [])

# Which modes each source supports. "phrase" results are small and precise, so
# they are taken in full; everything else is capped by --limit and labelled.
MODES = {"openalex": ["phrase", "scoped"], "arxiv": ["phrase", "scoped"],
         "scopus": ["phrase", "scoped"],
         "wos": ["phrase", "scoped"],
         "semanticscholar": ["relevance"], "crossref": ["relevance"],
         "eprint": ["relevance"], "dblp": ["relevance"]}
UNCAPPED = {"phrase"}


def queries_from_thread(thread: Path) -> list[str]:
    """Reads the fenced `queries` block out of thread.md."""
    body = c.thread_block(thread, "queries")
    if not body:
        return []
    return [ln.strip() for ln in body.splitlines()
            if ln.strip() and not ln.strip().startswith("#")]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--thread", type=Path)
    ap.add_argument("--query", action="append", default=[])
    ap.add_argument("--sources", help="comma-separated; default: thread.md ```sources "
                    f"block, else {','.join(DEFAULT_SOURCES)}")
    ap.add_argument("--limit", type=int, default=300,
                    help="cap for scoped/relevance modes, per query per source")
    ap.add_argument("--phrase-limit", type=int, default=2000,
                    help="safety cap for phrase modes, which are taken in full")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    queries = list(a.query)
    if a.thread and not queries:
        queries = queries_from_thread(a.thread)
    if not queries:
        c.log("no queries. Put them in thread.md inside a ```queries block, or pass --query.")
        return 2

    from_thread = [w for ln in (c.thread_block(a.thread, "sources") or "").splitlines()
                   if not ln.strip().startswith("#") for w in ln.replace(",", " ").split()]
    spec = a.sources or ",".join(from_thread) or ",".join(DEFAULT_SOURCES)
    chosen = [s.strip() for s in spec.split(",") if s.strip() in SOURCES]
    if unknown := [s for s in spec.split(",") if s.strip() and s.strip() not in SOURCES]:
        c.log(f"unknown sources ignored: {unknown} (known: {', '.join(SOURCES)})")
    path = a.thread / "candidates.csv" if a.thread else None
    corpus = c.read_rows(path) if path else []
    started_with = len(corpus)
    total_returned, notes, skipped = 0, [], set()

    for qi, q in enumerate(queries, 1):
        c.log(f"\n[{qi}/{len(queries)}] query: {q}")
        # A source refused during the previous query gets another chance here:
        # flakiness should cost one query, not the whole run.
        if revived := c.revive_hosts():
            c.log(f"  (retrying previously refused: {', '.join(revived)})")
        skipped.clear()
        query_rows = []
        for name in chosen:
            if name in skipped:
                continue
            for mode in MODES.get(name, ["relevance"]):
                cap = a.phrase_limit if mode in UNCAPPED else a.limit
                err, avail = "", None
                try:
                    rows, avail = SOURCES[name](q, cap, mode)
                except c.HostUnavailable as e:
                    # The source is refusing us. Drop it for the rest of the run
                    # rather than blocking every other source behind it.
                    rows, err = [], f"UNAVAILABLE — {e}"
                    skipped.add(name)
                except Exception as e:
                    rows, err = [], repr(e)[:160]
                truncated = bool(avail) and len(rows) < avail
                notes.append({"source": name, "mode": mode, "query": q,
                              "available": avail, "taken": len(rows),
                              "truncated": truncated, "cap": cap,
                              **({"error": err} if err else {})})
                av = f"{avail:,}" if isinstance(avail, int) else "?"
                c.log(f"  {name:16s} {mode:9s} taken {len(rows):5d} of {av:>9s}"
                      f"{'  [CAPPED]' if truncated else ''}  {err}")
                query_rows += rows
                if name in skipped:
                    break

        total_returned += len(query_rows)
        if a.dry_run or not path:
            continue

        # Checkpoint after EVERY query. A long run that dies or is interrupted
        # must not lose everything -- measured the hard way on 23 September,
        # when three hours of work produced no file at all.
        before = len(corpus)
        corpus = merge_into(corpus, query_rows)
        c.write_rows(path, corpus)
        c.append_query_log(a.thread, notes[-sum(1 for n in notes if n["query"] == q):])
        c.log(f"  → corpus {before:,} → {len(corpus):,}")

    c.log(f"\nrows returned across all queries: {total_returned:,}")
    if a.dry_run or not path:
        c.log("(dry run — nothing written)")
        return 0

    c.write_run(a.thread, "gather", {"queries": queries, "sources": chosen,
                                     "limit": a.limit, "phrase_limit": a.phrase_limit,
                                     "modes": MODES, "notes": notes,
                                     "sources_dropped_last_query": sorted(skipped),
                                     "dead_hosts": c.dead_hosts(),
                                     "rows_returned": total_returned,
                                     "rows_after_merge": len(corpus),
                                     "new_rows": len(corpus) - started_with})
    c.log(f"candidates.csv: {started_with:,} → {len(corpus):,} "
          f"(+{len(corpus)-started_with:,} new)")
    errs = [n for n in notes if n.get("error")]
    if errs:
        by_src = {}
        for n in errs:
            by_src[n["source"]] = by_src.get(n["source"], 0) + 1
        c.log("source failures: " + ", ".join(f"{k}={v}" for k, v in sorted(by_src.items())))
    return 0


if __name__ == "__main__":
    sys.exit(main())
