#!/usr/bin/env python3
"""cite_check.py -- does the new literature cite the old literature?

Written for a thread whose accepted papers split into an old cluster and a new
one with almost nothing in between (75 papers before 2015, ~500 from 2025-26).
The natural reading is that the problem was worked on, dropped for a decade,
and rediscovered under new vocabulary. --old-before and --modern-from set the
two clusters for your own thread.

That reading is an assertion until someone counts citations. This counts them.

Three measures, weakest to strongest:

  1. Does a modern paper cite ANY pre-2015 work at all? A paper citing nothing
     old may simply be a short preprint, so this is context, not evidence.
  2. What share of its references are pre-2015? Compared against the share you
     would expect if it drew on an older field.
  3. Does it cite one of OUR old in-scope papers -- the actual ancestry?
     This is the one that matters. A modern paper that cites old
     general background but never the old work on its own problem has still
     missed the lineage.

Matching is by DOI first and normalised title second, and a title match needs
an exact normalised equality -- no fuzzy ratio. A false match here would
manufacture the continuity the test exists to look for.

Resumable: every paper's result is checkpointed, so an interrupted overnight
run continues instead of starting again.

  python3 cite_check.py --thread <t> --old-before 2015 --modern-from 2023
"""
from __future__ import annotations

import argparse, json, re, statistics, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import common as c

S2 = "https://api.semanticscholar.org/graph/v1/paper"
MODERN_FROM = 2023   # set by --modern-from
OLD_BEFORE = 2015    # set by --old-before


