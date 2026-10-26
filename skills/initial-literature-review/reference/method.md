# Initial Literature Review of a Field

*Drafted 22 September 2026, after the 17 September group meeting. **Status: approved and locked, 22 September 2026.** This is the definition of the process — the thing that gets packaged so that Gintarė, Thomas and anyone else in the group can run it themselves.*

> **This file's job.** This is **the definition**: what the method is, what it gives you, when to run it and when not to. `manual.md` beside it is **the operating manual**, the same stages step by step. `SKILL.md` one level up is what an agent follows when running it. If these ever disagree on *what the method is*, this file wins; on *how a script behaves*, the scripts win.

---

## What it is, in one paragraph

This is a repeatable way of getting from *"we should look into X"* to a defensible map of the field around X: what exists, who works on it, which claims and assumptions keep recurring, which venues and communities own the subject, where the field's own authors say the open problems are — and therefore what a research question in that area could sensibly be. It is deliberately a **first pass over unfamiliar ground**. You run it when you do not yet know an area well enough to ask a precise question about it. Its job is to make the area legible, not to answer anything.

---

## What it defines

Three things, and only these three.

**1. An order of operations.** Six stages that always run in the same order, because each one is only cheap if the previous one was done:

1. **Define** the thread — the question in one sentence, what counts as in, what counts as out, where the boundary with neighbouring topics sits. Half an hour, before any searching.
2. **Gather** — go as wide as the sources allow, using three *different kinds* of search that fail in different ways: keyword matching, citation-graph traversal, and LLM-driven search. Log every query.
3. **Screen** — in / out / maybe on title and abstract only, against the step-1 criteria, with a one-line reason for each decision. No PDFs.
4. **Store** — everything that passed goes into the shared Zotero library in one paste of identifiers, tagged by thread.
5. **Read and extract** — triage by priority, read the ones that earn it, and turn each into a short structured file: what it does, what it assumes, its threat model, what it proves, its limits, what it makes you want to read next.
6. **Synthesise** — with every paper in the same shape, the comparison table is generated rather than assembled by hand, and the patterns and the stated open problems become visible.

Plus a **stop rule**, which is part of the definition and not an afterthought: a first pass is finished when new queries return only things you already hold, the references you meant to chase resolve to things you already hold, and a sweep of the relevant venues' programmes surfaces nothing new. Paper count measures nothing.

**2. The shape of what comes out of each stage.** This is the part that actually makes it a process rather than advice, because it is what lets work pass between people:

- a **query log** — every search, its exact string, the source, the search mode, the date, the hit count, so a search can be repeated or extended later by someone else;
- a **candidates file** — one row per paper found, never deleted from, which is the evidence of what was looked at;
- a **screening file** — decision, reason, who, when, for every candidate, which is the audit trail behind any claim to have covered a field;
- **the shared library** — one Zotero group library holding the metadata, the PDFs and the highlights;
- **one analysis file per paper**, structured fields plus reasoning, named by the citation key;
- **a topic file** — the argument being built across those papers.

Everything is linked by one thing: the **citation key**. It names the analysis file, sits in Zotero, and is what LaTeX eventually cites. Fix its format once and pin it, and the pieces stay connected with no integration work at all. Break it and there are three disconnected systems instead of one.

**3. Which mechanism does which stage — and where AI is and is not trusted.** AI drafts; a human confirms. Concretely: AI is genuinely good at the wide gather and at drafting screening decisions and extraction fields; it is weakest exactly at cross-paper structured extraction, where the published benchmark figure is around 43% recall. So every extracted field is a claim to be checked against the paper, never data. Reading is the part no tool does.

**What it deliberately does not define:** which reading assistant you personally prefer, whether you highlight or not, whether you screen by hand or let AI draft it. Those are preference. Only the handoffs are fixed, because the handoffs are where the work passes from one person to another.

---

## What it gives us

