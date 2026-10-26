# scripts/

All take `--thread <path to a thread folder>`, most support `--dry-run`, and every
one writes a JSON record into `<thread>/runs/` so a run can be repeated and
`status.py` can say where things stand.

**Lost? Run `status.py`.** It reads the thread folder and tells you the next command.

| Script | In → out | Gate |
|---|---|---|
| `common.py` | shared helpers — polite HTTP with backoff, identifier normalisation, citation-key generation, the CSV schema, run records. Not run directly. | |
| `gather.py` | thread queries → `candidates.csv` + `queries.md`, in explicit **search modes** (below) | |
| `expand.py` | seed papers → citation edges from several providers, unioned → `candidates.csv` | |
| `add_ids.py` | bare arXiv IDs / DOIs / titles → resolved rows merged with provenance. How manual and LLM finds get back into the corpus | |
| `corpus_report.py` | `candidates.csv` → a readable report on what is actually in it. Descriptive only | |
| `dedupe.py` | `candidates.csv` → merged rows, citation keys assigned | |
| `screen.py` | `--emit` batches for the agent · `--apply` its decisions · `--audit` the human sample · `--stats` | **B** |
| `ingest.py` | accepted rows → Zotero, keys pinned, PDFs attempted → `pdf-status.md` | **C** |
| `fetch_pdfs.py` | items with no readable PDF → fetches the free ones from Zenodo, arXiv and IACR ePrint and attaches them | **C** |
| `extract_prep.py` | one paper → full text + highlights in one working file | |
| `extract_check.py` | a drafted analysis → validates fields **and that every quote is really in the paper** | **D** |
| `index.py` | `papers/*.md` frontmatter → `_index.csv`, the comparison table | |
| `bib.py` | Zotero metadata + our keys → `library.bib` | |
| `status.py` | a thread folder → where it is and what to run next | |
| `selftest.py` | known-answer tests. `--offline` skips the network ones. | |

## A typical run

```bash
S=<skill folder>/scripts   # see ../reference/workflow.md for how to find it
T=research/threads/my-topic

python3 $S/status.py  --thread $T          # always safe; says what is next
python3 $S/gather.py  --thread $T
python3 $S/expand.py  --thread $T --seed <old foundational DOI> --direction forward
python3 $S/dedupe.py  --thread $T
python3 $S/screen.py  --thread $T --emit   # agent bands them, writes decisions
python3 $S/screen.py  --thread $T --apply decisions.json
python3 $S/screen.py  --thread $T --audit  # Gate B — read audit.csv
python3 $S/ingest.py  --thread $T          # Gate C — then read pdf-status.md
python3 $S/extract_prep.py --thread $T --all
#   agent drafts research/papers/<bibkey>.md
python3 $S/extract_check.py --thread $T    # Gate D — then sample the quotes
python3 $S/index.py --papers research/papers
python3 $S/bib.py   --papers research/papers --out research/library.bib
```

## Search modes — why `gather.py` runs each source more than once

Capping results measures how well a source **ranks**, not what it **holds**, and
ranking is the thing that fails. But "take everything" is only meaningful if the
query is precise enough that everything is a finite set. Measured on
`"AI agent identity"`, 23 September:

| source | mode | reported matches |
|---|---|---:|
| arxiv | `all:AI agent identity` (words matched apart) | 199,738 |
| arxiv | `all:"AI agent identity"` (quoted) | **4** |
| openalex | `search=` (includes full text) | 212,360 |
| openalex | `title_and_abstract.search` | 5,932 |
| openalex | `title_and_abstract.search:"phrase"` | **103** |
| crossref | `query.bibliographic` | 1,172,217 |

A 50,000× difference on arXiv between the same words quoted and unquoted. So
each source runs in named modes and each is logged separately:

- **`phrase`** — exact phrase, title+abstract. Small and precise, so it is **taken in full** (safety cap `--phrase-limit`, default 2,000).
- **`scoped`** — the words, title+abstract only. Capped by `--limit`, marked `[CAPPED]`.
- **`relevance`** — the source offers no strict mode (Crossref, Semantic Scholar, ePrint). This is its top-N ranking and is labelled as such rather than presented as coverage.

