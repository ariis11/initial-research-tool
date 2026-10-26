# Paper Extraction Template

*Version 3, 6 October 2026. The generic fields are the same for every review. The `thread` block asks, of every paper, the questions one particular review is about, so it is defined per thread in `thread.md` (see `thread-block-example.md`). Version 2, 23 September 2026.*

*Earlier:* Replaces v1 (29 August). Rewritten around two things v1 did not have: **every judgement field must carry a quote**, and the fields are organised so that the gap analysis falls out of them instead of being invented later.*

---

## The three rules

**1. Metadata is copied, judgement is quoted.** Fields in the `meta` block come from the item record and need no evidence. Every field in the `claims` block is a judgement about what the paper says, and each one must have a matching entry in `evidence` giving a verbatim quote and where it came from.

**1a. `none` and `null` are different answers, and only one of them needs a
quote.** A negative finding cannot be evidenced by a quotation -- no sentence
in a paper says "we reference no standard" -- so requiring one forces genuine
negatives to be recorded as `null`, where they become indistinguishable from
"nobody looked". That destroys exactly the counts this review is built on.

So: **`none` means checked and absent, and needs no quote.** Use it whenever
you have read the relevant parts and the thing is not there. **`null` means not
established** -- the section was missing, the PDF was truncated, the record had
no document. Every `null` gets an `unanswered` entry saying which it was.
`none` does not.

**2. Nothing is guessed.** If the paper does not answer a field, the value is `null` and a line in `unanswered` says so. An empty field is information — it is often the most useful information in the file, because a paper that never states its threat model is telling you something. A confabulated field is worse than no file at all.

**3. Verified means a human checked it.** `verified` stays `false` until someone has read the quotes against the paper. The date and initials go in when they do.

---

## The file

One file per paper, at `research/papers/<bibkey>.md`. The name is the citation key and nothing else.

```markdown
---
# ── meta: copied from the item record, no evidence needed ──────────────
bibkey: crites2023mercurial
zotero_key: ABCD1234
title: "Mercurial Signatures for Variable-Length Credentials"
authors: [Crites, Lysyanskaya]
year: 2023
venue: CRYPTO
venue_type: conference          # conference | journal | preprint | standard | report
peer_reviewed: true
doi: 10.1007/...
arxiv: null
threads: [agent-identity]       # which threads this paper serves

# ── claims: each needs an evidence entry ───────────────────────────────
problem: "Delegating a credential without revealing the delegation chain"
contribution_type: construction # construction | framework | analysis | attack | measurement | sok | position
techniques: [mercurial-signatures, equivalence-classes]
system_model: "Issuer, delegator, delegatee, verifier; no online authority"
threat_model: "Malicious issuer, honest-but-curious verifier"
assumptions: [random-oracle, generic-group]
security_argument: game-based-proof   # game-based-proof | simulation | uc |
    # formal-model | symbolic-verification | machine-checked | informal | none |
    # n/a -- use n/a for a specification or survey that makes no security
    # argument because its genre does not have one. `none` says the paper
    # should have argued and did not; `n/a` says the question does not apply;
    # `null` says you could not tell. Same three-way split applies to
    # `evaluation`.
evaluation: benchmark           # benchmark | measurement | proof-only | case-study | deployment | none | n/a
real_deployment: false
limitations_stated: "Chain length must be fixed at issuance"

# ── gap-facing: the fields the synthesis is built from ─────────────────
open_problems_stated: "Revocation across a delegation chain is left open"
leaves_open: "No treatment of what happens when an intermediate key is compromised"
limitations_unstated: "Assumes verifier clock sync, never mentioned"
what_would_make_it_wrong: "If the equivalence-class assumption fails under adaptive queries"
contradicts: []                 # bibkeys making an incompatible claim
builds_on: [dodis2002accumulator]
chase: [crites2019delegatable]  # references worth pulling in, where the bibkey is KNOWN
chase_unresolved: ["Kilian & Petrank, non-interactive zero-knowledge"]
    # Worth chasing but not yet in the corpus, so no bibkey exists. Free text.
    # This field exists because an agent correctly refused to invent plausible
    # bibkeys: a fictional one passes extract_check and silently corrupts the
    # citation graph, which is worse than an unresolved string.

# ── thread block: the questions THIS review is about ───────────────
# Defined per thread, in thread.md, not here. List the questions your
# synthesis will ask of every paper, give the ones with a fixed set of answers
# an ```extraction-vocab block in thread.md, and extract_check.py enforces
# those values. `null` where the paper is silent -- silence here is often the
# finding. A worked example of a full block, from an agent-identity review, is
# in templates/thread-block-example.md.
thread:
  my_question: value            # one key per question; null if the paper is silent
  takeaway: "One sentence: what this paper does for THIS thread."

