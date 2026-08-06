# Evidence — Task 5: process-map-synthesis

## What was built
11-task DAG for "Determine claim coverage — AAMI Comprehensive Car Insurance":
capture description → confirm policy/incident validity → check general exclusions
→ classify applicable cover → check cover-specific conditions → verify evidence →
determine at-fault status/excess → determine settlement path → check additional
covers → reach coverage decision → escalate to manual review. 13 edges, single
start node, two terminal node types (decision, human_review).

## Real bugs the tests caught (this is the actual verification, not a formality)
1. `test_aami_process_map_is_fully_valid` failed on the first run: task t7
   referenced claim subject `excess_definition`, but the actual extracted claim's
   subject was `excess` — a real naming mismatch between the map and the claim
   set, caught mechanically rather than by a reviewer noticing during a read-through.
2. `test_every_content_task_has_claim_refs_or_is_structural` failed: task t9
   ("Check additional and optional covers") had zero claim_refs despite being a
   content task — fixed by extracting 3 more real claims (transport cover, new car
   after total loss, hire car after theft) from pages 30/32/33 rather than
   silently loosening the test.
3. `test_validate_dag_structure_catches_a_cycle` failed on the first version of the
   validator itself: the cycle-detection DFS only ran when exactly one root
   existed, so a graph with zero roots (which a cycle can cause) skipped cycle
   detection entirely and reported only "no unique start node," not the cycle.
   Fixed by running DFS over every node regardless of root count.

All three were fixed in-session, per this repo's verification.md discipline
("a check that has never failed is not evidence" — these failed for real reasons,
not injected ones, then were fixed and reverified).

## Final run
```
tests/test_synthesis.py::test_aami_process_map_is_fully_valid PASSED
tests/test_synthesis.py::test_task_count_is_in_readable_range PASSED
tests/test_synthesis.py::test_every_content_task_has_claim_refs_or_is_structural PASSED
tests/test_synthesis.py::test_validate_dag_structure_catches_a_cycle PASSED
tests/test_synthesis.py::test_validate_dag_structure_catches_non_terminal_leaf PASSED
tests/test_synthesis.py::test_validate_claim_refs_catches_dangling_reference PASSED
tests/test_synthesis.py::test_validate_node_types_catches_invalid_type PASSED
Full suite (all tests, all tasks so far): 19 passed
```
11 tasks (within the 8-20 target range), every content task has claim_refs, DAG is
acyclic with a single reachable start and all leaves terminal.

## Known limitation (disclosed)
Task t9 (additional/optional covers) only has 3 of the ~8 additional/optional
covers named in the PDS backed by extracted claims (transport cover, new car after
total loss, hire car after theft). The rest (towing/storage, hire car after
not-at-fault, trailer cover, unlimited-day hire car, roadside assist) are named in
the task description but not yet claim-backed — logged as an open issue (task 7).
