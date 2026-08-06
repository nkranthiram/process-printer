---
name: text-ingestion
description: Parse raw text (not a PDF) from one or more source documents into
  citation-anchored spans that everything downstream can quote exactly. Use for
  "ingest this text", "load these pasted policy documents", "I have text not a
  PDF", "process these documents as plain text".
---

# Text Ingestion

The plain-text sibling of `pdf-ingestion`. Same job — turn a raw source into
`SourceSpan` rows that are the citation primitive every later claim, task, and
issue points back to — but for input that has no pages, no layout, and no font
sizes to detect headings from. Use this instead of `pdf-ingestion` when the input
is already text (pasted, uploaded as .txt/.md, or extracted upstream some other
way), not a PDF file.

## Contract

- Every input is one **document**, given (or assigned) a stable `document_label`
  distinct from every other document in the batch — this label is what
  `cross-document-reconciliation` groups and cites by, so it must be
  human-meaningful (e.g. `"AAMI PDS v2024"`, not `"doc_1"`) whenever the user
  supplies one.
- Every paragraph becomes one `SourceSpan`, exactly as in `pdf-ingestion` — no
  page number is available, so the anchor is `(document_label, paragraph_index,
  char_offset_start, char_offset_end)` instead. This is still an exact,
  mechanically-verifiable citation — just not a page.
- Headings are detected structurally, not visually (no font data exists here):
  Markdown `#`/`##`/... prefixes, or ALL-CAPS / numbered lines under a
  conservative heuristic (short line, no trailing punctuation, followed by body
  text) build the `section_path`, same as `pdf-ingestion`'s heading stack. If
  neither signal is present, skip section_path rather than guessing — a missing
  section_path is honest; a wrong one is misleading.
- Nothing is summarized or paraphrased at this stage — spans hold exact source
  text, identical rule to `pdf-ingestion`.
- Multiple documents in one batch are ingested independently — each gets its own
  `DocumentVersion`-equivalent record and its own span numbering. Nothing about
  ingestion itself compares documents to each other; that is
  `cross-document-reconciliation`'s job, one stage later, same separation
  discipline as `claim-extraction` vs `process-map-synthesis`.

## Procedure

1. For each input text block, compute a content hash (sha256) so re-ingesting
   identical text is detected rather than silently reprocessed — matches
   `pdf-ingestion`'s `content_hash` behavior.
2. Split into paragraphs on blank lines / list-item boundaries, same grouping
   rule as `pdf-ingestion` step 5 (one `SourceSpan` per paragraph or list item,
   not per line — a citation to "the fourth line of a six-line paragraph" isn't
   useful to a reviewer).
3. Walk paragraphs in order, maintaining a heading stack: a line matching the
   heading heuristic (Markdown prefix, or short un-punctuated line followed by
   body text) pushes/pops the stack; every body paragraph's `section_path` is
   the stack joined with `" > "`.
4. Record each `SourceSpan` with `document_label`, `section_path` (nullable),
   exact paragraph text, and `order_index` (position in the document, for
   reconstructing reading order).
5. If the schema/table in use is the one built for `pdf-ingestion` (which has a
   non-nullable `page: int` column), set `page = 0` with a documented convention
   that `page 0` means "text-ingested, no page concept" — don't invent a fake
   page number by counting paragraphs, that would silently look like a real page
   citation to a reviewer. (See `architecture.md`: this is a known schema gap
   from the single-document PDF-only v1 build, flagged here rather than
   papered over.)

## Anti-patterns

| Don't | Do |
|---|---|
| Invent a page number from paragraph count so the existing UI "just works" | Use `page = 0` / a null-page convention and flag it, so citations stay honest |
| Guess document identity/labels from content when the user gave none | Ask, or fall back to a content-hash-derived label — never silently merge two distinct inputs under one label |
| Detect headings from font-weight assumptions (there is no font data in plain text) | Use structural signals only: Markdown syntax or short-line-before-body heuristic |
| Ingest a multi-document batch as one giant document | One `DocumentVersion`-equivalent per input text block, always — reconciliation needs the boundary |
| Paraphrase or clean up wording while grouping into spans | Verbatim only, identical rule to `pdf-ingestion` |

## Fallbacks

- No heading signal at all (flat prose, no Markdown, no short capitalized
  lines): treat the whole document as one flat section, same fallback rule as
  `pdf-ingestion` — flat-but-correct beats structured-but-wrong.
- Ambiguous document boundaries in a single pasted blob (e.g. the user pastes
  two documents back-to-back without a clear separator): ask which is which
  rather than guessing a split point — a wrong split silently corrupts every
  citation downstream.

## Chains

```
(user provides raw text, one or more documents) → text-ingestion → claim-extraction
```
