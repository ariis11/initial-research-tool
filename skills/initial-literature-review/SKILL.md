---
name: initial-literature-review
description: Run a first-pass literature review of an unfamiliar research area - define the thread, gather from several scholarly sources, dedupe, screen in bands with a human audit, ingest into Zotero, fetch PDFs, extract one quoted analysis file per paper, and synthesise. Use when someone says "look into X", wants a map of a field, a related-work or state-of-the-art section, or wants to know whether an area is already solved. Not for a single factual lookup, staying current in a known area, or deep work on papers already chosen.
---

# Initial literature review

A repeatable way from *"we should look into X"* to a defensible map of the field around X: what exists, who works on it, how it divides, and what its own authors call open. The full definition is in `reference/method.md`; the step-by-step for humans, with where every file is saved, is `reference/workflow.md`. Read it before a first run, and check the request against the "When *not* to use it" section of `reference/method.md` before starting.

**The rule everything follows:** deterministic work is a script, judgement is you (the agent), and the human decides at five gates. At a gate, **stop, show what is needed, and wait**. Never approve a gate on the human's behalf.

## Where things are

- The scripts are in `scripts/` inside this skill's base directory. Call them by absolute path: `python3 <skill-dir>/scripts/status.py ...`. `scripts/README.md` lists every script.
- The user's work lives in **their** workspace, never in this skill folder:
  `research/threads/<thread>/` per thread, `research/papers/<bibkey>.md` shared across threads. Ask where the workspace is if it isn't obvious; default to `./research` in the current project.
- Templates: `templates/thread.md` (Gate A skeleton), `templates/extraction-template.md` (fields for every paper), `templates/thread-block-example.md` (a worked topic-specific block), `templates/extraction-example.md` (one filled file).

## Before the first run

Run `python3 <skill-dir>/scripts/check_access.py`. If `ILR_MAILTO` is not set, Python is older than 3.12, PyYAML is missing, or Zotero is unreachable, walk the user through `reference/setup.md` step by step. Keys go in `~/.ilr-env`, typed by the user. **Never ask for a key in chat, and never write one into a file yourself.**

## Always start with status

```bash
python3 <skill-dir>/scripts/status.py --thread <thread>
```

It reads the folder and names the next step. The files on disk are the whole state, so a thread can be resumed weeks later.

## The stages

Below, `S=<skill-dir>/scripts` and `T=<workspace>/threads/<thread>`.

### 1 · Define → Gate A

Copy `templates/thread.md` to `$T/thread.md` and fill it **in conversation with the user**: the question, in/out criteria, the boundary with neighbouring work, seed papers, and queries in **every vocabulary** the area spans. One vocabulary searched in one tool misses most of a field (see `reference/evidence-gathering.md`). Optional blocks in `thread.md`: `sources`, `relevance`, `extraction-vocab`.

A search built to confirm a hypothesis finds the hypothesis. Keep a first pass broad, and record any hypothesis as one thing to test, not as the frame.

Before Gate A, tell the user which Zotero library and collection the papers will go to (`zotero-cli library list`; the collection is the thread folder name).

**Gate A: the user approves `thread.md`. Nothing is gathered before that.**

### 2 · Gather

```bash
python3 $S/gather.py --thread $T                      # all queries, all default sources
python3 $S/expand.py --thread $T --seed <DOI> --direction forward   # per seed, old ones especially
python3 $S/add_ids.py --thread $T --source <tool> --id <doi|arxiv> # finds from elsewhere
```

Long runs go in the background. Papers found by hand or by an LLM search tool go in through `add_ids.py` with an honest `--source`. Then `backfill_abstracts.py` for rows missing an abstract, and `corpus_report.py` for a readable picture of what came back.

### 3 · Dedupe

```bash
python3 $S/dedupe.py --thread $T
```

This assigns the citation key (`firstauthor` + `year` + `keyword`). The key names the analysis file, sits in Zotero and is what LaTeX cites. **Never invent, rename or reassign a key.**

### 4 · Screen → Gate B

```bash
python3 $S/screen.py --thread $T --emit        # writes $T/screening/batch-NNN.json
```

Read each batch and judge each paper from title, abstract and venue only, **against the criteria in thread.md, not your own sense of interest**:
1 = core, 2 = probable, 3 = borderline (a human decides), 4 = out. One-line reason each. Write the decisions to `$T/screening/decisions-NNN.json` as `[{"bibkey": ..., "band": "1", "reason": ...}]`, then:

```bash
python3 $S/screen.py --thread $T --apply $T/screening/decisions-NNN.json
python3 $S/screen.py --thread $T --stats
python3 $S/screen.py --thread $T --audit       # writes audit.csv
```

Large corpora can be split across subagents, one batch range each. If so, check consistency with `screener_consistency.py --boundaries <last batch of each range>`, or double-screen a sample and run `screener_agreement.py`. If band 3 is more than a quarter of the corpus, the criteria are too vague: go back to Gate A instead of pushing on.

**Gate B: the user reads `audit.csv`, overturns what is wrong, and gives every band-3 row a final band (1, 2 or 4).** Then write it back with `screen.py --thread $T --apply $T/audit.csv --by <their initials>`. `status.py` will not move past Gate B while any band 3 remains. Band 4 matters most: a wrongly dropped paper is invisible from then on. Never re-run `--audit` before the user's edits are applied, because it overwrites `audit.csv`.

Optional second cut for big corpora: `tier.py --emit/--apply` splits accepted rows into A (the review proper), B (background) and `-` (drop). Once a thread is tiered, the later steps take only tier A.

### 5 · Ingest and PDFs → Gate C

```bash
python3 $S/ingest.py --thread $T               # accepted rows → Zotero, writes pdf-status.md
python3 $S/fetch_pdfs.py --thread $T           # free copies from Zenodo, arXiv, ePrint
python3 $S/missing_pdfs.py --thread $T         # what is left, grouped by publisher → missing-pdfs.md
```

**Gate C: the user fetches licensed PDFs in a browser.** Never script a paywall, never log in to a publisher, never bypass bot protection. When the user has downloaded files, attach them with `attach_local.py --thread $T --from ~/Downloads` (exact DOI match) or `attach_downloads.py` (title match, dry run first). With a library holdings spreadsheet, `holdings.py` checks Springer entitlement offline.

### 6 · Extract → Gate D

Settle the thread's own `thread:` block and its `extraction-vocab` with the user **before** the first file. A field added later means re-reading every finished paper.

```bash
python3 $S/extract_prep.py --thread $T --all --limit 5   # full text into $T/extraction-workspace/
```

For each paper, read the working file and write `<workspace>/papers/<bibkey>.md` following `templates/extraction-template.md`. Rules that are not negotiable:

- **Every judgement field carries a verbatim quote** with its location. Copy quotes from the working file and never paraphrase inside quote marks.
- **`null` means not established and gets an `unanswered` entry. `none` means checked and absent.** Never guess.
- **`chase`, `builds_on` and `contradicts` hold only keys that exist.** A paper worth chasing but not in the corpus goes in `chase_unresolved` as free text.
- `verified` stays `false`. Only a human sets it.

```bash
python3 $S/extract_check.py --thread $T        # every quote string-matched against the paper
```

Always pass `--thread`, and keep `$T/extraction-workspace/` until Gate D is done: quotes are verified against those files, and without them the check only warns.

Fix every error. **Gate D: the user reads a sample and judges whether each quote actually supports its claim.** The machine has only shown that the quotes exist.

### 7 · Synthesise → Gate E

```bash
python3 $S/index.py --papers <workspace>/papers          # _index.csv, the comparison table
python3 $S/bib.py --papers <workspace>/papers --out <workspace>/library.bib
```

Write `$T/synthesis.md` from the table and the files: how the area divides, who is in it, recurring assumptions, and the **stated** open problems (quoted) and **structural** ones (literatures that address the same problem without citing each other). Every claim cites a key.

Do not claim "nobody has done X" from absence in the corpus. That needs a targeted adversarial search for X.

**Gate E: the user shapes the document in conversation until it says what they think**, then decides whether another pass is needed. The stop rule is in `reference/method.md`.

## Things that have gone wrong before

- **Do not export the bibliography from Zotero.** Its exporters invent their own keys. Use `bib.py`.
- **Zotero's full-text index lags behind attachments by minutes.** The PDF scripts check the file on disk, so trust their numbers over `get fulltext`.
- **A capped search measures ranking, not coverage.** `gather.py` logs every query's mode and whether the cap bit, in `queries.md`. Keep that log; it is the audit trail.
- **Never delete rows from `candidates.csv`.** It is the record of what was looked at.

## Confidentiality

Treat the user's employer, client or other non-public material as out of scope for anything written here unless the user says it is cleared. The thread folder is meant to be shared.
