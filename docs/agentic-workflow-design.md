# From process map to agentic workflow

This document explains how to turn a Process Printer output — a human-facing
process map plus its task descriptions, claims, and issue log, from **any**
source document or domain — into an **agentic workflow**: a BPMN-style
process with autonomous agent steps, deterministic rule steps, and explicit
human escalation gateways, structured so it can be built directly on UiPath
Maestro (or any comparable BPMN-style workflow engine). It is a design
document, not an implementation — the output is the set of node specs a
builder needs, not working code.

**§1–§8 and §11 are the generic method** — they operate only on the generic
Process Printer artifacts (a process map's tasks/edges, its cited claims,
its issue log) and apply to a process map generated from any document:
insurance, HR, procurement, lending, compliance, or anything else. **§9 is a
single worked example** — the AAMI Comprehensive Car Insurance
claims-coverage map already produced by this app
(`backend/data/aami_process_map.json` — 11 tasks, e.g. "Capture claim
description" → "Confirm policy and incident validity" → "Check general
exclusions" → "Classify which cover applies" → … → decision outcome, each
with cited claims and issue-log entries for unresolved gaps/ambiguities).
It exists so the method stays checkable against a concrete instance rather
than staying abstract — but it is **one instance of the method, not the
method itself**. Applying this to a different document means re-running
§2–§3 against that document's own process map and its own claims, not
adapting AAMI's node list, node count, or field values.

This design was produced by putting the question to two independent models
(Claude and GPT) and running a structured debate between them before
converging — see the chain of reasoning summarized in "Why this design"
below if you want the disagreements that got resolved, not just the answer.

---

## 1. Why a human process map can't just have "AI added to it"

A human process map is written for a reader who can hold ambiguity in their
head and keep going — a handler reads "check the general exclusions" (or,
in another domain, "check the applicant meets eligibility criteria," "review
the submission for completeness") and applies judgment. A BPMN-style
executable workflow can't do that: every gateway needs a machine-evaluable
condition, and every agent step needs a bounded output contract. "Use
judgment" has to become "operate within these limits, and here is exactly
what triggers escalation."

The practical consequence: **the agentic workflow will have more nodes than
the human map, not the same nodes relabeled.** A single human task that
bundles multiple judgment calls into one line typically decomposes into a
classification step, a screening/evaluation step, and one or more escalation
gateways once you make every decision boundary explicit.

---

## 2. Classifying each node: agent, deterministic, or human

Apply this test to every task in the source process map, in order:

**Q1 — Is the input-to-output mapping fully specifiable as rules/lookups
today?**
If yes → **deterministic task** (rule engine / DMN / script, no LLM). E.g.
"check a date falls within a defined period," "look up a coverage/approval
limit," "check a required waiting period has elapsed," "confirm a required
field is present." If a lookup or a boolean/enum rule answers it and the
source clause resolves to that rule with no interpretation required, don't
put an agent here — it's slower, costs money, and adds a hallucination
surface for zero benefit.

**Q2 — If not, does resolving it require synthesizing unstructured evidence
against a semi-structured standard?**
If yes → **candidate agent step**. E.g. "classify which category/type
applies" (freeform narrative or submission → one of N defined categories,
using the source document's own definitions), "screen for
exclusions/disqualifiers" (narrative → applicable clauses, some with fuzzy
tests like "material" or "reasonable"), "draft a recommendation" (structured
facts → recommended outcome + rationale). These need an LLM because the
input space (freeform narratives, submissions, descriptions) is unbounded
and not enumerable as rules.

