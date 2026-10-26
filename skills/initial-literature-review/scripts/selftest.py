#!/usr/bin/env python3
"""selftest.py -- known-answer tests. Run after touching any script.

The citation test is the important one. In September, ResearchRabbit found by
hand the single most valuable result of the whole three-round exercise:
seeded with Camenisch & Lysyanskaya 2002 and read forward, it surfaced
Deochake 2026, which appeared in NONE of the 894 papers the seven other tools
returned. If expand.py cannot reproduce that, it has not replaced the manual
step and must say so rather than quietly assume coverage.

It also pins the finding that OpenAlex alone is not enough -- it holds
Deochake as a node but records zero references for it.
"""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import common as c, expand, extract_check as xc

CAMENISCH = "10.1007/3-540-45708-9_5"   # Dynamic Accumulators, CRYPTO 2002
TARGET = "heartbeat"                     # Deochake 2026
fails = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}{'  — ' + detail if detail else ''}")
    if not ok:
        fails.append(name)


def test_units():
    print("\nunit — normalisation and keys")
    check("arXiv version stripped", c.norm_arxiv("https://arxiv.org/abs/2509.13597v2") == "2509.13597")
    check("DOI normalised", c.norm_doi("https://doi.org/10.56553/POPETS-2023-0093") == "10.56553/popets-2023-0093")
    check("bibkey format", c.make_bibkey(["Mir, Omid"], 2023,
          "Practical Delegatable Anonymous Credentials From Equivalence Class Signatures") == "mir2023delegatable")
    check("collision suffixed", c.make_bibkey(["Mir, Omid"], 2023,
          "Practical Delegatable Anonymous Credentials", {"mir2023delegatable"}) == "mir2023delegatablea")


def test_csv_keeps_foreign_columns():
    """A later stage's column must survive a write by an earlier stage.

    tier.py adds tier/tier_reason/tiered_by to candidates.csv. common.write_rows
    used to write a fixed field list with extrasaction="ignore", which deleted
    them without a word -- on 4 October an ingest run destroyed 4,329 tier
    judgements that way, and the only symptom was a filter silently matching
    nothing and the run ingesting seven times what it should have.
    """
    print("\nunit — CSV preserves columns this module does not own")
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / "candidates.csv"
        row = {**c.blank_row(), "bibkey": "x2026y", "title": "T",
               "tier": "A", "tier_reason": "because", "tiered_by": "agent"}
        c.write_rows(f, [row])
        back = c.read_rows(f)[0]
        check("foreign column survives a write", back.get("tier") == "A")
        check("its companions survive too",
              back.get("tier_reason") == "because" and back.get("tiered_by") == "agent")
        check("owned columns still written", back.get("bibkey") == "x2026y")


def test_quote_matching():
    """The property the whole extraction gate rests on: a quote that is not in
    the paper must be caught, and a real one must survive PDF text mangling."""
    print("\nunit — quote verification")
    src = xc.norm("The scheme is secure under the generic group model. "
                  "We evaluate on a stan-\ndard benchmark suite.")
    check("real quote found", xc.norm("secure under the generic group model") in src)
    check("quote survives hyphen line-break",
          xc.norm("evaluate on a standard benchmark") in src)
    check("fabricated quote rejected",
          xc.norm("evaluated on a fleet of quantum abacuses") not in src)
    check("case and punctuation ignored",
          xc.norm("SECURE, under the Generic-Group Model!") in src)


def test_citation_graph():
    print("\nknown-answer — crypto → agent citation crossing")
    oa, _ = expand.oa_edges(CAMENISCH, "forward", 1200)
    s2, _ = expand.s2_edges(CAMENISCH, "forward", 1200)
    print(f"    openalex {len(oa)} edges · semanticscholar {len(s2)} edges")

    def has(rows):
        return any(TARGET in (r["title"] or "").lower() for r in rows)

    check("OpenAlex alone misses it (the reason for multi-provider)",
          not has(oa), "if this starts passing, OpenAlex has fixed its coverage")
    check("Semantic Scholar finds it", has(s2))
    check("union reproduces the manual ResearchRabbit result", has(oa + s2))
    check("seed resolves and returns a real corpus", len(oa) > 400 and len(s2) > 400)


if __name__ == "__main__":
    test_units()
    test_csv_keeps_foreign_columns()
    test_quote_matching()
    if "--offline" not in sys.argv:
        test_citation_graph()
    print(f"\n{'all passed' if not fails else str(len(fails)) + ' FAILED: ' + ', '.join(fails)}")
    sys.exit(1 if fails else 0)
