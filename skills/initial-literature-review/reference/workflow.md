# How it works, end to end

From "I want to understand area X" to a written map of the field, step by step: what you do, what runs, and where every result is saved. You don't have to type the commands: ask Claude ("start a thread on X", "what's next on my thread?") and it runs them. They are shown so you can see what is happening and run them yourself if you prefer.

In the commands, `S` is the skill's `scripts/` folder and `T` is your thread folder, e.g. `research/threads/agent-payments`. To find `S` after installing the plugin:

```bash
S="$(dirname "$(find ~/.claude -path '*initial-literature-review/SKILL.md' | head -1)")/scripts"
```

---

## The whole flow on one page

```
 your idea ──► 1 DEFINE ──► Gate A ──► 2 GATHER ──► 3 DEDUPE ──► 4 SCREEN ──► Gate B
                thread.md   you OK it   searches +    one row per   bands 1–4    you audit
                                        citations     paper, keyed  + reasons    a sample
                                            │
                                            ▼
                                     candidates.csv  ◄── the one table everything updates
                                            │
 Gate E ◄── 7 SYNTHESISE ◄── Gate D ◄── 6 EXTRACT ◄── Gate C ◄── 5 INGEST + PDFs
 you shape   synthesis.md    you check   papers/*.md   you fetch   Zotero collection
 the text    _index.csv      quotes      one per paper paywalled   + PDFs attached
             library.bib                               PDFs
```

The five gates are where **you** decide. Claude stops at each one and waits.

---

## 1 · Define the thread → Gate A

**You:** tell Claude the area and why you care about it. Claude drafts `thread.md` with you from `templates/thread.md`. Plan on half an hour of conversation, and expect a few rounds.

**What goes into `thread.md`:**

| Section | What it is | Why it matters |
|---|---|---|
| The question | One sentence, usually "what does field X consist of?" | Keeps the pass a survey, not a hunt for one answer |
| In / out | What counts, what doesn't, with reasons | Screening is judged against this, word for word |
| Boundary | Neighbouring threads, colleagues' work | Avoids gathering what someone already has |
| ```` ```queries ```` block | The search strings, one per line, grouped by vocabulary | This is literally what `gather.py` runs |
| Seed papers | 5–10 anchor papers, at least one **old** one per community | Starting points for the citation walk |
| ```` ```sources ```` block (optional) | Which databases to search | Default: OpenAlex, Semantic Scholar, arXiv, IACR ePrint, + Scopus if you have a key |
| ```` ```relevance ```` block (optional) | Weighted terms | Only changes the *order* papers are screened in |
| ```` ```extraction-vocab ```` block | Allowed values for your topic-specific fields | Filled before step 6, not now |

**How to write the queries.** Different communities name the same thing differently: cryptographers, systems people, standards bodies and lawyers will each use their own words for one idea. One tool searched in one vocabulary misses most of a field. In our September test, **90% of papers were found by exactly one of nine tools**. So write the queries in every vocabulary the area spans, keep each short and precise, and expect 20–60 queries for a broad area.

**Gate A:** you read `thread.md` and say it's right. **Nothing is searched before that.**

**Saved:** `research/threads/<thread>/thread.md`

---

## 2 · Gather

**Runs:**

```bash
python3 $S/gather.py --thread $T                                   # every query × every source
python3 $S/expand.py --thread $T --seed 10.1007/... --direction forward   # per seed paper
python3 $S/add_ids.py --thread $T --source researchrabbit --id <doi>      # anything found by hand
python3 $S/backfill_abstracts.py --thread $T                       # fill missing abstracts
python3 $S/corpus_report.py --thread $T                            # what came back, readable
```

**What happens:**

- **`gather.py`** sends every line of the `queries` block to every source, in up to three **modes**. *Phrase* is the exact phrase in title and abstract: precise, and taken in full (up to a safety cap of 2,000, `--phrase-limit`). *Scoped* is the words anywhere in title and abstract: broader, so capped at `--limit` (default 300). *Relevance* is the source's own top-N ranking, for sources that have no strict mode. Each result becomes a row in `candidates.csv`, and each search is logged in `queries.md` with how many results existed and how many were taken.
- **`expand.py`** follows the citation graph from each seed: forward (papers citing it) or backward (papers it cites), across OpenAlex, Semantic Scholar and Crossref combined, because each provider is missing edges the others have. This finds papers that share none of your words.
- **`add_ids.py`** brings in anything found elsewhere (an LLM search tool, Google Scholar, ResearchRabbit, a colleague's list), labelled with where it came from.

| Source | Key needed? | What it's good for |
|---|---|---|
| OpenAlex | no (needs `ILR_MAILTO`) | the broadest open index; phrase search on title+abstract |
| Semantic Scholar | optional `S2_API_KEY` | CS coverage, citation edges, abstracts |
| arXiv | no | preprints, the newest work |
| IACR ePrint | no | cryptography preprints, invisible to most AI tools |
| Scopus | `ELSEVIER_API_KEY` + institution network | curated journals and conferences, venue metrics |
| Web of Science | `WOS_STARTER_API_KEY` | Clarivate-indexed journals; not in the default set, so add `wos` to the thread's `sources` block with the others you want, e.g. `openalex semanticscholar arxiv eprint wos` (the list replaces the default, it doesn't add to it) |
| Crossref | no | metadata; off by default (10% precision in one test) |
| DBLP, Google Scholar | — | by hand only (bot protection / no API) |

