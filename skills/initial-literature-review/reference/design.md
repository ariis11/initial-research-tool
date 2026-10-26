# Implementation Plan

*23 September 2026. How the method in `method.md` gets built.*

> **Design notes, partly historical.** Written while the pipeline was being built. Where it disagrees with `workflow.md` or the scripts, they win.

**Status: in use since September 2026 across four real threads.** See `scripts/README.md` for how to run each script and `../SKILL.md` for the order.

**The build rule:** deterministic work is a script, judgement is the agent, and the human appears at five gates and nowhere else.

---

## The pipeline, with its gates

| # | Step | Who | Output |
|---|---|---|---|
| 1 | **Define the thread** — question, in/out, vocabularies, seed papers | conversation | `thread.md` |
| | **🚦 Gate A** — you approve it. Nothing runs before this. | | |
| 2 | **Gather** — keyword APIs + citation walk + agent search. **Everything kept, no cap.** | script | `candidates.csv`, `queries.md` |
| 3 | **Dedupe** — merge versions, assign the citation key | script | `candidates.csv` |
| 4 | **Screen** — four bands + a reason each, title/abstract only | agent | `candidates.csv` (band columns), `audit.csv` |
| | **🚦 Gate B** — you audit the sample. | | |
| 5 | **Ingest** — add to Zotero, pin the key, tag, fetch PDFs | script | `pdf-status.md` |
| | **🚦 Gate C** — you fetch the PDFs the machine couldn't, and do anything else needing a login or a GUI. | | |
| 6 | **Extract** — one analysis file per paper, every claim quoted | agent + scripts | `papers/<bibkey>.md` |
| | **🚦 Gate D** — you spot-check that quotes support their claims. | | |
| 7 | **Synthesise** — comparison table, then the review document | script + agent | `_index.csv`, `synthesis.md` |
| | **🚦 Gate E** — you shape the document in conversation until it says what you think. | | |
| 8 | **Enough, or another pass?** | you | — |

### The screening bands

| Band | Meaning | Outcome | You check |
|---|---|---|---|
| 1 · Core | clearly in | accepted | random 10% |
| 2 · Probable | in, weaker reason | accepted | random 25% |
| 3 · Borderline | genuinely unsure | **you decide** | all |
| 4 · Out | not relevant | rejected | random 5% |

Band 3 should be small. If it comes back as a third of the corpus, the thread definition is too vague — go back to Gate A rather than grinding through it. Band 4 is sampled even though it is tempting not to: a wrongly-included paper costs ten minutes later, a wrongly-excluded one is invisible forever, and recall is the whole reason this method exists.

---

## Architecture

```
skills/initial-literature-review/
├── SKILL.md               the agent's instructions: what to do at each
│                          stage, which script to run, when to stop and ask
├── reference/
│   ├── method.md          the definition — why, when, when not
│   ├── manual.md          the stages, written for a human
│   ├── sources.md         which sources exist, what each is good for
│   ├── setup.md           one-time setup per person
│   ├── design.md          this file
│   └── evidence-*.md      the tool tests that justify all of the above
├── templates/
│   ├── thread.md                    skeleton for Gate A
│   ├── extraction-template.md       the fields every paper gets
│   ├── thread-block-example.md      a full topic-specific block, worked
│   └── extraction-example.md        one filled in
└── scripts/               one CLI per step; scripts/README.md lists them
```

```
research/
├── threads/<name>/
│   ├── thread.md          the question and criteria
│   ├── queries.md         every search run, appended, never rewritten
│   ├── candidates.csv     everything found. never deleted from
│   ├── (candidates.csv)   + band, reason, who, when — same file, more columns
│   ├── audit.csv          the sample drawn for you
│   ├── identifiers.txt    what went into Zotero
│   ├── pdf-status.md      which items still have no PDF
│   ├── synthesis.md       the review document — the actual deliverable
│   └── runs/              one JSON per script run: parameters, counts, errors
├── papers/<bibkey>.md     extractions — flat and global, one per paper
├── papers/_index.csv      generated comparison table, never hand-edited
└── library.bib            bibliography export, never hand-edited
```

