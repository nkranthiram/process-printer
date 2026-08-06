# Evidence — Task 13: scenario-validation

## 5 scenarios traced, covering more than the happy path
1. Chipped windscreen, safely repairable, first claim → **Covered**, excess-free
   (10-step full path to decision t10)
2. Driver over the legal alcohol limit, single-vehicle crash → **Not covered**
   (short 4-step path: exclusion catches it at t3, straight to decision)
3. Rear-ended at a red light, not at fault, full at-fault details supplied →
   **Covered**, $0 excess — deliberately mirrors AAMI's own worked example on
   page 60 of the PDS, so the trace can be checked against the document's own
   numbers, not just the map's internal logic
4. Car left unattended/unlocked/keys-in, stolen → **Not covered** (4-step
   exclusion path)
5. Illegal mobile-phone use, single-vehicle crash → **Escalate to manual review**
   (5-step path ending at t11/human_review) — the required non-happy-path,
   non-clean-decision case per the skill's contract

## Automated verification
```
tests/test_validation.py::test_aami_validation_cases_traced_paths_are_real PASSED
tests/test_validation.py::test_at_least_five_scenarios_and_not_all_happy_path PASSED
tests/test_validation.py::test_all_cases_pass PASSED
tests/test_validation.py::test_validate_traced_paths_catches_a_nonexistent_edge PASSED
tests/test_validation.py::test_validate_traced_paths_catches_wrong_start_node PASSED
tests/test_validation.py::test_validate_traced_paths_catches_non_terminal_ending PASSED
Full backend suite: 41 passed
```
`test_aami_validation_cases_traced_paths_are_real` mechanically checks every
scenario's `traced_path` against the actual DAG — every consecutive step is a real
edge, every trace starts at the map's one start node, every trace ends at a
terminal (decision/human_review) node. The three `catches_*` tests are the
red-before-green proof for that checker itself (nonexistent edge, wrong start,
non-terminal ending all provably caught).

## Live check against the real running server
```
GET /api/documents/{id}/validation-cases → 5 cases
- Chipped windscreen ... -> pass (10 steps)
- Driver over the legal alcohol limit ... -> pass (4 steps)
- Rear-ended at a red light ... -> pass (10 steps)
- Car left unattended/unlocked ... -> pass (4 steps)
- Illegal mobile-phone use ... -> pass (5 steps)
```
Matches the seeded data exactly — persisted, retrieved via the real API, task ids
in `traced_path` resolve to real persisted `ProcessTask` rows (checked in
`test_seed.py::test_seed_aami_end_to_end`).
