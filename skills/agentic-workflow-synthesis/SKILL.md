---
name: agentic-workflow-synthesis
description: Turn any Process Printer process map (tasks + task descriptions +
  claims + issue log, from any source document/domain) into an agentic
  workflow spec — expanded BPMN-style nodes (deterministic/agent/agent+escalation/
  human/service/gateway), each with a full builder-ready field set. Use for
  "turn this into an agentic workflow", "build the Maestro spec", "add agent
  automation to this process", "which steps should be agents vs rules vs
  human", "convert this process map to BPMN".
---

# Agentic Workflow Synthesis

Turns a human-facing process map — from **any** document or domain, not just
insurance — into the node-level spec an implementer (e.g. a UiPath Maestro
builder, or any BPMN-style workflow engine) needs, without building the
workflow itself. This is a **downstream, optional stage**, run after a
process map is already validated (see `process-printer/SKILL.md`) — never a
replacement for it. The human map stays the artifact a BPA reviews and signs
off on; this skill consumes that map once it's approved and produces a
*different*, more detailed artifact for automation, versioned against the
process-map version it was generated from.

The method below is domain-agnostic by construction: it operates only on the
generic Process Printer artifacts (`ProcessTask`, `ProcessEdge`,
`AtomicClaim`, `Issue`) and never on the source document's subject matter.
Domain-specific examples in this file (insurance, claims) illustrate the
method — they are not part of it. When applying this skill to a new document
(HR onboarding, procurement approval, loan underwriting, whatever the source
material describes), re-derive the node list and every example from that
document's own claims; do not carry over another domain's node structure,
escalation triggers, or field values.

Full worked rationale for the method (including one concrete domain example
and the debate that produced it) lives in `docs/agentic-workflow-design.md` —
read it for the *why* behind a judgment call this skill doesn't explicitly
cover, but treat its AAMI/insurance content as *one worked instance*, not the
definition of the method.

## Non-negotiables

