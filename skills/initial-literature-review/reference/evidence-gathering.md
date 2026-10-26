# Finding Papers: What We Tested, What We Found

**Aristidas Končius · 16 September 2026**
*Summary of the September tool tests. The full test log and raw exports are kept by the author and are available on request.*

Nine tools. Five real search queries from our own area. Three rounds over three days.
Not a review of what tools claim — a measurement of what they actually return.

**Everything we ended up recommending is free.**

---

## The five test queries

| | Query |
|---|---|
| Q1 | autonomous agent delegated authorization |
| Q2 | verifiable credentials selective disclosure |
| Q3 | zero-knowledge proof policy compliance |
| Q4 | anonymous credential revocation |
| Q5 | LLM agent security |

> **Important for reading every number below:** in round 1 we only looked at the **top 50 results** from each tool. That was on purpose — nobody screens thousands of papers. But it means we measured **how well a tool ranks**, not how much it contains. A tool holding the perfect paper at position 200 counts here as having missed it.

---

# Round 1 — the normal tools

Six tools that match your words against text. The ordinary way everyone searches.

| Tool | Papers | Has abstract | Free PDF | Median year | From 2024+ | Found by nobody else | Worked? |
|---|---|---|---|---|---|---|---|
| **OpenAlex** | 241 | 83% | 78% | 2021 | 27% | **208 (86%)** | ✅ every time |
| **Google Scholar** | 216 | 100%* | 87% | 2026 | 81% | **175 (81%)** | 🔵 by hand only |
| **Semantic Scholar** | 149 | 88% | 100% | 2025 | **89%** | **107 (72%)** | ⚠️ died after 3 queries |
| **arXiv** | 133 | 100% | 100% | 2026 | 73% | **103 (77%)** | ⚠️ API blocked, website fine |
| **IACR ePrint** | 67 | 100% | 100% | 2022 | 42% | **49 (73%)** | ✅ every time |
| **DBLP** | 142 | none, by design | — | — | — | not comparable | ❌ blocked on server, fine on laptop |

\* Google Scholar's "abstracts" are just search snippets — two fragments around your search words, not real abstracts.

**How many each tool found per query:**

| Query | OpenAlex | GScholar | SemScholar | arXiv | IACR | DBLP |
|---|---|---|---|---|---|---|
| Q1 | 50 | 67 | 50 | 47 | **1** | **0** |
| Q2 | 47 | 39 | 49 | 17 | 13 | 14 |
| Q3 | 47 | 44 | 50 | 12 | 6 | **1** |
| Q4 | 49 | 24 | — | 7 | **42** | 31 |
| Q5 | 48 | 42 | — | 50 | 5 | **96** |

### What round 1 showed

**717 papers came back, and 90% of them were found by only one tool.** The best agreement between any two tools was 19%.

They all index roughly the same literature, then disagree almost completely about what goes on the first page. **Whichever tool you personally use, you are seeing a small and random-ish slice.**

**And the ranking can fail badly.** *Dynamic Accumulators and Application to Efficient Revocation of Anonymous Credentials* (Camenisch & Lysyanskaya, 2002) has about a thousand citations and is the foundational paper of its area. Searching its exact topic, **five of the six tools did not return it at all** — not ranked low, absent from the first fifty. It's in all their databases. It just didn't rank.

