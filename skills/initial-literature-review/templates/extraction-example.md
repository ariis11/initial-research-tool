# Worked example — one analysis file, filled in

*A real file from an agent-identity review: Chan et al., "Visibility into AI Agents", FAccT 2024. It passes `extract_check.py`: every quote below was string-matched against the paper's full text. Use it to see the shape: what goes in the frontmatter, how evidence is quoted with a location, how `unanswered` is used, and what the four prose sections are for. The `thread:` block is that review's own; yours will ask your thread's questions (see `thread-block-example.md`). `verified: false` because no human has done the Gate D check on it yet.*

The file is saved as `research/papers/chan2024visibility.md`. Everything from the first `---` to the end is the file:

````markdown
---
# ── meta ───────────────────────────────────────────────────────────────
bibkey: chan2024visibility
zotero_key: IPILZF7T
title: "Visibility into AI Agents"
authors: [Chan, Ezell, Kaufmann, Wei, Hammond, Bradley, Bluemke, Rajkumar, Krueger, Kolt, Heim, Anderljung]
year: 2024
venue: "ACM Conference on Fairness, Accountability, and Transparency (FAccT '24)"
venue_type: conference
peer_reviewed: true
doi: 10.1145/3630106.3658948
arxiv: null
threads: [agent-identity]

# ── claims ─────────────────────────────────────────────────────────────
problem: "As activities are delegated to systems that pursue goals with limited supervision, nobody — regulators, service providers, the public, or the agent's own user — has the information needed to say where, why, how and by whom AI agents are being used, so existing governance structures cannot be evaluated or enforced"
contribution_type: framework
techniques: [agent-identifiers, agent-cards, watermarking, request-headers, software-attestation, real-time-monitoring, activity-logging, compute-provider-know-your-customer, tool-provider-gating, differential-privacy, data-trusts]
system_model: "A supply chain rather than a system: developers build the agent or its underlying model, deployers run it and serve instances to users, compute providers supply the hardware, tool and service providers expose the APIs the agent acts through, and regulators sit outside. The deployer is the central intermediary because it already sees every input and output, and the paper then asks how the same measures extend to decentralized deployments that bypass deployers entirely"
threat_model: "Five agent-specific risk classes — malicious use where agents remove the expertise barrier to harm, overreliance and societal disempowerment, delayed and diffuse impacts that are only visible in aggregate, multi-agent risks including collusion and destabilising feedback loops of the 2010 flash-crash kind, and sub-agents that multiply points of failure. Against the measures themselves: adversarial removal of watermarks, agents circumventing APIs by mimicking human interaction, agents spoofing human identity verification, and abuse of the collected data for surveillance"
assumptions: [deployers-see-all-inputs-and-outputs, most-capable-models-reachable-only-through-deployers, identifiers-can-be-cryptographically-bound-to-an-instance, compute-providers-can-detect-large-scale-agent-deployments, tool-access-is-a-chokepoint-agents-will-not-route-around]
security_argument: informal
evaluation: none
real_deployment: false
limitations_stated: "The authors decline to advocate immediate implementation, saying more research is needed on feasibility and on mitigating the measures' own harms, and close by stating that visibility is not by itself sufficient because those harmed may still lack the power to intervene"

