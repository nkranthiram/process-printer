# Architecture — Process Printer

Status: living document, updated as the build progresses. See `PROGRESS.md` for
task-by-task status and `../DECISIONS.md` for anything promoted to the parent
ways-of-working repo.

## What this is

Given a policy-type document (or set of documents), extract a **task-level process
map** and per-task descriptions that a claims handler or Business Process Analyst
(BPA) can use to understand and (manually, for now) apply the coverage-determination
process — with every task traceable back to the source document on click, plus a
logged list of gaps/ambiguities the document doesn't resolve.

**Explicitly out of scope**: building or running an automated claim-decisioning
agent/execution engine. This tool produces the map and descriptions for human
review — it does not decide claims.

## Stack decisions

| Layer | Choice | Why | Alternatives considered |
|---|---|---|---|
| Backend language | Python 3.11 (via `/opt/homebrew/bin/python3.11`) | User requirement. System default `python3` resolved to 3.8.8 (anaconda), too old for modern typed FastAPI/Pydantic v2 usage — 3.11 was available via Homebrew | Anaconda's 3.8 — rejected, EOL-adjacent and lacks modern typing features |
| Backend framework | FastAPI + Pydantic | Typed request/response models double as API docs; async-friendly for LLM calls | Flask (less structure), Django (too heavy for this scope) |
| Persistence | SQLite via SQLAlchemy (dev); schema written to be swappable to Postgres | Zero external services needed to run locally; SQLAlchemy models are the migration path to Postgres later without a rewrite | Flat JSON files (rejected — provenance/evidence tables need real joins, see `provenance.md`'s explicit warning against flattening evidence into arrays) |
| PDF parsing | PyMuPDF (`fitz`) | Gives page number + bounding box per text span, which is the citation primitive everything else depends on | pdfplumber (weaker table handling), unstructured.io (heavier dependency for what we need) |
| Extraction "brain" | Pluggable LLM client interface, real implementation targets Anthropic's API via `ANTHROPIC_API_KEY` | Keeps the pipeline generic across future documents (user requirement: swap document, re-run, works generically) | Hard-coding a one-off script for the AAMI PDS only — rejected, fails the generic-pipeline requirement |
| Frontend | React + TypeScript + Vite | User requirement (React); Vite for fast local iteration | Next.js (unneeded SSR complexity for an internal tool) |
| Styling / components | Tailwind CSS + a small hand-built component set (shadcn/ui patterns, not the full library dependency) | Clean, consistent, "sophisticated" look without a heavy design-system dependency | MUI (heavier, more opinionated visual style than requested) |
| Process map rendering | React Flow | Purpose-built for DAG/node-edge rendering with click interactions, which is exactly the citation-on-click requirement | Custom SVG (more work, no benefit here) |
| Backend tests | pytest | Python default | |
| Frontend tests | Vitest + React Testing Library | Vite-native, fast | Jest (works but redundant given Vite) |

## Known constraint (disclosed, not fabricated)

This build environment has no `ANTHROPIC_API_KEY` set. The extraction pipeline
(`backend/app/pipeline/extraction.py`) is written against a real LLM client
interface so it works generically once a key is supplied. For the first proof run
against the AAMI Comprehensive Car Insurance PDS, the extraction pass was performed
directly by the building agent (reading the PDF, producing the same schema the
pipeline would) rather than by a live model call — every record produced this way is
tagged `extractor_version: manual-agent-pass-v1` so it's never confused with an
automated-pipeline run. See `PROGRESS.md` notes.

## Data model (see `backend/app/models/`)

- `DocumentVersion` — one row per uploaded document/version
- `SourceSpan` — page/section/bbox-anchored text extracted from a document; the
  citation primitive
- `AtomicClaim` — a single extracted rule/condition/exception, linked to its
  `SourceSpan`(s)
- `ProcessTask` — a node in the process map (task-level, not clause-level)
- `ProcessEdge` — a transition between tasks, with a condition
- `Issue` — a gap or ambiguity, linked to the claims/tasks it affects
- `ValidationCase` — a traced claim scenario with its expected/actual outcome

Provenance follows `practices/provenance.md`: evidence is its own linked
record, never a flattened array field, so "why does this task say that" is always
answerable by following a link, not by trusting prose.

## API surface (implemented)

FastAPI, prefix `/api`:
- `GET /documents` — list ingested documents
- `GET /documents/{id}/process-map` — tasks + edges, each task's citations resolved
  from `claim_refs` (JSON list of claim ids) into full `Citation` objects
- `GET /documents/{id}/issues` — logged gaps/ambiguities with resolved citations
- `GET /documents/{id}/validation-cases` — traced scenarios with pass/fail
- `POST /chat` — `{document_id, message}` → grounded answer + sources; `mode` field
  (`retrieval_only` | `llm_grounded`) tells the caller honestly which path answered

On startup, the app seeds the AAMI document automatically (`init_db()` +
`seed_aami()`) so there's something to see without a manual upload step — a real
upload endpoint (parse a NEW document through the same pipeline) is the natural
next increment but wasn't required for this pass; see "What's next" below.

## Frontend structure (implemented)

`App.tsx` loads documents/process-map/issues/validation-cases once, then switches
between four tabs without refetching: **Process map** (React Flow canvas +
click-to-expand task detail panel with citations), **Gaps & ambiguities**, **Test
scenarios**, **Ask a question** (chat). All data comes from the API layer above —
no client-side re-derivation of process logic, matching the "chatbot answers from
the validated graph, not raw documents" principle from the original design
discussion.

## Open decisions log

Entries follow `practices/decision-log.md` format. Newest first.

### Test-isolation strategy: singleton Base/models, swap engine per test
**Date:** this build.
**Decision:** `database.use_test_db()` rebinds the module-level SQLAlchemy engine
and calls `drop_all`+`create_all` against the *existing* `Base.metadata`, rather
than deleting model modules from `sys.modules` and re-importing them fresh per test.
**Why:** the sys.modules-deletion approach caused a real bug — `app.seed`'s
functions, imported once at pytest collection time, kept referencing the first
`Base`'s model classes, while the fixture created a second `Base` and mapped tables
under it. SQLAlchemy happily built INSERT statements from the first (never-created)
mapper, silently dropping columns that happened to differ between what the engine's
tables actually had and what the stale class thought they had. See
`docs/evidence/08-backend-api-and-seed.md` for the full trace.
**Alternatives considered:** per-test in-memory SQLite (`:memory:`) — rejected,
still needs a fresh engine per test since SQLite in-memory DBs are connection-scoped,
doesn't remove the double-Base risk on its own. Full pytest-xdist process isolation
— rejected as overkill for this project's size.
**Revisit if:** the model layer grows enough that `drop_all`/`create_all` per test
becomes a real time cost — a savepoint-and-rollback-per-test pattern would be the
next step.

### Manual-agent-pass extraction instead of waiting for an API key
**Date:** this build.
**Decision:** Ran claim extraction for the AAMI PDS directly (the building agent
reading parsed spans and producing the same schema an LLM call would), rather than
blocking the whole build on an `ANTHROPIC_API_KEY` not being available in this
sandbox.
**Why:** the user asked to see the approach proven on the real document now, with
the pipeline built generically for future documents. Blocking on a key would have
meant no proof at all versus a proof clearly labeled as a substitute for the
automated path (`extractor_version: manual-agent-pass-v1` on every affected row).
**Alternatives considered:** ship only the pipeline scaffolding with synthetic
placeholder data — rejected per the user's explicit "verify individual cases"
requirement, which needs real content, not placeholders.
**Revisit if:** an API key becomes available — re-run `extraction.py`'s
`AnthropicLLMClient` path and compare its output against the manual pass as a
sanity check before trusting it for a new document.

### Process map versioning: clone-on-change, never mutate in place
**Date:** 2026-08-06 (tasks 22–28, UI overhaul + feedback loop).
**Decision:** An approved `ChangeRequest` is applied by cloning the current
`ProcessMapVersion`'s tasks/edges into a brand-new version row, applying exactly
one structural mutation to the clone, re-validating with the same DAG structural
checks used at build time (`synthesis.py`'s validator, reused not reimplemented),
and only committing if still valid. The base version's rows are never touched.
"Current" is simply the most recently created version for a document — no
separate pointer/flag needed.
**Why:** an auditable version history was an explicit requirement ("maintaining
versions for these changes is also important"). Editing in place would make it
impossible to answer "what did this look like before the BPA's change," and
would risk a bad automated edit silently corrupting the live map with no
rollback path.
**A real bug this caught before it shipped:** `process_tasks.id` is a global
primary key across every version, not scoped per `process_map_id` — the first
implementation cloned tasks with their original ids, which collides with the
still-existing row from the base version the moment a second version exists.
Fixed by generating fresh ids for every task in a new version and rewriting
edges through an id map. Proven red-before-green (see
`docs/evidence/22-ui-overhaul-and-versioning.md`).
**Alternatives considered:** a single mutable `ProcessTask`/`ProcessEdge` table
with a separate append-only changelog — rejected because reconstructing "what
did v1 actually look like" from a changelog is strictly more complex than just
keeping the old rows, and the data volume (a handful of tasks per document) makes
full cloning cheap.
**Revisit if:** the task count per process map grows large enough that cloning
the whole graph per change becomes wasteful — a delta/patch representation would
be the next step, but isn't justified at this scale.

### Chatbot scope enforcement: deterministic gate before any LLM call
**Date:** 2026-08-06.
**Decision:** `classify_intent()` in `app/chat.py` is plain regex classification
that runs *before* retrieval or any LLM call. A message matching a coverage
question pattern is refused immediately, in code — it never reaches an LLM
prompt at all.
**Why:** the user was explicit that this app must never answer coverage
questions, only review/give feedback on the process map. A prompt-level
instruction ("don't answer coverage questions") is not a hard guarantee — a
sufficiently adversarial or oddly-phrased user message can talk a model around
prompt-level instructions. A code-level gate that never constructs the LLM call
in the first place is a stronger guarantee, and is unit-tested with a
`monkeypatch` that makes `retrieve()` raise if it's ever invoked for a coverage
question (see `test_chat_scope.py::test_coverage_question_never_reaches_retrieval_or_llm`).
**Alternatives considered:** LLM-based intent classification only — rejected as
the sole gate, since it reintroduces exactly the prompt-injection risk this is
meant to close. (LLM assistance is still used, but only *after* the gate, for
drafting a structured change-request payload from an already-classified
`change_request` message.)
**Revisit if:** regex classification proves too brittle against real BPA
phrasing in practice — the fallback would be a small, cheap, deterministic-output
classifier call that still runs *before* any context-bearing prompt, preserving
the same guarantee.

### Process map layout: recomputed client-side, not trusted from storage
**Date:** 2026-08-06.
**Decision:** `frontend/src/layout.ts` computes node positions from the live
graph structure (longest-path rank + fixed generous spacing) on every render,
rather than trusting the `position_x`/`position_y` values stored on each
`ProcessTask` row.
**Why:** the stored positions came from a coarse backend grid (task 5's
`seed.py`) that didn't account for variable title length — this is what caused
the reported text/box overlap. Recomputing client-side also means the layout
self-heals automatically when a `ChangeRequest` adds or removes a task — no
backend position math has to be kept in sync with graph edits.
**Alternatives considered:** a full graph-layout library (e.g. `dagre`) —
rejected for now to avoid a new dependency for a graph this small (≤15 nodes);
the hand-rolled longest-path layering is a few dozen lines and fully covered by
`layout.test.ts`. Revisit if process maps grow large/complex enough (wide
fan-outs, many cross-links) that a real layout engine's cycle/crossing-
minimization would matter.

### "Review & Apply Changes" — batch feedback, versioning granularity resolved by debate
**Date:** 2026-08-06 (tasks 29–33).
**Decision:** Added a session-scoped, conversational feedback flow layered on
top of (not replacing) the per-message `ChangeRequest` flow. A BPA converses
freely; clicking "Review & Apply Changes" runs an LLM reconciliation pass over
the transcript, producing grounded `DraftChangeItem`s the BPA can
approve/reject/edit individually; confirming applies every **approved** item
as **exactly one** new `ProcessMapVersion` — not one version per edit, not one
opaque version per whole session.
**Why this granularity:** resolved via a 2-round claude/gpt debate (see chat
history) that initially split on whether the unit of a version should be one
edit or one whole batch. Landed on: the unit of versioning is whatever a human
approved together, at any size — which subsumes both original positions (a
1-item approval behaves exactly like the old per-message flow; an N-item
approval is one clean version) and avoids materializing meaningless
"mid-batch" states that were never themselves approved by anyone (an artifact
of internal apply order, not a real checkpoint).
**How atomicity is enforced:** `apply_change_set` applies every edit in a
batch to a single in-memory draft, validating the DAG after each mutation for
exact failure localization, but persists to the database only once, only if
every edit succeeds. A mid-batch failure leaves the database completely
untouched — proven via a deliberately-reintroduced regression (see
`docs/evidence/29-30-review-apply-changes.md`).
**Alternatives considered:** one version per edit within the approved set
(loses the "one coherent approval event" framing GPT argued for, and pollutes
history with N rows for what was conceptually one BPA decision) — rejected.
One opaque version per session with edits only in a metadata blob (Claude's
critique: doesn't actually deliver mechanical rollback, just an audit
narrative) — rejected in favor of keeping `_apply_single_change` reusable and
validated per-step without paying for durable intermediate storage.
**Revisit if:** dependency-aware clustering becomes necessary (two coupled
edits currently apply independently and could partially succeed in confusing
ways) — flagged as a named follow-up, not built this round.

### Chat remains stateless; the frontend supplies the transcript
**Date:** 2026-08-06.
**Decision:** Rather than add server-side chat/conversation persistence, the
`/consolidate` endpoint takes the transcript as a request body (the frontend
already holds it in React state from `ChatPanel`'s turn history).
**Why:** avoids a larger persistence/session-management build-out for a
single-user local app, and keeps the existing stateless `/api/chat` endpoint
unchanged. The tradeoff is explicit: this doesn't deliver the "incremental,
per-turn update" half of the debate's conclusion as fully as a
server-persisted transcript would — each consolidate call re-reconciles the
full transcript rather than updating a running list turn by turn. Grounding
discipline (citations, `needs_clarification` for ambiguity) is unaffected;
only the *mechanism* is a full-transcript reconciliation pass rather than a
true incremental pipeline.
**Revisit if:** conversations get long enough that full-transcript
reconciliation becomes slow/expensive, or if multi-session/multi-device
continuity is ever needed — at that point, persisting chat turns server-side
(and making `/consolidate` operate incrementally against stored turns) is the
natural next step.

## What's next (named, not silently deferred)

- Real file-upload endpoint wired to the same ingest→extract→synthesize pipeline,
  for a genuinely new document (the pipeline is generic; only the upload/trigger
  endpoint is missing)
- Close the additional-covers extraction gap logged in the issue log (task t9)
- Swap in the automated `AnthropicLLMClient` extraction path once a key is
  available, and diff its output against the manual-pass baseline
- Real browser visual verification (this sandbox couldn't navigate to localhost —
  see `docs/evidence/10-12-frontend.md` and `docs/evidence/22-ui-overhaul-and-versioning.md`)
- Postgres migration if this moves beyond a single local reviewer's use
- Change-request retrieval quality: a vaguely-worded add/modify request can miss
  the right anchor task and fall back to `unclear` — worth revisiting if this
  becomes a common friction point (see `docs/evidence/22-ui-overhaul-and-versioning.md`)
- `add_task`/`modify_task` change types are implemented in `versioning.py` and
  have now both been live-verified end-to-end via the "Review & Apply Changes"
  flow (see `docs/evidence/29-30-review-apply-changes.md`) — this item is closed
- No dependency-aware clustering of coupled edits in `apply_change_set` (see
  `docs/evidence/29-30-review-apply-changes.md`)
- No server-side chat transcript persistence — `/consolidate` re-reconciles
  the full transcript each call rather than updating incrementally (see the
  "Chat remains stateless" decision above)
- The old per-message `ChangeRequest` path and the new session-based
  `ReviewSession` path aren't deduplicated against each other if a BPA
  triggers both for overlapping feedback in one conversation

## Decision: committed change-log replay for durable versioning (not just a durable mechanism)

**Problem found:** versioning (`ProcessMapVersion`, `apply_change`/
`apply_change_set`) was fully built and tested, but `*.db` is (correctly)
gitignored — so the actual **data** produced by an approved BPA edit (v2, v3,
...) only ever existed in whichever machine's local SQLite file it was
approved on. A fresh clone reseeded straight back to v1, silently losing
every approved edit. This was a real gap between "versioning is built" and
"the process map is actually saved to the repo," caught by directly
inspecting the local DB rather than assuming the mechanism implied the data
was safe.

**Decision:** commit the *edits themselves*, not a database file. New
`backend/data/change_log/*.json`, one file per approved change set, applied
in filename order by `app/pipeline/change_log.py` — through the exact same
`apply_change_set()` engine the live "Review & Apply Changes" flow uses, so
replay and a live approval are semantically identical (same atomicity, same
DAG validation, same one-version-per-approved-set rule).

**Why title references, not database ids:** `ProcessTask`/`ProcessEdge` row
ids are regenerated on every fresh seed (`_persist_new_version`'s `id_map`),
so a change-log entry can't commit `task_id: "<uuid>"` and expect it to
resolve later. Entries instead reference tasks by `task_title` /
`after_task_title` (the same string a BPA sees in the UI), and
`change_log.py` resolves title -> current-run id immediately before applying,
refreshing that index after each entry so a later entry can reference a task
an earlier entry just added.

**A real gap this surfaced, fixed alongside it:** `ValidationCase`s were
never carried forward across a version at all — even the original live-built
v2 (task 30-33) silently had zero scenario coverage. Fixed in
`versioning.py`'s `_persist_new_version`: a case carries forward only if
every task on its traced path still exists post-edit (remapped via the same
`id_map`); otherwise it's dropped and named in the new version's
`change_summary`, rather than silently vanishing or being carried forward
with a stale, unverified pass/fail verdict. Concretely: removing "Check
additional and optional covers" correctly drops 2 of the AAMI build's
original 5 validation cases — visible, not hidden.

**What this doesn't solve:** the change-log file has to be hand-authored
today after a live approval (see `docs/process-map-snapshots/README.md`) —
there's no "commit this approved edit to the repo" button yet. Revisit if
approvals become frequent enough that manual authoring is a bottleneck.
