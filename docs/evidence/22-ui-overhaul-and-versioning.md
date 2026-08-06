# Evidence: UI overhaul, versioned change requests, gap feedback (tasks 22–28)

Date: 2026-08-06

## What changed, per the user's 4 requests

1. **Lighter background** — `index.css`, `nodeStyles.ts`, and every component
   rewritten from a dark slate-950 theme to a soft slate-50 background with
   white cards, pastel node colors, and a blue accent (Apple/Google-style
   clean product UI). `docs/screenshots` not captured this round (see
   disclosed limitation below); verified via `tsc --noEmit` + full test suite
   + live curl checks of the served HTML/JS.

2. **Process map spacing** — root cause: the backend stored a fixed, tight
   grid (`260px` × `140px` in `seed.py`) that didn't account for variable
   title length/wrapping. Replaced with a client-side layered auto-layout
   (`frontend/src/layout.ts`) computed from the actual graph structure every
   render (longest-path rank, generous fixed spacing, deterministic
   non-overlap) — self-heals when a change request adds/removes tasks, rather
   than needing backend position math kept in sync. `TaskNode` also got a
   fixed `min-h-[104px]` + `line-clamp-3` so node height is predictable
   regardless of title length.

3. **Chatbot repurposed for BPA feedback, never coverage questions** —
   `app/chat.py` rewritten: `classify_intent()` runs a deterministic
   regex-based scope gate *before* any retrieval or LLM call — coverage
   questions are refused in code, not just discouraged by a prompt. Change
   requests are drafted (LLM-assisted when a key is present, conservative
   heuristic fallback otherwise) and logged as `ChangeRequest` rows, never
   applied automatically. Approving one calls
   `app/pipeline/versioning.py::apply_change`, which clones the current
   `ProcessMapVersion`'s tasks/edges into a **new** version, applies exactly
   one structural mutation, re-runs the same DAG validator used at build time,
   and only commits if the result is still valid — the base version is never
   mutated in place.

4. **Gap feedback + approval** — `Issue` model extended with `bpa_feedback` /
   `resolution_notes` / `pending_review` status; new `PATCH
   /api/documents/{id}/issues/{issue_id}` endpoint; `IssuesPanel` now has a
   feedback input + resolve/defer buttons per issue. Combined with
   `ChangeRequestsPanel` (approve/reject) under one "Feedback" tab.

## Red-before-green proofs (not just asserted)

1. **Task-ID collision bug in `versioning.py`** — caught during code review
   before ever running anything (process_tasks.id is a global primary key,
   not scoped per version; naive cloning with the same ids would collide).
   Deliberately reintroduced the bug and ran the test suite: 4/6 new
   `test_versioning.py` tests failed with the exact `SAWarning`/IntegrityError
   predicted. Reverted the fix, reran: 6/6 pass.
2. **Coverage-question phrasing gap** — the original `_COVERAGE_PATTERNS`
   didn't catch `"Is a cracked windscreen covered?"` (only matched
   `is (my|this|it|the)`, not `is a`). This is the exact message the
   *original* build's own test used to exercise coverage-style retrieval —
   caught when running the full suite, not before. Broadened the pattern to
   `\bis\b.{0,60}\bcovered\b` and rewrote the now-outdated test to assert the
   new required behavior (refusal) instead of the old one.
3. **Explain-intent classification gap** — `"Why is the exclusions check
   before the excess step?"` didn't match any `_EXPLAIN_PATTERNS` (classified
   `general` instead). Caught by a parametrized test, fixed by adding a
   `^why\b` pattern.

## Test counts

- Backend: **68/68** pytest pass (41 original + 27 new: 6 versioning, 16 chat
  scope, 5 new API-level HTTP tests via TestClient — coverage refusal, explain
  mode, change-request logging, approve, reject, issue feedback PATCH).
- Frontend: **30/30** vitest pass (17 original + 5 new `layout.test.ts` +
  2 new `IssuesPanel.test.tsx` (feedback submit, resolve) + 5 new
  `ChangeRequestsPanel.test.tsx` + `App.test.tsx` updated for the new tab
  structure and version badge).
- `tsc --noEmit` clean on both the app and test tsconfig (a real type error —
  a test mock missing the new `change_request_id` field — was caught this
  way and fixed).
- Production build (`npm run build`) clean.

## Live end-to-end verification (real running server, real ANTHROPIC_API_KEY)

Ran against the actual running backend (fresh DB, restarted to pick up the
new tables) with the real configured LLM key, not just mocks:

1. `POST /api/chat` with `"Is a cracked windscreen covered?"` →
   `mode: out_of_scope`, refused, `sources: []`. Confirmed live, not just
   unit-tested.
2. `POST /api/chat` with an ambiguous add-step request → LLM honestly
   returned `change_type: unclear` because retrieval didn't surface the right
   anchor task in context — this is the designed behavior (prefer "unclear"
   over guessing), not a bug, though it does surface a real retrieval-quality
   limitation (see below).
3. `POST /api/chat` with a clearly-named remove request → LLM correctly
   identified the exact task id. Approved it via
   `POST .../change-requests/{id}/approve` → process map went from **v1 (11
   tasks)** to **v2 (10 tasks)**, with `"Check additional and optional
   covers"` genuinely gone from the task list, `version_label` changed, and
   `GET .../process-map/versions` showing both versions with `is_current`
   correctly flagged.
4. `PATCH /api/documents/{id}/issues/{issue_id}` with BPA feedback → real
   `bpa_feedback` and `status: pending_review` persisted and returned.
5. Full backend suite re-run with the real key present (not monkeypatched
   away) — still 68/68, confirming llm_grounded-mode behavior doesn't break
   anything the tests assume.

## Disclosed limitations (not glossed over)

- **No visual browser verification this round** — same sandbox constraint as
  the original build (navigation to `localhost`/`127.0.0.1` is blocked here).
  Verified instead via: clean `tsc`, clean production build, 30/30 component
  tests (including interaction tests for the new feedback controls), and
  confirming the dev server serves the updated source
  (`curl .../src/App.tsx | grep Feedback` returns matches). The user should
  visually confirm the light theme and map spacing themselves.
- **Change-request retrieval quality**: `draft_change_request`'s LLM prompt is
  only as good as `retrieve()`'s simple keyword-overlap scorer at finding the
  right anchor/target task. A well-named request ("remove the 'X' step")
  works reliably; a vaguer one ("add a step after capturing the claim
  description...") can miss the intended anchor and correctly fall back to
  `unclear` rather than silently misfiring — but that means some legitimate
  requests will need rephrasing rather than being auto-drafted. Not fixed
  this round; worth revisiting if this becomes a common friction point.
- **Heuristic (no-LLM-key) change-request drafting is intentionally weak** —
  only handles a narrow "remove X" pattern and defaults to `unclear`
  otherwise. This is a deliberate choice (see `chat.py` docstring: don't
  guess structure without a model to help parse free text), not an oversight.
