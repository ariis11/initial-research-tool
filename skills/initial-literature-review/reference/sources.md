# Source Register for Corpus Gathering

---

## 1. First, a distinction that matters

**Indexes are not publishers, and neither one confers credibility.**

- **Indexes / catalogues** — OpenAlex, Crossref, DBLP, Semantic Scholar, Scopus, Web of Science, Lens, Dimensions. These are card catalogues. They tell you a paper exists and where it appeared. They make no quality claim whatsoever, and a bad paper is indexed exactly as well as a good one.
- **Repositories** — arXiv, IACR ePrint, SSRN, Zenodo, HAL, TechRxiv. These host what authors upload. **arXiv is not peer-reviewed**, and this matters more here than in most fields: the preprint flood is the central fact of this research area, and the observation that the design space is crowded while the rigour space is empty comes directly from it. Good work is on arXiv, but so is product marketing in academic clothing. Coverage and speed are what arXiv gives you; validation is not.
- **Publishers / proceedings** — where peer review actually happened. This is the only layer that carries a credibility signal, and the signal is the *venue*, not the platform.

So credibility is decided at extraction time by the `venue_type`, `peer_reviewed`, and `credibility` fields in the template — not by which database a paper came out of. The register below is chosen for **coverage**, and coverage is the only thing it is chosen for.

## 2. Bibliographic sources

| Source | Endpoint | Access (tested 2026-08-29) | What it adds | What it misses |
|---|---|---|---|---|
| **arXiv** | `https://export.arxiv.org/api/query` | **Works** — must be `https`; the `http` form silently returns nothing | cs.CR / cs.AI / cs.MA preprints with full abstracts, date-sortable | Unrefereed; no venue field for later published versions |
| **OpenAlex** | `https://api.openalex.org/works` | **Works**, no key | Broadest coverage; `group_by` returns venue frequency counts directly | Variable metadata quality; abstracts inverted-index encoded |
| **DBLP** | `https://dblp.org/search/publ/api?format=json` | **Works** | Authoritative venue names and author disambiguation — the venue-truth source | **Titles only, no abstracts.** CS only |
| **Crossref** | `https://api.crossref.org/works` | **Works** | DOIs, publisher-side journal metadata | Weak on proceedings; usually no abstracts |
| **Semantic Scholar** | `api.semanticscholar.org/graph/v1` | **429 without a key** | Forward citations — the only volume source for "who cited this since" | Unusable at scale until a key is issued |
| **IACR ePrint** | `eprint.iacr.org/search?q=` | **HTML only**, scrapes cleanly | Crypto theory: delegatable credentials, accumulators, mercurial signatures | Barely indexed elsewhere — missed entirely if not searched directly |
| **Scopus** | via university | **Blocked until 1 Oct** | **Defines the SJR quartiles** the supervisor asked for | Subscription |
| **Web of Science** | via university | **Blocked until 1 Oct** | **Defines the Clarivate JCR quartiles** — the other Q1/Q2 system | Subscription |
| **Lens.org** | `lens.org` | Free tier | Scholarly works **plus patents** — the landscape file flagged agent-verification patents as prior-art signals | Rate limits |
| **EUR-Lex** | `eur-lex.europa.eu` | Free | AI Act, eIDAS, implementing acts — primary text for the regulatory thread | Not a paper source |

**Two things worth correcting about access.** First, Scopus and Web of Science are not optional extras — they are the systems that *define* Q1/Q2. Any quartile claim in the plan ultimately traces to one of them, so the venue pass should wait for university access rather than lean on secondary sites. Second, and more cheerfully: **the top of this field is already open access.** USENIX publishes every paper free (verified), NDSS is free via the Internet Society, all IACR proceedings are free at iacr.org, and PETS publishes as PoPETs open access. So the institutional-access gap mostly affects IEEE, ACM, Springer and Elsevier — and much of what matters there is on arXiv or the authors' pages anyway. Gather metadata now, fetch PDFs after 1 October.

**On MCPs:** I searched the connector registry for Zotero, arXiv, Scholar, and general academic-search servers. **Nothing available in this session.** The APIs above cover the same ground directly, and Zotero import works through a pasted identifier list rather than a connector, so nothing is actually lost.

**Deliberately not used:** Google Scholar — no API, blocks automation, scraping gets the IP banned. Manual spot-checks only.

---

