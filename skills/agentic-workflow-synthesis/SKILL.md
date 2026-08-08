---
name: agentic-workflow-synthesis
description: Turn a Process Printer process map (tasks + task descriptions +
  claims + issue log) into an agentic workflow spec — expanded BPMN-style
  nodes (deterministic/agent/agent+escalation/human/service/gateway), each
  with a full builder-ready field set. Use for "turn this into an agentic
  workflow", "build the Maestro spec", "add agent automation to this
  process", "which steps should be agents vs rules vs human".
---

# Agentic Workflow Synthesis

Turns a human-facing process map into the node-level spec an implementer
(e.g. a UiPath Maestro builder) needs — without building the workflow itself.
This is a **downstream, optional stage**, run after a process map is already
validated (see `process-printer/SKILL.md`) — never a replacement for it. The
human map stays the artifact a BPA reviews and signs off on; this skill
consumes that map once it's approved and produces a *different*, more
detailed artifact for automation, versioned against the process-map version
it was generated from.

Full design rationale and worked example: `docs/agentic-workflow-design.md`
(produced via a Claude/GPT debate — read it for the *why*, not just the
*what*, before making judgment calls this skill doesn't cover).

## Non-negotiables

- **More nodes than the source map, not the same nodes relabeled.** A human
  task like "check general exclusions" typically decomposes into a
  classification step, a screening step, and one or more gateways once every
  decision boundary has to be machine-evaluable. Producing a 1:1
  node-for-node relabeling is a sign this wasn't actually done.
- **Every node classified by the Q1→Q2→Q3 test, in order** (see Method
  below) — never assigned a type by guessing which "feels" more AI-native.
- **The escalation boundary is a branch inside an agent node, not a separate
  node type.** An agent step resolves the clear cases autonomously and
  routes the fuzzy ones to a human; that routing condition is itself
  deterministic (a threshold or an enumerated flag).
- **Escalation scoping rule**: mandatory human review triggers on adverse
  outcomes caused by *agent interpretation* (exclusion judged applicable,
  discretionary language, unresolved ambiguity) — always, regardless of
  confidence. It must NOT trigger on adverse outcomes from *pure
  deterministic rule evaluation* (lapsed policy, outside period, unpaid
  premium). Conflating these floods the human queue with unambiguous cases
  and causes alert-fatigue on exactly the cases that need real judgment.
  Every gateway that routes "adverse outcome" must therefore split by
  *cause*, not just by outcome.
- **Grounding is two checks, not one**: fabrication (does the cited clause
  exist verbatim in the source?) and misapplication (does the clause's
  actual content support the specific claim made with it?). A node spec
  that only names one check is incomplete.
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
  unsupervised" traces back to real `claim_refs` — same citation discipline
  as the rest of this app, extended one layer downstream.

## Method

Apply to every task in the source process map, in this order:

1. **Q1 — Is the input→output mapping fully specifiable as rules/lookups
   today?** Yes → `deterministic` node (Business Rule/DMN). No interpretation
   required, no LLM.
2. **Q2 — Does resolving it require synthesizing unstructured evidence
   against a semi-structured standard?** Yes → candidate `agent` node
   (unbounded input space — narratives, freeform descriptions — not
   enumerable as rules).
3. **Q3 — Within that agent step, does a sub-decision depend on
   reasonable-person/case-specific judgment the source leaves open, or on
   facts not yet in evidence?** Yes → that sub-decision becomes a mandatory
   escalation branch inside the agent node (`agent+escalation`), not a
   separate node.

A single source task commonly decomposes into: 1 or more agent/rule nodes +
1 or more gateways + (where the design doc's worked example applies) a
human queue node its escalation branches route to. Insert a **QA-lane
routing edge** (async, sampled, off the mainline — see design doc §6) from
every gateway branch that ends in "auto-process," not a synchronous review
hop.

For every resulting node, author the full field set (see
`docs/agentic-workflow-design.md` §3): id, type, goal (as an output, not an
activity), trigger, inputs (exact schema + retrieval scope), outputs (exact
schema — agent nodes always include `confidence`, `citations[]`,
`rationale`), decision logic / authority boundary, grounding requirement
(fabrication + misapplication, restricted to the relevant clause category),
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
- **Building this for a brand-new document/process** (not AAMI) → the
  method is generic; only the specific node list and field values change.
  Re-run the Q1–Q3 test against that document's own process map — do not
  copy AAMI's node structure onto an unrelated process.

## Anti-patterns

- Relabeling each existing task node "Agent: <title>" without expanding it —
  this is the single most common failure mode this skill exists to prevent.
- Putting a confidence threshold in a node spec without the calibration
  metadata fields — an uncalibrated number presented as a real threshold.
- One combined "grounding: yes" checkbox instead of separate fabrication +
  misapplication checks.
- Routing deterministic declines through the same human queue as
  agent-judgment adverse outcomes ("just to be safe") — defeats the
  automation and burns reviewer attention on cases needing no judgment.
- A synchronous QA gate on every auto-processed case — that's a second
  approval hop, not QA; QA is async, sampled, post-hoc, with a circuit
  breaker back to synchronous review on drift.
- Skipping the decide/draft split — a node that both decides an outcome and
  drafts customer-facing wording should always be two nodes.

## Output

An `AgenticWorkflowVersion` (see `backend/app/models/agentic_workflow.py`):
a list of `AgenticWorkflowNode` rows (each carrying the full field set above
as `spec_json`, `node_kind`, and `source_task_title` when derived from a
specific process-map task) and `AgenticWorkflowEdge` rows (finite, named
conditions), versioned against the exact `ProcessMapVersion` it was
generated from. See `app/pipeline/agentic_workflow.py` for the validator
(structural: escalation-scoping rule enforced, edges exhaustive, every
citation resolves to a real claim) and `data/aami_agentic_workflow.json` for
the worked AAMI example (transcribed from the debate-vetted design in
`docs/agentic-workflow-design.md` §5/§9 — the highest-fidelity source
available for that specific case).
