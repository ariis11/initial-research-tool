# Thread — <short name>

*Opened <YYYY-MM-DD> by <who>. One thread = one first pass over one area.*

**Status: DRAFT, awaiting Gate A.** Nothing is gathered until the owner approves this file. Replace every TO FILL marker before running the scripts: `status.py` treats the thread as undefined while any is left.

---

## 1. The question

[TO FILL] One sentence. For a first pass this is usually a survey question, not a research question:

> What does the field of <X> currently consist of: what problems is it trying to solve, with what mechanisms, in which communities, and what do its own authors call open?

## 2. What counts as in

[TO FILL] The sub-topics, one bullet each, broad enough that a paper written in another community's vocabulary still qualifies.

## 3. What counts as out

[TO FILL] Neighbouring topics that look relevant and are not, each with a one-line reason. Screening is judged against this list, so vague exclusions become band-3 papers.

## 4. Boundary with neighbouring work

[TO FILL] Other threads, colleagues' work, earlier passes. Anything already extracted elsewhere is reused, not re-gathered.

## 5. Vocabularies and queries

Different communities name the same idea differently, and one tool searching one vocabulary misses the rest. Write the queries in every vocabulary the area spans: systems, cryptography, standards, law, HCI, whatever applies. Short and precise beats long and fuzzy: phrase searches are taken in full, everything else is capped.

```queries
# [TO FILL] replace these placeholder lines, then delete this one
# ── A · <first vocabulary> ──
<query one>
<query two>

# ── B · <second vocabulary> ──
<query three>
```

Optional: which sources `gather.py` uses for this thread. Leave the block out for the default set (OpenAlex, Semantic Scholar, arXiv, IACR ePrint, plus Scopus when a key is configured). Known names: openalex, semanticscholar, crossref, arxiv, eprint, scopus (needs a key), wos (needs a key). The list replaces the default set, so name every source you want. DBLP and Google Scholar are searched by hand.

```sources
# openalex semanticscholar arxiv eprint
```

Optional: terms that order the screening batches, most relevant first, as `<weight> <regex>`. This only changes the order; every paper is still screened. Leave it out and the words of the queries are used.

```relevance
# 4 core term|synonym
# 2 supporting term
```

## 6. Seed papers

[TO FILL] Five to ten anchor papers for `expand.py`, each a DOI, arXiv ID or exact title. Include at least one **old** foundational paper from each community. Reading forward from an old paper finds the work that shares none of your vocabulary.

- <DOI or arXiv ID> — <why it is a seed>

## 7. Extraction: the questions this review asks of every paper

*Fill this before extraction starts; gathering does not need it.* The topic-specific fields that go in each analysis file's `thread:` block. See `templates/thread-block-example.md` for a full worked block. Fields with a fixed set of answers get controlled values here, and `extract_check.py` enforces them:

```extraction-vocab
# field: value | value | value
```

## 8. Stop rule

A first pass is finished when new queries return only papers already held, the references worth chasing resolve to papers already held, and a sweep of the relevant venues' programmes surfaces nothing new. Paper count measures nothing.