## 3. What each source actually searches

You asked exactly the right question, and the answer varies enough to change how queries must be written. All figures below are real counts from 2026-08-29.

| Source | Default search covers | Evidence |
|---|---|---|
| **arXiv** | `all:` = title + abstract + authors + comments + journal-ref. Narrower prefixes available: `ti:`, `abs:`, `au:`, `cat:` | For `cat:cs.CR` + "AI agent": `ti:` 188 · `abs:` 357 · `all:` 398 |
| **OpenAlex** | Plain `search=` hits **full text** where available — very broad. `filter=title_and_abstract.search:` restricts it | Same query: fulltext 14,655 · title+abstract 362. **A 40× difference — the earlier count of 14,655 was a fulltext search, not a topical one** |
| **DBLP** | **Title and author only.** No abstracts exist in DBLP at all | "tamper-evident" → 59, all title matches |
| **Crossref** | Bibliographic metadata — title, container, authors | — |
| **IACR ePrint** | Title, authors, abstract, keywords | — |
| **Semantic Scholar** | Title + abstract | — |

**What follows from this.** DBLP queries must be short and title-shaped — a five-word conceptual phrase returns nothing there while returning hundreds on OpenAlex. And OpenAlex needs the mode chosen deliberately: fulltext for recall when hunting a specific technical term, title-and-abstract for topical sweeps. Using the default everywhere silently mixes the two.

---

## 4. Venue programs — and a correction

This is the source most people skip and the highest-signal one available. Search shows what *exists*; an accepted-papers list shows what the field *accepts*. The gap between those two is the observation this thesis is positioned on, and reading programs is how it becomes evidence rather than assertion.

**Correction to the first version of this file:** I populated this list with the *publication targets* rather than the venues to sweep. Those are two different lists and conflating them was wrong — it is the same mistake I flagged in the venue strategy, made here by me. For **gathering**, venue rank is not a filter at all. Relevance is the only criterion; credibility gets recorded at extraction time.

**Sweep these — last two to three years of accepted papers, titles first:**

*Security:* USENIX Security · IEEE S&P · ACM CCS · NDSS · PETS/PoPETs · CSF · ESORICS · ACSAC · EuroS&P · AsiaCCS · DSN · SaTML · WPES
*Cryptography:* CRYPTO · EUROCRYPT · ASIACRYPT · PKC · TCC · FC · ACNS · CHES
*Blockchain and applied crypto:* **IEEE ICBC** · DAPPS · BCCA · COINS · IEEE Blockchain · ACM AFT
*Identity specifically:* Open Identity Summit · IFIP IDMAN-lineage workshops · EIC (industry, market-intel tier)
*AI and agents, for the boundary:* NeurIPS · ICML · ICLR · AAAI · IJCAI · AAMAS · ACL
*Where this exact conversation happens:* AGENT-SEC and the agentic-security workshops attached to the big four

**On ICBC specifically.** It belongs in this sweep and its omission was an error. It is an established IEEE ComSoc conference, now in its eighth edition, and its 2026 program included zkSNARK-verified privacy and zero-knowledge credential work — directly adjacent to the credentials and ZKP threads. You also have a network there, which is worth something a ranking does not capture.

Its CORE rank is C, and that is a fact about CORE, not a verdict on the community. Worth holding both things at once: CORE also ranks PKC and TCC as B, which no cryptographer would accept as a description of reality. The rank matters for one purpose only — your supervisor set A*/A as the criterion for **publication targets**. For gathering, and for your existing contacts, it is simply in.

Programs are static HTML on conference sites and parse cleanly; DBLP carries every proceedings volume and is usually more consistent.

---

## 5. Standards and primary sources

- **IETF Datatracker** — `datatracker.ietf.org/api/v1/doc/document/?type=draft&format=json` — **works**; 276 drafts match `agent` alone. Query `agent`, `delegation`, `attenuating`, `on-behalf-of`, `agentic`, `workload identity`.
- **IETF mail archives** — `mailarchive.ietf.org/arch/browse/oauth/` — the arguments are here, not in the drafts. A `-00` draft with no list traffic is one person's idea; a `-02`+ with contentious traffic is a live research problem. Available nowhere else.
- **OpenID Foundation** — AuthZEN WG (AARP, COAZ)
- **NIST** — AI Agent Standards Initiative · NCCoE project pages · COSAiS overlays
- **W3C / DIF** — DID and VC specs, MCP-I
- **MCP** — `github.com/modelcontextprotocol` — the authorization spec *and* its issue tracker, where the unsolved parts are visible
- **A2A** — `a2a-protocol.org`
- **CEN/CENELEC JTC 21** (prEN 18229-1) · **ISO/IEC JTC 1/SC 42** (ISO/IEC DIS 24970)
- **ENISA** certification portal and ad hoc working group calls