**Recall you can defend.** This is the main thing, and it is the part that was measured rather than assumed. Across nine tools, five real queries from our own area and three rounds: 717 distinct papers came back, and **90% of them were returned by exactly one tool**; the best agreement between any two tools was 19%. The tools index broadly the same literature and then disagree almost completely about what reaches the first page. Two consequences we can now state as fact rather than opinion — the foundational paper of one of our own areas, with roughly a thousand citations, was **absent from the top 50 of five of six tools searching its exact topic** while sitting in all of their databases; and searching in one field's vocabulary returns only that field's papers, with AI search making it no better — asked in pure AI-agent language, the LLM tool returned **zero** cryptography papers. The process exists because of these numbers. Single-tool searching is a much bigger risk than the paywall is.

**An audit trail.** At the end you can say "we covered this field" and show the queries, the candidate list, and a reason for every paper that was dropped. That sentence is otherwise unbacked, and it is the sentence a thesis proposal, a related-work section and a reviewer response all rest on.

**Reading that compounds instead of evaporating.** A paper read once and extracted stays useful to you in year three and is visible to everyone else in the group. Without this, what one person reads is invisible to everyone, and a search run six months ago cannot be repeated.

**A stop condition.** It tells you when a first pass is done, which is otherwise a feeling.

**Onboarding.** Someone joining should be able to read this, install the setup list, look at one filled example, and produce their first correct extraction the same day. If they can't, the document is wrong — fix the document, not the person.

---

## When to use it

Run it when **all** of these are true:

- the area is **new to you** — you can't yet name the sub-communities, the standard assumptions, or the venues;
- you need a **map**, not an answer — you want to know what people write about, how the area is carved up, and what its authors themselves call open;
- the output will feed a **decision about direction** — choosing a topic, sharpening a research question, deciding whether an area is worth entering, writing a related-work or state-of-the-art section, or preparing a plan or proposal;
- it is **worth days, not hours**. This is a deliberate pass with a setup cost.

The typical triggers: starting a PhD topic or a new chapter; a supervision meeting that ends in "look into X"; being asked whether some area is already solved; opening a new thread in an ongoing project.

It is also **not once per project.** A first pass almost always spawns sub-questions, and each of those is its own first pass later, with its own thread file and its own stop rule. It branches; it does not end.

---

## When *not* to use it — the meeting's actual conclusion

The 17 September meeting agreed that what was presented is a large and useful part of AI-assisted research, but **one part of it**, and that treating it as the whole would be a mistake. Its scope is the **initial orientation in a field**. Other work needs something different:

- **A specific factual or technical question** ("does construction X have a security proof against Y?") — that's a targeted lookup, not a field map. Running this process on it is pure overhead.
- **Staying current in an area you already know** — that's the everyday capture habit: a daily digest, an inbox, ten minutes a week of sorting. It shares the library, but nothing else. It is a separate loop with a separate rhythm.
- **Deep engagement with a small set of papers you have already chosen** — reproducing a result, working through proofs, comparing two constructions in detail. That starts after this process has handed over its output.
- **Actually doing the research** — designing, building, proving, experimenting, writing. This process only establishes where the ground is.

The short version: **this is the process for knowing what a field contains. It is not the process for producing knowledge in it.**

---

## Honest limits, stated up front

These belong in the definition, because they are what a user of the packaged version will otherwise overclaim.

**On "identifying gaps."** This process reliably surfaces two kinds of gap: the **stated** ones — open problems the papers' own authors name — and the **structural** ones — two literatures that clearly address the same problem and do not cite each other. It does **not** prove that something is missing from a field. A thing being absent from your corpus is weak evidence that it is absent from the world, and the measured ranking failures above are exactly why. Claims of the form "nobody has done X" need a targeted adversarial search for X specifically, on top of this.

**On the boundary with a "deep pass."** The six stages are the same ones a deeper pass would use. What actually differs is breadth versus depth, how much gets fully extracted, and where the stop rule is set. It is an honest simplification to call this a separate process, but the line is one of degree, not of kind — worth saying plainly rather than implying a cleaner separation than exists.

**On what is still untested.** The gather stage and the read/extract stage have been tested hands-on against real queries from our own area. The screen and store stages are so far desk-reviewed only, and the licensed-database routes (Scopus, Web of Science, IEEE, ACM, Springer) become available from 1 October and are untested until then.
