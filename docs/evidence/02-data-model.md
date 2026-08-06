# Evidence — Task 2: Backend data model

## Red-before-green

Broke `AtomicClaim.conditions` → `conditions_WRONG_NAME` (a real field rename, not a
contrived assertion), ran the suite:

```
FAILED tests/test_models.py::test_claim_links_to_span_and_document - TypeError:
'conditions' is an invalid keyword argument for AtomicClaim
1 failed, 3 passed in 1.96s
```

`test_claim_links_to_span_and_document` is the specific test that failed — exactly
the one exercising the field that broke. The other 3 stayed green because they don't
touch `conditions`, which is itself evidence they're not vacuously passing.

Restored the field, ran again:

```
tests/test_models.py::test_document_and_span_round_trip PASSED           [ 25%]
tests/test_models.py::test_claim_links_to_span_and_document PASSED       [ 50%]
tests/test_models.py::test_process_map_tasks_and_edges PASSED            [ 75%]
tests/test_models.py::test_issue_and_validation_case PASSED              [100%]
4 passed in 0.20s
```

## What's covered
- `DocumentVersion` ↔ `SourceSpan` relationship and round-trip read
- `AtomicClaim` ↔ `SourceSpan` link, JSON-encoded `conditions` field round-trips
- `ProcessMapVersion` ↔ `ProcessTask`/`ProcessEdge` relationships, edge direction
- `Issue` status field, `ValidationCase` round-trip incl. JSON `traced_path`

## What's not covered yet
- No FK-constraint enforcement tests (SQLite FKs are off by default; not yet turned
  on — noted as a follow-up, not a blocker for this stage)
- No test yet for cascade-delete behavior (`cascade="all, delete-orphan"` declared
  but unexercised) — will add once the API layer needs delete/re-ingest behavior
