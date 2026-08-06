# Process Printer — Build Progress

Source of truth for build status. Updated after each task completes — don't rely on
chat history for current state, rely on this file. See `architecture.md` for design
decisions and `../DECISIONS.md` for anything promoted to the parent repo.

Legend: `todo` · `in_progress` · `blocked` · `done`

| # | Task | Order dependency | Status | Tests | Evidence |
|---|---|---|---|---|---|
| 1 | Scaffold repo structure + architecture.md skeleton + this tracker | none | done | n/a | this file, architecture.md |
| 2 | Backend data model (SQLAlchemy models + unit tests) | 1 | done | 4/4 pass, red-before-green proven | `docs/evidence/02-data-model.md` |
| 3 | `pdf-ingestion` skill + module, run on AAMI PDS | 2 | done | 4/4 pass, red-before-green, real 76pg PDF | `docs/evidence/03-pdf-ingestion.md` |
| 4 | `claim-extraction` skill + module + pluggable LLM client; manual extraction pass on AAMI PDS | 3 | done | 4/4 pass, 35/35 claims citation-verified | `docs/evidence/04-claim-extraction.md` |
| 5 | `process-map-synthesis` skill + module: claims → task-level DAG | 4 | done | 7/7 pass, 3 real bugs caught+fixed | `docs/evidence/05-process-map-synthesis.md` |
| 6 | `task-description-authoring` skill: task descriptions + citations | 5 | done (folded into task 5 — descriptions authored alongside each task node) | n/a | `data/aami_process_map.json` |
| 7 | `gap-ambiguity-logging` skill: issue log from AAMI extraction | 4 | done | 5/5 pass | `docs/evidence/07-gap-ambiguity-logging.md` |
| 8 | Backend API layer (FastAPI routes) | 2–7 | done | 34/34 pass + live-server curl smoke test | `docs/evidence/08-backend-api-and-seed.md` |
| 9 | Chatbot endpoint grounded in generated map/claims | 8 | done (built alongside task 8) | covered by test_api.py chat tests | n/a |
| 10 | Frontend scaffold (Vite+React+TS+Tailwind) + design system | none (parallel to 2–9) | done | tsc clean, build clean | `docs/evidence/10-12-frontend.md` |
| 11 | Frontend: process map view + task detail panel w/ citations | 8, 10 | done | 7/7 component tests | `docs/evidence/10-12-frontend.md` |
| 12 | Frontend: issues/gaps panel + chatbot panel | 8, 9, 10 | done | 6/6 component tests | `docs/evidence/10-12-frontend.md` |
| 13 | `scenario-validation` skill + 5 real claim scenarios traced through AAMI map | 6, 7 | done | 6/6 pass, 41/41 backend suite, live-verified | `docs/evidence/13-scenario-validation.md` |
| 14 | Backend tests run, output captured | 2–9 | done | 41/41 pass | throughout docs/evidence/*.md |
| 15 | Frontend tests run, output captured | 10–12 | done | 17/17 pass | `docs/evidence/10-12-frontend.md` |
| 16 | End-to-end manual verification pass (red-before-green) + evidence doc | 11–15 | done | 41 backend + 17 frontend, live endpoint sweep | this file + all docs/evidence/*.md |
| 17 | `architecture.md` finalized + `DECISIONS.md` entries | ongoing | done | n/a | `architecture.md`, `../DECISIONS.md` |
| 18 | Final walkthrough summary for user | all | done | n/a | delivered in chat |
| 19 | `text-ingestion` skill: plain-text (non-PDF) ingestion, generalizes `pdf-ingestion` | none (parallel to 20) | done (skill authored; module implementation not yet built/tested — see notes) | not yet run | `skills/text-ingestion/SKILL.md` |
| 20 | `cross-document-reconciliation` skill: cluster + classify claims across 2+ documents (duplicate/contradiction/supersession/etc.) | none (parallel to 19) | done (skill authored; module implementation not yet built/tested — see notes) | not yet run | `skills/cross-document-reconciliation/SKILL.md` |
| 21 | `process-printer` master skill: routes to all 8 stage skills, branch rules, cross-cutting non-negotiables | 19, 20 | done | n/a (routing doc, not code) | `skills/process-printer/SKILL.md`, `skills/RESOLVER.md` updated |

## Notes / constraints on record

- **Tasks 19–21 (2026-08-06)**: authored as `SKILL.md` procedure/contract documents
  only, per user request — no backend module code was written or tested for
  `text-ingestion` or `cross-document-reconciliation` yet. `cross-document-reconciliation`'s
  SKILL.md explicitly flags a real schema gap it depends on: `Issue.issue_type`
  currently only recognizes `gap | ambiguity | low_confidence_extraction`, and
  `Issue.document_id` is a single FK — neither supports a multi-document
  reconciliation finding cleanly yet. That's a schema change for whenever these
  two skills get implemented against real multi-document input, not done here.

- No `ANTHROPIC_API_KEY` configured in this sandbox as of task start. Automated
  extraction pipeline (task 4) is built to call a real LLM when a key is present;
  for this build the extraction pass on the AAMI PDS was performed by the agent
  directly and tagged `extractor_version: manual-agent-pass-v1` in provenance —
  not the automated pipeline. Re-run with a key to get a fresh automated pass.
- Scope: this app produces the **process map + task descriptions for human review**
  (BPAs / claims handlers). It does not build or run an automated claim-decisioning
  agent — that's explicitly out of scope per user instruction.
- Source document: `docs/aami-comprehensive-car-insurance-pds.pdf` (parent folder's
  `docs/`, not this app's `docs/` — this app's `docs/` holds generated
  architecture/evidence docs only).

## Changelog

- Task 1 done: repo scaffolded (`backend/`, `frontend/`, `skills/`, `docs/evidence/`),
  `architecture.md` written with stack decisions + the no-API-key constraint disclosed.
- Task 2 done: SQLAlchemy models for DocumentVersion, SourceSpan, AtomicClaim,
  ProcessMapVersion/Task/Edge, Issue, ValidationCase. 4 pytest tests, red-before-green
  proven (broke a real field, watched the specific test fail, restored, watched it
  pass). See docs/evidence/02-data-model.md.
- Task 3 done: pdf-ingestion skill (moved to correct project-local skills dir after
  an initial filing mistake — caught and fixed same session) + PyMuPDF-based module.
  Ran on the real 76-page AAMI PDF: 461 spans, 0 failed pages. Known limitation
  disclosed: section_path heading detection is imperfect on some pages; page+quote
  citation accuracy unaffected. See docs/evidence/03-pdf-ingestion.md.
- Task 4 done: claim-extraction skill, pluggable LLMClient (Anthropic, ready for a
  future keyed run) + manual-pass loader. 35 claims extracted from AAMI PDS, every
  raw_quote sliced from real parsed spans (not hand-typed). Built a mechanical
  citation verifier and proved it catches both a fabricated quote and a
  right-quote-wrong-page error, kept as permanent regression tests. 35/35 claims
  verified. See docs/evidence/04-claim-extraction.md.
- Task 5 done: process-map-synthesis skill + validator module (node-type check,
  dangling-claim-ref check, DAG structure check — acyclic/single-root/terminal-leaves).
  11-task DAG built for AAMI coverage determination. Tests caught 3 real bugs
  (subject-name mismatch, an under-cited task, a blind spot in cycle detection
  itself) — all fixed in-session. 19/19 tests passing overall. See
  docs/evidence/05-process-map-synthesis.md.
- Task 6 done alongside task 5: task-description-authoring skill written; every
  task's `description` field authored per its contract (plain-language, claim-
  grounded, citations available via claim_refs rather than inline).
- Task 7 done: gap-ambiguity-logging skill + 7 real issues logged (2 gaps, 5
  ambiguities) from the AAMI extraction, each linked to the task/claims it affects.
  24/24 tests passing overall. See docs/evidence/07-gap-ambiguity-logging.md.
- Task 8 done: seed pipeline (ingest→extract→synthesize→issues into a real DB,
  idempotent on re-run) + FastAPI routes (documents, process-map, issues, chat) +
  Pydantic schemas. Found and fixed a real test-isolation bug (double-Base mismatch)
  along the way. 34/34 backend tests pass; also smoke-tested against a live running
  uvicorn server with real curl requests (not just TestClient) per verification.md.
  See docs/evidence/08-backend-api-and-seed.md.
- Task 9 done alongside task 8: retrieval-based chatbot (keyword-overlap over
  tasks+claims), honestly labeled `mode: retrieval_only` since no ANTHROPIC_API_KEY
  is configured in this sandbox; a real `llm_grounded` path is implemented and used
  automatically if a key is ever set. Verified live via curl.
- Tasks 10–12 done together (frontend scaffold + process map view + task detail
  panel w/ click-to-expand citations + issues panel + chat panel). Vite+React+TS+
  Tailwind v4+React Flow+Vitest/RTL. Caught and fixed 2 real bugs: jsdom missing
  ResizeObserver (React Flow dependency) and a tsconfig-dependent @ts-expect-error
  that failed the PRODUCTION build though tests passed — fixed by switching to a
  type cast; re-verified both test suite and production build green afterward.
  14/14 frontend tests pass. Live-verified against the real running backend (not
  mocks): API response JSON diffed field-by-field against the TS types, matches
  exactly. Disclosed gap: real-browser visual verification wasn't possible in this
  sandbox (loopback navigation blocked) — named explicitly, not glossed over. See
  docs/evidence/10-12-frontend.md.
- Task 13 done: scenario-validation skill + 5 scenarios (2 covered, 2 excluded, 1
  escalated to human review — deliberately not all happy-path) traced through the
  real DAG, mechanically checked against real edges/start/terminal nodes. Persisted
  via seed.py, served via new /validation-cases endpoint, surfaced in a 4th
  frontend tab. Live-verified via curl against the running server. 41/41 backend,
  17/17 frontend tests passing. See docs/evidence/13-scenario-validation.md.
- Tasks 14–15 done as a byproduct of every prior task (tests run and evidence
  captured throughout, not deferred to the end).
- Task 16 done: full-suite final run (41 backend + 17 frontend tests, all green)
  plus a live HTTP sweep of every endpoint against the running server incl. a 404
  check on an unknown document id.
- Task 17 done: architecture.md finalized with implemented API surface, frontend
  structure, and 2 open-decisions-log entries (test-isolation strategy, manual-
  extraction-pass rationale) plus a named "what's next" list. DECISIONS.md in the
  parent ways-of-working repo updated with a no-promotion-yet entry per
  harvesting.md.
- Task 18 done: final summary delivered.

**BUILD COMPLETE — all 18 tasks done.** 41/41 backend tests, 17/17 frontend tests,
live server verified. See chat for the walkthrough summary.
