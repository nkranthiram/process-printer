# Evidence: "Review & Apply Changes" consolidated feedback flow (tasks 29–33)

Date: 2026-08-06

## Design origin

Built directly from a 2-round claude/gpt debate on: (1) whether to layer this
on top of the existing per-message ChangeRequest flow or replace it — both
agreed **layer, don't replace**; (2) whether consolidation should be
incremental or a cold transcript re-read — both converged on **incremental
where possible, reconciliation pass at review time**; (3) versioning
granularity — this was the real disagreement, resolved over 2 rounds to:
**one committed version per human-approved set of edits, of any size** (not
one-version-per-edit, not one-opaque-version-per-whole-session). Full debate
transcript is in the conversation history; the resolution is implemented here.

## What was built

- **`ReviewSession` / `DraftChangeItem` models** — a session accumulates draft
  items; nothing is applied to the process map until explicit confirm.
- **`versioning.py` refactored**: extracted `_apply_single_change` (pure,
  operates on an in-memory `ProcessMapDraft`, validates after each mutation)
  from the existing `apply_change`. Added `apply_change_set`: applies N edits
  sequentially to one in-memory draft, and only persists **once**, as one new
  `ProcessMapVersion`, if every edit in the set validates — if any edit fails,
  nothing is written to the database at all, and the caller learns exactly
  which item failed via `ChangeApplyError.item_id`.
- **`review_session.py`**: `consolidate_transcript` runs an LLM reconciliation
  pass over the supplied transcript + already-drafted items for the session,
  producing grounded, citable items (`source_message_refs`) or
  `needs_clarification` for anything ambiguous — never a guess. No-LLM-key
  fallback is deliberately conservative (flags feedback-shaped messages as
  `needs_clarification`, never fabricates structure).
- **API**: `POST .../review-sessions/consolidate`, `GET .../current`,
  `PATCH .../items/{id}` (approve/reject/edit — BPA edits tagged
  `human_override=True`), `POST .../confirm` (applies approved items as one
  version; refuses with 409 if HEAD moved since the session was pinned),
  `POST .../discard`.
- **Frontend**: "Review & Apply Changes" button in `ChatPanel` (disabled until
  there's at least one turn), `ReviewSessionPanel` modal — per-item
  approve/reject/edit, confirm shows a live count of approved items, discard
  abandons the session without touching the map.

## Red-before-green proofs

1. **Batch atomicity** (`test_change_set_applies_multiple_edits_as_exactly_one_version`
   + a dedicated regression): deliberately reintroduced a "persist after every
   edit" bug into `apply_change_set` — the atomicity test failed exactly as
   predicted (4 versions instead of 2). Reverted, reran: 9/9 versioning tests
   pass. This is the mechanism that makes "one version per approved batch"
   real rather than aspirational.
2. **Supersede mechanic** (`test_superseded_item_is_kept_not_deleted`):
   deliberately removed the line that marks an old item `status="superseded"`
   when a new item supersedes it — test failed (`'draft' == 'superseded'`).
   Reverted, reran: 6/6 review_session tests pass.

## Test counts

- Backend: **84/84** pytest (9 versioning incl. 3 new batch-apply tests, 6
  new review_session pipeline tests, 7 new live-HTTP API tests including the
  stale-HEAD-refusal 409 check).
- Frontend: **37/37** vitest (5 new `ReviewSessionPanel.test.tsx`, 2 new
  `ChatPanel.test.tsx` for the button/consolidate flow).
- `tsc --noEmit` clean on both app and test tsconfig; production build clean.

## Live end-to-end verification (real server, real ANTHROPIC_API_KEY)

Ran a realistic 5-turn conversation through the real running backend:

1. Turns 1–2 were a pure "why" explanation (not a change request).
2. Turn 3 asked to remove the "additional and optional covers" step.
3. Turn 5 asked to add an identity-verification step after claim capture.
4. `POST .../consolidate` with all 5 turns → the LLM correctly extracted
   **exactly 2 items**, correctly ignored the explanatory turns, correctly
   resolved both anchor task ids from the live process map context, with
   accurate `source_message_refs` (`["turn-3"]`, `["turn-5"]`).
5. Approved both items via `PATCH .../items/{id}`.
6. `POST .../confirm` → **exactly one** new version (v1 → v2), containing
   both edits (`Removed step "Check additional and optional covers"; Added
   step "Verify policyholder identity..."`), `changed_by: "bpa via review
   session"`. Task count net-neutral (11 → 11: one removed, one added) —
   confirmed by listing tasks before/after.
7. `GET .../current` after confirm → `null`, confirming the session is
   correctly no longer surfaced as open/reconciled.
8. Full backend suite re-run with the real key present: still 84/84.

## Disclosed limitations (not glossed over)

- **No server-side chat transcript persistence.** The chat endpoint remains
  stateless per-message; the frontend accumulates `turns` in React state and
  supplies the full transcript to `/consolidate` on button click. This means
  the "incremental" half of the debate's conclusion is only partially
  realized — the consolidation call itself does a full-transcript
  reconciliation pass each time (grounded and citation-checked, but not a
  true per-turn incremental update). Noted as a named follow-up in
  architecture.md, not silently different from the design.
- **No dependency-aware clustering.** Two coupled edits (e.g. a rename plus
  the edge label that references it) are applied independently in
  `apply_change_set`, in item order, with no detection that they're related.
  If one fails, the other may still apply, which the debate flagged as a risk
  worth watching. Not built this round.
- **The old per-message `ChangeRequest` flow is untouched and still live** —
  a single terse message like "remove the exclusions step" still
  immediately creates a pending `ChangeRequest` in the Feedback tab via that
  path, independent of whatever's accumulating in an open `ReviewSession`.
  This is intentional (layer, don't replace, per the debate) but means the
  same feedback could in principle surface through both paths if a BPA uses
  both chat behaviors in one conversation — not deduplicated across the two
  systems.
- **`needs_clarification` items require a manual edit to become approvable**
  — verified live in the no-LLM-key heuristic path; the item-level "Edit"
  action in `ReviewSessionPanel` is how a human resolves this, tested via
  `test_update_draft_item_approve_and_confirm_applies_one_version`.
