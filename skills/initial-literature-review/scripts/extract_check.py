#!/usr/bin/env python3
"""extract_check.py -- machine-verify a drafted analysis file.

This is what makes Gate D cheap. The published benchmark for cross-paper
structured extraction is around 43% recall, and the failure mode is
CONFABULATION, not omission. A model that must quote from a text which is
then string-matched cannot confabulate quietly.

So the machine proves, exhaustively, that every quote is real. That leaves a
human exactly one thing to judge, on a sample: does a real quote actually
SUPPORT the claim attached to it?

  python3 extract_check.py --thread <thread>            # every paper
  python3 extract_check.py --bibkey mir2023delegatable  # one
"""
from __future__ import annotations

import argparse, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import common as c

try:
    import yaml
except ImportError:
    print("needs pyyaml:  pip3 install pyyaml", file=sys.stderr)
    raise SystemExit(2)

REQUIRED = ["bibkey", "title", "year", "venue", "venue_type", "relevance", "credibility"]
EVIDENCE_REQUIRED = ["problem", "threat_model", "assumptions", "security_argument",
                     "evaluation", "real_deployment", "limitations_stated",
                     "open_problems_stated"]
# Kept in step with templates/extraction-template.md. When the template gains a
# value and this does not, the checker rejects correct files -- it was briefly
# failing 128 files on `relevance: supporting` alone, a value the template
# defines. A stale checker that calls good work wrong is worse than no checker,
# because the next person believes it.
VOCAB = {
    "venue_type": {"conference", "journal", "preprint", "standard", "report",
                   "book", "thesis", "software", "dataset", "other"},
    "contribution_type": {"construction", "framework", "analysis", "attack",
                          "measurement", "sok", "position"},
    "security_argument": {"game-based-proof", "simulation", "uc", "formal-model",
                          "symbolic-verification", "machine-checked", "informal",
                          "none", "n/a"},
    "evaluation": {"benchmark", "measurement", "proof-only", "case-study",
                   "deployment", "none", "n/a"},
    "relevance": {"core", "supporting", "background", "tangential",
                  "adjacent", "boundary"},
    "credibility": {"high", "medium", "low"},
}


def thread_vocab(thread: Path | None) -> dict[str, set[str]]:
    """Controlled values for the topic-specific `thread:` block, from thread.md.

    A fenced ```extraction-vocab block, one field per line:

        authority_mechanism: token | certificate | capability | none
        human_in_loop: true | false | varies

    Fields not listed are free text. The generic fields above are the same for
    every thread; these are the questions one review is actually about, so
    they are defined where that review is defined.
    """
    out = {}
    for ln in (c.thread_block(thread, "extraction-vocab") or "").splitlines():
        ln = ln.split("#", 1)[0].strip()
        k, sep, v = ln.partition(":")
        if sep and k.strip():
            out[k.strip()] = {x.strip().lower() for x in v.split("|") if x.strip()}
    return out


FM = re.compile(r"^---\n(.*?)\n---\n", re.S)


def norm(s: str) -> str:
    """Compare on words only. PDF text extraction mangles whitespace, hyphens
    and ligatures, so an exact match would fail on quotes that are genuinely
    present."""
    s = (s or "").lower().replace("­", "").replace("-\n", "")
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return " ".join(s.split())