## 6. Citation-graph expansion

Fed by the `key_references` field in every extraction. **Backward** comes free from extraction. **Forward** — who cites the anchors — needs Semantic Scholar (key required) or OpenAlex `cited_by_api_url`, and is how you catch the paper that supersedes yours. Connected Papers, Inciteful and Litmaps for manual discovery passes.

### 6a. ResearchRabbit and Elicit — how they actually work

*Added 2026-09-04.* Both are UI tools over the same open corpora the APIs above already hit, so neither adds a source. What they add is **operator speed** on two specific steps: ResearchRabbit on Layer 0 mechanism 2 (structural discovery), Elicit on screening and first-pass extraction. Neither confers credibility — §1 still holds, and `venue_type` / `peer_reviewed` / `credibility` are still decided at extraction time against the actual paper.

**ResearchRabbit** — free, no paid tier.

- *Mechanism:* you seed a **collection** with a handful of known-good papers rather than typing a query. It then walks the citation graph around that seed set and offers four views: **Similar Work** (graph-neighbourhood plus embedding similarity), **Earlier Work** (what the seeds cite — backward), **Later Work** (what cites the seeds — forward), and **Authors** (co-authorship network, and "these authors' other papers").
- *Why it matters here:* it is query-independent. A paper that shares none of the Layer 2 vocabulary still surfaces if an anchor cites it — exactly the recall hole §8 Layer 0 was written to cover. It is also the cheapest available route to **forward citations**, which is otherwise blocked: Semantic Scholar returns 429 without a key, and OpenAlex `cited_by_api_url` needs paging code.
- *Zotero integration:* two-way. It imports an existing Zotero collection as a seed set and can push discovered papers back, which fits the §9 workflow — ResearchRabbit finds, Zotero holds, `Add Item by Identifier` fetches metadata and OA PDFs.
- *Alerts:* per-collection email notifications when new papers enter that neighbourhood. Worth setting on the anchor collection and treating as a feed alongside arXiv cs.CR.
- *Limits:* underlying data is Semantic Scholar / OpenAlex-lineage, so **IACR ePrint is effectively invisible** — the crypto-theory thread (delegatable credentials, mercurial signatures, accumulators) must still be searched directly at `eprint.iacr.org`. No abstract-level screening, no export of a clean CSV matching the corpus schema, and the graph view flatters connectedness — a dense-looking cluster is a citation artefact, not a finding.

**Elicit** — free tier is rate-limited on the table/extraction features; heavy use is paid.

- *Mechanism:* you enter a **research question in natural language**, not a boolean query. It runs semantic retrieval over a Semantic Scholar-derived corpus (~125M works), returns ranked papers, and then — the actual product — builds a **table with one row per paper and columns you define**, filling each cell by extracting from the paper's text. "Threat model", "cryptographic primitive", "does it evaluate on a real deployment", "proof of security or argument only" are all legitimate columns.
- *Why it matters here:* that table is structurally the same object as `templates/extraction-template.md`. Used well, Elicit does the mechanical first pass over the screening queue and leaves the judgement calls — and it handles the screening funnel too (batch-classify a candidate list against inclusion criteria).
- *Limits, and these are load-bearing:*
  - **Every extracted cell is a claim by a language model and has to be verified against the paper before it enters the corpus.** Cells are wrong in ways that look confident. Treat Elicit output as a draft extraction, never as data.
  - The corpus is Semantic Scholar-lineage — same blind spot as ResearchRabbit for **IACR ePrint**, plus patchy proceedings coverage, and it only extracts well where full text is open. Behind IEEE/ACM/Springer paywalls it works off the abstract and quietly gets thinner.
  - Its column vocabulary is tuned for **empirical and biomedical literature** (population, intervention, outcome, sample size). A cryptographic construction paper has no sample size, and asking for one produces plausible nonsense. Define columns in this field's terms or the table degrades into filler.
  - It is a precision tool, not a recall tool. It does not replace category browsing or venue-program sweeps, and the §10 stop rule is unchanged.

