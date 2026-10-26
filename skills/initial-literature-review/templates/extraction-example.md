# Worked Example — Extraction Template Applied

*Filled 2026-08-29 against `extraction-template.md`. Purpose: test that the fields work on a real paper before running the template across hundreds. Kept out of `papers/` because it is a specimen, not corpus data.*

**Honest caveat, which is part of the demonstration:** filled from the abstract and bibliography plus what is already established in `research/threads/field-landscape/2026-08-23-field-landscape.md`, not from a full read. Several fields therefore say `unknown` — which is what rule 1 requires, and what an entry should look like before the full text is worked through.

---

```yaml
id: lotfi2026trajectory
title: "Securing Agentic AI: From Per-Action Checks to Trajectory Assurance"
authors: Alireza Lotfi, Subangkar Karmaker Shanto, Imtiaz Karim, Elisa Bertino
affiliation_type: academic          # Purdue CS + UT Dallas
year: 2026
venue: arXiv (accepted to ACM AI Leadership Summit 2026)
venue_type: arxiv-only
peer_reviewed: no                   # summit acceptance is not security-venue review
doi_or_url: https://arxiv.org/abs/2608.01558
contribution_type: position
areas: [agent-identity, delegation-authz, trajectory-assurance, agent-protocols,
        prompt-injection, supply-chain-security, model-provenance, observability-telemetry,
        policy-governance, multi-agent-systems]
techniques: [none]
one_line: >
  Argues that agent security must be a verifiable property of architectures and runtimes
  rather than guidance, and enumerates eleven open problems across the agentic stack.
relevance: core
relevance_reason: n/a
credibility: verify-first           # strong group, no peer review, no results to check

maturity: theory-only
field_state: contested
artifact_available: n/a
venue_rank: n/a
citations_approx: unknown (check 2026-09)

key_references:
  - cite: "Chan et al., Visibility into AI Agents, FAccT 2024"
    id: arXiv:2401.13138
    why: The accountability/observability framing this paper builds its supply-chain section on; peer-reviewed, unlike most of the corpus.
    chase: yes
  - cite: "Anbiaee et al., Security Threat Modeling for Emerging AI-Agent Protocols: MCP, A2A, Agora, ANP, 2026"
    id: arXiv:2602.11327
    why: Load-bearing for the multi-agent delegation section, and already independently in the corpus — the overlap is itself a signal.
    chase: no      # already gathered
  - cite: "Wang et al., AgentSpec: Customizable Runtime Enforcement for Safe and Reliable LLM Agents, ICSE 2026"
    id: unknown — ICSE proceedings
    why: The closest existing thing to a runtime trajectory-enforcement mechanism; needed to establish whether behavioural containment is genuinely unaddressed or merely unformalised.
    chase: yes
  - cite: "Zhou et al., FormalJudge: A Neuro-Symbolic Paradigm for Agentic Oversight, 2026"
    id: arXiv:2602.11136
    why: Neuro-symbolic oversight is the main competing approach to a cryptographic one — the alternative that has to be argued against, not ignored.
    chase: yes
  - cite: "Shi et al., Progent: Securing AI Agents with Privilege Control"
    id: arXiv:2504.11703
    why: Privilege control is the per-action baseline the paper's whole argument is defined against.
    chase: yes
```

**1. Problem.** Agent safety is determined by whether overall behaviour stays consistent with the rules and invariants of the systems agents operate in, not by the correctness of individual actions. As LLM agents delegate across organisational boundaries, securing them becomes a landscape spanning the whole stack rather than a single problem.

**2. Central claim.** Security for agentic systems must become a verifiable property of the architectures, protocols, and runtimes that govern agent behaviour, rather than an optional layer of guidance.

**3. System model.** The full agentic stack: single agent (prompts, memory, retrieval, tool interfaces); multi-agent delegation and communication across organisational boundaries; and the model routing and execution control plane beneath both.

