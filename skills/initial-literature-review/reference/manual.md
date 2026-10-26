# The Research Pipeline

*Created 2026-09-14. The group's standard way of working: every step from "we should look into X" to "it's cited in a paper", what tool does it, and where each artefact lives. Written so that someone joining in year three can read this one file and be productive the same day.*

> **This file's job.** The **operating manual** for the method defined in `method.md` — the how, not the why. Read the definition first; it says when this process applies and when it doesn't. Steps 11–12 below (write, verify before submitting) sit *outside* the scoped initial-review process and are kept here because the group needs them somewhere.

> **Where this and the scripts disagree, the scripts win.** This manual was written before the pipeline was automated. `workflow.md` (the step-by-step, with where every file is saved), `SKILL.md` and `scripts/README.md` describe what the tools actually do.

**The design rule everything follows:** durable state lives in open, portable formats (Zotero, BibTeX, CSV, markdown in git). AI tools are interchangeable accelerators bolted on top. Tools die — Zotero shipped three major versions in 2026 and broke plugins each time — and nothing important should die with them.

**The join key:** every artefact is linked by the **citation key**, format `<firstauthor><year><keyword>` (e.g. `crites2023mercurial`). `dedupe.py` generates it, Zotero holds it, the analysis file is named after it, LaTeX cites it. Pin the keys so they never change. Break this and you have three disconnected systems instead of one.

---

## Where everything is stored