# ── gap-facing ─────────────────────────────────────────────────────────
open_problems_stated: "Stopping an agent may require intervening on its sub-agents, and no method exists for determining when an agent has created one; how to balance privacy against identity verification is named as open; and the feasibility and implications of all three measure categories are left for further work"
leaves_open: "The paper reaches authorisation twice in single sentences — an identifier that 'might explicitly confirm permissions', an agent card field for 'the agent's permissions' — and never develops either. Who issues a permission, what binds it to an instance, and above all how one is withdrawn are absent. The omission is sharpest where the paper reaches for Let's Encrypt as the model for certifying valid identifiers: it takes the issuance half of the certificate-authority analogy and leaves behind the half that CAs spend most of their engineering on, which is revocation and its propagation"
limitations_unstated: "Every measure is implemented by the deployer, and the paper's own power-concentration section argues that routing agent activity through a small number of certified deployers is itself a systemic risk. The framework therefore prescribes strengthening the position of the actors whose dominance it identifies as a hazard, and the mitigations offered — voluntary standards, open-source identifier frameworks — are the weakest instruments in the paper applied to its hardest problem. Second, the three measures are described as complementary but they trade against each other in a way never quantified: real-time monitoring is sold on avoiding logs for privacy reasons, while sub-agent and delayed-impact detection is sold on retaining logs beyond the agent's lifetime"
what_would_make_it_wrong: "If identifiers are honoured only where they are already cheap to honour, visibility is obtained into exactly the agents that were never the problem while malicious decentralized deployments stay dark, and the measures' net effect is to surveil ordinary use. The paper half-sees this and answers with compute-provider KYC and tool-access gating, both of which it then concedes are surveillance and market-concentration hazards — so the argument has no exit that is not also a harm"
contradicts: []
builds_on: []
chase: []
chase_unresolved: ["Chan et al., Harms from Increasingly Agentic Algorithmic Systems, FAccT 2023", "Naihin et al., preliminary implementation of a real-time monitoring system for agents (ref 116)", "Egan & Heim, Oversight for Frontier AI through a Know-Your-Customer Scheme for Compute Providers, arXiv:2310.13625", "Carey & Everitt, Human Control: Definitions and Algorithms, UAI 2023", "Zhang et al., Watermarks in the Sand: Impossibility of Strong Watermarking for Generative Models, arXiv:2311.04378", "Cooper, Moss, Laufer & Nissenbaum, Accountability in an Algorithmic Society, FAccT 2022"]

# ── thread block ───────────────────────────────────────────────────────
thread:
  identifies_what: agent
  principal_relation: "The identifier's purpose is to link an action to the agent and through it to the user, developer(s) and deployer; the agent card records how the instance was created — by its user directly or by another agent — along with the compute provider, the developers of any scaffolding or component model, and the tool providers it may use. Authority is never traced to the principal, only accountability: the paper establishes whom to hold responsible, not whose permissions the agent is spending"
  authority_mechanism: token
  authority_binding: "Bound to a specific agent instance and to the outputs it emits — a watermark on media, a header on an API request — with an attached agent card recording the goal the user set, the tools the agent can reach, its permissions, its lifetime and the actors behind it"
  scoping: [operation, amount, time, task-context, provenance]
  attenuation: null
  delegation_depth: multi-hop
  revocation: suspend
  revocation_on_demand: true
  revocation_scope: agent-authority
  revocation_latency: unstated
  attribution: "The explicit purpose of two of the three measures. Activity logs record inputs and outputs, tool use, internal reasoning, self-critique and memory management to enable post-incident attribution and forensics; identifiers link an action to a particular agent instance and to the actors behind it; and the paper notes logs may have to be combined across agents where one agent is a continuation of another"
  human_in_loop: varies
  non_determinism: addressed
  standards_referenced: [ai-act, gdpr, pci-dss, hipaa]
  names_field_as: "visibility"
  cites_pre_2015: true
  key_numbers: "Google's no-logging provision for language model deployments still keeps logs for 72 hours"
  takeaway: "Names the sub-agent stop problem precisely — halting an agent may mean halting agents nobody knows exist — and builds identification machinery that has no withdrawal step."

# ── quality ────────────────────────────────────────────────────────────
quality:
  peer_reviewed: true
  peer_review_evidence: "In *The 2024 ACM Conference on Fairness, Accountability, and Transparency* *(FAccT ’24), June 03–06, 2024, Rio de Janeiro, Brazil.* ACM, New York, NY, USA, 16 pages."
  self_published: false
  document_kind: paper
  rigour: [argument-only]
  artifacts: none
  reproducible_claim: false
  page_count: 16
  references_count: 181
  venue_tier: null

# ── our judgement ──────────────────────────────────────────────────────
relevance: core
relevance_why: "The reference statement of agent identifiers and agent cards, and the clearest articulation anywhere in the corpus of why stopping an agent is harder than stopping a process"
credibility: high

