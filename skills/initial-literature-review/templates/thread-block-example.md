# Example `thread` block — an agent-identity review

*A real block from the review it was built for: who an AI agent is and how its authority is granted, scoped and withdrawn. It is here as a worked example of how specific a thread block should be, and of the counting traps that shape one. Copy the approach, not the fields. Your own block goes in your extraction files, and its controlled values go in an ```extraction-vocab block in `thread.md`.*

The matching `thread.md` vocabulary block for this example:

````markdown
```extraction-vocab
authority_mechanism: token | certificate | capability | signature | policy | attestation | legal | none
delegation_depth: none | single-hop | multi-hop | unbounded
revocation_effective: verified | contradicted | unverified | n/a
revocation_scope: agent-authority | verification-material | both | n/a
non_determinism: addressed | scoped-out | denied
```
````

**One rule this example needed.** A genuine absence is `none`: read it, the paper offers no way for authority to end. `null` means you could not establish it. Two rules pulled against each other during the first run, agents split on it, and the corpus ended up holding genuine silences under both values, so neither count was clean until a second pass normalised them. Write your own block's none/null rule down before extraction starts.

```yaml
# ── thread block: the questions THIS review is about ───────────────────
# Filled for every paper. `null` where the paper is silent -- silence here is
# the finding. A paper proposing an agent protocol that never mentions
# revocation is evidence for the central claim, and only a field that can be
# null can record that.
thread:
  identifies_what: agent        # agent | counterparty | workload | model | device | human |
    # `counterparty` = the scheme identifies who the agent DEALS WITH and gives
    # the agent no identity of its own -- it is a bearer-token holder.
    # organisation | tool-provenance | data-provenance | none | below-this-level |
    # null
    # `none` = the paper ARGUES AGAINST an identity layer. A position, and the
    #   sharpest disagreement this review can report.
    # `below-this-level` = the design simply operates lower down: permissions
    #   attach to tool names and arguments, so no principal is identified and
    #   none needs to be. Checked and absent, but NOT an argued position.
    #   Merging the two would report a stance where there is only a different
    #   level of abstraction.
  principal_relation: "Acts for a named human account holder"   # how its authority traces to a principal; null if never stated
  authority_mechanism: token    # token | certificate | capability | signature |
    # policy | attestation | legal | none | null -- `legal` for authority that
    # is normative rather than technical (actual, implied or apparent authority
    # in agency law). Coding those as `none` would count a paper entirely about
    # authority as ignoring it.
  authority_binding: "Bound to one transaction, not to the decision behind it"  # what the authority is tied to
  scoping: [operation, amount]  # audience | time | operation | amount | data |
    # task-context | provenance | none | null -- provenance means the capability
    # is scoped by where the data or request came from, a distinct axis
  attenuation: true             # can authority be narrowed when passed on? null if not discussed
  delegation_depth: multi-hop   # none | single-hop | multi-hop | unbounded | null
  revocation: status-list       # none | none-by-design | expiry | crl | ocsp |
    # status-list | accumulator | heartbeat | supersede | suspend |
    # threshold-contraction | access-time-evaluation | never-granted |
    #   terminate-holder | legal-process |
    # named-unspecified | other | null
    #   supersede = reissue supersedes the old grant (e.g. threshold membership
    #     changes and the previous share set stops working)
    #   suspend = a state transition in a governance state machine, reversible
    #   threshold-contraction = a spending or trust limit contracts automatically
    #   terminate-holder = authority ends by ending the AGENT, not its
    #     credential: an authenticated remote terminate, abort or recall. Every
    #     other value here withdraws a token and leaves the agent running. The
    #     2001 Ajanta papers have this and almost nothing modern does.
    #   legal-process = authority ends by court order, seizure in rem, or an
    #     on-chain force-close -- a remedy outside the protocol entirely.
    #   never-granted = standing authority for a class of action is refused
    #     outright -- e.g. no permanent permission for irreversible actions.
    #     Neither revocation nor scoping, and in at least one paper it is the
    #     strongest control present: the authority that was never issued does
    #     not have to be withdrawn.
    #   access-time-evaluation = the actor carries no standing grant at all;
    #     permission is re-evaluated from current state on every access, so
    #     withdrawal is a state edit rather than a message that must propagate.
    #     Structurally unlike every list- or credential-based mechanism above,
    #     and the only kind whose withdrawal is straightforward to measure.
    # none-by-design = the paper's own construction could not support revocation
    #   without weakening its security argument, and says so. A principled
    #   absence, not an oversight, and a different finding entirely.
  revocation_effective: null    # verified | contradicted | unverified | n/a | null
    # Does the paper show the withdrawal ARRIVES? A mechanism and its effect are
    # different claims, and the corpus holds papers that are `true` on the first
    # and measure failure on the second: one found 12 of 18 chatbots still
    # serving withdrawn content, another found revoked memory records returned
    # ranked above their replacements. Counting those as "revocation works"
    # would be the single worst error this review could make.
    #   verified     = measured, and it took effect
    #   contradicted = measured, and it did not
    #   unverified   = a mechanism is proposed and never tested  <- the common case
    #   n/a          = no mechanism to test
  revocation_on_demand: false   # true | false | null -- CAN A PARTY SAY STOP?
    # true  = some party can actively withdraw authority already granted
    # false = authority only LAPSES, on a timer or at the end of a session
    # The single most important field in this block. A 2-minute TTL is a damage
    # window, not a withdrawal: nobody can stop an agent holding a token that is
    # still valid. Counting expiry as revocation overstates what the field has
    # solved, which is the exact error this review exists to avoid making.
  revocation_scope: agent-authority   # agent-authority | verification-material |
    # both | n/a | null -- WHOSE authority ends. Use n/a when `revocation` is
    # `none` or `none-by-design`: there is no mechanism, so it has no scope and
    # no latency. Writing null there puts "no mechanism exists" in the same
    # bucket as "the PDF was unreadable".
  revocation_latency: "15 minutes, stated"   # verbatim figure | unstated | n/a | null
    # unstated = a mechanism exists and the paper gives no number. Distinct from
    # null, which means no mechanism, or that you could not read far enough.
    # Nearly every paper with revocation lands on `unstated`, and that IS the
    # finding: the field proposes withdrawal without ever saying how fast.
  attribution: "Signed receipts let a verifier say which agent acted"  # can you tell afterwards who did what? null if not
  human_in_loop: false          # approve | stop | both | none | advertised-absent |
    # varies | null -- `advertised-absent` is for a design that SELLS the
    # human's absence: "no manual intervention", "user unreachability" listed
    # among the advantages. Not the same as never raising the question, and the
    # absence is exactly what makes stopping impossible.
    # approve = a human signs off BEFORE the action
    # stop    = a human can halt an action already running
    # These are different powers and only the second is revocation applied to
    # people. `varies` fired on 7 of 11 papers in one batch and stopped
    # discriminating, which is what exposed the distinction.
    # varies = the paper deliberately defines both modes (human-present and
    # human-absent) as design options. Recording that as null pollutes the
    # silence count with papers that thought about it hardest.
  non_determinism: null         # addressed | scoped-out | denied | null
    # addressed = the paper treats the agent as capable of acting outside its
    #   mandate (prompt injection, goal drift, being argued into it)
    # scoped-out = the paper names the problem precisely and declares it out of
    #   scope or future work. It saw the gap and chose not to fill it, which is
    #   a different finding from never having seen it.
    # denied    = the paper explicitly asserts this cannot happen, e.g. that
    #   behaviour is fully determined by credential scope. STRONGER evidence
    #   for the review's claim than silence, and must not be filed as silence.
    # null      = the paper does not raise it at all
  standards_referenced: [oauth2, spiffe]   # OPEN list -- the named ones below are
    # common here, but write whatever the paper cites: ap2, a2a, mcp, x402, spiffe,
    # oauth2, oidc, did, vc, wimse, erc8004, eidas, ai-act, spki, gdpr, nis2,
    # iso42001, nist-ai-rmf, owasp-agentic, rfc9421, ct, scim, ngac, pci-dss...
    # A closed list made standards-aware papers look standards-unaware.
  names_field_as: "agentic identity"       # the paper's own term for the area
  cites_pre_2015: false         # does its bibliography reach back before 2015?
  key_numbers: "4.2 ms verification, 12 kB token"   # any measured result worth quoting, else null
  takeaway: "Signs the transaction but not the intent behind it, so a substituted decision still verifies."
