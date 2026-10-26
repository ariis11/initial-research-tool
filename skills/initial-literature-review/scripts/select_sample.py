#!/usr/bin/env python3
"""select_sample.py -- pick a stratified extraction sample, per area.

Added 10 October 2026 for the phd-field thread: a broad map over twelve areas
with thousands of accepted papers, and a plan due in two days. Extracting
everything is not the job; extracting the strongest few per area is enough to
say what each area is, who is in it, and what it measures.

Areas come from the screening reason, which starts with the area code:
"[C2] Capability tokens ...". Per area, papers are ranked by:

  band 1 before band 2
  surveys / SoKs first (up to --surveys per area) -- they are the map's spine
  then citations per year since publication (Semantic Scholar, fetched here,
  500 per request), so a 2026 paper with 30 citations beats a 2019 one with 60
  peer-reviewed venue over preprint as a tie-break

The sample is marked tier A, the rest of the accepted rows tier B -- the same
convention ingest.py already follows (it ingests tier A only).

  python3 select_sample.py --thread <thread> --per-area 12 --surveys 2
"""
from __future__ import annotations

import argparse, json, re, sys, time, urllib.request
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import common as c

AREA = re.compile(r"^\s*\[([A-Za-z0-9_.-]+)\]")
SURVEY = re.compile(r"\b(survey|SoK|systematization|systematisation|review|taxonomy|landscape)\b", re.I)
GREY = re.compile(r"arxiv|preprint|ssrn|zenodo|research square|techrxiv|openreview", re.I)
S2_BATCH = ("https://api.semanticscholar.org/graph/v1/paper/batch"
            "?fields=citationCount,year,venue,publicationTypes")
THIS_YEAR = 2026


def citations(rows: list[dict]) -> dict[str, int]:
    ids = []
    for r in rows:
        if d := c.norm_doi(r.get("doi")):
            ids.append(("DOI:" + d, r["bibkey"]))
        elif x := c.norm_arxiv(r.get("arxiv")):
            ids.append(("ARXIV:" + x, r["bibkey"]))
    out = {}
    hdrs = {"Content-Type": "application/json", "User-Agent": c.UA,
            **c.auth_headers("api.semanticscholar.org")}
    for i in range(0, len(ids), 500):
        chunk = ids[i:i + 500]
        for attempt in range(4):
            time.sleep(1.1)
            try:
                req = urllib.request.Request(S2_BATCH, method="POST", headers=hdrs,
                                             data=json.dumps({"ids": [k for k, _ in chunk]}).encode())
                with urllib.request.urlopen(req, timeout=120) as resp:
                    res = json.loads(resp.read())
                break
            except Exception as e:
                c.log(f"  s2 retry {attempt + 1}: {e!r}"[:120])
                time.sleep(10 * 2 ** attempt)
        else:
            continue
        for (_, key), p in zip(chunk, res):
            if p and p.get("citationCount") is not None:
                out[key] = p["citationCount"]
    return out


def score(r: dict, cites: dict) -> tuple:
    y = int(str(r.get("year") or THIS_YEAR)[:4]) if str(r.get("year") or "")[:4].isdigit() else THIS_YEAR
    per_year = cites.get(r["bibkey"], 0) / max(1, THIS_YEAR - y + 1)
    reviewed = 0 if GREY.search(f"{r.get('venue', '')} {r.get('venue_type', '')}") or not r.get("venue") else 1
    return (r["band"] == "1", per_year, reviewed, bool((r.get("abstract") or "").strip()))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--thread", type=Path, required=True)
    ap.add_argument("--per-area", type=int, default=12)
    ap.add_argument("--surveys", type=int, default=2)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    path = a.thread / "candidates.csv"
    rows = c.read_rows(path)
    acc = [r for r in rows if r.get("band") in ("1", "2")]
    # Screeners flag the weaker copy of a near-duplicate in its reason; never
    # sample the same paper twice.
    sampleable = [r for r in acc if not re.search(r"duplicate of", r.get("reason") or "", re.I)]
    by_area = defaultdict(list)
    for r in sampleable:
        m = AREA.match(r.get("reason") or "")
        by_area[m.group(1) if m else "??"].append(r)
    c.log(f"{len(acc):,} accepted: " + ", ".join(f"{k} {len(v)}" for k, v in sorted(by_area.items())))

    cites = citations(acc)
    c.log(f"citation counts for {len(cites):,} of {len(acc):,}")

    chosen = []
    report = {}
    for area, pool in sorted(by_area.items()):
        if area == "??":
            continue
        pool.sort(key=lambda r: score(r, cites), reverse=True)
        # dedupe.py misses some versions (a 2025 preprint and its 2026 venue
        # copy under different keys) -- keep the first of each title.
        seen, uniq = set(), []
        for r in pool:
            t = c.title_slug(r["title"])
            if t not in seen:
                seen.add(t); uniq.append(r)
        pool = uniq
        surveys = [r for r in pool if SURVEY.search(r["title"])][:a.surveys]
        rest = [r for r in pool if r not in surveys][:a.per_area - len(surveys)]
        pick = surveys + rest
        chosen += pick
        report[area] = {"accepted": len(pool), "sampled": len(pick), "surveys": len(surveys)}

    keys = {r["bibkey"] for r in chosen}
    for r in acc:
        r["tier"] = "A" if r["bibkey"] in keys else "B"
        r["tier_reason"] = "extraction sample" if r["bibkey"] in keys else "accepted, not sampled"
        r["tiered_by"] = "select_sample.py"
    c.log(f"sample: {len(chosen)} papers")
    for k, v in report.items():
        c.log(f"  {k}: {v['sampled']:3d} of {v['accepted']:5d} (surveys {v['surveys']})")
    if a.dry_run:
        return 0
    c.write_rows(path, rows)
    (a.thread / "sample.md").write_text(
        "# Extraction sample\n\n| area | bibkey | band | cites | year | venue | title |\n|---|---|---|---:|---|---|---|\n"
        + "\n".join(f"| {AREA.match(r['reason']).group(1)} | `{r['bibkey']}` | {r['band']} | "
                    f"{cites.get(r['bibkey'], '')} | {r['year']} | {r['venue'][:30]} | {r['title'][:90]} |"
                    for r in sorted(chosen, key=lambda r: r["reason"][:4])) + "\n",
        encoding="utf-8")
    c.write_run(a.thread, "select_sample", {"per_area": a.per_area, "surveys": a.surveys,
                                            "areas": report, "sampled": len(chosen),
                                            "unlabelled": len(by_area.get("??", []))})
    return 0


if __name__ == "__main__":
    sys.exit(main())
