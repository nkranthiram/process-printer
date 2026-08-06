---
name: cross-document-reconciliation
description: Compare atomic claims extracted from multiple source documents to
  find duplicates, contradictions, supersession, and scope differences before
  synthesizing a process map. Use for "these documents might conflict", "check
  for contradictions across documents", "reconcile multiple sources", "which
  document wins".
---

# Cross-Document Reconciliation

The stage the single-document AAMI build never needed: when claims come from more
than one document, some will restate each other, some will genuinely conflict,
and some will look like conflicts but aren't (one document is just narrower in
scope, or a later document explicitly supersedes an earlier one). This skill turns
a pile of per-document claims into a judgment, per cluster, about which of those
is actually true — without ever silently picking a winner the user didn't sanction.

Runs after `claim-extraction` has produced claims independently for each document,
and before `process-map-synthesis` builds the task DAG. Only relevant when there
are 2+ source documents; skip entirely for a single-document run.

## Contract

- Claims are never compared document-to-document at large (O(n²) LLM calls across
  a whole corpus) — cluster first by subject, then only compare **within** a
  cluster. Clustering, not classification, is what keeps this tractable.
- Every cluster gets exactly one classification: `duplicate` (same claim, restated),
  `consistent` (different claims, no conflict), `true_contradiction` (both claims
  can't be right as stated), `exception_hierarchy` (one is a general rule, the
  other a documented exception to it — not a conflict), `scope_difference`
  (claims apply to different conditions/products/dates and simply don't overlap),
  `definition_mismatch` (same term, different meaning across documents),
  `supersession` (one document explicitly states it overrides/replaces another).
- **Deterministic checks run before any judgment call.** Explicit supersession
  language ("this document replaces...", "effective from... this policy
  supersedes...") and explicit effective-date/version ordering are checked first,
  mechanically, before falling back to semantic classification of the remainder.
  This mirrors the debate-derived design principle: resolve what can be resolved
  cheaply and deterministically before spending judgment on what's left.
- **Nothing is auto-resolved into a single answer**, even a `supersession` finding.
  This skill produces a *classified, evidenced judgment per cluster* — it always
  becomes an `Issue` (or is folded into a claim's provenance if trivially a
  duplicate). Actually picking which claim the process map uses is either (a) the
  deterministic supersession rule applied transparently and logged, or (b) left
  for human review via `gap-ambiguity-logging`'s issue log — never a silent
  same-document-style claim substitution.
- Every reconciliation judgment cites the specific claims (and through them, the
  specific source spans/documents) it compared — same citation discipline as
  every other stage.

## Procedure

1. Normalize claim `subject`/`predicate` terms across all documents in the batch
   (e.g. "windscreen" and "windshield glass" mapped to one canonical subject) —
   without this, clustering silently misses claims that are actually about the
   same thing.
2. Cluster claims by normalized subject using blocking keys (exact/near-exact
   subject match) first; only fall back to broader semantic grouping for claims
   that don't land in any blocking-key cluster, to keep comparison volume bounded.
3. Within each cluster with claims from more than one document, run the
   deterministic pre-pass: scan each claim's source span and surrounding
   section_path/text for explicit supersession or effective-date language. If
   found, classify the cluster `supersession` and record which document/claim
   wins and why (quoting the supersession language itself as evidence — this is
   not a "trust me" resolution).
4. For clusters the deterministic pass didn't resolve, classify: are the claims
   restating each other (`duplicate`), non-overlapping in condition/scope
   (`scope_difference`), a general-rule-plus-documented-exception pair
   (`exception_hierarchy`), the same term meaning different things
   (`definition_mismatch`), or genuinely incompatible as stated
   (`true_contradiction`)?
5. For every cluster that isn't a clean `duplicate` or `consistent`, create an
   `Issue` via `gap-ambiguity-logging`'s contract, tagged with the specific
   classification as `issue_type`, referencing every claim in the cluster via
   `claim_refs`, and naming every source document involved by label — a reviewer
   must be able to see *which* documents disagree and *why* without re-deriving
   it.
6. Only `duplicate` and deterministically-resolved `supersession` clusters feed a
   single claim into `process-map-synthesis`; everything else (`true_contradiction`,
   unresolved parts of `exception_hierarchy`/`scope_difference`/
   `definition_mismatch`) is logged and excluded from the draft map until a human
   resolves it — the map should never quietly pick a side.

## Anti-patterns

| Don't | Do |
|---|---|
| Run O(n²) comparisons across every claim in the corpus | Cluster by subject first, compare only within clusters |
| Treat every cross-document difference as a "contradiction" | Classify with the full taxonomy — most differences are scope/exception/definition, not true conflicts |
| Auto-resolve a contradiction because one document "seems more authoritative" | Only resolve via explicit, quoted supersession/effective-date language — otherwise it's a logged issue, not a resolution |
| Let a resolved `supersession` silently overwrite/delete the losing claim | Keep both claims; record which one the map uses and why, so the trail is auditable |
| Skip reconciliation because "it's probably fine" for a small batch | Run it whenever 2+ documents are present, even for 2 short documents — conflicts are exactly as easy to miss by eye as duplicates |

## Fallbacks

- No LLM available for semantic clustering/classification: fall back to
  exact/near-exact subject-string blocking only, and flag every cluster that
  *might* need semantic grouping but didn't get it as a lower-confidence pass —
  disclosed, not silently skipped (same discipline as `claim-extraction`'s
  `manual-agent-pass-v1` tagging).
- A cluster is genuinely ambiguous even after classification (e.g. supersession
  language exists but is itself unclear about scope): classify it
  `true_contradiction` rather than force-fitting it into `supersession` — a
  false "resolved" is worse than an honest "unresolved."
- Current schema note: the existing `Issue` model's `issue_type` field only
  recognizes `gap | ambiguity | low_confidence_extraction` and `document_id` is a
  single foreign key — using it for a reconciliation finding across multiple
  documents needs either a schema extension (add the reconciliation
  classifications as valid `issue_type` values, and a many-to-many
  `document_refs`) or, until that's done, recording the additional document
  labels in the `description` text and `claim_refs` as a documented interim
  workaround. Don't silently force a multi-document finding into a
  single-`document_id` row without flagging this.

## Chains

```
claim-extraction (per document) → cross-document-reconciliation → process-map-synthesis
                                                                  ↘ gap-ambiguity-logging
```