**The shape:** the method folder is the tool, a thread folder is one use of it, and `papers/` and `library.bib` are shared across every use — because a paper is read once and serves every thread that touches it.

---

## How the citation key holds together

**Tested against the real library on 23 September, because the obvious assumption was wrong.**

### The three different keys

| | Example | Who makes it | What it is |
|---|---|---|---|
| **Zotero item key** | `3QNXCRIJ` | Zotero | 8 random characters. Internal plumbing. How scripts address an item. Never seen by a human. |
| **An exporter's key** | `Mir2023_3QNXCRIJ` | whichever exporter you ran | Generated on the fly from the metadata. **Different exporters produce different keys for the same paper.** |
| **The citation key** | `mir2023delegatable` | **us, at dedupe** | The one that names files, rows and `\cite{}`. |

Zotero does **not** hold a citation key. It holds an item key, and any bibliography you export from it gets a key invented at export time. Measured: `zotero-cli get bibtex` on a real item returned `Mir2023_3QNXCRIJ`; Zotero's own UI exporter uses a different formula again. **So exporting the bibliography out of Zotero would hand back keys that do not match ours — which is exactly the failure this section exists to prevent.**

### The fix: we write the bibliography, Zotero never gives us keys

The original plan was to pin keys into Zotero's Extra field and let Better BibTeX honour them on export. That mechanism is real, but it depends on Better BibTeX, **which is not installed** — and the group's own evidence is that Zotero broke its plugins on every major release in 2026. Building the join key on a plugin is building it on sand.

So the bibliography is generated by us instead:

**`bib.py` reads each item's current metadata out of Zotero (read-only), pairs it with our citation key from the mapping, and writes `library.bib` itself.**

This gets both halves right. Metadata comes from Zotero, so any correction made by hand in the Zotero UI flows through. The key comes from us, so it cannot change, cannot be reinvented, and never makes a round trip through a third-party exporter.

**The rule that falls out of this, and it is short: never export the bibliography from Zotero's UI. Run `bib.py`.** Anything exported from Zotero directly carries the wrong keys.

### The mapping is the bridge

`ingest.py` records, for every paper, the pair `bibkey ↔ zotero_key`. That pair lives in `candidates.csv` and in every extraction file's frontmatter, and it is what lets the two worlds talk:

- **Scripts** use `zotero_key` to ask Zotero for full text, annotations and metadata.
- **Humans, files and LaTeX** use `bibkey` and never see the Zotero key.

### End to end, one paper

1. **Dedupe** generates `mir2023delegatable` from first author + year + title keyword. It goes into `candidates.csv`. Zotero has not been touched.
2. **Screen** carries it into `candidates.csv`'s band columns and `audit.csv` unchanged.
3. **Ingest** runs `zotero-cli add doi 10.56553/popets-2023-0093`. Zotero creates the item and assigns `3QNXCRIJ`. The script records `mir2023delegatable ↔ 3QNXCRIJ`, and additionally writes `Citation Key: mir2023delegatable` into the item's Extra field — **as a convenience so the key is visible and searchable in the Zotero UI, not because anything depends on it.**
4. **Extract** writes `research/papers/mir2023delegatable.md`, whose frontmatter carries both `bibkey` and `zotero_key`. `extract_prep.py` uses the Zotero key to pull the full text; the filename uses ours.
5. **Index** builds `_index.csv` keyed on `bibkey`.
6. **Bibliography**: `bib.py` writes `@article{mir2023delegatable, ...}` with metadata read from Zotero.
7. **Writing**: `\cite{mir2023delegatable}` resolves in `library.bib` and names the analysis file. Same string in all seven steps.

