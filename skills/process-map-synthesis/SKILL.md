---
name: process-map-synthesis
description: Group atomic claims into a task-level process map (a DAG) that a
  claims handler or BPA can actually follow. Use for "build the process map",
  "turn these rules into a flow", "what are the steps in this process".
---

# Process Map Synthesis

Turns a pile of atomic claims into something a human can walk through: a small
number of task nodes with clear transitions, not a clause-by-clause rules dump. This
is the step most likely to go wrong in the "too detailed" direction — the user
explicitly asked for task-level granularity, readable by a claims handler, not a
rule-engine-ready decision tree.

## Contract

- The map is a DAG: no cycles, every node reachable from the single start node,
  every path terminates in a decision or an explicit escalation/human-review node
- Task count stays in the "a handler can hold this in their head" range (roughly
  10-20 nodes for a single process like coverage determination) — if synthesis
  produces far more than that, the claims need regrouping into coarser tasks, not
  the map left fine-grained
- Every task links to the `AtomicClaim`s that justify its description — no task
  description states something no linked claim supports
- Edges carry a human-readable condition label (e.g. "Excess waived", "Excluded"),
  not a raw boolean expression — the audience is a person reading a diagram

## Procedure

1. Cluster claims by which point in the process they inform: does this claim
   determine *whether something is covered at all* (general exclusion), *which
   specific benefit applies* (cover-type classification), *what the policyholder
   owes* (excess), or *what evidence is needed*? These clusters are the seeds of
   task nodes — not one node per claim.
2. Order the tasks the way a handler would actually work through them: capture the
   claim description → confirm policy/period validity → check general exclusions →
   classify which specific cover applies → check that cover's own conditions/
   exclusions → determine excess → determine settlement path (repair vs. total
   loss) → check additional covers → gather required evidence → reach a decision or
   escalate.
3. Write each task's `node_type` from a fixed, small vocabulary (input_required,
   eligibility_test, exclusion_test, exception_test, evidence_sufficiency_test,
   classification, human_review, decision) — this taxonomy exists so the *shape* of
   a task is visible at a glance in the UI, not just its title.
4. Attach `claim_refs` — every claim that supports this task's description. A task
   with zero claim_refs is either genuinely a structural/navigational step (fine —
   e.g. "capture claim description") or a sign the task was invented rather than
   derived, which needs checking.
5. Add edges with condition labels for the paths a handler would actually take —
   don't enumerate every combinatorial branch if the underlying claims don't
   distinguish them; collapse where the document doesn't force a split.
6. Run structural validation: no cycles, single reachable start, every leaf is a
   decision or human-review node. This is deterministic code, not a judgment call —
   run it, don't eyeball the diagram.

## Anti-patterns

| Don't | Do |
|---|---|
| One task node per atomic claim (clause-level map) | Cluster into task-level nodes; a handler reads tasks, not clauses |
| A task description with no supporting claim_refs and no structural justification | Every content claim in a description traces to a claim_id |
| Force every exclusion into its own branch, exploding the node count | Group related exclusions into one "check general exclusions" task; the BPA reads the underlying claims for detail |
| A dead-end node that's neither a decision nor an escalation | Every leaf resolves to a decision or an explicit human-review terminal |
| Silently drop an irreducible ambiguity to keep the map clean | Route it to a human-review node instead of hiding it — see gap-ambiguity-logging |

## Fallbacks

- If claims don't cleanly cluster into a linear-ish flow (e.g. genuinely
  order-independent checks), model them as parallel branches into a shared
  downstream node rather than forcing an arbitrary order.
- If a document doesn't give enough claims to populate a task node meaningfully
  (e.g. a benefit is named but never actually described), that task becomes a
  `human_review` node and an `Issue` (gap) gets logged — don't invent a plausible
  description to fill the gap.

## Chains

```
claim-extraction → process-map-synthesis → task-description-authoring
process-map-synthesis + task-description-authoring → scenario-validation
```