Every row of `queries.md` records **available**, **taken**, and whether the cap
bit. Without the mode, "we searched OpenAlex for X" is not a reproducible
statement.

## Configuration

Nothing personal or topic-specific is built into the scripts. It comes from three places:

- **`~/.ilr-env`**, read automatically by every script (see `../reference/setup.md`):
  `ILR_MAILTO` (required, your own address), `ILR_INSTITUTION`, `ILR_INSTITUTION_MATCH`,
  and the optional keys `S2_API_KEY`, `ELSEVIER_API_KEY`, `ELSEVIER_INSTTOKEN`,
  `WOS_STARTER_API_KEY`, `IEEE_API_KEY`. `ILR_PAPERS` overrides where analysis files live.
- **`thread.md`**, per thread, in fenced blocks: `queries` (what `gather.py` runs),
  `sources` (which sources), `relevance` (screening order), `extraction-vocab`
  (controlled values for the topic-specific extraction fields, enforced by `extract_check.py`).
- **Command-line flags**, for anything that is a one-off decision: tier rules in
  `select_tier.py`, year cut-offs in `cite_check.py`, screener boundaries in
  `screener_consistency.py`.

Zotero writes need authorising once: `zotero-mcp authorize-local`, then **Always Allow**.

## More scripts

| Script | What it does |
|---|---|
| `check_access.py` | which sources answer, which keys work, whether you are on the institution network |
| `merge_shards.py` | fold per-source gather shards into one corpus |
| `backfill_abstracts.py` | fill missing abstracts in bulk after gathering |
| `subtract.py` | drop from one thread what another already accepted |
| `tier.py` | second cut of the accepted rows: A review proper, B background |
| `select_sample.py` / `select_tier.py` | per-area sampling for very broad threads (area code at the start of the screening reason, e.g. `[C2] ...`) |
| `screener_consistency.py` / `screener_agreement.py` | did several screeners apply the criteria the same way? |
| `missing_pdfs.py` | what is still without a PDF, grouped by publisher → `missing-pdfs.md` |
| `holdings.py` | Springer entitlement checked against the library's ISBN list |
| `attach_local.py` / `attach_downloads.py` | attach PDFs you downloaded to the right Zotero items |
| `venue_quality.py` | CiteScore, SJR and SNIP per venue from Scopus |
| `cite_check.py` | does the new literature cite the old? |
| `wos.py` | Web of Science Starter API |

## Two sources that are not scripted, by decision

`gather.py` defaults to **OpenAlex, Semantic Scholar, arXiv and IACR ePrint**, plus Scopus when `ELSEVIER_API_KEY` is set. Crossref is available with `--sources` but off by default: it measured 10% precision on one thread.

**DBLP** sits behind an anti-bot challenge. Defeating that is impolite and is how an entire university IP range gets blocked, so DBLP stays manual — used by hand for venue verification, where it is genuinely good. Calling it raises an error saying so rather than failing quietly.

**Google Scholar** cannot be automated at all, by design. Publish or Perish by hand is the only route.

Neither is a gap in the tool. Both are Gate C work.

## PDFs — ask the open repositories before blaming the paywall

Measured on the agent-identity thread: of 183 items with no readable PDF, **123 (67%) were free all along** — 100 Zenodo, 16 SSRN, 5 arXiv, 3 ePrint. Only 42 needed a subscription. Zotero's add-by-identifier only fetches a PDF when it finds one easily, and for Zenodo it usually does not.

`fetch_pdfs.py` recovered **73** of them automatically through public APIs. What it leaves is genuinely manual:

- **Licensed** (IEEE, ACM, Springer, Elsevier, SPIE) — LibKey Nomad or the Zotero Connector, in a browser, signed in. **A script must not drive a paywall with someone's credentials**: it breaks publisher terms and gets a whole university IP range blocked.
- **SSRN** — needs an interactive session.
- **Zenodo records with no PDF** — software and dataset deposits. There is no paper to fetch; this is the correct outcome, not a failure.

## Never do this

**Do not export the bibliography from Zotero.** Verified 23 September: an item whose citation key was pinned to `mir2023delegatable` still exported as `@article{Mir2023_3QNXCRIJ}`. Zotero holds an item key, not a citation key, and its exporters invent one at export time. Run `bib.py`.
