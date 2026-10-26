#!/usr/bin/env python3
"""add_ids.py -- merge papers found OUTSIDE the scripted sources.

The pipeline runs three search mechanisms, but two of them are partly manual by
necessity: Google Scholar cannot be automated at all, DBLP sits behind an
anti-bot wall, ResearchRabbit needs a login, and LLM-driven searching is done
by the agent rather than by a script. Everything those turn up still has to
land in the same corpus, with the same provenance, or the audit trail has a
hole in it.

This resolves bare identifiers or titles into full rows and merges them, marked
with which mechanism found them.

  python3 add_ids.py --thread <thread> --source llm-search --id 2604.23280 --id 2605.05440
  python3 add_ids.py --thread <thread> --source publish-or-perish --file ids.txt
  python3 add_ids.py --thread <thread> --source researchrabbit --title "Some Paper Title"
"""
from __future__ import annotations

import argparse, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import common as c
from expand import merge_into, _oa_row

OPENALEX = "https://api.openalex.org/works"
ARXIV = "http://export.arxiv.org/api/query"
import xml.etree.ElementTree as ET

NS = {"a": "http://www.w3.org/2005/Atom"}


def from_arxiv(aid: str, source: str) -> dict | None:
    txt = c.get_text(ARXIV, {"id_list": c.norm_arxiv(aid), "max_results": 1})
    e = ET.fromstring(txt).find("a:entry", NS)
    if e is None or "Error" in (e.findtext("a:title", "", NS) or ""):
        return None
    return {**c.blank_row(),
            "title": " ".join((e.findtext("a:title", "", NS) or "").split()),
            "authors": c.join_list([a.findtext("a:name", "", NS) for a in e.findall("a:author", NS)]),
            "year": (e.findtext("a:published", "", NS) or "")[:4],
            "venue": "arXiv", "venue_type": "preprint",
            "doi": c.norm_doi(e.findtext("a:doi", "", NS)),
            "arxiv": c.norm_arxiv(e.findtext("a:id", "", NS) or aid),
            "url": e.findtext("a:id", "", NS) or "",
            "abstract": " ".join((e.findtext("a:summary", "", NS) or "").split())[:4000],
            "sources": source, "found_by": f"{source}:id:{aid}",
            "first_seen": c.now_iso()}


def from_openalex(q: str, source: str, by_doi: bool) -> dict | None:
    if by_doi:
        try:
            w = c.get_json(f"{OPENALEX}/doi:{c.norm_doi(q)}", {"mailto": c.MAILTO})
        except c.HttpError:
            return None
    else:
        r = c.get_json(OPENALEX, {"filter": f'title.search:{q}', "per-page": 1,
                                  "mailto": c.MAILTO})
        if not r.get("results"):
            return None
        w = r["results"][0]
    row = _oa_row(w, f"{source}:lookup:{q}")
    row["sources"] = source
    return row


def resolve(token: str, source: str) -> tuple[dict | None, str]:
    token = token.strip()
    if not token or token.startswith("#"):
        return None, "skipped"
    if re.fullmatch(r"(arxiv:)?\d{4}\.\d{4,5}(v\d+)?", token, re.I):
        return from_arxiv(token, source), "arxiv"
    if token.lower().startswith("10.") or "doi.org/" in token.lower():
        return from_openalex(token, source, by_doi=True), "doi"
    return from_openalex(token, source, by_doi=False), "title"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--thread", type=Path, required=True)
    ap.add_argument("--source", required=True,
                    help="which mechanism found these, e.g. llm-search, "
                         "publish-or-perish, researchrabbit, asta, standards")
    ap.add_argument("--id", action="append", default=[], help="arXiv ID, DOI or title")
    ap.add_argument("--file", type=Path, help="one identifier or title per line")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    tokens = list(a.id)
    if a.file:
        tokens += [l.strip() for l in a.file.read_text(encoding="utf-8").splitlines()]

    rows, notes = [], []
    for tok in tokens:
        try:
            row, how = resolve(tok, a.source)
        except Exception as e:
            row, how = None, f"error: {repr(e)[:90]}"
        if row:
            rows.append(row)
            c.log(f"  ok    [{how}] {tok:22s} {row['title'][:56]}")
        elif how != "skipped":
            c.log(f"  MISS  [{how}] {tok}")
        notes.append({"token": tok, "resolved_by": how, "found": bool(row)})

    c.log(f"\nresolved {len(rows)} of {len([t for t in tokens if t.strip() and not t.startswith('#')])}")
    if a.dry_run:
        c.log("(dry run — nothing written)")
        return 0

    path = a.thread / "candidates.csv"
    existing = c.read_rows(path)
    merged = merge_into(existing, rows)
    c.write_rows(path, merged)
    c.append_query_log(a.thread, [{"source": a.source, "mode": "manual-identifier",
                                   "query": f"{len(tokens)} identifiers",
                                   "available": len(tokens), "taken": len(rows)}])
    c.write_run(a.thread, f"add-ids-{a.source}",
                {"source": a.source, "tokens": len(tokens), "resolved": len(rows),
                 "rows_after_merge": len(merged),
                 "new_rows": len(merged) - len(existing), "notes": notes})
    c.log(f"candidates.csv: {len(existing)} → {len(merged)} (+{len(merged)-len(existing)} new)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