```

---

## Why these fields

**The `thread` block is what makes a second pass unnecessary.** Every field in
it is a question the synthesis will ask, so asking them once, while the PDF is
open, is the whole saving. Three of them carry most of the weight:

**`named-unspecified` exists because of a counting trap.** Six papers in one
batch named revocation only as a state variable, an admissibility condition or
an asserted property, with no mechanism and no propagation story. Recorded as
`other`, those are indistinguishable from a real CRL or status list, and a
synthesis counting non-null `revocation` as "addresses how authority ends"
would overstate mechanism adoption substantially. `revocation_scope` exists for
the same reason: one paper had a full revocation section for *service signing
keys* and nothing for the agent's authority.

**`revocation_on_demand` is the field to look at first.** An extraction agent
found papers recording `expiry` where no withdrawal exists at all -- a short TTL
bounds the damage but gives nobody a way to say stop. If the synthesis counts
those as revocation it will report that the field has solved something it has
not, and the whole asymmetry claim collapses under the first reviewer who reads
one of the papers. Expect most of this corpus to be `false`.

- `revocation` and `revocation_latency` — the review's central asymmetry is that
  the field is far more interested in granting authority than in ending it. That
  claim is only as good as the count of papers that genuinely say nothing, which
  is why `null` must mean *silent* and never *unread*.
**`denied` is worth more than `null`.** One paper asserts that an agent's
behaviour is entirely determined by its credential scope and that there is "no
behavioural backstop". That is not silence -- it is a claim the review can
contest, and filing it as silence throws away the strongest kind of evidence
available: an author stating the assumption out loud.

- `non_determinism` — the one thing that separates this problem from its
  pre-LLM ancestor. Deterministic code cannot be talked into exceeding its
  mandate; an LLM agent can. A paper silent here has inherited the old model.
- `cites_pre_2015` — measured per paper rather than inferred from a citation
  API, which held reference lists for only a quarter of the corpus.
