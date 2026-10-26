#!/usr/bin/env python3
"""dedupe.py -- collapse duplicate versions into one row and assign the key.

The same work arrives as an arXiv preprint, a conference paper and an extended
journal version. Matched in this order, first hit wins:

  1. DOI, normalised
  2. arXiv ID, version stripped -- 2509.13597v2 and 2509.13597 are one paper
  3. first-author surname + year + title slug, with fuzzy title matching

The surviving row takes the PUBLISHED version's venue metadata but KEEPS the
arXiv ID as well as the DOI, because Crossref frequently carries no abstract
while arXiv always does -- measured at 56% abstract coverage on Springer LNCS
material in September.

It also assigns the citation key: ours, generated here, before Zotero has
seen anything. Existing keys are never reassigned -- once a key names a file
it is frozen.

  python3 dedupe.py --thread research/threads/my-topic
"""
from __future__ import annotations

import argparse, difflib, sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import common as c

# A published venue beats a preprint for metadata; higher wins.
RANK = {"journal-article": 5, "article": 5, "proceedings-article": 4,
        "conference-paper": 4, "book-chapter": 3, "posted-content": 1,
        "preprint": 1, "": 0}


def rank(row: dict) -> int:
    return RANK.get((row.get("venue_type") or "").lower(), 2)


def match_key(row: dict) -> str:
    slug = c.title_slug(row.get("title", ""))
    au = c.surname(c.split_list(row.get("authors", ""))[0]) if row.get("authors") else ""
    return f"{au}|{row.get('year','')}|{slug}"


def merge_group(rows: list[dict]) -> dict:
    """One row out of many. Best metadata wins per field, nothing is lost."""
    rows = sorted(rows, key=rank, reverse=True)
    out = {**c.blank_row(), **rows[0]}
    for r in rows[1:]:
        for f in ("doi", "arxiv", "url", "venue", "year", "authors", "title", "venue_type"):
            if not out.get(f) and r.get(f):
                out[f] = r[f]
        # keep the longest abstract -- coverage is patchy and uneven
        if len(r.get("abstract") or "") > len(out.get("abstract") or ""):
            out["abstract"] = r["abstract"]
        # never lose a screening decision already made
        for f in ("band", "reason", "screened_by", "screened_at", "zotero_key", "bibkey"):
            if not out.get(f) and r.get(f):
                out[f] = r[f]
    out["sources"] = c.join_list([r.get("sources", "") for r in rows])
    out["found_by"] = c.join_list([r.get("found_by", "") for r in rows])
    out["versions"] = c.join_list(
        [f"doi:{r['doi']}" for r in rows if r.get("doi")] +
        [f"arxiv:{r['arxiv']}" for r in rows if r.get("arxiv")])
    out["n_sources"] = str(len(c.split_list(out["sources"])))
    out["first_seen"] = min((r.get("first_seen") or "9999") for r in rows)
    return out


def cluster(rows: list[dict], fuzzy: float) -> list[list[dict]]:
    """Union-find over the three match rules."""
    parent: dict[int, int] = {i: i for i in range(len(rows))}

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]; i = parent[i]
        return i

    def union(i, j):
        ri, rj = find(i), find(j)
        if ri != rj:
            parent[max(ri, rj)] = min(ri, rj)

    for field in ("doi", "arxiv"):
        seen: dict[str, int] = {}
        for i, r in enumerate(rows):
            v = (r.get(field) or "").strip()
            if not v:
                continue
            if v in seen:
                union(seen[v], i)
            else:
                seen[v] = i

    # Rule 3, bucketed by author+year so this stays O(n * bucket) not O(n^2).
    buckets: dict[str, list[int]] = defaultdict(list)
    for i, r in enumerate(rows):
        au = c.surname(c.split_list(r.get("authors", ""))[0]) if r.get("authors") else ""
        buckets[f"{au}|{r.get('year','')}"].append(i)
    for key, idxs in buckets.items():
        if key.startswith("|") or len(idxs) < 2:
            continue                      # no author -- too weak to match on
        for a in range(len(idxs)):
            for b in range(a + 1, len(idxs)):
                i, j = idxs[a], idxs[b]
                si, sj = c.title_slug(rows[i]["title"]), c.title_slug(rows[j]["title"])
                if not si or not sj:
                    continue
                if si == sj or difflib.SequenceMatcher(None, si, sj).ratio() >= fuzzy:
                    union(i, j)

    groups: dict[int, list[dict]] = defaultdict(list)
    for i, r in enumerate(rows):
        groups[find(i)].append(r)
    return list(groups.values())


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--thread", type=Path, required=True)
    ap.add_argument("--fuzzy", type=float, default=0.93,
                    help="title similarity for rule 3 (default 0.93)")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    path = a.thread / "candidates.csv"
    rows = c.read_rows(path)
    if not rows:
        c.log(f"nothing in {path}")
        return 2

    groups = cluster(rows, a.fuzzy)
    merged = [merge_group(g) for g in groups]
    merged.sort(key=lambda r: (str(r.get("year") or ""), r.get("title") or ""), reverse=True)

    # Assign keys. Existing ones are frozen -- a key that names a file never moves.
    taken = {r["bibkey"] for r in merged if r.get("bibkey")}
    assigned = 0
    for r in merged:
        if r.get("bibkey"):
            continue
        r["bibkey"] = c.make_bibkey(c.split_list(r.get("authors", "")),
                                    r.get("year"), r.get("title", ""), taken)
        taken.add(r["bibkey"]); assigned += 1

    collapsed = len(rows) - len(merged)
    multi = sum(1 for r in merged if int(r.get("n_sources") or 1) > 1)
    c.log(f"rows in        {len(rows)}")
    c.log(f"distinct out   {len(merged)}   (collapsed {collapsed})")
    c.log(f"keys assigned  {assigned}")
    c.log(f"from >1 source {multi}  ({100*multi//max(len(merged),1)}%) "
          f"— September baseline was 10%")

    if a.dry_run:
        c.log("(dry run — nothing written)")
        return 0

    c.write_rows(path, merged)
    c.write_run(a.thread, "dedupe", {"fuzzy": a.fuzzy, "rows_in": len(rows),
                                     "rows_out": len(merged), "collapsed": collapsed,
                                     "keys_assigned": assigned,
                                     "multi_source": multi})
    return 0


if __name__ == "__main__":
    sys.exit(main())