**Good news: the paywall is not the problem we assumed.** Publishers have to register their papers with Crossref to get a DOI, so paywalled work *is* findable with free tools — 83–100% of results came with abstracts. A subscription buys the **PDF**, not visibility. The one real gap is pure cryptography (only 56% had abstracts, because Springer doesn't deposit them) — and IACR ePrint covers exactly that gap, free, at 100%.

---

# Round 2 — the AI tool

**Ai2 Asta.** You ask a question in plain language; an LLM reads it, runs its own searches, reads abstracts, and comes back with a graded list. Free, no account, about one minute per query.

| Query | Papers | Also found by the six | **Only Asta found** | Unique % |
|---|---|---|---|---|
| Q1 | 63 | 21 | 42 | 67% |
| Q2 | 75 | 45 | 30 | **40%** |
| Q3 | 72 | 13 | 59 | **82%** |
| Q5 | 74 | 12 | 62 | **84%** |
| **Total** | **284** | 91 | **193** | **68%** |

### What round 2 showed

**Two thirds of what Asta returned, none of the six normal tools had found.**

**It also fixed the ranking failure.** Asked about anonymous credential revocation, Asta opened its answer with the Camenisch & Lysyanskaya 2002 paper that five tools had buried — and called it foundational without being asked.

**The pattern worth copying:** look at the unique column. On Q2, our most precisely worded query, Asta added only 40%. On Q3 and Q5, the vague fast-moving ones, it added 82–84%.

> **Use AI search for questions you can't phrase precisely yet. Not for the ones you can.**

**It's honest about its own results.** Every paper gets graded Perfectly / Relevant / Somewhat Relevant with a one-line reason. On the precise query: 74 of 75 "Perfectly Relevant". On the vague one: 18 Perfectly, 54 "Somewhat". It didn't pretend the weak search went well. That grading is also free screening — it's doing step ② for you.

---

# Round 3 — escaping the vocabulary trap

### Why we needed a third round

Rounds 1 and 2 kept running into the same wall.

**The same idea has two different names depending on who's writing.** Cryptographers call it *anonymous credential revocation*. AI people call it *agent authorization*. It's the same underlying mechanism. Our area sits between the two.

**Round 1 measured how bad this is.** We searched the same underlying idea in three different phrasings. IACR ePrint returned **1 paper, then 13, then 42**. Same idea — the words alone made a 42× difference.

**Round 2 tested whether AI fixes it. It doesn't.** We asked Asta in pure AI-agent language. It returned 63 good papers and **zero** cryptography papers — not one mention of anonymous credentials, selective disclosure, zero-knowledge proofs or accumulators. The AI stayed inside whatever vocabulary we handed it.

So round 3 asked a different question: **is there a tool that doesn't use words at all?**

**ResearchRabbit follows citations instead.** You give it papers you already trust and it walks the citation graph — what they cite, what cites them. Papers cite each other regardless of what words they use. That's the only known way around the problem.

### What we did

| Test | We gave it | We asked for | Result |
|---|---|---|---|
| **Sanity check** | one recent accumulator paper | what it cites | ✅ Camenisch 2002 came back in 10 seconds, plus the whole lineage |
| **Agent → crypto** | an AI-agent delegation paper | similar papers | ❌ 86 results, **zero** cryptography |
| **Crypto → agent** | Camenisch 2002 | what cites it (1,074 papers) | ✅ **found the bridge** |

### What round 3 showed

Reading forward from that 2002 paper turned up:

> **Deochake, 2026 — *Heartbeat-Bound Hierarchical Credentials: Cryptographic Revocation for AI Agent Swarms***

Cryptographic revocation applied to AI agents — exactly the crossing point we'd been unable to reach. **None of the other eight tools found it, across 894 papers.**

**And the rule that makes it work: citations only run forward in time.** A 2026 paper can cite a 2002 paper; the 2002 paper can't cite forward. So:

- Seeding with **recent** papers found nothing outside their own niche — the new literature hasn't absorbed the old ideas yet, so there's nothing to follow.
- Seeding with **old** papers found the crossings — because anyone applying those ideas to a new field *has to cite* the original work.

> **Start from an old, foundational paper and read its citations forward.** That single move is the one thing nothing else could reproduce.

---

# What to actually use

| Tool | Use it for |
|---|---|
| **OpenAlex** | The backbone — bulk, repeatable, citable in a methods section. But it ranks old (median 2021), so never use it alone |
| **arXiv** | Where our field publishes first. Use the **website**; the API blocks you |
| **IACR ePrint** | The cryptography half — the only fix for the abstract gap |
| **Semantic Scholar** | Recency balance: 89% of its results were 2024+, vs OpenAlex's 27%. **Get the free API key** or it cuts you off |
| **Google Scholar** (via Publish or Perish) | Full-text reach, including inside paywalled papers. By hand only |
| **DBLP** | **Checking, not finding** — exact venue, whether a preprint was ever published, linking versions |
| **Ai2 Asta** | Questions you can't phrase precisely yet |
| **ResearchRabbit** | Seed with old papers, read citations forward |

**Minimum sensible habit: use three, not one** — one keyword tool, Asta, and ResearchRabbit. They fail in different ways, which is the entire point.

---

# Things worth knowing for the future

**1. "Search" means different things in the same tool.** The same OpenAlex query returns **134** results on the website and **8,133** through the API — the website searches titles and abstracts, the API also searches full text. So *"I searched OpenAlex for X"* is not a reproducible statement. **Our search log needs a "search mode" field**, or a reviewer can't repeat what we did.

**2. A big result count is a bad sign, not a good one.** Semantic Scholar reports ~71,900 matches for "LLM agent security"; OpenAlex reports 4,253. That isn't more coverage — it's looser matching. Nobody reads 71,900 papers.

**3. Free tools push back when you script them.** In one afternoon of light use: arXiv blocked us for hours, Semantic Scholar cut us off after three queries, DBLP threw up an anti-bot wall. Only OpenAlex took everything without complaint. If we ever automate this, budget for that.

**4. Google Scholar can't be automated at all**, by design. Publish or Perish by hand is the only route.

**5. Citation tools reach paywalled work for free.** ResearchRabbit surfaced the Springer-published Camenisch papers with no subscription, because citation data itself is open.

---

# What we haven't done yet

- **1 October**, when VU access opens: Scopus AI, Web of Science Research Assistant, and full-text search inside IEEE / ACM / Springer / Elsevier. Worth checking first whether **ACM went fully open access in 2026** — that might close one gap by itself.
- **Standing alerts — completely untested.** Everything above is about deliberate searching. We've tested nothing for the automatic layer: Google Scholar alerts, arXiv monthly listings, Scholar Inbox. About twenty minutes to set up, and in a field moving this fast it probably matters more than any single search.
- **Standards bodies are missing from our sources.** IETF, NIST and the OpenID Foundation are actively drafting in our area, and **no academic index covers any of it.** Both AI tools kept pointing at those drafts as the relevant work.

---

## If you remember three things

1. **Use more than one tool.** 90% of what we found came from exactly one tool.
2. **Use AI search for the questions you can't word properly yet** — that's where it doubles your results.
3. **To find foundational work, or work that bridges two fields: start from an old paper and read forward.**
