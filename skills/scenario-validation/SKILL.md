---
name: scenario-validation
description: Trace a real claim scenario through a process map and record whether
  it reaches the right outcome, as evidence the map actually works. Use for "verify
  this works for real cases", "test the process map", "trace a scenario".
---

# Scenario Validation

The closest thing to unit testing for a process map: take a realistic claim
description, walk it through the DAG task by task exactly as a handler would, and
record where it ends up. This is what turns "the map looks structurally sound" into
"the map produces the right answer for cases that matter."

## Contract

- Every `ValidationCase` states, before tracing: the claim description, and the
  expected outcome with a one-line reason tied to specific claim citations
- The trace records the actual sequence of task ids walked, in order, following
  real edges in the map — not a summary of "which tasks are relevant"
- `result` is `pass` only if the actual outcome matches the expected outcome; a
  mismatch is `fail` and stays recorded as a fail (a mismatch here is either a bug
  in the map or a bug in the expectation — both are worth knowing, so it doesn't
  get quietly corrected away)
- Scenario selection deliberately covers more than the easy path: at least one
  clear-cover case, one clear-exclusion case, one excess-waiver/calculation case,
  and one case that should escalate to human review — a suite of only "happy path"
  scenarios doesn't prove much

## Procedure

1. Write the scenario as a claims handler would receive it — a plain-language
   claim description, not pre-classified into "this is an exclusion case."
2. Starting at the map's single start node, at each task decide which outgoing
   edge the scenario's facts satisfy, using only the task's linked claims (not
   outside knowledge) to make that call — if the claims genuinely don't resolve
   which edge applies, that's itself a finding (route to human_review and note why,
   don't force a resolution the map doesn't support).
3. Record the full `traced_path` (list of task ids in walked order) and the
   terminal node reached.
4. State the `actual_outcome` in the same terms as `expected_outcome`, so they're
   directly comparable, and set `result`.
5. Run structural validation on the trace: every consecutive pair in `traced_path`
   must be a real edge in the map, and the trace must start at the map's start node
   and end at a terminal node — this is checkable mechanically, not just by eye.

## Anti-patterns

| Don't | Do |
|---|---|
| Only write scenarios that obviously work | Include an exclusion case and an escalation case, not just happy paths |
| Summarize "the relevant tasks" instead of the literal walked sequence | Record every task in order, including ones that just confirm and pass through |
| Silently mark a mismatch as a pass because "the map is probably fine" | Record it as `fail`; a fail here is valuable, not embarrassing |
| Skip validating the trace is actually a real path in the graph | Check every consecutive pair against real edges — a plausible-looking trace can still reference an edge that doesn't exist |

## Fallbacks

None — this is pure analysis over data already produced by earlier stages.

## Chains

```
process-map-synthesis + task-description-authoring → scenario-validation
```
