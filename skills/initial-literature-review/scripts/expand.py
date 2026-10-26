#!/usr/bin/env python3
"""expand.py -- citation-graph traversal across several providers.

Follows citations instead of matching words, which is the only mechanism that
reaches work sharing none of your vocabulary. For this thesis that is the
whole game: seeding from an AI-agent paper returned 86 results and zero
cryptography, while seeding from Camenisch & Lysyanskaya 2002 and reading
forward found the one paper bridging the two literatures.

The rule that came out of the September testing, and the reason --direction
defaults to forward: seed from the OLD CRYPTOGRAPHY papers and read FORWARD.
Backward from the agent side finds nothing, because the recent agent
literature has not absorbed the primitives yet -- there is nothing to
traverse toward.

Several providers, unioned, because citation graphs disagree. OpenAlex holds
Deochake 2026 as a node but records ZERO references for it, so the edge that
mattered most does not exist in its graph at all. A citation graph is not a
fact about the world; it is one provider's reference-parsing coverage, and
they disagree worst on recent preprints -- which is what this field is made
of. Every edge records which provider supplied it.

  python3 expand.py --thread research/threads/my-topic \
      --seed 10.1007/3-540-45708-9_5 --direction forward
"""
from __future__ import annotations

import argparse, os, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import common as c

OPENALEX = "https://api.openalex.org/works"
S2 = "https://api.semanticscholar.org/graph/v1/paper"
CROSSREF = "https://api.crossref.org/works"
S2_FIELDS = "title,year,externalIds,venue,publicationTypes,abstract"

# ────────────────────────────── OpenAlex ─────────────────────────────────────

def _oa_row(w: dict, found_by: str) -> dict:
    ids = w.get("ids") or {}
    loc = (w.get("primary_location") or {}).get("source") or {}
    inv = w.get("abstract_inverted_index")
    abstract = ""
    if inv:
        positions = [(p, word) for word, ps in inv.items() for p in ps]
        abstract = " ".join(word for _, word in sorted(positions))[:4000]
    return {
        **c.blank_row(),
        "title": w.get("display_name") or "",
        "authors": c.join_list([a.get("author", {}).get("display_name", "")
                                for a in (w.get("authorships") or [])]),
        "year": w.get("publication_year") or "",
        "venue": loc.get("display_name") or "",
        "venue_type": w.get("type") or "",
        "doi": c.norm_doi(ids.get("doi")),
        "arxiv": c.norm_arxiv((w.get("primary_location") or {}).get("landing_page_url", "")
                              if "arxiv" in str(ids.get("doi", "")) else ""),
        "url": ids.get("doi") or w.get("id") or "",
        "abstract": abstract,
        "sources": "openalex",
        "found_by": found_by,
        "first_seen": c.now_iso(),
    }


def oa_resolve(seed: str) -> str | None:
    doi = c.norm_doi(seed)
    if doi:
        try:
            return c.get_json(f"{OPENALEX}/doi:{doi}", {"mailto": c.MAILTO})["id"].rsplit("/", 1)[-1]
        except c.HttpError:
            pass
    arx = c.norm_arxiv(seed)
    if arx and "/" not in seed[:6]:
        try:
            r = c.get_json(OPENALEX, {"filter": f"ids.openalex:{arx}", "mailto": c.MAILTO})
            if r.get("results"):
                return r["results"][0]["id"].rsplit("/", 1)[-1]
        except c.HttpError:
            pass
    r = c.get_json(OPENALEX, {"filter": f"title.search:{seed}", "mailto": c.MAILTO})
    if r.get("results"):
        return r["results"][0]["id"].rsplit("/", 1)[-1]
    return None


def oa_edges(seed: str, direction: str, limit: int) -> tuple[list[dict], dict]:
    wid = oa_resolve(seed)
    if not wid:
        return [], {"provider": "openalex", "seed": seed, "resolved": None, "found": 0}
    rows: list[dict] = []
    if direction in ("forward", "both"):
        cursor, got = "*", 0
        while got < limit:
            r = c.get_json(OPENALEX, {"filter": f"cites:{wid}", "per-page": 200,
                                      "cursor": cursor, "mailto": c.MAILTO})
            batch = r.get("results", [])
            if not batch:
                break
            rows += [_oa_row(w, f"openalex:cites:{wid}") for w in batch]
            got += len(batch)
            cursor = (r.get("meta") or {}).get("next_cursor")
            if not cursor:
                break
    if direction in ("backward", "both"):
        w = c.get_json(f"{OPENALEX}/{wid}", {"mailto": c.MAILTO})
        refs = (w.get("referenced_works") or [])[:limit]
        for i in range(0, len(refs), 50):
            chunk = "|".join(x.rsplit("/", 1)[-1] for x in refs[i:i + 50])
            r = c.get_json(OPENALEX, {"filter": f"openalex_id:{chunk}",
                                      "per-page": 50, "mailto": c.MAILTO})
            rows += [_oa_row(x, f"openalex:refs:{wid}") for x in r.get("results", [])]
    return rows, {"provider": "openalex", "seed": seed, "resolved": wid, "found": len(rows)}