def norm_title(t: str) -> str:
    t = (t or "").lower()
    t = re.sub(r"[^a-z0-9 ]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def year_of(r: dict) -> int | None:
    v = (r.get("year") or "").strip()
    return int(v) if v.isdigit() else None


def s2_id(r: dict) -> str | None:
    doi = c.norm_doi(r.get("doi") or "")
    if doi and not doi.startswith("10.48550/"):
        return f"DOI:{doi}"
    ax = c.norm_arxiv(r.get("arxiv") or "")
    if not ax and doi.startswith("10.48550/arxiv."):
        ax = doi.split("arxiv.", 1)[1]
    return f"arXiv:{ax}" if ax else None


def references(pid: str) -> list[dict] | None:
    """-> the paper's reference list, or None when S2 does not have the paper.

    None and [] mean different things: None is "we could not look", [] is "we
    looked and it cites nothing we can see". Collapsing them would quietly turn
    lookup failures into evidence for the hypothesis.
    """
    try:
        d = c.get_json(f"{S2}/{pid}/references",
                       {"fields": "title,year,externalIds", "limit": 100}, tries=3)
    except Exception:
        return None
    # S2 returns {"data": null} for a paper it knows but holds no references
    # for, so the key being present proves nothing. Checked the value instead
    # after `"data" not in d` let a None through and crashed the run.
    data = d.get("data") if isinstance(d, dict) else None
    if not isinstance(data, list):
        return None
    out = []
    for e in data:
        p = e.get("citedPaper") or {}
        if p:
            out.append(p)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--thread", type=Path, required=True)
    ap.add_argument("--limit", type=int)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--modern-from", type=int, required=True,
                    help="first year of the 'new' literature")
    ap.add_argument("--old-before", type=int, required=True,
                    help="papers before this year count as the 'old' literature")
    a = ap.parse_args()

    rows = c.read_rows(a.thread / "candidates.csv")
    global MODERN_FROM, OLD_BEFORE
    MODERN_FROM, OLD_BEFORE = a.modern_from, a.old_before
    A = c.in_scope(rows)
    old = [r for r in A if (year_of(r) or 9999) < OLD_BEFORE]
    modern = [r for r in A if (year_of(r) or 0) >= MODERN_FROM]

    # the ancestry, indexed for exact lookup
    old_doi = {c.norm_doi(r.get("doi") or "") for r in old}
    old_doi.discard("")
    old_title = {norm_title(r.get("title")): r["bibkey"] for r in old if r.get("title")}

    ck = a.thread / "cite-check-progress.json"
    done = json.loads(ck.read_text()) if ck.exists() else {}
    todo = [r for r in modern if r["bibkey"] not in done and s2_id(r)]
    no_id = [r for r in modern if not s2_id(r)]
    if a.limit:
        todo = todo[:a.limit]

    c.log(f"tier A {len(A)} · pre-{OLD_BEFORE} {len(old)} · {MODERN_FROM}+ {len(modern)}")
    c.log(f"resolvable {len(modern)-len(no_id)} · no identifier {len(no_id)} · "
          f"already done {len(done)} · to check {len(todo)}")

    for i, r in enumerate(todo, 1):
        refs = references(s2_id(r))
        if refs is None:
            done[r["bibkey"]] = {"status": "not in S2"}
        else:
            years = [p.get("year") for p in refs if p.get("year")]
            pre = [y for y in years if y < OLD_BEFORE]
            hits = []
            for p in refs:
                d = c.norm_doi(((p.get("externalIds") or {}).get("DOI") or ""))
                if d and d in old_doi:
                    hits.append(d)
                    continue
                k = old_title.get(norm_title(p.get("title")))
                if k:
                    hits.append(k)
            done[r["bibkey"]] = {"status": "ok", "refs": len(refs),
                                 "dated": len(years), "pre": len(pre),
                                 "ancestry": sorted(set(hits))}
        if i % 10 == 0 or i == len(todo):
            ck.write_text(json.dumps(done, indent=1))
            c.log(f"  [{i}/{len(todo)}] checkpointed")
    ck.write_text(json.dumps(done, indent=1))

    ok = {k: v for k, v in done.items() if v.get("status") == "ok"}
    miss = len(done) - len(ok)
    with_refs = {k: v for k, v in ok.items() if v["dated"] > 0}
    L = []
    def say(s=""):
        print(s); L.append(s)

    say("# Does the new work cite the old work?")
    say()
    say(f"Tier A holds {len(old)} papers before {OLD_BEFORE} and {len(modern)} "
        f"from {MODERN_FROM} on. This checks whether the second group cites the "
        f"first.")
    say()
    say(f"- modern tier-A papers: **{len(modern)}**")
    say(f"- of those with a resolvable identifier: {len(modern)-len(no_id)}")
    say(f"- Semantic Scholar had a reference list for: **{len(with_refs)}**")
    say(f"- not in S2 or no dated references: {miss + len(ok) - len(with_refs)}")
    say()
    if not with_refs:
        say("No reference lists retrieved — nothing can be concluded.")
    else:
        anyold = sum(1 for v in with_refs.values() if v["pre"] > 0)
        anc = {k: v for k, v in with_refs.items() if v["ancestry"]}
        shares = [v["pre"] / v["dated"] for v in with_refs.values()]
        say("## The three measures")
        say()
        say(f"**1. Cites any pre-{OLD_BEFORE} work:** {anyold} of {len(with_refs)} "
            f"({anyold/len(with_refs):.0%})")
        say()
        say(f"**2. Share of references that are pre-{OLD_BEFORE}:** "
            f"median {statistics.median(shares):.1%}, mean {statistics.fmean(shares):.1%}")
        say()
        say(f"**3. Cites one of the {len(old)} tier-A ancestry papers:** "
            f"**{len(anc)} of {len(with_refs)} ({len(anc)/len(with_refs):.1%})**")
        say()
        if anc:
            say("Those that do:")
            say()
            for k, v in sorted(anc.items(), key=lambda kv: -len(kv[1]["ancestry"]))[:25]:
                say(f"- `{k}` → {', '.join(v['ancestry'][:6])}")
            say()
        cited = {}
        for v in with_refs.values():
            for x in v["ancestry"]:
                cited[x] = cited.get(x, 0) + 1
        say(f"Ancestry papers cited at least once: **{len(cited)} of {len(old)}**")
        if cited:
            say()
            for x, n in sorted(cited.items(), key=lambda kv: -kv[1])[:15]:
                say(f"- {x}: cited by {n}")
        say()
        say("## Reading this")
        say()
        say("Measure 3 is the one that carries weight. A modern paper may cite "
            "plenty of old cryptography and still never touch the mobile-agent "
            "tradition that posed the same problem; measure 1 would count that "
            "as continuity and measure 3 would not.")
        say()
        say("Caveat worth keeping: S2 reference lists are incomplete for grey "
            "literature, and much of this corpus is preprints and standards. "
            "A low number is partly a coverage artefact, so the honest claim is "
            "bounded by how many reference lists were retrieved at all "
            f"({len(with_refs)} of {len(modern)}).")

    out = a.out or (a.thread / "citation-gap.md")
    out.write_text("\n".join(L) + "\n")
    c.log(f"\n→ {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
