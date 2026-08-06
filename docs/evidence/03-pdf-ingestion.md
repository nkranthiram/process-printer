# Evidence — Task 3: pdf-ingestion

## Red-before-green
Injected a bug disabling the paragraph-flush condition (`if text and False:`),
ran `test_parses_real_aami_pds` against the actual AAMI PDF — failed as expected
(`assert len(result.spans) > 300` against an empty `spans` list). Restored, reran,
green. Full output in terminal history; summary:

```
Before fix: 1 failed, 3 passed
After fix:  4 passed
```

## Real-document run (not synthetic)
Parsed the actual `docs/aami-comprehensive-car-insurance-pds.pdf`:
- 76 pages, 0 failed pages
- 461 spans extracted
- Every span has a page number in [1,76] and non-empty text
- `order_index` is monotonic and gapless (0..460)
- content_hash is stable across repeated runs on the same bytes (sha256, 64 hex chars)

## Known limitation (disclosed)
Heading/`section_path` detection is font-size-based and imperfect on this
document: some spans carry a stale `section_path` from an earlier heading that
hasn't been superseded yet (e.g. page 42's windscreen-cover text is filed under
`"pay extra for > cover"` rather than the true local heading, because the PDS's
actual sub-heading for that clause didn't clear the font-size threshold used).
**This does not affect citation accuracy** — the page number and raw quoted text
are always correct and are what claim-extraction and the UI will primarily cite;
`section_path` is supplementary context, not the citation guarantee. Follow-up
idea, not done now: use bold-weight + size combined, or hand this classification
to the LLM extraction pass once a key is available, rather than pure heuristics.

## What's not covered yet
- OCR fallback for scanned (non-text-layer) PDFs — not built; skill explicitly
  documents this as a hard failure mode (`status: failed`), not attempted here
- Table extraction is not structured (tables currently flow through as plain text
  paragraphs) — acceptable for v1 since the AAMI PDS is mostly prose, revisit if a
  future document is table-heavy