| # | Artefact | Format / location | What it holds | Who writes it |
|---|---|---|---|---|
| 1 | **Query log** | `research/threads/<thread>/queries.md` | Every search: source, exact query string, date, result count | Whoever gathers |
| 2 | **Candidates** | `research/threads/<thread>/candidates.csv` | One row per candidate found, with identifiers, metadata and provenance. Never deleted from | `gather.py`, `expand.py`, `add_ids.py` |
| 3 | **Screening decisions** | the `band`, `reason`, `screened_by`, `screened_at` columns of `candidates.csv`; the human sample in `audit.csv` | band 1–4 + one-line reason + who + when | Human, AI-drafted (`screen.py`) |
| 4 | **Ingest record** | `zotero_key` column of `candidates.csv` + `pdf-status.md` | Which accepted rows are in Zotero, and which still lack a PDF | `ingest.py` |
| 5 | **The library** | **Zotero**, your personal library unless the group agrees on a shared group one (see `setup.md` step 3) | Bibliographic metadata, PDFs, highlights and annotations, collections, tags | Everyone |
| 6 | **Bibliography** | `research/library.bib` | Written from Zotero metadata under our own citation keys; what LaTeX reads | `bib.py` |
| 7 | **Per-paper analysis** | `research/papers/<bibkey>.md` | YAML frontmatter (structured fields) + prose (reasoning, objections) | Human, AI-drafted |
| 8 | **Comparison tables** | `research/papers/_index.csv` (generated) | Every paper's frontmatter as one table | Script — **never hand-edited** |
| 9 | **Thread synthesis** | `research/threads/<thread>/synthesis.md` | The argument being built across papers | Human |
| 10 | **The schema** | the skill's `templates/extraction-template.md` + `templates/extraction-example.md`, plus the thread's own ```extraction-vocab block in `thread.md` | What the fields mean and one filled example | Whoever owns the pipeline |
| 11 | **PDFs** | Zotero storage (or a synced folder via ZotMoov) | The files themselves | Zotero |

**What is deliberately *not* in Zotero:** the thousands of candidates that never passed screening (they stay in the CSV, which preserves provenance at zero cost), and the structured analysis (Zotero has no custom fields and no query language — see step 8).

---

## Step 0 — One-time setup (about two hours, once per person)

| Install | Why |
|---|---|
| **Zotero** desktop with `zotero-cli` (see `setup.md`) | Where accepted papers and PDFs live |
| **Better BibTeX** plugin (optional) | Nicer citation keys in the Zotero UI. **Never** use it to export `library.bib`: `bib.py` writes it |
| **Zotero Connector** (browser) | Saves a paper *with its PDF* from a publisher page |
| **LibKey Nomad** + **Unpaywall** (browser) | One click from a paywall to the copy your institution licenses |
| **Zotero MCP** (`uv tool install zotero-mcp-server`, then `zotero-mcp setup`) | Gives Claude Code read access to the library, PDF text and annotations |
| One reading plugin — **LLM for Zotero** *or* **PapersGPT** | In-reader Q&A. One, not five |
| **Scholar Inbox** account | Daily personalised arXiv digest |

Agree as a group, once: the citation-key format, the tag vocabulary, the extraction schema fields. Write them in `templates/extraction-template.md`. That's the substrate; everything else is preference.

---

## Step 1 — Define the thread and its criteria *(30 minutes, before any searching)*

Write down, in the thread file: the question, what counts as **in**, what counts as **out**, and where the boundary is with neighbouring threads.

*Value:* screening becomes mechanical rather than a fresh judgement call on every paper, and two people screen the same way. Skipping this is why literature reviews drift.

---

## Step 2 — Gather *(the step AI helps most with)*

Three mechanisms, because no single one has good recall.

**Layer 1 — broad queries** (`AI agent security`, `machine identity`, `delegation cryptography`…) — high volume, low precision, run through the APIs.
**Layer 2 — precise queries** (`delegatable anonymous credentials`, `multi-hop delegation chain cryptographic`…) — high precision.
**Layer 0 — query-independent** — arXiv cs.CR category browsing month by month, citation-graph expansion from anchor papers, venue-programme sweeps (CCS, USENIX, NDSS, S&P, PETS, CRYPTO).

| Source | Tool | Note |
|---|---|---|
| OpenAlex, Crossref, arXiv, DBLP | API calls, run from Claude Code or a script | Free, no scraping, reproducible |
| **IACR ePrint** | Searched **directly** at `eprint.iacr.org` | Invisible to nearly every AI tool — the crypto literature lives here |
| Structural expansion | **ResearchRabbit** — seed with 5–10 anchor papers, take Similar / Earlier / Later Work | Finds papers that share none of your vocabulary |
| The hard cross-disciplinary question | **Undermind** or **Ai2 Asta** | Multi-hop agents; best at long-tail work |
| Venue truth, quartiles | **Scopus / Web of Science** (+ their AI assistants) | From 1 October only. Quartile claims must come from here |
| Full text of OA papers | **CORE**, **Unpaywall** | Legal bulk full text |

**Never scrape a paywalled publisher.** Wiley forbids anything but its API, Springer charges for TDM access, Elsevier gives academic API access free, IEEE caps at 200 results and 10 words per query term. A scraper against them is a licence breach and libraries block the whole university's IP range.

*Output:* rows appended to the **gathered CSV** (2), and every query written into the **query log** (1).
*Value:* recall. This is the step where missing a paper costs you a year.

---

## Step 3 — Deduplicate and normalise *(script, minutes)*

The same work appears as an arXiv preprint, a conference paper and an extended journal version. Merge on **DOI → arXiv ID → normalised author+year+title-slug**, keep one row with a `versions` list, and assign the provisional citation key.

*Value:* without this the corpus looks bigger than it is and the venue tally double-counts.

---

## Step 4 — Screen *(the first kind of analysis — cheap, on title + abstract)*

Decide **in / out / maybe** against the step-1 criteria. No PDFs needed.

*How:* let Claude Code make a first pass over the CSV, producing a proposed decision **and a one-line reason** for each row; you confirm or overturn. If a thread exceeds ~300 candidates, use **ASReview** instead — open-source active learning, and it's citable in a methods section.

*Output:* the **screened CSV** (3) with decision, reason, who, when — then generate **`zotero-identifiers.txt`** (4) from everything marked include.
*Value:* turns 800 candidates into 60 real ones, with an auditable record of why the other 740 went.

---

## Step 5 — Ingest into Zotero *(only what passed)*

In Zotero: **File → Add Item by Identifier**, paste the whole identifier list at once.

**What Zotero actually gets you from a DOI:** item type, title, authors, journal or proceedings name, volume, issue, pages, date, publisher, ISSN/ISBN, DOI, URL, language. It also tries to fetch an **open-access PDF** automatically.

**What it often doesn't get:**
- **Abstracts** are patchy — Crossref frequently has none. arXiv IDs always give you the abstract, so prefer the arXiv ID when both exist.
- **PDFs behind paywalls.** Add-by-identifier only finds free copies.

**Filling the PDF gap** — three routes, in order of ease:
1. arXiv or ePrint version exists → it came automatically.
2. **LibKey Nomad** or **Unpaywall** button on the publisher page → then the **Zotero Connector** saves the item *with* the PDF in one click.
3. Nothing free exists → use your institution's licensed access via the connector, or request it.

Then tag: `thread/<name>` and `status/to-read`.

*Value:* one clean, shared, deduplicated library where the metadata is correct and the PDFs are attached — which is what every later step depends on.

---

## Step 6 — Triage *(15 minutes per batch)*

Skim abstract, intro and conclusion. Tag `prio/1`, `prio/2`, `prio/3`.

*Value:* full extraction costs an hour or more per paper. Not every included paper deserves it. Extract `prio/1` fully, `prio/2` briefly, leave `prio/3` as a citable record.

---

## Step 7 — Read and annotate *(in Zotero's own PDF reader)*

Use a fixed highlight-colour convention across the group, e.g. **yellow = central claim · red = limitation or assumption · green = method/construction · blue = quotable line**.

*Value:* this is what makes the next step cheap. Your highlights become the draft extraction instead of being lost. Consistent colours mean anyone can read anyone's annotations.

---

## Step 8 — Extract *(the second kind of analysis — expensive, per paper)*

1. Pull the annotations out — Zotero's own **Add Note from Annotations**, or `zotero-mcp` reads them directly.
2. Hand the annotations plus the PDF text to **Claude Code** with `templates/extraction-template.md`; it drafts `research/papers/<bibkey>.md`.
3. **Verify every field against the paper.** Set `verified: true` and the date in the frontmatter.
4. Tag the Zotero item `status/extracted`.

```markdown
---
bibkey: crites2023mercurial
title: "…"
venue: CRYPTO 2023
venue_type: conference
peer_reviewed: true
credibility: high
primitive: [mercurial-signatures, equivalence-classes]
threat_model: malicious-issuer, honest-verifier
security_argument: game-based-proof
real_deployment: false
relevance: core
chase: [dodis2002accumulator, crites2019delegatable]
verified: 2026-10-14
---