A big run takes hours, mostly waiting on rate limits. Claude runs it in the background, and it saves the CSV after every query, so an interrupted run loses at most one query.

**Saved:** in `research/threads/<thread>/`: `candidates.csv` (every paper found, never deleted from), `queries.md` (every search, exactly as run), `runs/*.json` (one record per script run), and `corpus-report.md`.

---

## 3 · Dedupe

**Runs:** `python3 $S/dedupe.py --thread $T`

Merges the preprint, the conference version and the journal version of one paper into one row (by DOI, then arXiv ID, then near-identical title), and gives each paper its **citation key**: first author + year + a distinctive title word, e.g. `chan2024visibility`. That key is permanent. It names the analysis file, goes into Zotero, and is what you `\cite{}` in LaTeX.

**Saved:** `candidates.csv`, updated in place.

---

## 4 · Screen → Gate B

**Runs:** `screen.py --emit` writes the unscreened papers into batch files. Claude reads each batch and decides, from title, abstract and venue only, against your in/out criteria:

| Band | Meaning | Outcome | You check at Gate B |
|---|---|---|---|
| 1 | clearly in | accepted | random 10% |
| 2 | in, weaker reason | accepted | random 25% |
| 3 | genuinely unsure | **you decide** | all of them |
| 4 | out | rejected | random 5% |

Each paper gets a one-line reason. `screen.py --apply` writes the decisions into `candidates.csv`, and `screen.py --audit` draws the sample you check.

**Gate B:** open `audit.csv` (any spreadsheet app works). It holds every band-3 paper plus a random sample of the others.

1. For each row, check whether the band and reason hold. Where you disagree, change the `band` (and `reason`).
2. Give every band-3 row a final band: 1 or 2 to keep it, 4 to drop it. Nothing moves on while any band 3 is left.
3. Save, then write your decisions back: `screen.py --thread $T --apply $T/audit.csv --by <your initials>`.

Do step 3 before running `--audit` again, because a new audit draws a fresh sample and overwrites the file. Band 4 matters most: a paper wrongly thrown out is never seen again. If band 3 is more than a quarter of everything, the criteria are too vague. Go back to step 1 rather than pushing through.

**Optional, for big corpora:** `tier.py` makes a second cut of the accepted papers: **A** is the review proper (read in full, goes to Zotero), **B** is background (stays in the CSV and gets cited from there).

**Saved:** `candidates.csv` (columns `band`, `reason`, `screened_by`, `screened_at`, and `tier` if used), `screening/batch-*.json` and `screening/decisions-*.json` (the raw decisions), `audit.csv` (your sample).

---

## 5 · Ingest into Zotero, get PDFs → Gate C

**Runs:**

```bash
python3 $S/ingest.py --thread $T          # accepted papers → Zotero
python3 $S/fetch_pdfs.py --thread $T      # free PDFs from Zenodo, arXiv, ePrint
python3 $S/missing_pdfs.py --thread $T    # what's still missing, grouped by publisher
```

**Where things go in Zotero:**

| What | Where |
|---|---|
| Library | whichever library `zotero-cli` currently points at. **The default is your personal My Library**, and that is what everyone uses unless the group agrees on a shared group library. Check with `zotero-cli library list`. To use a group library, run `zotero-cli library switch --library-type group --library-id <id>` before ingesting. Group writes are not tested yet, so try `--limit 5` first |
| Collection | one per thread, **named after the thread folder** (e.g. `agent-payments`), created automatically. Override with `--collection <name>` |
| Tags | `thread/<thread-name>` and `status/to-read` on every item |
| Citation key | written to the item's **Citation Key** field, so you can search Zotero by it |
| PDFs | attached to the item, in Zotero's own storage |
| What is *not* in Zotero | rejected papers (they stay in the CSV), tier-B papers, and the analysis itself |

Back in the thread, each ingested row gets its Zotero item key in the `zotero_key` column. That's how the scripts find the paper's PDF later.

