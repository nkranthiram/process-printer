---
name: workflow-alignment-testing
description: Verify a generated agentic workflow (AgenticWorkflowVersion)
  stays faithful to the human process map (ProcessMapVersion) it was derived
  from — same task coverage, aligned task descriptions/citations, and
  equivalent scenario outcomes — and document the results as a separate,
  dated report. Use after agentic-workflow-synthesis produces or updates a
  workflow, or on "does the workflow match the process map", "test the
  agentic workflow", "verify workflow alignment", "did the BPMN version
  diverge from the process map".
---

# Workflow Alignment Testing

A process map (human-facing, task-level) and its agentic workflow (BPMN-
style, node-level) are two different views of the *same* underlying process.
They will never be node-for-node identical by design — a single process-map
task legitimately expands into several workflow nodes (see
`agentic-workflow-synthesis/SKILL.md`'s non-negotiables) — but they must
never *diverge*: every task must still be represented, every node's stated
purpose must still trace back to what its source task actually says, and a
real case walked through either artifact must land on the same real-world
outcome. This skill is what actually checks that, mechanically wherever
possible, and documents the result somewhere a BPA can check it without
re-deriving it themselves.

This is a **downstream, mandatory check**, not an optional nice-to-have: per
`agentic-workflow-synthesis/SKILL.md`, generating or regenerating a workflow
is not complete until this skill has run against it and produced a report.

## The three alignment checks

Run all three, every time. They catch different failure modes and none
substitutes for another.

**1. Coverage alignment (structural, fully mechanical)**
Every `ProcessTask` in the source process map must be represented by at
least one `AgenticWorkflowNode` whose `source_task_title` matches it — a
task with zero derived nodes is a silently dropped task, not "not
applicable." Group nodes by `source_task_title`; a source task expanding
into 2+ nodes (classification + screening + gateway, say) is expected and
correct, not a failure. Nodes with no `source_task_title` (pure
gateways/service nodes the workflow needed but the human map didn't call out
— e.g. "ingest documents," "generate outcome letter") are allowed and don't
count against coverage, but must be logged as workflow-only additions in the
report so a reviewer sees them named, not just absent from the count.

**2. Description & citation alignment (mechanical + judgment)**
For every group of nodes sharing a `source_task_title`:
- *Mechanical part*: collect the union of `claim_refs` across that group's
  nodes. Every claim in that union must either (a) already appear in the
  source task's own `claim_refs`, or (b) belong to a directly adjacent
  source task that the group's nodes explicitly also derive from (e.g. an
  exclusion-screening node legitimately citing claims from both "screen
  exclusions" and the cover-classification task feeding it). Any claim
  outside both is a fabricated-scope citation — the node is citing something
  its source task never claimed — and fails this check regardless of
  whether the underlying citation is itself real (the agentic-workflow
  validator already checks that a citation *exists*; this check is whether
  it's the *right* citation for *this* node's claimed origin).
- *Judgment part*: read the source task's `description` against each
  derived node's `goal` + `decision_logic` / `authority_boundary`. They must
  be consistent — the node may narrow scope (a source task covering "check
  general exclusions" decomposing into a node that only screens *one*
  exclusion category is fine) but must never contradict, invert, or silently
  drop a condition the source description states as a requirement. Record
  the judgment call and a one-line reason in the report; this is not
  auto-passable and must not be reported as "pass" without an actual
  comparison having been made (see Anti-patterns).

**3. Outcome equivalence (scenario-based)**
Reuse the process map's existing `ValidationCase`s (see
`scenario-validation/SKILL.md`) — do not invent a separate scenario set for
the workflow; the whole point is testing whether the *same* case produces
the *same* real-world conclusion in both artifacts. For each `ValidationCase`:
- The process-map side already has its `expected_outcome` / `actual_outcome`
  / `traced_path` from scenario-validation — reuse it, don't re-run it.
- Trace the same scenario through the agentic workflow graph: at each node,
  decide the outgoing edge the scenario's facts satisfy (deterministic nodes
  by their stated rule, agent nodes by their decision logic / authority
  boundary, gateways by their named conditions), following real edges only,
  exactly as scenario-validation does for the process map.
- Before comparing, state an explicit **outcome-equivalence mapping**
  between the process map's terminal categories (e.g. "covered", "excluded",
  "escalated to human") and the workflow's terminal node states (e.g. an
  auto-processed close via the QA lane, a human-queue routing, a
  deterministic-decline auto-close). Do not compare loosely by eye — write
  the mapping down in the report so a reviewer can check it, since the two
  artifacts don't share identical terminal-node vocabulary by construction.
- `result` is `pass` only if the workflow trace's terminal state maps to the
  same category as the process map's `actual_outcome` under the stated
  mapping. A mismatch is `fail`, recorded and kept, never quietly resolved
  away — same discipline as `scenario-validation`.