## Why it matters here
## What it actually does
## Assumptions and limits
## Objections
```

**Why this lives outside Zotero.** Zotero has tags, a free-text "Extra" field and notes — but **no custom fields, no table view and no query language**. It cannot answer "show me every paper using accumulators whose threat model assumes an honest issuer", and that question is the entire point of extraction. Markdown files in git are queryable, diffable, reviewable by a co-author, hold reasoning as well as fields, and survive any tool dying.

**Verify, always.** Cross-paper structured extraction is the weakest thing AI currently does — the benchmark figure is around 43% recall. Treat every drafted cell as a claim to check, never as data.

*Value:* this is the step where reading compounds instead of evaporating. It is the group's actual intellectual asset.

---

## Step 9 — Synthesise

Generate `_index.csv` from all the frontmatter (a script, or Claude Code), sort and group it, and look for the gap. Write the argument into the **thread file** (9).

Optional tools: **NotebookLM** to brief yourself or a colleague on a subtopic from 20–50 PDFs; **VOSviewer + OpenAlex** to produce a field map figure with a stateable method for a presentation.

*Value:* the generated table is the evidence behind "this is an open problem" — the sentence a thesis proposal lives or dies on.

---

## Step 10 — Stop rule

A thread is covered when three things hold at once: new queries return only items already held; `chase:` references resolve to items already held; and a venue-programme sweep surfaces nothing new. Paper count measures nothing.

---

## Step 11 — Write *(year 2 onward)*

`bib.py` writes `library.bib` → Overleaf reads it → cite by the same key that names the analysis file. **Writefull** for language inside Overleaf, **Mathpix** for equations from PDFs and handwriting, **CryptoBib** for clean crypto references, **Thesify** for structural feedback before sending a draft to a supervisor.

---

## Step 12 — Verify before submitting

**scite** — has any of this been disputed? · **SwanRef** or Paperpal's checker — does every reference actually exist? · a **retraction scan** over the library (`zotero-mcp` can do this, or the Retraction Watch database via Crossref).

*Value:* one hour that prevents the single most embarrassing category of error.

---

## The daily loop, separate from all of the above

**Scholar Inbox** digest + arXiv cs.CR listing + ResearchRabbit alerts → anything interesting goes straight into a Zotero `inbox` collection, unread, no decision. Once a week, triage the inbox into threads or delete it.

*Value:* ten minutes a day means never being scooped and never citing a superseded version.

---

## Ownership and maintenance

One person owns the pipeline per term: checks that plugins still work after Zotero updates, that the auto-export still runs, that the schema is being filled consistently, and reports once to the group. Without a named owner the stack quietly rots and everyone drifts back to Google Scholar.

## The onboarding test

A new member should be able to: read this file, install the step-0 list, read `templates/extraction-template.md` and one example analysis file, and produce their first correct extraction the same day. If they can't, this document is wrong — fix the document, not the person.