# ── verification ───────────────────────────────────────────────────────
verified: false
verified_by: null
verified_date: null

evidence:
  problem:
    quote: "Information about where, why, how, and by whom certain AI agents are used, which we refer to as visibility, is critical to these objectives."
    loc: "p.1, abstract"
  contribution_type:
    quote: "In this paper, we assess three categories of measures to increase visibility into AI agents: agent identifiers, real-time monitoring, and activity logs."
    loc: "p.3, §1.3"
  techniques:
    quote: "Agent identifiers indicate whether and which AI agents are involved in a given interaction, such as watermarks or IDs that distinguish agents in their requests to ser- vice providers."
    loc: "p.4, §3"
  system_model:
    quote: "The deployer is the entity that operates an AI system and serves it to users. The deployer may not be the same as the developer(s)."
    loc: "p.4, §2"
  threat_model:
    quote: "In comparison to risks from other AI systems, these risks focus on the potential for agents to remove humans from the loop [35, 101]."
    loc: "p.2, §1.1"
  assumptions:
    quote: "Moreover, since deployers can already see the inputs and outputs of deployed systems, they can attach agent identifiers to outputs, perform real-time monitoring, and collect activity logs."
    loc: "p.5, §3"
  security_argument:
    quote: "The difficulty of im- plementing identifiers varies based on the format of the output: for instance, adversarial users may easily remove watermarks [178]."
    loc: "p.5, §3.1.1"
  evaluation:
    quote: "Finally, while we discuss potential implementations of the measures, more research is required to understand their feasi- bility and implications."
    loc: "p.5, §3"
  real_deployment:
    quote: "Rather than advocating for immediate implementation of these measures, we emphasize the need for further understanding them and how to mitigate their negative impacts."
    loc: "p.3, §1.3"
  limitations_stated:
    quote: "Visibility informs actions to manage risks from the deployment of increasingly agentic systems, but is not by itself sufficient."
    loc: "p.10, §5"
  open_problems_stated:
    quote: "Stopping an agent from causing further harm might involve intervening not only on the agent, but also on any relevant sub-agents [30, 154]. Yet, this process may be difficult because we lack methods for determining when an agent has created a sub-agent."
    loc: "p.3, §1.1.5"
  thread.identifies_what:
    quote: "An agent identifier indicates whether and which AI agents are involved in interactions."
    loc: "p.5, §3.1"
  thread.principal_relation:
    quote: "Unique identifiers for each AI agent could facilitate accountability by linking an action to an AI agent and its user, developer(s), and deployer."
    loc: "p.5, §3.1"
  thread.authority_mechanism:
    quote: "Such identifiers might explicitly confirm permissions to access certain services, such as performing financial transactions or accessing certain websites."
    loc: "p.9, §4.2"
  thread.authority_binding:
    quote: "Agent identifiers are attached to select outputs, are visible to certain actors, and may include additional information about the agent."
    loc: "p.5, §3.1"
  thread.scoping:
    - quote: "The agent’s permissions (e.g., whether it has sudo access in a terminal);"
      loc: "p.16, Appendix A.2"
    - quote: "Thus, real-time monitoring may be most suitable for identifying violations of clear rules such as restrictions on allowed activities of agents, limits on tools and permissions made available to agents, leakage of sensitive infor- mation, or usage caps for particular users or agents."
      loc: "p.7, §3.2"
    - quote: "Details about the persistence of the agent, such as whether the agent has a set lifetime;"
      loc: "p.16, Appendix A.2"
    - quote: "The agent’s goal, including both what the user specifies and what the system appears to be achieving [69];"
      loc: "p.16, Appendix A.2"
    - quote: "For example, financial institutions could restrict access to AI agents without identifiers from certain trusted deployers."
      loc: "p.9, §4.2"
  thread.delegation_depth:
    quote: "For example, an agent could call copies of itself through an API, or itself train, fine-tune, or otherwise pro- gram another agent."
    loc: "p.3, §1.1.5"
  thread.revocation:
    quote: "A potential response to such a flagged activity could be pausing it until the deployer can verify explicit user approval, just as banks monitor transactions and temporarily suspend accounts if they suspect fraud."
    loc: "p.7, §3.2"
  thread.revocation_on_demand:
    quote: "If the transactions of the agent contain agent identifier, a regulator could match the identifier to the corresponding agent card and ask the deployer of the agent to investigate further or shut it down."
    loc: "p.7, §3.1.2"
  thread.revocation_scope:
    quote: "Once behaviour is flagged, a deployer can intervene on the agent and potentially inform relevant authorities."
    loc: "p.7, §3.2"
  thread.revocation_latency:
    quote: "Real-time monitoring involves oversight of agent activity in real- time, with the goal of flagging and potentially filtering problematic behaviour."
    loc: "p.7, §3.2"
  thread.attribution:
    quote: "Activity logs can inform an understanding of the agent’s im- pacts as well as allow one to tie behaviour to specific user choices, facilitating post-incident attribution and forensics [119]."
    loc: "p.7, §3.3"
  thread.human_in_loop:
    quote: "A user could be given the opportunity to request human review of any action taken to impede its agent."
    loc: "p.7, §3.2"
  thread.non_determinism:
    quote: "Sub-agents could be problematic because they introduce additional points of failure; each sub-agent may itself malfunction, be vulnerable to attack, or otherwise operate in a way contrary to the user’s intentions."
    loc: "p.3, §1.1.5"
  thread.standards_referenced:
    - quote: "Some actors may need agent identifiers to fulfil their existing duties, such as e-commerce websites which must authenticate users and safeguard customer payment information [44]."
      loc: "p.5, §3.1.1"
    - quote: "Additionally, existing data protection laws, such as GDPR, impose further restrictions."
      loc: "p.8, §3.4"
  thread.names_field_as:
    quote: "Addressing the risks of AI agents requires visibility:5 information about where, why, how, and by whom AI agents are used."
    loc: "p.3, §1.2"
  thread.cites_pre_2015:
    quote: "[63] Eugene F. Fama and Michael C. Jensen. 1983. Agency Problems and Residual Claims."
    loc: "p.12, References"
  thread.key_numbers:
    quote: "The no- logging provision of Google [71] keeps logs for 72 hours."
    loc: "p.7, §3.2 footnote"

