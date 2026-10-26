#!/usr/bin/env python3
"""status.py -- where is this thread, and what happens next.

Reads the thread folder and says so. No hidden state: the files on disk ARE
the state, which is what makes a thread resumable weeks later by anything
that can read a directory.

  python3 status.py --thread research/threads/my-topic
"""
from __future__ import annotations

import argparse, json, sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import common as c

BANDS = {"1": "core", "2": "probable", "3": "borderline", "4": "out"}
ACCEPTED = {"1", "2"}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--thread", type=Path, required=True)
    ap.add_argument("--papers", type=Path)
    a = ap.parse_args()

    t = a.thread
    if not t.exists():
        c.log(f"no such thread: {t}")
        return 2
    papers = c.papers_dir(t, a.papers)
    rows = c.read_rows(t / "candidates.csv")
    bands = Counter(r.get("band") or "" for r in rows)
    accepted = c.in_scope(rows)          # tier A if tiered, else bands 1-2
    borderline = bands.get("3", 0)
    ingested = [r for r in accepted if r.get("zotero_key")]
    extracted = [r for r in accepted
                 if (papers / f"{r['bibkey']}.md").exists()]
    runs = sorted((t / "runs").glob("*.json")) if (t / "runs").exists() else []

    print(f"\nthread: {t.resolve().name}")
    print("=" * 56)

    thread_md = t / "thread.md"
    defined = False
    if thread_md.exists():
        txt = thread_md.read_text(encoding="utf-8")
        qs = c.thread_block(t, "queries") or ""
        placeholder = any(ln.strip().startswith("<") for ln in qs.splitlines())
        defined = "[TO FILL]" not in txt and "```queries" in txt and not placeholder
    line("1  Define", defined,
         "thread.md has a question, criteria and queries" if defined
         else "thread.md missing, still has [TO FILL] or <placeholder> queries, "
              "or has no ```queries block")

    line("2  Gather", bool(rows), f"{len(rows)} candidates" if rows else "nothing gathered")
    keyed = sum(1 for r in rows if r.get("bibkey"))
    line("3  Dedupe", bool(rows) and keyed == len(rows),
         f"{keyed}/{len(rows)} rows have a citation key" if rows else "—")

    scr = sum(bands.get(b, 0) for b in BANDS)
    line("4  Screen", bool(rows) and scr == len(rows),
         f"{scr}/{len(rows)} screened · " +
         " ".join(f"{BANDS[b]}={bands.get(b,0)}" for b in BANDS) if rows else "—")

    audit = t / "audit.csv"
    line("   Gate B", audit.exists() and not borderline,
         (f"audit.csv drawn ({len(c.read_rows(audit))} rows)" if audit.exists()
          else "run screen.py --audit, then read it")
         + (f" · {borderline} band-3 rows still need your decision" if borderline else ""))

    line("5  Ingest", bool(accepted) and len(ingested) == len(accepted),
         f"{len(ingested)}/{len(accepted)} in-scope rows in Zotero" if accepted
         else "nothing accepted yet")
    pdf = t / "pdf-status.md"
    line("   Gate C", pdf.exists(), "pdf-status.md written — fetch what is listed"
         if pdf.exists() else "produced by ingest.py")

    line("6  Extract", bool(accepted) and len(extracted) == len(accepted),
         f"{len(extracted)}/{len(accepted)} analysis files in {papers.name}/")
    line("   Gate D", False, "run extract_check.py, then read a sample of quotes")

    syn = t / "synthesis.md"
    line("7  Synthesise", syn.exists(),
         "synthesis.md exists" if syn.exists() else "not started")

    print("=" * 56)
    print(f"runs recorded: {len(runs)}")
    if runs:
        last = json.loads(runs[-1].read_text(encoding="utf-8"))
        print(f"last run: {last.get('script')} at {last.get('at')}")
    print(f"\nnext: {next_step(defined, rows, keyed, scr, audit, accepted, ingested, extracted, syn, borderline)}\n")
    return 0


def line(label, done, detail):
    print(f"  [{'x' if done else ' '}] {label:14s} {detail}")


def next_step(defined, rows, keyed, scr, audit, accepted, ingested, extracted, syn,
              borderline=0) -> str:
    if not defined:
        return "Gate A — write thread.md: the question, in/out criteria, and a ```queries block"
    if not rows:
        return "gather.py --thread <thread>"
    if keyed != len(rows):
        return "dedupe.py --thread <thread>"
    if scr < len(rows):
        return "screen.py --emit, have the agent band them, then screen.py --apply"
    if not audit.exists():
        return "screen.py --audit  (Gate B — then read audit.csv)"
    if borderline:
        return (f"Gate B — {borderline} band-3 rows need a human decision: set them to "
                "1, 2 or 4 in audit.csv, then screen.py --apply audit.csv --by <initials>")
    if not accepted:
        return "nothing was accepted — check the criteria, this is a Gate A problem"
    if len(ingested) < len(accepted):
        return "ingest.py --thread <thread>  (then Gate C: pdf-status.md)"
    if len(extracted) < len(accepted):
        return "extract_prep.py --all, draft the analyses, then extract_check.py"
    if not syn.exists():
        return "index.py, then write synthesis.md  (Gate E)"
    return "Gate E — iterate synthesis.md, then decide whether another pass is needed"


if __name__ == "__main__":
    sys.exit(main())