# ─────────────────────────── Semantic Scholar ────────────────────────────────

def _s2_row(p: dict, found_by: str) -> dict:
    ex = p.get("externalIds") or {}
    return {
        **c.blank_row(),
        "title": p.get("title") or "",
        "authors": c.join_list([a.get("name", "") for a in (p.get("authors") or [])]),
        "year": p.get("year") or "",
        "venue": p.get("venue") or "",
        "venue_type": c.join_list(p.get("publicationTypes") or []),
        "doi": c.norm_doi(ex.get("DOI")),
        "arxiv": c.norm_arxiv(ex.get("ArXiv")),
        "url": f"https://doi.org/{ex['DOI']}" if ex.get("DOI") else "",
        "abstract": (p.get("abstract") or "")[:4000],
        "sources": "semanticscholar",
        "found_by": found_by,
        "first_seen": c.now_iso(),
    }


def s2_edges(seed: str, direction: str, limit: int) -> tuple[list[dict], dict]:
    """Semantic Scholar is the provider most likely to hold edges OpenAlex lacks.

    Unauthenticated it rate-limits hard -- 429 within two calls during testing.
    Set S2_API_KEY once the university email exists.
    """
    doi, arx = c.norm_doi(seed), c.norm_arxiv(seed)
    pid = f"DOI:{doi}" if doi else (f"arXiv:{arx}" if arx else None)
    headers = {}
    if key := os.environ.get("S2_API_KEY"):
        headers["x-api-key"] = key
    if not pid:
        try:
            r = c.get_json(f"{S2}/search", {"query": seed, "limit": 1}, headers=headers)
            if r.get("data"):
                pid = r["data"][0]["paperId"]
        except c.HttpError as e:
            return [], {"provider": "semanticscholar", "seed": seed, "error": str(e)}
    if not pid:
        return [], {"provider": "semanticscholar", "seed": seed, "resolved": None, "found": 0}

    rows, note = [], {"provider": "semanticscholar", "seed": seed, "resolved": pid}
    for kind, want in (("citations", ("forward", "both")), ("references", ("backward", "both"))):
        if direction not in want:
            continue
        offset = 0
        while offset < limit:
            try:
                r = c.get_json(f"{S2}/{pid}/{kind}",
                               {"fields": S2_FIELDS, "limit": 100, "offset": offset},
                               headers=headers, tries=3)
            except c.HttpError as e:
                note["error"] = f"{kind}: {e}"
                break
            data = r.get("data", [])
            if not data:
                break
            inner = "citingPaper" if kind == "citations" else "citedPaper"
            rows += [_s2_row(d[inner], f"semanticscholar:{kind}:{pid}")
                     for d in data if d.get(inner)]
            offset += len(data)
            if len(data) < 100:
                break
    note["found"] = len(rows)
    return rows, note

# ────────────────────────────── Crossref ─────────────────────────────────────

def crossref_edges(seed: str, direction: str, limit: int) -> tuple[list[dict], dict]:
    """Crossref holds publisher-deposited reference lists. Backward only --
    it has no forward citation index."""
    doi = c.norm_doi(seed)
    if not doi or direction == "forward":
        return [], {"provider": "crossref", "seed": seed, "skipped":
                    "no DOI" if not doi else "no forward index"}
    try:
        msg = c.get_json(f"{CROSSREF}/{doi}", {"mailto": c.MAILTO})["message"]
    except c.HttpError as e:
        return [], {"provider": "crossref", "seed": seed, "error": str(e)}
    rows = []
    for ref in (msg.get("reference") or [])[:limit]:
        rdoi = c.norm_doi(ref.get("DOI"))
        title = ref.get("article-title") or ref.get("volume-title") or ref.get("unstructured") or ""
        if not (rdoi or title):
            continue
        rows.append({**c.blank_row(), "title": title[:400],
                     "authors": ref.get("author", ""), "year": ref.get("year", ""),
                     "venue": ref.get("journal-title", ""), "doi": rdoi,
                     "url": f"https://doi.org/{rdoi}" if rdoi else "",
                     "sources": "crossref", "found_by": f"crossref:refs:{doi}",
                     "first_seen": c.now_iso()})
    return rows, {"provider": "crossref", "seed": seed, "resolved": doi, "found": len(rows)}

