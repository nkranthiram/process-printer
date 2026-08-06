---
name: process-printer
description: Turn one or more source documents (PDF or plain text) into a tested,
  citable, task-level process map with task descriptions and a gap/contradiction
  log, for a claims-handler/BPA audience. Use for "build a process map from these
  documents", "run process printing", "turn this policy into a process map",
  "what's the process for determining X from these documents". Entry point — reads
  this first, then routes to the individual stage skills.
---

# Process Printer

The master/router skill for this project. If you only read one file before starting
a document-to-process-map build, read this one — it tells you which stage skill to
start at, when to branch, and the rules that hold across every stage. Each stage's
own `SKILL.md` has the real procedural detail; this file is the map of the map, not
a duplicate of it.

## What this produces

A `ProcessTask`/`ProcessEdge` DAG (task-level, not clause-level — walkable by a
claims handler), one task description per node, and an `Issue` log of everything
the source document(s) don't resolve or disagree on — every task, claim, and issue
citable back to an exact quote in a source document. See `architecture.md` and
`PROGRESS.md` at the app root for the concrete data model and current build state.

## Step 1 — pick the ingestion entry point

| Input | Start at |
|---|---|
| One or more PDF files | `pdf-ingestion/SKILL.md` |
| Raw/pasted text, no PDF | `text-ingestion/SKILL.md` |

Both stages produce the same output shape (citable `SourceSpan`s) — everything
downstream is identical regardless of which one ran.

## Step 2 — extract claims, per document, independently

`claim-extraction/SKILL.md` — always run once per document, never across
documents at this stage. Scope extraction to the process being mapped (e.g.
"claim coverage determination"), not an exhaustive extraction of the whole
document.

## Step 3 — branch: single document vs. multiple documents

| Documents in this run | Do |
|---|---|
| **One** document | Skip straight to Step 4 — there is nothing to reconcile. |
| **Two or more** documents | Run `cross-document-reconciliation/SKILL.md` first. This is the stage the original single-document AAMI build never exercised — it clusters claims across documents and classifies each cluster (duplicate / consistent / contradiction / exception-hierarchy / scope-difference / definition-mismatch / supersession) before anything gets synthesized into a map. Only clean duplicates and deterministically-resolved supersessions feed a single claim forward; everything else becomes a logged issue, not a silent pick. |

## Step 4 — synthesize the process map

`process-map-synthesis/SKILL.md` — group claims (post-reconciliation, if that
stage ran) into a small number of task nodes and edges. Task-level granularity,
readable by a claims handler in one sitting — this is the single easiest stage to
over-build into a clause-by-clause decision tree; don't.

## Step 5 — write task descriptions

`task-description-authoring/SKILL.md` — one handler-facing description per task
node, grounded in its linked claims, citations available on click rather than
inline in the prose (per this project's UI convention).

## Step 6 — log everything unresolved (runs throughout, not just at the end)

`gap-ambiguity-logging/SKILL.md` — every gap, ambiguity, low-confidence
extraction, or (if Step 3 ran) cross-document classification that wasn't cleanly
resolved becomes an `Issue`. Per this project's standing instruction: log and keep
going, don't pause the build to ask.

## Step 7 — test what was built

`scenario-validation/SKILL.md` — trace realistic scenarios end-to-end through the
finished map and record pass/fail evidence, the same discipline as the AAMI
build's 5 scenarios. Alongside scenario tracing, always also run the two
structural checks proven out in the AAMI build (see `docs/evidence/`):
citation verification (every claim's `raw_quote` is a real substring of its
source) and DAG validity (no cycles, every path terminates in an outcome or an
explicit escalation node). These are cheap, mechanical, and catch a different
class of bug than scenario tracing does — run both, not one or the other.

## Rules that hold across every stage (non-negotiable)

- **Verbatim citations only.** Every claim's `raw_quote` is an exact substring of
  a real source span. A quote that doesn't verify is a fabrication, not an
  extraction — check this programmatically, every run, not by eye.
- **Task-level, not clause-level.** The process map is for a claims handler/BPA to
  walk in one sitting, not a rule-engine-ready decision tree.
- **Log, don't pause.** Gaps, ambiguities, and (per `cross-document-reconciliation`)
  unresolved cross-document conflicts are logged and the build continues; the
  human reviews the log afterward.
- **Never auto-resolve a genuine contradiction.** The only exception is explicit,
  quoted supersession/effective-date language — resolved deterministically and
  transparently, not "because it seems more authoritative."
- **Red-before-green testing.** Prove a check would have caught the broken state
  before trusting it to certify the fix — this applies to citation verification,
  DAG validity, and scenario tracing alike (see `verify-output` skill and this
  repo's `practices/verification.md`).
- **Disclose, don't oversell.** If extraction was done by an agent directly
  (no LLM key configured) rather than an automated model call, tag it
  (`manual-agent-pass-v1`) and say so — never present a manual pass as if it were
  the automated pipeline.

## Chain, end to end

```
                          ┌─ pdf-ingestion ──┐
(source documents) ──────►│                  ├──► claim-extraction (per document)
                          └─ text-ingestion ─┘              │
                                                             │ 1 document        2+ documents
                                                             ▼                        ▼
                                                  process-map-synthesis ◄── cross-document-reconciliation
                                                     │              ↘                   ↘
                                                     ▼            gap-ambiguity-logging (throughout)
                                          task-description-authoring
                                                     │
                                                     ▼
                                          scenario-validation (+ citation & DAG structural checks)
```

## See also

- `RESOLVER.md` in this folder — quick-reference table of every stage skill.
- `architecture.md`, `PROGRESS.md` at the app root — current build state and data
  model this pipeline's output plugs into.