**4. Threat model.** Untrusted inputs via prompt, memory, retrieved knowledge and tool interfaces; manipulation of the routing and execution control plane; unverified model provenance. Whether a formal adversary model is given is `unknown` pending full read. The framing treats *composition* as the adversary's lever rather than any single action.

**5. Assumptions.** *Implicit:* that per-action authorisation is broadly solvable and the hard residue is sequence-level. *Implicit:* that "system-level constraints and safety invariants" can be expressed precisely enough to check against — the paper appears to assume the specification already exists. **That second implicit assumption is the gap this thesis lives in.** Stated assumptions `unknown` pending full read.

**6. Mechanism.** None. This is a roadmap paper; its contribution is the decomposition and the eleven open problems.

**7. What is actually established.** *Proven:* nothing. *Argued informally:* the unifying principle in field 2. *Asserted:* the completeness of the eleven-problem enumeration. *Empirical:* nothing. Recorded without prejudice — a position paper owes no proofs. But it means the paper supports the citation "a credible group considers this open" and not "this has been shown to be hard".

**8. Evaluation.** None. n/a.

**9. Numbers worth keeping.** Eleven open problems; #5 Agent Identity & Delegated Authorization, #9 Behavioral Trajectory Validation. No quantitative results.

**10. Limitations admitted by the authors.** `unknown` pending full read.

**11. Limitations not admitted.** Behavioural containment is named "perhaps the most fundamental challenge" with no definition of what containment would mean formally — so the hardest problem identified is the least specified. The eleven problems are also presented as a flat list where several are plainly dependent: trajectory validation is not attackable before delegation semantics are pinned down.

**12. What would have to be true for this to be wrong.** That sequence-level violation is not a distinct problem class — i.e. that a sufficiently expressive per-action policy language collapses trajectory assurance back into per-action checking. Worth taking seriously rather than dismissing: if true, the thesis's secondary thread loses its motivation. `Progent` and `AgentSpec` in `key_references` are the two papers most likely to settle it.

**13. What it leaves open.** Explicitly, all eleven problems, of which #5 and #9 are the thesis. Unmentioned by the authors: what a formal definition of trajectory compliance would look like; whether delegation accountability and delegation privacy can hold simultaneously; what any of it costs. **All three are cryptographer-shaped and this group is not positioned to answer them.**

**14. Relation to the thesis.** `must-cite-and-differentiate`. Strongest available external validation that both threads are open, and simultaneously the clearest warning that a well-resourced group is on the same ground. Differentiation line: they chart the landscape; the thesis formalises two points on it.

**15. Relation to other papers in the corpus.** Frames the same accountability gap `otsuka2026identity` states in one sentence — complementary, not duplicative. Sits above the preprint flood in §3 of the landscape file: those propose constructions for problems this paper only names. Shares `anbiaee2026threats` with the existing corpus.

**16. Standards and regulatory hooks.** None directly. The multi-hop delegation framing maps onto the IETF agent-delegation drafts but the paper does not engage them — if the full text cites no drafts, that absence is itself an opening worth occupying.

**17. Verdict.** Real and strategically important, but as a map rather than a result. It says where to dig and confirms the ground is unclaimed; it does not claim any of it.

**18. Quotable.** "security must become a verifiable property of the architectures, protocols, and runtimes that govern agent behavior, rather than an optional layer of guidance" (abstract).

---

## What this example proved about the template

- Field 7 does real work immediately — it separated "a credible group says this is open" from "this has been shown to be hard". Different citations, used differently.
- Fields 11–13 produced three candidate research questions from a single paper.
- `key_references` produced four new fetchable items on the first paper, one of which (`AgentSpec`) directly bears on whether the thesis's secondary thread survives. Four new items per paper is the expansion rate to expect early; it collapses toward zero as the graph closes, which is the saturation signal.
- Filling from abstract plus bibliography got roughly two thirds of the fields honestly — the rest genuinely needs the full text.
- Field 15 will feel useless for the first twenty papers and indispensable after eighty. Fill it from the start anyway.