- **More nodes than the source map, not the same nodes relabeled.** A human
  task that bundles multiple judgment calls into one line (e.g. "check
  eligibility," "review submission," "assess risk") typically decomposes
  into a classification step, a screening/evaluation step, and one or more
  gateways once every decision boundary has to be machine-evaluable.
  Producing a 1:1 node-for-node relabeling is a sign this wasn't actually
  done.
- **Every node classified by the Q1→Q2→Q3 test, in order** (see Method
  below) — never assigned a type by guessing which "feels" more AI-native.
- **The escalation boundary is a branch inside an agent node, not a separate
  node type.** An agent step resolves the clear cases autonomously and
  routes the fuzzy ones to a human; that routing condition is itself
  deterministic (a threshold or an enumerated flag).
- **Escalation scoping rule**: mandatory human review triggers on adverse
  outcomes caused by *agent interpretation* — the agent applied judgment to
  resolve ambiguous, discretionary, or contested language in the source
  document (e.g. words like "reasonable," "material," "as soon as
  practicable"), or the source is genuinely silent on the fact pattern —
  always, regardless of confidence. It must NOT trigger on adverse outcomes
  from *pure deterministic rule evaluation* (a date outside a defined
  window, a numeric threshold not met, a required field missing).
  Conflating these floods the human queue with unambiguous cases and causes
  alert-fatigue on exactly the cases that need real judgment. Every gateway
  that routes an adverse outcome must therefore split by *cause* (agent
  judgment vs. deterministic rule), not just by outcome. What counts as
  "adverse" is domain-specific (decline, rejection, escalation-required,
  non-compliant, etc.) — the cause-based split applies regardless of what
  the adverse outcome is called in a given process.
- **Grounding is two checks, not one**: fabrication (does the cited source
  span exist verbatim in the document?) and misapplication (does that
  span's actual content support the specific conclusion the agent drew from
  it?). A node spec that only names one check is incomplete.
- **Confidence is a calibrated signal, not a vibe.** Every agent node's
  confidence threshold ships tagged as provisional (`threshold_set_id`,
  `calibration_dataset_version`, `calibration_owner`) — never a bare number
  presented as settled.
- **The issue log becomes a standing pre-check**, consulted before the
  relevant agent node runs (does this fact pattern match a known
  document-is-genuinely-silent issue? → escalate regardless of confidence),
  not something the agent has to rediscover per case.
- **Never invent a rule the source claims don't support.** Every
  deterministic rule and every "positive list of what an agent may decide
  unsupervised" traces back to real `claim_refs` from the source process
  map's own extraction — same citation discipline as the rest of this app,
  extended one layer downstream.

## Method

Apply to every task in the source process map, in this order:

1. **Q1 — Is the input→output mapping fully specifiable as rules/lookups
   today?** Yes → `deterministic` node (Business Rule/DMN). No
   interpretation required, no LLM.
2. **Q2 — Does resolving it require synthesizing unstructured evidence
   against a semi-structured standard?** Yes → candidate `agent` node
   (unbounded input space — narratives, freeform descriptions, unstructured
   submissions — not enumerable as rules).
3. **Q3 — Within that agent step, does a sub-decision depend on
   reasonable-person/case-specific judgment the source leaves open, or on
   facts not yet in evidence?** Yes → that sub-decision becomes a mandatory
   escalation branch inside the agent node (`agent+escalation`), not a
   separate node.

A single source task commonly decomposes into: 1 or more agent/rule nodes +
1 or more gateways + a human queue node its escalation branches route to
(when the process has one — see design doc for a worked example of this
shape). Insert a **QA-lane routing edge** (async, sampled, off the mainline
— see design doc §6) from every gateway branch that ends in "auto-process,"
not a synchronous review hop.

For every resulting node, author the full field set (see
`docs/agentic-workflow-design.md` §3): id, type, goal (as an output, not an
activity), trigger, inputs (exact schema + retrieval scope), outputs (exact
schema — agent nodes always include `confidence`, `citations[]`,
`rationale`), decision logic / authority boundary, grounding requirement
(fabrication + misapplication, restricted to the relevant content category),
confidence/escalation trigger, escalation target + queue + SLA, error
handling (schema-validation retry-then-escalate, never guess), audit
requirements, and downstream edges (finite, exhaustive, mutually exclusive
— never "etc."). Agent nodes additionally get: context source (named
retrieval scope, not "the whole document"), tools list with a per-tool
firing rule, escalations handle, max iterations/stop conditions, guardrails.

## Fallbacks

- **Source process map has no issue log entries yet** → still build the
  pre-check hook, just with an empty known-issues set; don't skip the
  pattern because there's nothing in it yet.
- **A task's claims don't clearly resolve Q1 vs Q2** → default to `agent`
  with a conservative (low) confidence threshold and an explicit escalation
  trigger for the ambiguous cases, rather than forcing a deterministic rule
  the source doesn't actually support. Log this as an open issue on the
  agentic-workflow artifact, same discipline as `gap-ambiguity-logging`.
- **Building this for a new document/process in any domain** (insurance,
  HR, procurement, lending, compliance, anything else) → the method is
  fully generic; only the specific node list and field values change. Run
  the Q1–Q3 test fresh against that document's own process map and its own
  claims. Do not copy another domain's node structure, node count,
  escalation triggers, or example field values onto an unrelated process —
  every node and every escalation trigger must trace to that document's own
  `claim_refs`.

## Anti-patterns

- Relabeling each existing task node "Agent: <title>" without expanding it —
  this is the single most common failure mode this skill exists to prevent.
- Putting a confidence threshold in a node spec without the calibration
  metadata fields — an uncalibrated number presented as a real threshold.
- One combined "grounding: yes" checkbox instead of separate fabrication +
  misapplication checks.
- Routing deterministic declines/rejections through the same human queue as
  agent-judgment adverse outcomes ("just to be safe") — defeats the
  automation and burns reviewer attention on cases needing no judgment.
- A synchronous QA gate on every auto-processed case — that's a second
  approval hop, not QA; QA is async, sampled, post-hoc, with a circuit
  breaker back to synchronous review on drift.
- Skipping the decide/draft split — a node that both decides an outcome and
  drafts customer-facing (or otherwise externally visible) wording should
  always be two nodes.
- Assuming a domain's terminology (e.g. "policy," "claim," "exclusion")
  carries over to a different source document — reclassify from that
  document's own claims rather than reusing prior node names or wording.

## Output

An `AgenticWorkflowVersion` (see `backend/app/models/agentic_workflow.py`):
a list of `AgenticWorkflowNode` rows (each carrying the full field set above
as `spec_json`, `node_kind`, and `source_task_title` when derived from a
specific process-map task) and `AgenticWorkflowEdge` rows (finite, named
conditions), versioned against the exact `ProcessMapVersion` it was
generated from. See `app/pipeline/agentic_workflow.py` for the validator
(structural: escalation-scoping rule enforced, edges exhaustive, every
citation resolves to a real claim in the source document's own extraction —
not a fixed domain vocabulary) and `data/aami_agentic_workflow.json` for one
worked example (an insurance PDS, transcribed from the debate-vetted design
in `docs/agentic-workflow-design.md` §5/§9) — a reference instance of the
method, not a template to copy onto a different document's process map.