**Collisions:** same first author, same year, same title keyword → a letter suffix (`smith2026agentsa`, `smith2026agentsb`), checked against keys already present in `papers/` and `library.bib`.

## Citation graphs disagree with each other — tested 23 September

The mechanism matters more than any tool that implements it, so it is worth separating the two.

**What it is.** Instead of matching words, you follow citations. Papers cite each other regardless of which vocabulary they use, so a citation edge crosses a field boundary that no keyword ever will. This is the only mechanism that reaches work sharing none of your search terms.

**Why it is the most valuable mechanism *here*, specifically.** This thesis sits between two literatures that do not share words. Measured in round three: seeding from an *AI-agent* paper returned 86 results and **zero** cryptography. Seeding from Camenisch & Lysyanskaya 2002 and reading forward found **Deochake 2026, *Heartbeat-Bound Hierarchical Credentials: Cryptographic Revocation for AI Agent Swarms*** — a paper appearing in **none** of the 894 distinct results the seven other tools returned.

**The rule that came out of it is tool-independent and is the thing to automate:** *seed from the old cryptography papers and read forward.* Backward from the agent side finds nothing, because the recent agent literature has not absorbed the primitives yet, so there is nothing to traverse toward.

### The finding that changes the design

The plan said `expand.py` would use OpenAlex, on the reasoning that ResearchRabbit is a GUI while OpenAlex is the same graph behind an open API. **Tested, and that reasoning was wrong:**

| Check | Result |
|---|---|
| Camenisch 2002 in OpenAlex | ✅ `W1607188293`, 729 citations recorded (ResearchRabbit reported 1,074) |
| Walk its citations forward, 2025 onward | 62 papers — **none crossing into the agent literature** |
| Is Deochake 2026 in OpenAlex? | ✅ Yes, `W7162023451` |
| Does OpenAlex record its references? | ❌ **Zero.** `referenced_works` is empty |

OpenAlex has the **node** but not the **edges**. The citation from Deochake to Camenisch exists in the world and in ResearchRabbit's data; it does not exist in OpenAlex's graph. So an `expand.py` built on OpenAlex alone would silently have missed the single most valuable result of the entire three-round test.

**This is the round-one finding all over again, applied to a layer we had treated as objective.** "No single tool sees the field" was established for *search*. It holds for *citation graphs* too: a citation graph is not a fact about the world, it is one provider's reference-parsing coverage, and providers disagree — badly, on exactly the recent preprints this field is made of.

### What `expand.py` does instead

**Query several citation providers and union the results:** OpenAlex, Semantic Scholar (the likely source of the edge ResearchRabbit had — RR draws on the S2/OpenAlex lineage, and OpenAlex demonstrably lacks it), and Crossref, where publishers deposit reference lists. Record which provider supplied each edge, exactly as `sources` records which tool returned each paper.

**ResearchRabbit keeps a role, and it is not the pipeline.** It stays the manual check for the case the APIs are structurally bad at — very recent preprints whose references nobody has parsed — and the interactive tool for exploring a neighbourhood by eye. Its limits are why it cannot be the automated step: login is manual and not delegated, the free tier caps at 40 results per search, and papers flagged "Incomplete data" cannot be used as seeds at all, which disqualifies most 2025–26 arXiv preprints in agent security.

**And this makes the Semantic Scholar API key matter.** The earlier note called it optional. It is not: S2 is likely the provider holding the edges OpenAlex lacks, and testing this on 23 September hit the documented 429 within two calls. Worth requesting as soon as the university email exists.

### The regression test to build in

`expand.py` has a known-answer test, and it should be written before the script: **seeded with Camenisch & Lysyanskaya 2002 and reading forward, does it return Deochake 2026?** ResearchRabbit found it by hand. If the automated version cannot reproduce that, it does not yet replace the manual step, and the honest thing is to say so rather than to assume coverage.

## How deduplication merges

Matched in this order, first hit wins:

1. **DOI**, normalised — lowercased, `https://doi.org/` stripped.
2. **arXiv ID**, normalised — version suffix stripped, so `2509.13597v2` and `2509.13597` are one paper.
3. **First-author surname + year + title slug** — lowercased, punctuation and stopwords removed, with fuzzy title matching, to catch the cases where neither identifier is present.

The surviving row keeps the **published version's metadata** for venue, year and peer-review status, but keeps the **arXiv ID as well as the DOI** — because Crossref frequently has no abstract while arXiv always does, a gap measured at 56% abstract coverage on Springer LNCS material in the September test. It also keeps `versions` (every identifier seen), `sources` (which tools returned it) and `n_sources`.

That last column is worth having for its own sake: the September test found 90% of papers were returned by exactly one tool, so `n_sources: 1` is the normal case, not a warning sign.

---

## Where extraction lives

Extraction is the agent's job — it is reading and judgement, and no script can do it. But it is wrapped by two scripts, and the second one is the important one:

- **`extract_prep.py`** pulls the raw material together: PDF full text plus any highlights, out of Zotero, into one file. Deterministic, no judgement.
- The **agent** reads that and drafts `papers/<bibkey>.md` against the template, quoting every claim.
- **`extract_check.py`** then verifies mechanically that the YAML parses, required fields are present, every claim has an evidence entry, and **every quote appears verbatim in the source text**.

That last check is what makes Gate D cheap. The machine proves exhaustively that the quotes are real; the human checks on a sample whether a real quote actually *supports* the claim attached to it. The published failure rate for cross-paper structured extraction — around 43% recall — is a confabulation problem, and a model that must quote from a text that is then string-matched cannot confabulate quietly.

---

## Deliberately not built yet

**The stop rule.** One clean end-to-end run; you decide whether another pass is needed. The three conditions in `method.md` are all computable and can be automated later, once there is a real run to calibrate against.

**Packaging for the group.** Done, 27 October 2026, after four real threads: the method is a Claude Code skill, distributed as a plugin from its own repository. Every script is still a plain CLI, so it runs without Claude too.

**The group Zotero library.** It does not exist yet; the first threads run against a personal library. Nothing in the design changes when it does — only which library the scripts point at.

---

## Prerequisites — checked against the real machine, 23 September

**Working already:** `zotero-cli` and `zotero-mcp` are installed (same package, `zotero-mcp-server`, two front ends onto the same library), Zotero is reachable in local mode, reads work, and the local semantic index is built.

**Needed before ingest can run — a human action, once:**

- **Authorize local writes.** `zotero-mcp authorize-local`, then choose **"Always Allow"** in the Zotero dialog. Until this is done every write is refused, which blocks `ingest.py` entirely — adding an item is a write. Verified by attempting one.

**Not needed, contrary to the earlier draft:**

- **Better BibTeX.** Worth installing for the Zotero UI's own sake, but nothing in this pipeline depends on it now that `bib.py` writes the bibliography.
- **A Semantic Scholar API key.** OpenAlex, Crossref, arXiv and DBLP are open; S2 works unauthenticated at a lower rate. The scripts use polite pools and back off on 429.
- **A Zotero group library.** First threads run against the personal one; only the target library changes when a group one exists.

## Notes on the sources

**No API key is needed to start.** OpenAlex, Crossref, arXiv and DBLP are open. Semantic Scholar works unauthenticated at a lower rate limit; a free key removes the 429s but needs an institutional email, which is not available yet. The scripts therefore use the polite pools (a `mailto` on OpenAlex and Crossref) and back off on 429 rather than depending on a key.

**IACR ePrint has no usable API** and is invisible to nearly every AI tool, which is exactly why it matters for this field. `gather.py` queries its search endpoint directly.

**Never scrape a paywalled publisher.** Wiley, Springer and Elsevier forbid it, IEEE caps queries, and a scraper gets the whole university's IP range blocked. Licensed access from 1 October is for reading PDFs and full-text search, through the browser, at Gate C.
