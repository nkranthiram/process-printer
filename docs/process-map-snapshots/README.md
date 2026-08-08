# Process map snapshots

This folder answers one question durably: **"what does the process map
actually look like right now, and is that reproducible from a clean clone?"**

## The two things committed here

1. **`v2-current-process-map.json`** / **`version-history.json`** — a
   point-in-time export of the live API's `/process-map` and
   `/process-map/versions` responses, taken and committed as human-readable
   evidence. Task/edge/version **ids in these files are runtime-generated
   UUIDs and will differ on your own machine** — don't diff on ids, diff on
   `title`/`description`/`change_summary`/structure. This file is a snapshot,
   not the reproduction mechanism.

2. **`backend/data/change_log/*.json`** (the actual source of truth for
   reproducibility) — the committed, ordered log of every BPA-approved edit
   that has ever been applied to the AAMI process map, referencing tasks by
   their stable **title**, not a database row id (row ids are regenerated on
   every fresh seed — see `backend/app/pipeline/change_log.py` for why).

## How this stays true after a fresh clone

Before this change, the app only had one seed path: `seed_aami()` built **v1**
(the raw extraction) every time, and any approved BPA edits made through the
chatbot/review-session flow lived only in that machine's local, gitignored
SQLite file. Clone the repo fresh, and v2+ was gone — versioning existed as a
*mechanism* but the actual versioned *data* wasn't durable.

Now, `seed_aami()`:
1. Builds v1 exactly as before (manual-agent-pass extraction of the AAMI PDS).
2. Calls `apply_change_log()`, which replays every file in
   `backend/data/change_log/`, in filename order, through the exact same
   `apply_change_set()` engine the live chatbot review-session flow uses —
   so replay and a real live approval produce identical version semantics
   (one committed version per approved change set, atomic, DAG-validated,
   never mutates the version it's built from).

Result: **any fresh clone + fresh DB reproduces the full v1 → v2 → ... history
automatically**, because the history is data committed to the repo, not
something that only ever existed in a chatbot conversation on one laptop.

## What happens to validation cases across a version

A `ValidationCase` (traced claim scenario) is only carried forward into a new
version if every task on its traced path still exists after the edit. If an
edit removes a task a scenario walked through, that scenario is **not**
silently carried forward with its old pass/fail verdict (that would
misrepresent something never actually re-traced) — it's dropped, and the
drop is named in the new version's `change_summary` field. Concretely, in the
committed `0001_*.json` change-log entry: removing "Check additional and
optional covers" correctly drops 2 of the original 5 AAMI validation cases,
visible in `version-history.json`'s v2 `change_summary`. Re-tracing a dropped
scenario against the new map is a manual step — see
`skills/scenario-validation/SKILL.md`.

## Adding a new approved edit to the committed history

When a BPA approves a change through the live app (per-message or the
"Review & Apply Changes" batch flow), that change is real and persisted for
that running instance — but per the above, it will not survive a fresh clone
unless it's also written as a change-log file:

1. Note the approved edit's `change_type` and `payload` (visible in the
   ChangeRequest/DraftChangeItem record, or the resulting version's
   `change_summary`).
2. Add a new `backend/data/change_log/000N_<description>.json` file,
   following the existing `0001_*.json` as a template — reference tasks by
   `task_title` / `after_task_title` / `edge_from_title` / `edge_to_title`,
   never by database id.
3. Re-run the backend test suite (`pytest tests/test_change_log.py
   tests/test_seed.py`) to confirm the new entry replays cleanly against the
   real AAMI structure before committing.
4. Re-export this snapshot (`GET /api/documents/{id}/process-map` and
   `.../process-map/versions`) and overwrite the two JSON files here.

This is a manual step by design, not automatic on every approval — automatic
would mean every live chatbot experiment gets permanently written into repo
history, including ones a BPA later rejects or revises.