## Contract for the report artifact

Every run produces a **new**, separately dated report file — never
overwrites a prior run's report, so alignment history over time (as the
process map or workflow gets re-versioned) stays inspectable, same
versioning discipline as the rest of this app.

- **Location**: `docs/workflow-alignment-reports/`
- **Filename**: `{document-slug}__pm-{process_map_version_label}__wf-{agentic_workflow_generator_version}__{run-date}.md`
  (e.g. `aami-comprehensive-car-insurance__pm-v2__wf-manual-agent-pass-v1__2026-08-12.md`)
- **Required contents**:
  1. Header stating which exact `ProcessMapVersion` id/label and which exact
     `AgenticWorkflowVersion` id/generator_version were compared — never
     "the current map," always the specific version, since both are
     versioned artifacts that change over time.
  2. **Coverage table**: every source task, the node(s) derived from it (or
     explicitly "NONE — gap"), and pass/fail.
  3. **Workflow-only nodes list**: nodes with no `source_task_title`, named
     and justified (why the workflow needed them beyond the human map).
  4. **Description/citation alignment table**: per source-task group, the
     mechanical claim-scope result (pass/fail + any out-of-scope claims
     found) and the judgment note (consistent / narrowed-but-consistent /
     contradiction found, with the one-line reason).
  5. **Outcome-equivalence mapping** used, stated explicitly before the
     results table.
  6. **Scenario outcome table**: one row per `ValidationCase`, with the
     process-map outcome, the workflow-traced outcome, and pass/fail.
  7. **Summary**: counts (X/Y coverage, X/Y description-aligned, X/Y
     scenario-equivalent) and an overall verdict — `aligned`,
     `aligned-with-noted-gaps` (some workflow-only additions or narrowings,
     but zero failures), or `misaligned` (any hard failure in any check).
  8. Any check that could not be completed (e.g. no `ValidationCase`s exist
     yet for this document) is stated as **not run**, never silently
     omitted or counted as a pass.

## Procedure

1. Identify the exact `ProcessMapVersion` and `AgenticWorkflowVersion` pair
   under test — the workflow's own `process_map_version_id` /
   `process_map_version_label` fields name which map it was generated
   from; use that pair, don't assume "latest of both."
2. Run the coverage check (mechanical) — group nodes by
   `source_task_title`, diff against the full source task list.
3. Run the description/citation alignment check — mechanical claim-scope
   diff per group, then the judgment read per group.
4. Run the outcome-equivalence check — state the terminal-category mapping,
   then trace every existing `ValidationCase` through the workflow graph
   and compare to its already-recorded process-map outcome.
5. Write the report per the Contract above, to a **new** file — never edit
   a previous run's report.
6. If any check is `misaligned` or `not run`, say so plainly in whatever
   response accompanies this skill's use — do not report a workflow as
   "tested and aligned" when the report itself says otherwise.

## Anti-patterns

| Don't | Do |
|---|---|
| Mark description alignment "pass" for every group without actually reading each source task's description against its derived nodes | Record the one-line judgment reason per group — a pass with no stated reasoning is not evidence |
| Compare terminal outcomes "by eye" without writing down the equivalence mapping | State the category mapping explicitly in the report before scoring any scenario |
| Overwrite the previous alignment report on every rerun | Write a new, dated file every run — alignment drift over time is exactly what this exists to catch |
| Treat a node with no `source_task_title` as automatically suspicious | Log it in the Workflow-only nodes list with its justification; some are legitimate (ingest, close-out) |
| Silently skip the scenario check because no `ValidationCase`s exist | Report that check as **not run**, explicitly, not omitted |
| Invent new test scenarios specifically for the workflow | Reuse the process map's existing `ValidationCase`s — divergent scenario sets can't prove the two artifacts agree |

## Fallbacks

- **No `ValidationCase`s exist for this document yet** → run checks 1 and 2
  in full, report check 3 as **not run** with the reason, and recommend
  running `scenario-validation` first before treating the workflow as
  fully tested.
- **A source task has zero derived nodes** → this is a coverage `fail`, not
  a soft warning — log it plainly in the coverage table; do not treat an
  intentionally-scoped-out task as equivalent to an oversight without an
  explicit note from whoever generated the workflow saying so.
- **The process map or workflow changes after a report was written** → the
  report is a point-in-time artifact; do not edit it retroactively. Run this
  skill again against the new version pair and write a new report; the old
  one stays as history.

## Chains

```
agentic-workflow-synthesis (produces/updates an AgenticWorkflowVersion)
        │
        ▼
workflow-alignment-testing  ──▶  docs/workflow-alignment-reports/*.md
        │
        ▼   (only if misaligned or not-run)
     surface findings back to the BPA / whoever triggered the regeneration
```