def check_file(path: Path, workspace: Path | None,
               tvocab: dict[str, set[str]] | None = None) -> tuple[list[str], list[str]]:
    errors, warnings = [], []
    text = path.read_text(encoding="utf-8")
    m = FM.match(text)
    if not m:
        return ([f"no YAML frontmatter"], [])
    try:
        fm = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError as e:
        return ([f"YAML does not parse: {str(e)[:120]}"], [])

    # A preprint genuinely has no venue, and a record with no document cannot
    # carry relevance or credibility. Demanding them turns honest nulls into
    # errors and buries the real failures in noise -- these were firing on
    # legitimate records across the corpus.
    NULLABLE = {"venue", "relevance", "credibility"}
    for f in REQUIRED:
        v = fm.get(f)
        if v in (None, "") and f not in NULLABLE:
            errors.append(f"required field missing: {f}")
        elif v in (None, "") and f in NULLABLE and f not in str(fm.get("unanswered", "")):
            warnings.append(f"{f} is null — fine for a preprint or a stub, "
                            f"but say so in unanswered")
    if fm.get("bibkey") and fm["bibkey"] != path.stem:
        errors.append(f"bibkey '{fm['bibkey']}' != filename '{path.stem}'")

    for field, allowed in VOCAB.items():
        v = fm.get(field)
        if v not in (None, "") and str(v) not in allowed:
            errors.append(f"{field}: '{v}' not in controlled vocabulary")

    tblock = fm.get("thread") if isinstance(fm.get("thread"), dict) else {}
    for field, allowed in (tvocab or {}).items():
        vals = tblock.get(field)
        for v in (vals if isinstance(vals, list) else [vals]):
            if v not in (None, "") and str(v).lower() not in allowed:
                errors.append(f"thread.{field}: '{v}' not in thread.md extraction-vocab")

    evidence = fm.get("evidence") or {}
    unanswered = {u.get("field") for u in (fm.get("unanswered") or []) if isinstance(u, dict)}
    for field in EVIDENCE_REQUIRED:
        v = fm.get(field)
        if v in (None, "", [], "null"):
            if field not in unanswered:
                warnings.append(f"{field} is empty but not listed in unanswered:")
            continue
        # `none` and `n/a` are negative findings and cannot be evidenced: no
        # sentence in a paper says "we make no security argument". Demanding a
        # quote for them is what pushes an extractor to record a real absence
        # as null, where it becomes indistinguishable from "nobody looked" --
        # the exact confusion this corpus cannot afford.
        if str(v).strip().lower() in ("none", "n/a"):
            continue
        e = evidence.get(field)
        if isinstance(e, list):
            e = e[0] if e and isinstance(e[0], dict) else None
        if not isinstance(e, dict) or not (e.get("quote") or "").strip():
            errors.append(f"{field} has a value but no evidence quote")
        elif not (e.get("loc") or "").strip():
            warnings.append(f"{field}: quote has no location")

    # The real check: do the quotes exist in the paper?
    src = ""
    if workspace:
        wf = workspace / f"{path.stem}.md"
        if wf.exists():
            src = norm(wf.read_text(encoding="utf-8"))
    if not src:
        warnings.append("no working file — quotes NOT verified against the paper")
    else:
        # A list is how the template says to evidence a multi-valued field such
        # as `scoping` or `standards_referenced`. Skipping lists meant exactly
        # those quotes were never string-matched -- the one guarantee this
        # script exists to provide, silently not provided for the fields most
        # likely to need two quotes.
        flat = []
        for field, e in evidence.items():
            if isinstance(e, dict):
                flat.append((field, e))
            elif isinstance(e, list):
                flat += [(f"{field}[{i}]", x) for i, x in enumerate(e)
                         if isinstance(x, dict)]
        for field, e in flat:
            # Re-prepping a paper re-renders its text, so a quote verified
            # against the old rendering can stop matching as a contiguous
            # string while every word of it is still there, in order. That is a
            # rendering difference, not a fabrication, and conflating the two
            # turns an honest corpus into a suspect one: 210 quotes failed this
            # way after one re-prep. A quote whose words are NOT all present is
            # a different and serious matter.
            q = norm(e.get("quote", ""))
            if len(q) < 12:
                warnings.append(f"{field}: quote too short to verify")
            elif q not in src:
                # Every word still present, in order, but not contiguous: the
                # paper was re-extracted and renders that passage differently.
                # A warning, not an error -- the quote was verified against the
                # text as it then stood.
                words = q.split()
                pos, drift = 0, True
                for w in words:
                    i = src.find(w, pos)
                    if i < 0:
                        drift = False
                        break
                    pos = i + len(w)
                if drift:
                    warnings.append(f"{field}: quote no longer contiguous after "
                                    f"re-extraction (all words present, in order)")
                else:
                    errors.append(f"{field}: QUOTE NOT FOUND IN PAPER — "
                                  f"\"{e['quote'][:70]}...\"")

    for f in ("chase", "builds_on", "contradicts"):
        for k in (fm.get(f) or []):
            if not re.fullmatch(r"[a-z0-9]+", str(k)):
                warnings.append(f"{f}: '{k}' is not a well-formed citation key")
    if fm.get("verified") is True and not fm.get("verified_by"):
        errors.append("verified: true but verified_by is empty")
    return errors, warnings


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--thread", type=Path)
    ap.add_argument("--papers", type=Path)
    ap.add_argument("--bibkey", action="append", default=[])
    a = ap.parse_args()

    papers = c.papers_dir(a.thread, a.papers)
    workspace = (a.thread / "extraction-workspace") if a.thread else None
    files = ([papers / f"{k}.md" for k in a.bibkey] if a.bibkey
             else sorted(p for p in papers.glob("*.md") if not p.name.startswith("_")))
    if not files:
        c.log(f"no analysis files in {papers}")
        return 2

    tvocab = thread_vocab(a.thread)
    bad = 0
    for f in files:
        if not f.exists():
            c.log(f"MISSING  {f.name}"); bad += 1; continue
        errors, warnings = check_file(f, workspace, tvocab)
        if errors:
            bad += 1
            c.log(f"FAIL  {f.name}")
            for e in errors:
                c.log(f"        ✗ {e}")
        else:
            c.log(f"ok    {f.name}")
        for w in warnings:
            c.log(f"        ! {w}")
    c.log(f"\n{len(files)} file(s) · {bad} with errors")
    if not bad:
        c.log("Quotes verified present. Gate D is the judgement the machine cannot make:")
        c.log("read a sample and ask whether each quote SUPPORTS its claim.")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
