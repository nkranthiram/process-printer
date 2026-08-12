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
| 22 | Light theme overhaul (frontend) | none | done | 30/30 frontend tests still pass, tsc clean, build clean | `docs/evidence/22-ui-overhaul-and-versioning.md` |
| 23 | Process map layout fix: client-side layered auto-layout replaces cramped backend grid positions | none | done | 5/5 new layout.test.ts, red-before-green not needed (new logic, tests passed first run) | `frontend/src/layout.ts`, `frontend/src/layout.test.ts` |
| 24 | Backend: `ChangeRequest` model + `versioning.py` (apply approved change as a new immutable `ProcessMapVersion`) | 22 (parallel) | done | 6/6 pytest, red-before-green proven on a real task-id-collision bug caught before running | `docs/evidence/22-ui-overhaul-and-versioning.md` |
| 25 | Chatbot rescoped: refuses coverage questions (in code, before any LLM call), routes "explain" vs "change request" | 24 | done | 22 pytest (chat scope) + 68/68 full backend suite; red-before-green proven on a real classification gap | `docs/evidence/22-ui-overhaul-and-versioning.md` |
| 26 | API: change-request approve/reject, issue PATCH feedback endpoint, process-map version history endpoint | 24, 25 | done | 68/68 backend suite (incl. 6 new live-HTTP tests) | `docs/evidence/22-ui-overhaul-and-versioning.md` |
| 27 | Frontend: FeedbackPanel (issue BPA feedback/resolve) + ChangeRequestsPanel (approve/reject) + version history badge | 22, 26 | done | 30/30 frontend tests (5 new IssuesPanel, 5 new ChangeRequestsPanel, App.test.tsx updated) | `docs/evidence/22-ui-overhaul-and-versioning.md` |
| 28 | Live end-to-end verification against the real running app + real LLM key | 22-27 | done | manual curl walkthrough: coverage question refused, change request drafted+approved live creating v2 with a task genuinely removed, issue feedback PATCH confirmed | `docs/evidence/22-ui-overhaul-and-versioning.md` |
| 29 | Claude/GPT debate: consolidated "Review & Apply Changes" batch feedback design (versioning granularity, consolidation mechanism, dispute loop) | 28 | done | n/a (design debate, 2 rounds) | delivered in chat |
| 30 | Backend: `ReviewSession`/`DraftChangeItem` models, `versioning.apply_change_set` (N edits -> 1 version, atomic), `review_session.py` consolidation pipeline | 29 | done | 15/15 pytest (9 versioning incl. 3 new batch tests, 6 review_session), 2 real red-before-green proofs | `docs/evidence/29-30-review-apply-changes.md` |
| 31 | API: consolidate / current / PATCH item / confirm / discard endpoints for review sessions | 30 | done | 84/84 full backend suite (7 new live-HTTP tests incl. stale-HEAD 409 check) | `docs/evidence/29-30-review-apply-changes.md` |
| 32 | Frontend: "Review & Apply Changes" button (ChatPanel) + `ReviewSessionPanel` (item-level approve/reject/edit, confirm/discard) | 31 | done | 37/37 frontend tests (5 new ReviewSessionPanel, 2 new ChatPanel), tsc clean, build clean | `docs/evidence/29-30-review-apply-changes.md` |
| 33 | Live end-to-end verification: real 5-turn transcript, real LLM consolidation, 2-item batch approved and confirmed as exactly ONE version | 30-32 | done | live curl walkthrough against real running server + real ANTHROPIC_API_KEY | `docs/evidence/29-30-review-apply-changes.md` |
| 34 | Committed change-log replay: approved BPA edits (v2+) now reproducible from a clean clone/DB, not just a local gitignored `.db` file. New `app/pipeline/change_log.py`, `backend/data/change_log/0001_*.json` (the real, already-approved AAMI edit), wired into `seed_aami()`. Also fixed a real, pre-existing gap this surfaced: `ValidationCase`s are now carried forward across a version only if their traced path is still fully intact (dropped + named in `change_summary` otherwise) | 33 | done | 88/88 full backend suite (4 new change_log tests); 2 genuine red-before-green catches: an autoflush bug (SessionLocal is `autoflush=False`) and a synthetic-test-fixture realism gap; live-verified against a freshly reseeded real DB + running server | `docs/process-map-snapshots/README.md`, this file |
| 35 | New feature: **agentic workflow synthesis**, per `docs/agentic-workflow-design.md` (Claude/GPT-debated design). New `agentic-workflow-synthesis` skill (Q1-Q3 node classification test + full §3 field-set contract + escalation-scoping/grounding/calibration non-negotiables). New `AgenticWorkflowVersion`/`Node`/`Edge` models (versioned against the exact `ProcessMapVersion` it was generated from). New `app/pipeline/agentic_workflow.py` loader + validator (escalation-scoping rule enforced structurally, dual grounding checks required, calibration metadata required on every `agent_escalation` node, `claim_refs` resolve to real claim subjects). AAMI seed: `backend/data/aami_agentic_workflow.json`, 16 nodes / 29 edges transcribed from the design doc's own debate-vetted §5/§9 worked example, wired into `seed_aami()`. New `GET /api/documents/{id}/agentic-workflow` endpoint + new "Agentic workflow" frontend tab (`AgenticWorkflowPanel`) | 34 | done | 99/99 backend (9 new agentic_workflow tests incl. 6 red-before-green validator-catches-real-violations tests + 2 new live-HTTP tests); 44/44 frontend (5 new AgenticWorkflowPanel + 2 new App.test.tsx); tsc clean, build clean; live-verified against a freshly reseeded real DB + running server (16 nodes/29 edges served, real citations resolved e.g. `driver_impairment`) | `docs/process-map-snapshots/v2-agentic-workflow.json`, this file |
| 36 | Genericized `agentic-workflow-synthesis` skill: rewrote `SKILL.md` (overwritten, not versioned separately per user request) to remove insurance/AAMI-specific framing from the method itself — non-negotiables, escalation-scoping rule, anti-patterns, and fallbacks now stated in domain-neutral terms, with AAMI/insurance kept only as one labeled worked example. No code changes needed: `app/pipeline/agentic_workflow.py`'s validator was already domain-agnostic (validates `claim_refs` against whatever claim set is supplied at runtime, no hardcoded vocabulary) — confirmed by inspection before editing rather than assumed. `RESOLVER.md` entry unchanged (was already domain-neutral) | 35 | done | doc-only change; verified by reading `app/pipeline/agentic_workflow.py` to confirm no domain-specific logic contradicts the now-generic skill description | this file |
| 37 | Genericized `docs/agentic-workflow-design.md` (overwritten in place, per user request): restructured so §1-§8 and §11 are pure domain-neutral method (examples bracketed/generalized, Maestro-specific references clearly scoped as "if targeting Maestro"), and the entire AAMI worked example (diagram, task descriptions, insurance-specific pitfalls) consolidated into one clearly-labeled §9 "Worked example: AAMI Comprehensive Car Insurance" — explicitly marked as one instance of the method, not the method itself. Old §5 (AAMI diagram) and §10 (insurance-specific pitfalls) left as renumbering placeholders pointing to their new home in §9, so external §-number references elsewhere in the repo don't silently break. Updated the one internal cross-reference in `skills/agentic-workflow-synthesis/SKILL.md` (`§5/§9` → `§9`) | 36 | done | doc-only change; grepped repo for all `agentic-workflow-design.md` cross-references first (`architecture.md`, `PROGRESS.md`, the skill file) and confirmed/fixed each one after the rewrite rather than assuming none existed | this file |
| 38 | New skill: **`workflow-alignment-testing`** — verifies a generated `AgenticWorkflowVersion` stays faithful to the `ProcessMapVersion` it was derived from via three checks (coverage: every source task represented by ≥1 node; description/citation alignment: mechanical claim-scope diff + judgment read per source-task group; outcome equivalence: reuse existing `ValidationCase`s, trace through both artifacts, compare under an explicitly stated terminal-category mapping). Defines the versioned report artifact contract (`docs/workflow-alignment-reports/*.md`, one new dated file per run, never overwritten) + added the index `README.md` there. Wired `agentic-workflow-synthesis/SKILL.md` to reference it: new non-negotiable ("generating/regenerating a workflow is not done until tested") + new "Testing" section pointing to this skill, so the agent runs it automatically after producing a workflow. Updated `RESOLVER.md` table + chain diagram | 37 | done | skill-only artifact, per user's explicit scope (create the testing skill + wire the reference) — no test-runner code/automation built yet, named as the natural next step, not silently assumed done | this file |
| 39 | Frontend: rebuilt the "Agentic workflow" tab from a flat scrolling card list into an actual BPMN-style graph — `AgenticWorkflowGraphView` (React Flow, reuses the layered auto-layout, edge coloring surfaces the escalation-scoping rule visually) + `AgenticWorkflowGraphNode` + `AgenticNodeDetailPanel` (click-through spec: decision logic, both grounding checks, calibration metadata, inputs/outputs, downstream edges, citations, raw JSON). `layout.ts` generalized (`computeLayeredLayoutGeneric` + `computeAgenticWorkflowLayout` wrapper) so both graphs share one proven algorithm instead of a second divergent one | 35 | done | 55/55 frontend tests (10 new: AgenticWorkflowPanel rewritten, new AgenticNodeDetailPanel suite, new computeAgenticWorkflowLayout suite); real red-before-green caught 2 genuine failures (multi-element `getByText` ambiguity, missing citation subject in detail panel) before green; tsc clean; build clean | this file |
| 40 | Ran `workflow-alignment-testing` for real against the live AAMI v2 process map + agentic workflow (same `process_map_version_id`, confirmed programmatically) — first real exercise of that skill, not just its own creation. **Verdict: `misaligned`.** Found 2 real coverage gaps ("Verify the claim is adequately evidenced" and "Determine at-fault status and applicable excess" have zero derived nodes), 2 citation-scope violations traced directly to those gaps (excess claims folded into the wrong node; `AG-03` still cites claims from "Check additional and optional covers", a task removed in the v2 edit — stale workflow-spec drift), and a structural finding from writing the outcome-equivalence mapping down explicitly: `GW-02` has no path for an agent-screened exclusion to auto-decline, so 2 of 3 live regression scenarios diverge from the process map's literal auto-decline path | 39 | done | full report with coverage table, citation-scope table, stated equivalence mapping, and scenario table | `docs/workflow-alignment-reports/aami-comprehensive-car-insurance__pm-v2__wf-manual-agent-pass-v1__2026-08-12.md` |
| 41 | Redesigned the agentic workflow graph per user feedback ("too much scrolling... take inspiration from Camunda/UiPath/n8n"): switched `layout.ts` to support a left-to-right orientation (`computeAgenticWorkflowLayout` now horizontal, compact spacing) alongside the process map's existing top-to-bottom one (`computeLayeredLayout`, unchanged) via one shared generic algorithm. Rebuilt `AgenticWorkflowGraphNode` as a compact icon-first card (no goal/citation-summary text on-node — moved entirely to the click-through detail panel) with gateway nodes rendered as BPMN-style diamonds. `AgenticWorkflowGraphView` now uses smoothstep (right-angle) edges and a MiniMap, matching Camunda/n8n/UiPath's diagram conventions | 39 | done | 56/56 frontend tests (layout tests updated for the new horizontal-axis assertions + 1 new fan-out case); tsc clean; build clean | this file |
| 42 | **Reverted task 41** per user feedback — the horizontal/compact redesign made scrolling worse, not better ("edges too long spanning across several pages"). Restored `layout.ts`, `layout.test.ts`, `AgenticWorkflowGraphNode.tsx`, `AgenticWorkflowGraphView.tsx` to their exact task-39/40 content (verified byte-identical production build output — same asset hashes — as proof, not just visual similarity). Neither graph layout approach has actually solved the user's original visual-appeal/scrolling complaint yet; this is a clean baseline reset, not a fix — open for a different approach next (e.g. a real force/dagre-style auto-layout library instead of the hand-rolled layered one, or reconsidering whether a full 16-node graph should render at once vs. progressive disclosure) | 41 | done | 55/55 frontend tests (back to the exact pre-task-41 count); tsc clean; build clean (identical asset hashes to task 39/40's build) | this file |
| 43 | **Root-caused the actual bug** (user attached a screenshot showing a couple of absurdly long edges spanning the whole canvas). Confirmed via direct simulation against real data: the hand-rolled longest-path-relaxation layout algorithm has no cycle handling, and the agentic workflow contains a genuine cycle (`HUM-01 <-> HUM-02`, `BR-01 <-> HUM-01` — the human escalation/request-more-info loop, real data not a bug). Rank blew up to **94** for a 16-node graph that should be ~8 ranks deep — that's the "edges spanning several pages," present since task 39 regardless of orientation. Replaced the hand-rolled algorithm with **`dagre`** (proper feedback-arc-set cycle breaking before ranking — same class of algorithm Camunda/n8n/UiPath use). `computeLayeredLayout` (process map, unchanged top-to-bottom) and `computeAgenticWorkflowLayout` (agentic workflow, now left-to-right per explicit user request) are both thin wrappers around one shared `computeDagreLayout` helper. Reinstated the compact icon-first node design + BPMN diamond gateways from task 41 (that part was reasonable design, just undermined by the layout bug regardless of node styling) | 42 | done | 57/57 frontend tests (2 new: a synthetic-cycle regression test asserting bounded rank spread, a fan-out check); tsc clean; build clean; verified against real production data directly (dagre run on the actual 16-node/29-edge AAMI workflow — `GW-01` now sits immediately after `BR-01`, not blown out to rank 81+) | `architecture.md` "replaced the hand-rolled graph layout with dagre" |
| 44 | New Claude/GPT debate (2 rounds) on persona mining at LOW data volume (a couple hundred claims, not thousands) — `docs/persona-mining-design.md`'s original design assumed thousands and leaned on HDBSCAN + PSI/KL train-holdout validation, both unreliable/meaningless at N=20-40 actor-instances per role. Converged on: LLM+SME synthesis over evidence packs as the PRIMARY discovery mechanism (not clustering — a real, debated reversal from round 0's initial position that hierarchical clustering should be primary), with clustering demoted to a mandatory falsification/veto check on the SME's *cited* distinguishing dimensions, never an arbiter of cluster count; leave-one-claim-family-out review + mandatory SME sign-off + independent-claim-family support counts (not raw instance counts, which are gameable) replacing PSI/KL; mode selected PER ROLE on claim-family count (not per corpus), with mixed-mode corpora as the expected normal case; same ontology/schema/non-negotiables, plus new required honesty fields (`data_volume_regime`, `supporting_claim_families`, a capped `approved_low_confidence` validation-status ceiling, `confidence_note`). Written up as new §5 "Low-volume mode" in `docs/persona-mining-design.md` (delta against §2/§2.7, not a separate doc), plus 2 new Appendix open items | none (design doc only) | done | debate transcript reviewed for internal consistency before writing; doc-only change, no code | `docs/persona-mining-design.md` §5 |

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