unanswered:
  - field: thread.attenuation
    why: "Sub-agent creation is discussed at length as a risk and recorded on the agent card, but whether a sub-agent receives a narrowed version of its parent's permissions, or any permissions at all, is never raised. The paper has no vocabulary for restricting what a recipient gets"
---

## Why it matters here

This is the reference paper for the identification half of the thread, and the one that most clearly states why the stopping half is hard. Two things in it should anchor a chapter.

The first is the agent card. Appendix A is a specification in all but name: the underlying system's agency and generality evaluations, previous incidents, model dependencies; the instance's goal, tools, permissions, lifetime, intended sector, the number of people it can affect, the degree of human oversight; and the actors — user, compute provider, developers of the model and of the scaffolding, tool providers, and any humans the agent has interacted with. That list is more complete than anything the credential papers propose, and it includes the two fields they consistently omit: what the agent is *for*, and how long it is supposed to exist.

The second is a single paragraph, §1.1.5, which contains the best statement of the revocation problem in the corpus and does not call it that. Stopping an agent from causing further harm might require intervening not only on the agent but on its sub-agents — and no method exists for determining when an agent has created one. Every revocation scheme in this review assumes the set of things to be revoked is known. Here is a top-venue paper saying that for agents it is not, and that nobody knows how to find out.

What the paper does not do is connect identification to authority. Permissions appear twice, in subordinate clauses, as something an identifier *might* confirm and something an agent card *could* list. The design never asks where a permission comes from or how it ends.

## What it actually does

It proposes three measures and then stress-tests them against deployment topology.

*Agent identifiers* mark whether and which agent is in an interaction, with three design axes: which outputs carry them (watermarks for media, headers for API requests, and — the paper's own suggestion — identifiers on significant outputs such as purchases made on the user's behalf or compute requests above a threshold); which actors can see them (the counterparty, the bank, the API provider, possibly other agents, since multi-agent risks need agents to recognise each other); and how specific they are, from "some agent was involved" up to a unique per-instance identifier requiring attestation-style cryptography to vouch for provenance. The agent card hangs off the identifier.