**Gate C:** about two-thirds of missing PDFs turned out to be free, and `fetch_pdfs.py` gets those. The rest needs a licence. `missing-pdfs.md` lists them grouped by publisher, each with a direct link: (A) open in a browser, (B) open on the institution network or VPN, (C) not licensed, so request it by interlibrary loan. Download them into `~/Downloads`, then `attach_local.py --thread $T --from ~/Downloads` matches each file to its paper by the DOI inside the PDF and attaches it. **No script ever logs in to a publisher.**

**Saved:** in the thread: `pdf-status.md`, `missing-pdfs.md`, and `springer-access.md` if you ran `holdings.py`. In Zotero: the items, collection, tags and PDFs.

---

## 6 · Extract → Gate D

**First, once per thread:** agree with Claude on the questions your review asks of every paper (the `thread:` block), and put the allowed values in the ```` ```extraction-vocab ```` block of `thread.md`. See `templates/thread-block-example.md` for a full one. Do this *before* the first paper: adding a field later means re-reading everything.

**Runs:**

```bash
python3 $S/extract_prep.py --thread $T --all --limit 5   # PDF text + your Zotero highlights → working file
#   Claude reads each working file and writes research/papers/<key>.md
python3 $S/extract_check.py --thread $T                  # machine check of every file
```

Each paper gets **one analysis file**: structured fields at the top (problem, threat model, assumptions, what it proves, stated limits and open problems, plus your thread's own questions), then four short prose sections (why it matters here, what it does, assumptions and limits, objections). See `templates/extraction-template.md` and the filled `templates/extraction-example.md`.

**The quote rule** is what makes this trustworthy. Every judgement carries a **verbatim quote** with a page or section, and `extract_check.py` checks that every quote really appears in the paper's text. AI extraction across papers fails mostly by making things up, and a quote that is string-matched can't be made up quietly. "Not established" is `null` with a reason; "checked and absent" is `none`.

**Gate D:** the machine proved the quotes exist. You read a sample and judge whether each quote actually **supports** the claim next to it. When you've checked a file, set `verified: true`, `verified_by` and `verified_date`.

**Saved:** `research/papers/<key>.md`, one per paper, **shared across all threads** (a paper is read once and serves every thread that touches it). The paper's text goes in `research/threads/<thread>/extraction-workspace/<key>.md`. **Keep it until Gate D is done**: `extract_check.py` checks quotes against this file, and without it the check only warns that the quotes could not be verified.

---

## 7 · Synthesise → Gate E

**Runs:**

```bash
python3 $S/index.py --papers research/papers                         # one table of every paper
python3 $S/bib.py --papers research/papers --out research/library.bib # bibliography, our keys
```

`_index.csv` puts every paper's fields in one table, so a question like "how many of these papers say how authority is withdrawn?" is a count, not a feeling. Claude drafts `synthesis.md` from it: how the area divides, who works on it, recurring assumptions, the open problems the authors themselves state (quoted), and literatures that work on the same problem without citing each other. Every claim cites a key.

**Gate E:** you shape `synthesis.md` in conversation until it says what you think. Then decide: done, or another pass? A first pass is done when new queries return only papers you already have, the references worth chasing are already in, and a sweep of the main venues' programmes adds nothing new.

**Saved:** `research/threads/<thread>/synthesis.md`, `research/papers/_index.csv`, `research/library.bib`. Point Overleaf or LaTeX at `library.bib`. **Never export the bibliography from Zotero**: it invents its own keys.

---

## Every file, in one place

```
research/                                  ← your workspace; put it under git
├── threads/<thread>/
│   ├── thread.md               1   question, criteria, queries          (you + Claude)
│   ├── queries.md              2   every search as run                  (append-only)
│   ├── candidates.csv          2–5 every paper found + band, tier, zotero_key  (never delete rows)
│   ├── corpus-report.md        2   what the corpus contains
│   ├── screening/              4   batches and raw decisions
│   ├── tiering/                4   tier batches, if tiered
│   ├── audit.csv               4   your Gate B sample
│   ├── pdf-status.md           5   what ingest could not attach
│   ├── missing-pdfs.md         5   your Gate C to-do list, by publisher
│   ├── extraction-workspace/   6   full text per paper, kept until Gate D
│   ├── synthesis.md            7   the review itself
│   └── runs/                   all one JSON per script run: what ran, with what, what came back
├── papers/
│   ├── <key>.md                6   one analysis per paper, shared by all threads
│   └── _index.csv              7   generated table, never hand-edited
└── library.bib                 7   generated bibliography

Zotero (library zotero-cli points at)
└── collection "<thread>"       5   accepted papers, tagged thread/<thread>, with PDFs
```

**Lost?** `python3 $S/status.py --thread $T` reads the folder and tells you where the thread is and what comes next. Or ask Claude "where is my thread?".
