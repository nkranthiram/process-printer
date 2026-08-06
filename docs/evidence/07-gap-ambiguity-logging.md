# Evidence — Task 7: gap-ambiguity-logging

## What was logged
7 real issues found during extraction/synthesis of the AAMI PDS, not invented for
demo purposes:
- 2 `gap`: no explicit claim-lodgement deadline found in the extracted sections;
  additional/optional covers only partially claim-backed (3 of ~8)
- 5 `ambiguity`: "reasonable distance" undefined; unlicensed-driver owner-knowledge
  test is subjective; "not aware further damage could occur" is a state-of-mind
  test with no objective standard; "reckless act" examples are illustrative not
  exhaustive; no stated precedence between a general exclusion and a specific-cover
  inclusion when they'd otherwise conflict

Each links to the process task it affects and, where relevant, the claim(s) it
concerns — per the skill's contract, none block the task they're attached to; t3
and t9 were still fully synthesized with the open point named in their description
text (per task-description-authoring's rule).

## Verification
```
tests/test_issues.py::test_aami_issue_log_is_valid PASSED
tests/test_issues.py::test_issue_types_are_gap_or_ambiguity_or_low_confidence PASSED
tests/test_issues.py::test_validate_issues_catches_unknown_task_reference PASSED
tests/test_issues.py::test_validate_issues_catches_unknown_claim_reference PASSED
tests/test_issues.py::test_validate_issues_catches_empty_description PASSED
Full suite: 24 passed
```
The three "catches_*" tests are the red-before-green proof for the validator
itself (unknown task ref, unknown claim ref, empty description all provably
detected). No bugs found this round — the pattern from synthesis.py's validators
carried over cleanly.
