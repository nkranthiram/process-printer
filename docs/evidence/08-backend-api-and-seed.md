# Evidence — Task 8: seed pipeline + backend API layer

## Real bug found and fixed: test-isolation double-Base mismatch
Original `conftest.py` deleted `sys.modules['app.*']` between tests and re-imported
fresh, intending full isolation. This broke `test_seed.py` with:
```
sqlalchemy.exc.OperationalError: table atomic_claims has no column named conditions
```
Root cause: `app.seed`'s own module-level imports (`AtomicClaim`, etc.) were bound at
pytest's collection time, before any fixture ran. The fixture's `sys.modules`
deletion + re-import created a *second*, distinct `Base` class and a second set of
model classes bound to it — but `seed_aami()` (a function object already captured by
`test_seed.py`) kept using the *first* set of classes. SQLAlchemy generated the
INSERT statement from the first (never-created-in-this-engine) mapper, which by
coincidence produced a working INSERT for simpler tables but broke wherever the
column set was more elaborate — not a fabricated bug, a real one, caught by running
the actual seed pipeline end-to-end rather than only unit-testing each stage in
isolation (verification.md's "test the user's path" applies to test *infrastructure*
too).

Fixed by making `Base`/model classes a true singleton for the test process
(`database.use_test_db()` rebinds the engine/session and calls
`drop_all`+`create_all` against the *existing* metadata, never re-imports the model
modules). Full suite passed clean afterward, including a rerun of every previously-
green test (nothing regressed from the conftest change).

## Full pipeline integration test (`test_seed.py`)
```
tests/test_seed.py::test_seed_aami_end_to_end PASSED
tests/test_seed.py::test_seed_is_idempotent_on_rerun PASSED
Full suite: 26 passed
```
Verifies, against a real database: 76 pages / 300+ spans persisted, 38 claims
persisted each with a resolvable FK to a same-document span, 11 tasks / 14 edges
persisted with every edge's endpoints belonging to the same process map and every
task's claim_refs resolving to real persisted claims, 7 issues persisted each with a
resolvable task reference where one applies. Re-seeding the same document (same
content hash) replaces rather than duplicates — 1 document, 38 claims, not 2/76.