**Q3 — Within an agent step, does the specific sub-decision depend on
criteria the source document itself leaves to reasonable-person /
case-specific judgment (words like "reasonable," "material," "as soon as
practicable"), or on facts not yet in evidence?**
If yes → **mandatory human escalation for that sub-decision.**

The key structural point from Q3: **the escalation boundary is usually a
branch inside an agent node, not a separate node type.** A screening/
classification step isn't "agent OR human" — it's "the agent resolves the
clear cases autonomously and routes the fuzzy ones to a human," where the
routing condition itself is deterministic (a confidence threshold, or a flag
against an enumerated list of known-undecidable-by-document criteria).

**A related distinction that matters in practice:** separate "the agent is
uncertain" from "the document is genuinely silent." These need different
remediation. Low-confidence-but-the-document-has-an-answer is a
prompting/retrieval problem to fix in the agent. Document-genuinely-silent is
a *permanent* human-in-the-loop point regardless of how good the model gets —
this is exactly Process Printer's existing **issue log** concept, and it
should become a deterministic pre-check consulted *before* the relevant
agent runs ("does this fact pattern match a known issue-log entry? →
escalate regardless of agent confidence"), not something discovered after
the fact.

This gives three node types, with the third applied as a modifier on the
second rather than a fully separate category:

| Type | What it does | Where it comes from in the map |
|---|---|---|
| Deterministic task | Rule/lookup/script, zero LLM | Any claim that resolves to a boolean/enum with no interpretation |
| Autonomous agent task | LLM makes the call, fully within authority, output consumed downstream | Claims requiring synthesis over an unbounded input space |
| Agent task + escalation gate | Same as above, but a defined branch always routes to a human | Any sub-decision the source leaves discretionary, contradictory, or based on missing facts |

**Escalation scoping rule (the one point worth stating explicitly because
it's easy to get wrong):** mandatory human review should trigger on adverse
outcomes that flow from **agent interpretation** (a disqualifying clause
judged applicable, category ambiguity, discretionary language) — always,
regardless of confidence. It should **not** trigger on adverse outcomes from
**pure deterministic rule evaluation** (a date outside a defined window, a
threshold not met, a required field missing). Routing every deterministic
adverse outcome through a human queue defeats the purpose of automating the
unambiguous majority of cases, and causes reviewer alert-fatigue on exactly
the cases that need no judgment — which erodes attention for the cases that
do. Deterministic adverse outcomes should auto-process and fall into the
sampled QA loop instead (see §6). What counts as "adverse" (decline,
rejection, non-approval, non-compliant finding) is domain-specific; the
cause-based split applies regardless of what the source document calls it.

---

## 3. What a task description needs to contain

Every node needs a description detailed enough that a builder implementing
it doesn't have to come back and ask what "reasonable" means or what happens
if the model says something ungrounded. Use this field set for every node:

| Field | Purpose |
|---|---|
| **ID / name** | Stable identifier used in edges and logs |
| **Type** | Business Rule task (DMN) \| Autonomous agent (service task) \| Agent + escalation gate \| Human/User task \| Gateway |
| **Goal** | One sentence, stated as an *output* ("produce a classification with confidence and citations"), not an activity |
| **Trigger / entry condition** | The upstream event/edge that starts this node |
| **Inputs** | Exact schema: case fields, documents, prior node outputs. State whether the agent sees the full source or a retrieved subset (this determines the RAG design) |
| **Outputs** | Exact typed schema. For agent steps, every mandatory field including `confidence`, `citations[]`, `rationale` |
| **Decision logic / authority boundary** | For deterministic tasks: the actual rule. For agent tasks: a *positive list* of what it may decide unsupervised, not "use judgment" |
| **Grounding / citation requirement** | Two separate checks, not one (see §7) |
| **Confidence / escalation trigger** | The actual machine-checkable condition — self-reported confidence below threshold, a deterministic red-flag match, or absence of a required citation — stated as a number, flagged as provisional pending calibration (see §8) |
| **Escalation target** | Which queue, what the human sees, what actions they can take, what happens to the audit trail on each action |
| **Error handling / retries** | What happens on tool failure, timeout, or malformed output — schema-validation failure retries with a correction prompt N times, then escalates; never guesses |
| **SLA / timeout** | Especially for human queue items — reminder / escalation-of-escalation behaviour |
| **Audit / logging requirements** | Full input/output, model + prompt version, citation-verification result, human decision if any — not optional in a regulated or auditable domain |
| **Downstream edges** | Named conditions on outgoing edges, drawn from a finite enumerated set — BPMN gateways must be exhaustive and mutually exclusive, never "etc." |

For agent nodes specifically, add the fields that map directly onto Maestro's
Agent node handles (or the equivalent construct in another BPMN-style
engine):

- **Context source** — the exact retrieval scope (a named set of source-
  document sections, not "the whole document")
- **Tools list**, each with an explicit rule for *when* it may be called
- **Escalations handle** — the specific resource/queue it routes to and the
  condition that fires it
- **Max iterations / stop conditions**
- **Guardrails**
- **Branching condition on the agent's output**, used by the downstream
  gateway

---

## 4. Mapping onto UiPath Maestro constructs

This section documents *a* target platform's vocabulary, not a requirement —
substitute the equivalent constructs if targeting a different BPMN-style
engine. When targeting Maestro, its own vocabulary should be used directly
in the specs, not translated later by the builder:

- **Maestro Case** — the right outer shell for the *whole case instance*
  (a claim, an application, a request — whatever the process's real-world
  unit of work is), when that unit can reopen, need extra information,
  generate follow-ups, or run over days or weeks. This is a poor fit for a
  single linear BPMN process.
- **BPMN subprocess** — the right shape for a bounded, standardizable
  decision core within that case (e.g. a coverage/eligibility/approval
  determination), even when the surrounding case lifecycle is not fully
  linear.
- **Business Rule task** — runs DMN-style rules for every deterministic
  gate.
- **Agent (service task)** — invokes an autonomous agent with Context,
  Tools, and Escalations handles.
- **User / Human task** — the Action Center human-in-the-loop path for
  mandatory escalations.
- **Process App** — the operational triage dashboard / queue UI a reviewer
  actually works from (distinct from a single Action Center task).

Recommended hybrid, where the process has a multi-step case lifecycle: a
**Maestro Case wraps the case lifecycle; a BPMN subprocess handles the
decision-making core inside it.** For a process without a meaningful case
lifecycle (e.g. a single bounded approval flow), the BPMN subprocess alone
may be sufficient — decide this per process, not by default.

See §9 for a fully worked example of this shape applied to one real process.

---

## 5. Worked example, in outline: see §9

*(Section renumbered — the worked AAMI diagram and task descriptions now
live together in §9, so the general method in §1–§8 reads independently of
any one domain. If you're looking for a concrete instance of "what does this
actually look like," skip ahead to §9.)*

---

## 6. The QA lane: async, not a mainline gate

Governance requires evidence that the population of auto-processed decisions
(both auto-approved and auto-declined) is periodically checked — not just
the cases that triggered escalation. But this must **not** sit synchronously
in the mainline flow for every case:

- A mandatory QA gate on every auto-processed case isn't QA, it's a second
  approval hop wearing a QA costume — it kills the throughput benefit of
  autonomy and quietly shifts real decision authority onto whoever staffs
  that queue, undermining the "autonomous decision" claim it's meant to
  support.
- Run it instead as a **separate, asynchronous, post-hoc, stratified-sampled
  lane** — by risk tier, severity, model/prompt-version drift, or random
  percentage — reviewing already-closed cases, out of the customer-facing
  critical path.
- The lane needs a **circuit breaker**, not just a dashboard: a defined
  trigger (e.g. sampled error rate on a given node exceeds X% in a rolling
  window) that automatically forces that node back into synchronous human
  review until recalibrated. A sampled audit that only produces a monthly
  report is how threshold drift goes unnoticed for a quarter.

---

## 7. Grounding: two checks, not one

Every agent output must cite the exact source clauses/spans it relied on —
but "grounding requirement" as a single spec field predictably gets built as
the cheap half only. Require both, explicitly:

- **Fabrication check** — does the cited clause ID / quote actually exist,
  verbatim, in the retrieved source? Mechanical string-match, catches
  invented citations.
- **Misapplication check** — does the cited clause's actual content support
  the *specific claim* the agent made with it? A real, correctly quoted
  clause can still be stretched to support a conclusion it doesn't actually
  substantiate — this is the subtler failure and the one most likely to
  cause a wrong decision if it isn't checked separately. This needs either a
  second verification pass or a schema-level restriction on which content
  categories may be cited for which output field (e.g. a category
  classification may only cite category-definition clauses; a disqualifier
  screen may only cite disqualifier clauses).

## 8. Confidence is a calibrated signal, not a vibe

An LLM's self-reported confidence is not a calibrated probability. Treat it
as an operational signal that requires ongoing empirical work, and make that
explicit in every agent node's spec:

- `confidence_score` — the raw self-reported value
- `confidence_method` — how it was produced
- `threshold_set_id` — which threshold configuration is in force
- `calibration_dataset_version` — the labeled claim set it was tuned against
- `revalidation_trigger` — thresholds must be re-validated whenever the
  model, prompt, retrieval setup, or clause/content taxonomy changes
- `calibration_owner` — a named accountable owner, not an implicit default

An uncalibrated 0.9 is not meaningfully safer than an uncalibrated 0.7.
Confidence is not the same thing as decision authority.

---

## 9. Worked example: AAMI Comprehensive Car Insurance

Everything in this section is a **single concrete instance** of §1–§8's
method, applied to the AAMI claims-coverage process map. It illustrates the
method; it is not part of it. Applying this design to a different document
means re-deriving this section's diagram and task descriptions from that
document's own process map and claims — not reusing AAMI's node names, node
count, escalation triggers, or field values.

### 9.1 The redesigned AAMI claims-coverage workflow

```
Maestro Case: Claim lifecycle
└── BPMN subprocess: Coverage determination
      │
      ▼
   [Service] Ingest FNOL / documents / photos
      │
      ▼
   [Service] Extract & normalize facts into a claim packet
      │
      ▼
   [Business Rule / DMN]  BR-01: Policy & incident eligibility gate
      │
      ▼
   [Gateway] Missing or contradictory mandatory fact?
      ├── yes ─▶ [Human] Data Correction queue / info-request loop
      └── no  ─▶ continue
      │
      ▼
   [Agent] AG-02A: Classify applicable cover
      │
      ▼
   [Agent] AG-02B: Screen exclusions & exceptions
             (scoped to AG-02A's output; shares its evidence bundle;
              receives both candidates if AG-02A's classification was
              ambiguous, so the exclusion check isn't blind to the
              cover-classification uncertainty)
      │
      ▼
   [Gateway] Outcome, scoped explicitly by CAUSE of adversity:
      ├── deterministic decline (lapsed / outside period / unpaid premium)
      │     ─▶ auto-process ─▶ async sampled QA lane
      ├── agent-judgment adverse (exclusion applied, discretionary clause,
      │   unresolved cover ambiguity, above delegated authority)
      │     ─▶ [Human] Action Center review
      └── not excluded ─▶ continue
      │
      ▼
   [Business Rule / DMN] Sub-limits, excess, waiting-period check
      │
      ▼
   [Agent] AG-03: Draft settlement recommendation (decide)
      │
      ▼
   [Agent] Draft customer-facing explanation (draft — separate node from
             AG-03; a step that both decides and produces customer-facing
             wording should always be split into "decide" and "draft")
      │
      ▼
   [Gateway] Same cause-scoped test as above applied to the settlement outcome
      ├── agent-judgment adverse / over-authority ─▶ [Human] Action Center
      └── clean ─▶ auto-process ─▶ async sampled QA lane
      │
      ▼
   [Service] Generate outcome letter & write back to claims system ─▶ close
```

Two additions here that are **not** in the original human-facing process map
and are worth calling out as deliberate, not accidental (and generalize to
any domain, not just this example):

- **The async sampled QA lane** (§6) — a governance control an audit or
  regulator conversation will expect, that has no equivalent in a
  human-followed map because a human map has no "population of automated
  decisions" to sample from.
- **The issue log becomes a standing deterministic check** run before the
  relevant agent node, rather than something the agent has to rediscover per
  case.

### 9.2 Worked example task descriptions

**BR-01 — Policy & incident eligibility gate**
- **Type:** Business Rule task (DMN)
- **Goal:** Decide whether the claim is eligible to proceed to coverage
  analysis.
- **Inputs:** policy version ID, effective dates, incident date, territory,
  insured item, endorsement set, mandatory-fact-presence flags.
- **Outputs:** `gate_result` (`pass` \| `fail` \| `needs_human`),
  `reason_codes[]`, `missing_facts[]`, `citation_refs[]`.
- **Decision logic / authority boundary:** hard rules only, no inference. If
  the incident date falls outside the policy period → `fail`. If required
  fields are absent or source documents conflict → `needs_human`. No
  discretion beyond the coded rule table.
- **Escalation trigger:** conflicting dates, conflicting source documents,
  unresolved endorsement precedence, missing mandatory data.
- **Grounding:** every rule outcome maps to a clause/page reference from the
  pinned policy version in force for this claim.

**AG-02A — Classify applicable cover**
- **Type:** Autonomous agent (service task) + escalation gate
- **Goal:** Given the structured claim and incident narrative, determine
  which policy cover(s) apply, or that none apply.
- **Inputs:** `claim.incident_narrative`, `claim.structured_fields`,
  retrieved PDS sections defining each cover type (Context: named
  cover-definition sections only, not the full PDS), the policyholder's
  schedule (which covers they hold).
- **Outputs:**
  ```json
  {
    "candidate_covers": [
      {"cover_type": "string", "confidence": 0.0,
       "citations": [{"clause_id": "string", "quote": "string", "page": 0}]}
    ],
    "primary_recommendation": "string|null",
    "multi_cover_conflict": false,
    "no_cover_identified": false,
    "rationale": "string"
  }
  ```
- **Decision logic / authority boundary:** may finalize
  `primary_recommendation` autonomously only when exactly one cover has high
  confidence and no competing candidate is close. May not invent a cover not
  present in the policy schedule.
- **Escalation trigger:** confidence below threshold; top two candidates
  within a defined margin of each other; a candidate's applicability depends
  on discretionary wording; a required fact is missing.
- **Grounding:** fabrication + misapplication checks, restricted to
  cover-definition clauses only.
- **Route:** confident, unambiguous → AG-02B. Otherwise → Human: Cover
  Classification Review queue (Action Center).

**AG-02B — Screen exclusions & exceptions**
- **Type:** Autonomous agent (service task) + escalation gate
- **Goal:** Determine whether any exclusion or carve-out defeats the
  cover(s) AG-02A identified.
- **Inputs:** AG-02A's candidate cover(s) (both, if AG-02A flagged ambiguity),
  retrieved exclusion/exception clauses relevant to those covers, the
  normalized claim packet.
- **Outputs:** `exclusion_status`, `exclusion_hits[]`, `exception_flags[]`,
  `confidence`, `rationale`, `citation_refs[]`.
- **Decision logic / authority boundary:** evaluates only exclusions
  relevant to the already-classified cover(s). May identify a probable
  exclusion; may not issue a final adverse decision alone.
- **Escalation trigger:** discretionary wording ("reasonable," "as soon as
  reasonably possible"); contradictory evidence; exclusion outcome differs
  materially across ambiguous cover candidates passed in from AG-02A;
  missing material fact; low confidence.
- **Grounding:** fabrication + misapplication checks, restricted to
  exclusion/exception clauses only — this separation prevents the agent
  justifying an exclusion using cover-definition language or vice versa.
- **Route:** clean, high confidence → continue to sub-limits check.
  Otherwise → Human: Exclusion Judgment queue.

**AG-03 — Draft settlement recommendation**
- **Type:** Autonomous agent (service task), decide/draft split from the
  customer-facing explanation node
- **Goal:** Produce a recommended settlement outcome, amount band, and
  rationale.
- **Inputs:** cover classification, exclusion analysis, policy limits,
  valuation inputs, any human clarifications recorded upstream.
- **Outputs:** `recommended_outcome`, `payment_band`, `open_questions[]`,
  `confidence`, `citation_refs[]`.
- **Decision logic / authority boundary:** may draft a recommendation within
  delegated $/risk-tier authority. May not issue a final adverse or
  above-authority decision without human sign-off.
- **Escalation trigger:** outcome is adverse or partial-adverse **because of
  agent judgment** (not a prior deterministic decline — see §2's scoping
  rule); above delegated authority; low confidence; unresolved factual
  conflict; any clause using discretionary language ("may," "at its
  discretion").
- **Grounding:** fabrication + misapplication checks on every coverage and
  payment-rationale statement.
- **Route:** within authority and clean → auto-process, into the async
  sampled QA lane. Otherwise → Human: Settlement Approval queue.

**HITL-03 — Human ambiguity / adverse-judgment review**
- **Type:** User / Human task (Action Center), surfaced via a Process App
  queue
- **Goal:** Resolve genuine ambiguity, contradiction, or discretion the
  source document leaves open, or approve/override an agent-judgment
  adverse outcome.
- **Inputs:** claim packet, all prior agent outputs with their citations,
  the relevant issue-log entry if one exists, highlighted contradictions.
- **Outputs:** `human_decision` (approve \| override \| request-more-info \|
  escalate-to-specialist), `override_notes`, `additional_facts_requested[]`,
  `final_authority_reason`.
- **Decision logic:** reviewer selects from the enumerated outcome set only.
- **Escalation trigger (into this node):** any agent-derived adverse or
  above-authority outcome (§2's scoping rule) — never a pure deterministic
  decline.
- **Grounding:** reviewer must confirm or select the controlling citation(s)
  before completion — the decision trail stays as auditable as the agent's.

### 9.3 Pitfalls this example surfaced (some generalize, some are insurance-specific)

- **Version drift** *(generalizes)* — pin the exact document/policy version
  and any amendment/endorsement set used for the decision on every case
  record. A source document changes over time; a decision must always be
  traceable to the version in force when the case arose.
- **Clause precedence** *(generalizes)* — multiple source documents (a
  schedule, an endorsement, the base document) can conflict. Encode an
  explicit precedence order rather than leaving an agent to infer which
  document wins. In insurance this is schedule > endorsement > PDS, or
  whatever the actual legal hierarchy is; other domains have their own
  precedence rules (e.g. a signed contract amendment overriding a standard
  policy template).
- **Fabrication vs. misapplication** *(generalizes)* — treat as two separate,
  both-mandatory checks (§7), not one "grounding" checkbox.
- **Confidence ≠ authority** *(generalizes)* — calibrate empirically,
  re-validate on every model/prompt/retrieval change, and never let a high
  self-reported confidence substitute for the escalation rule (§8).
- **Deterministic vs. agent-judgment adverse outcomes** *(generalizes)* —
  keep these structurally separate in the escalation gateway (§2).
  Conflating them either floods a human queue with unambiguous cases (alert
  fatigue, no throughput gain) or, in the other direction, lets agent
  judgment calls slip through unreviewed.
- **Sampling without a circuit breaker** *(generalizes)* — an async QA lane
  that only produces a periodic report is how threshold drift goes
  unnoticed; it needs an automatic trigger back to synchronous review (§6).
- **Escalation-queue ownership and SLA** *(generalizes)* — split queues by
  cause (data-quality issue vs. genuine judgment call) with distinct SLAs,
  so a backlog metric stays meaningful rather than mixing two very different
  kinds of delay.
- **Regulatory audit expectations** *(insurance-specific, as an example)* —
  claims decisioning in particular typically has an external
  regulator/ombudsman audience for the audit trail; other domains will have
  their own equivalent (e.g. compliance/legal review for HR or procurement
  decisions) — confirm what the actual applicable audit requirement is for
  the domain at hand rather than assuming insurance's shape.

---

## 10. (reserved)

*(Left as a placeholder — the insurance-specific pitfalls previously
numbered here now live in §9.3, alongside the worked example they were
originally derived from, so this document's numbered sections read as
generic method (§1–§8, §11) plus one clearly-scoped worked instance (§9).)*

---

## 11. From this document to a build

The path from here to an actual implementation, for any source document:

1. Walk the source process map (produced by Process Printer, per
   `skills/process-printer/SKILL.md`) node by node through the Q1–Q3 test in
   §2, producing the expanded node list (more nodes than the human-facing
   map).
2. For every node, write the full field set from §3 (and the agent-specific
   additions) as its own task description — this is what
   `skills/agentic-workflow-synthesis/SKILL.md` produces, one node per
   underlying source task, each still traceable back to its underlying
   `claim_refs`.
3. If targeting UiPath Maestro specifically, confirm the exact current
   names/behaviour of its Autonomous Agent handles, Business Rule task, User
   Task, Process App, and Maestro Case constructs against the UiPath
   documentation for the product version being deployed — terminology
   evolves, and this document's Maestro references (§4) should be treated as
   directionally correct, not a substitute for checking the live docs at
   build time. If targeting a different engine, map §3's field set onto that
   engine's own constructs instead.
4. Build and calibrate the confidence thresholds against a labeled set of
   real historical cases for that specific process before enabling any
   auto-process path — every threshold value shown in §9.2 is illustrative
   of the AAMI instance, not a delivered value for a different process.
5. Stand up the async QA lane and its circuit breaker *before* enabling
   auto-processing, not after — the governance control has to exist before
   the volume it's meant to catch problems in does.

This document does not build the workflow. It is the spec a builder
implements against — see §9 for what a fully worked instance of that spec
looks like for one real document, and re-derive an equivalent §9 for any
other document using §1–§8's method.

---

## Why this design (debate summary)

This design was produced by dispatching the open questions to two
independent models (Claude and GPT) and running them through a structured
debate before converging. The main disagreements that got resolved along the
way, for anyone wanting the reasoning rather than just the conclusion:

- **Whether the escalation boundary is its own node type or a branch inside
  an agent node** — converged on "a branch inside an agent node" (§2):
  treating it as a separate node type undercounts how tightly coupled the
  autonomous and escalation paths are — they share the same evidence, the
  same context, and often the same underlying LLM call.
- **Whether QA review should be synchronous or asynchronous** — converged on
  asynchronous, sampled, with a circuit breaker (§6): a synchronous QA gate
  on every auto-processed case defeats the point of automating anything.
- **Whether "grounding" is one check or two** — converged on two, mandatory
  and separate (§7): fabrication-only checking misses the more dangerous
  failure mode (a real citation stretched to support an unsupported
  conclusion).
- **Whether confidence thresholds should ship as fixed numbers or as
  provisional, calibration-tracked values** — converged on provisional,
  explicitly tagged as uncalibrated until validated against a labeled
  dataset (§8) — a bare number invites treating an arbitrary starting guess
  as a validated safety threshold.