*Real-time monitoring* flags and filters behaviour as it happens and deliberately does not require logs — the analogy is a moderation filter versus a chat archive, and the motivation is business customers who buy no-logging guarantees. It can only catch what is recognisable in the moment: breaches of clear rules, usage caps, leakage, anomalies, and cross-agent patterns such as price correlation suggesting collusion. The suggested response to a flagged high-influence action is to pause it pending explicit user approval, on the model of a bank freezing a suspicious transaction.

*Activity logs* record inputs, outputs, tool calls, internal reasoning, self-critique and memory management for post-hoc forensics, with the sharp observation that logs may need to outlive the agent because impacts are delayed, and may need to be joined across agents when one is a continuation of another.

Section 4 then asks what happens when nobody runs a deployer. The answers are compute providers demanding proof of visibility measures from large deployments, and tool and service providers refusing requests from agents without identifiers from trusted deployers — explicitly a distributed enforcement mechanism, with Let's Encrypt invoked as the model for a free certifying authority. Section 3.4 and 4.3 then argue, at length and against the paper's own proposals, that all of this is a surveillance and power-concentration hazard.

## Assumptions and limits

The chokepoint assumption is the load-bearing one and the paper knows it is shaky. Visibility works because deployers see everything and because the best models are only reachable through deployers; enforcement in the decentralized case works because agents need tools and tools can demand identifiers. The paper then concedes that agents can bypass APIs by interacting with tools the way a human would, and proposes CAPTCHA-like detection and proof of human identity as the remedy. That is an arms race the paper's own risk section says agents are winning, and the admission that measures "should be robust to improvements in the capabilities of agents" is a requirement, not a design.

The three measures are presented as complementary and are partly in conflict. Real-time monitoring's selling point is that it needs no logs, which is what lets a deployer offer confidentiality. Sub-agent dynamics, delayed impacts and continuation across agent lifetimes all need logs retained well past the agent's lifetime and joined across instances. Both arguments are made well; the trade between them is never stated as a trade.

And the measures concentrate power in the actors the paper identifies as already too powerful. Deployers implement everything; compute providers, of which there are a handful, become surveillance points; tool providers become gatekeepers who can effectively exclude agents not blessed by a certified deployer. The paper argues this clearly in §4.3 and answers with voluntary standards and open-source identifier frameworks — the weakest available instruments pointed at the hardest problem, and offered as "mitigations to explore" rather than as a position.

## Objections

The authorisation gap is the one that matters for this review. A paper this thorough about identifiers, written by authors who understand certificate authorities well enough to cite Let's Encrypt as a model, contains no discussion of what happens when an identifier must stop being accepted. The CA analogy is exact and the paper takes only half of it: issuance is the easy half, and the reason CAs are hard is CRLs, OCSP, stapling, short-lived certificates and the propagation problem. Dropping that half while borrowing the architecture is the single clearest instance in this corpus of the asymmetry the review is about, and it occurs in the most carefully argued paper in the batch.

The second objection is that the paper's best insight is left as an aside. "We lack methods for determining when an agent has created a sub-agent" is not a footnote to a risk taxonomy — it is a statement that the thing to be identified cannot be enumerated, which undermines identifiers, monitoring and logs simultaneously. If you cannot tell that a sub-agent exists, you cannot require it to carry an identifier, cannot monitor it, and cannot log it. Three sentences later the paper moves on to §1.2.

Finally, there is no evaluation of any kind, which the authors state plainly, so everything here is a proposal. What I would want is narrow and tractable: take the agent-card field "the agent's permissions", instrument one scaffolding framework to populate it honestly, and measure how often the declared permissions match what the agent actually exercised. My expectation is that they diverge badly, because the permissions an agent holds are inherited from whatever credentials its environment hands it rather than declared anywhere — and if that is right, the agent card's most governance-relevant field is the one least likely to be accurate.
````