# ── quality: what the PAPER shows, not what its name suggests ──────────
# Venue reputation is NOT judged here. Judging it from journal names once gave
# 18% at decent venues where Scopus said 6%, and missed the corpus's strongest
# venue outright. So `venue_tier` is left null and filled afterwards from
# Scopus and WoS data. Everything below is visible in the document itself.
quality:
  peer_reviewed: true           # does the document itself show review? (proceedings of, journal issue, "accepted at")
  peer_review_evidence: "Published in Proceedings of NDSS 2026"   # what tells you, verbatim; null if nothing does
  self_published: false         # preprint server, Zenodo, SSRN, personal site with no venue
  document_kind: paper          # paper | specification | white-paper | thesis | report | standard | blog | dataset | software
  rigour: [formal-proof]        # LIST. formal-proof | empirical-evaluation |
    # systematic-review |
    # case-study | worked-example | argument-only | none. A paper that proves a
    # theorem AND benchmarks it is both, and forcing one undersells it.
  artifacts: code               # code | data | both | none | null
  reproducible_claim: false     # does it claim others can reproduce the result?
  page_count: 14                # a 3-page white paper and a 14-page paper are different objects
  references_count: 42          # a paper with 6 references is telling you something
  venue_tier: null              # FILLED BY SCRIPT from Scopus/WoS. Leave null.
  bibliography_trustworthy: true  # true | false | null
    # false when the reference list contains placeholder DOIs or arXiv ids
    # (2404.12345), author-less institutional entries, or in-text citations
    # numbered beyond the list. Six documents in this corpus failed this, and
    # in several the fabricated reference carried a load-bearing empirical
    # claim. A paper whose bibliography is invented cannot be cited for
    # anything, whatever its venue.

# ── our judgement ──────────────────────────────────────────────────────
relevance: core                 # core | supporting | background | tangential
relevance_why: "Proposes the delegation-chain mechanism this review is about"   # one line
credibility: high               # high | medium | low — venue + rigour, not citations

# ── verification ───────────────────────────────────────────────────────
verified: false
verified_by: null
verified_date: null

# One quote per field, OR a list where the field is multi-valued -- `scoping`
# and `standards_referenced` routinely need two and a single quote cannot
# evidence both.
evidence:
  problem:              {quote: "...", loc: "p.1, abstract"}
  scoping:              [{quote: "...", loc: "p.6, §4"}, {quote: "...", loc: "p.7"}]
  threat_model:         {quote: "...", loc: "p.4, §3.1"}
  assumptions:          {quote: "...", loc: "p.5, Def. 2"}
  security_argument:    {quote: "...", loc: "p.11, Thm. 1"}
  evaluation:           {quote: "...", loc: "p.14, §6"}
  real_deployment:      {quote: "...", loc: "p.15, §7"}
  limitations_stated:   {quote: "...", loc: "p.15, §7"}
  open_problems_stated: {quote: "...", loc: "p.16, §8"}

unanswered:
  - field: system_model
    why: "The paper never states whether the verifier is online"
  - field: thread.my_question
    why: "The paper never addresses it"
---

## Why it matters here
*Two or three sentences. What this paper does for the thread — not a summary of the paper.*

## What it actually does
*The mechanism, in your own words, at the level you would explain it to a colleague.*

## Assumptions and limits
*Including the ones the authors did not admit to. This is where `limitations_unstated` gets argued rather than asserted.*

## Objections
*Where you disagree, what you would want tested, what the paper would need to show to convince you.*
```

---

## Why these fields and not others

**The gap-facing block is the point of the whole file.** Four of its fields do different jobs and should not be collapsed into one "limitations" note:

- `open_problems_stated` — what the authors themselves name as open. This is the **strongest kind of gap claim** you can make, because the citation supports it directly. Always quote it.
- `leaves_open` — what the paper does not address and does not admit to not addressing. Your judgement, arguable, and the honest place for it is the prose, with this field as the one-line handle.
- `limitations_unstated` — assumptions smuggled in. This is where reviewers find holes and where research questions come from.
- `what_would_make_it_wrong` — the falsifier. Forces you to understand a paper rather than file it.

`contradicts` and `builds_on` are what make the corpus a graph rather than a list. Two papers that contradict each other on the same threat model is a finding on its own.

`chase` is the engine of the citation-graph mechanism. Every extraction feeds candidates back into gathering, which is why a thread branches rather than finishing.

**The `thread` block is what makes a second pass unnecessary.** Every field in
it is a question the synthesis will ask, so asking them once, while the PDF is
open, is the whole saving. Design it at Gate A, before extraction starts: a
field added halfway through means re-reading everything already done. See
`thread-block-example.md` for a full block and the reasoning behind each field.

**Controlled vocabularies are fixed** for `contribution_type`, `security_argument`, `evaluation`, `venue_type`, `relevance` and `credibility`. Free text in these columns makes the comparison table useless, which is the one thing it cannot be.

**The `quality` block separates three things that get confused.** Whether a
document was *reviewed*, what *kind* of document it is, and how much *work* is
behind it are independent, and a corpus like this one needs all three. A
well-argued specification is not a weak paper; it is not a paper. A peer-
reviewed three-page extended abstract with six references is a paper, and a
thin one.

`venue_tier` is deliberately left for a script. The one time venue quality was
judged by impression in this project it was wrong by a factor of three, in the
optimistic direction. `page_count` and `references_count` are there because they
are cheap, objective, and separate a real contribution from a position piece
faster than any judgement does.

**`credibility` is the venue and the rigour, never the citation count.** A heavily cited preprint with no proof is not credible; an obscure paper at CRYPTO with a tight reduction is.

---

## What the machine checks, and what you check

`extract_check.py` verifies mechanically, on every file: the YAML parses; every required field is present; every non-null field in `claims` has an `evidence` entry; **every quote appears verbatim in the paper's full text**; controlled-vocabulary fields use permitted values; every bibkey in `chase`, `builds_on` and `contradicts` is well-formed.

That leaves exactly one thing for a human, and it is the thing a machine cannot do: **does the quote actually support the claim attached to it?** That is the Gate D sample check, and it is why the quote rule exists — it converts verification from re-reading the paper into reading eight short quotes.