# ──────────────────────────────── main ───────────────────────────────────────

PROVIDERS = {"openalex": oa_edges, "semanticscholar": s2_edges, "crossref": crossref_edges}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--thread", type=Path, help="thread directory")
    ap.add_argument("--seed", action="append", required=True,
                    help="DOI, arXiv ID or title (repeatable)")
    ap.add_argument("--direction", default="forward",
                    choices=["forward", "backward", "both"])
    ap.add_argument("--providers", default="openalex,semanticscholar,crossref")
    ap.add_argument("--limit", type=int, default=2000, help="max edges per seed per provider")
    ap.add_argument("--dry-run", action="store_true", help="print, write nothing")
    a = ap.parse_args()

    chosen = [p.strip() for p in a.providers.split(",") if p.strip() in PROVIDERS]
    all_rows: list[dict] = []
    notes: list[dict] = []

    for seed in a.seed:
        c.log(f"\nseed: {seed}  ({a.direction})")
        for name in chosen:
            try:
                rows, note = PROVIDERS[name](seed, a.direction, a.limit)
            except c.HttpError as e:
                rows, note = [], {"provider": name, "seed": seed, "error": str(e)}
            except Exception as e:  # a provider failing must not kill the run
                rows, note = [], {"provider": name, "seed": seed, "error": repr(e)}
            notes.append(note)
            detail = note.get("error") or note.get("skipped") or ""
            c.log(f"  {name:16s} {len(rows):5d} edges  {detail}")
            all_rows += rows

    c.log(f"\ntotal rows before merge: {len(all_rows)}")

    if a.dry_run or not a.thread:
        for r in all_rows[:20]:
            c.log(f"  {r['year']}  {r['title'][:78]}")
        c.log(f"\n(dry run — nothing written)")
        return 0

    thread = a.thread
    path = thread / "candidates.csv"
    existing = c.read_rows(path)
    merged = merge_into(existing, all_rows)
    c.write_rows(path, merged)
    c.append_query_log(thread, [
        {"source": n["provider"], "mode": f"citation-{a.direction}",
         "query": f"seed:{n['seed']}", "hits": n.get("found", 0)} for n in notes])
    c.write_run(thread, "expand", {"seeds": a.seed, "direction": a.direction,
                                   "providers": chosen, "limit": a.limit,
                                   "notes": notes, "rows_returned": len(all_rows),
                                   "rows_after_merge": len(merged),
                                   "new_rows": len(merged) - len(existing)})
    c.log(f"candidates.csv: {len(existing)} → {len(merged)} "
          f"(+{len(merged) - len(existing)} new)")
    return 0


def merge_into(existing: list[dict], incoming: list[dict]) -> list[dict]:
    """Light merge on identifier only. The real deduplication is dedupe.py --
    this exists so repeated expand runs do not pile up obvious duplicates."""
    index: dict[str, dict] = {}
    for r in existing:
        for k in (f"doi:{r['doi']}" if r["doi"] else "",
                  f"arxiv:{r['arxiv']}" if r["arxiv"] else ""):
            if k:
                index[k] = r
    out = list(existing)
    for r in incoming:
        keys = [k for k in (f"doi:{r['doi']}" if r["doi"] else "",
                            f"arxiv:{r['arxiv']}" if r["arxiv"] else "") if k]
        hit = next((index[k] for k in keys if k in index), None)
        if hit:
            hit["sources"] = c.join_list([hit["sources"], r["sources"]])
            hit["found_by"] = c.join_list([hit["found_by"], r["found_by"]])
            hit["n_sources"] = str(len(c.split_list(hit["sources"])))
            if not hit.get("abstract") and r.get("abstract"):
                hit["abstract"] = r["abstract"]
        else:
            r["n_sources"] = str(len(c.split_list(r["sources"])))
            out.append(r)
            for k in keys:
                index[k] = r
    return out


if __name__ == "__main__":
    sys.exit(main())