**How they slot into the pipeline:** Layer 1/Layer 2 queries and category browsing produce the candidate list → **ResearchRabbit** expands it structurally and catches what no phrasing would → **Elicit** drafts screening decisions and extraction cells → human verification against the paper → corpus. Reversing that order, letting Elicit define the corpus, would make the coverage claim in §8 unsupportable.

## 7. Grey literature

Vendor whitepapers, consultancy reports and product-shaped "research papers" are gathered and extracted like everything else, then tagged `credibility: market-intel-only`. They evidence what is being commercialised and bought — which matters for the applied side — and nothing technical. What the market believes is unsolved is a genuine signal about where the gaps are.

---

## 8. Query set — two layers

Your concern was right: a precise query set has good precision and bad recall, and the papers it misses are exactly the ones nobody thought to name. The fix is two layers plus two query-independent mechanisms.

### Layer 1 — broad recall (run first, high volume, low precision)

`AI agent security` · `AI agent privacy` · `LLM agent security` · `autonomous agent trust` · `multi-agent communication security` · `machine identity` · `non-human identity` · `agent authorization` · `AI accountability` · `verifiable AI` · `AI audit` · `zero-knowledge proof machine learning` · `delegation cryptography` · `capability-based security`

These return hundreds to thousands. That is intended — they run through screening, and screening is cheap. Layer 1 exists to catch what Layer 2's vocabulary cannot anticipate.

### Layer 2 — precision (run second, on the same sources)

*Identity and delegated authorization:* `agent identity delegated authorization` · `multi-hop delegation chain cryptographic` · `attenuating capability token offline attenuation` · `on-behalf-of OAuth AI agent impersonation` · `workload identity SPIFFE agents`
*Trajectory and runtime assurance:* `verifiable agent trajectory attestation` · `runtime verification governed agent actions` · `behavioral trajectory validation` · `runtime enforcement LLM agent safety` · `temporal constraints LLM agents`
*Credentials, revocation, privacy:* `delegatable anonymous credentials` · `mercurial signatures equivalence classes` · `dynamic accumulator revocation` · `selective disclosure credential chain` · `unlinkability delegation chain`
*ZKP and verifiable computation:* `zkML verifiable inference proving cost` · `proof of execution AI` · `verifiable computation delegation`
*Agent protocols:* `MCP Model Context Protocol security` · `A2A agent-to-agent protocol security` · `formal security analysis agent protocol`
*Audit and regulation:* `tamper-evident audit trail AI Act Article 12` · `append-only transparency log provenance` · `certificate transparency agent audit`
*Boundary — what not to duplicate:* `confidential computing TEE agentic AI` · `prompt injection defense agent` · `privilege control AI agent`

### Layer 0 — the two mechanisms that do not depend on queries at all

This is the real answer to "what will we miss." No query set is complete, so recall does not rest on one:

1. **Category browsing.** Scan arXiv cs.CR listings month by month for the last 18 months, titles only. Brute force, but in a field moving this fast it catches what no phrasing would.
2. **Citation-graph expansion and venue-program sweeps.** Both find papers *structurally* rather than lexically — a paper that uses none of your vocabulary still gets caught if an anchor cites it or if it appeared at CCS.

Coverage is claimed only when all three mechanisms saturate together. That is a defensible methodology statement for the plan; "we ran these queries" is not.

---

## 9. Corpus hygiene

**Dedup key**, in order: DOI → arXiv id → normalised `firstauthor+year+title-slug`. The same work routinely appears three times (arXiv preprint, conference version, extended journal version). Keep **one** record with a `versions` list and extract against the most authoritative version, or the venue tally double-counts and the corpus looks bigger than it is.

**Bibkey:** `<firstauthor><year><keyword>`, matching the template's `id`.

**Zotero:** gathering emits a `.ris`/`.bib` plus a plain DOI/arXiv-id list. Zotero's *Add Item by Identifier* takes the whole list pasted at once and fetches metadata and open-access PDFs itself.

## 10. Stop rule

Per thread, not global. A thread is covered when three things hold at once: new queries return only items already held; `chase: yes` references resolve to items already held; and a venue-program sweep for that thread surfaces nothing new. Paper count measures nothing.
