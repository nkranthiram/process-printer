---
name: pdf-ingestion
description: Parse an uploaded policy/procedure PDF into page- and section-anchored
  text spans that everything downstream can cite. Use for "ingest this document",
  "parse the PDF", "load a new policy document", "re-run on a different document".
---

# PDF Ingestion

Turns a raw PDF into `SourceSpan` rows — the citation primitive every later claim,
task, and issue points back to. If this stage loses the connection between text and
its page/location, nothing built on top of it can be trusted, no matter how good the
extraction reasoning is later.

## Contract

- Every paragraph/list-item of body text becomes one `SourceSpan` with a page number
- Headings are detected (by font size, not by keyword-matching page content) and
  used to build a `section_path` for every span under them, e.g.
  `"Section 4: Motor vehicle cover > Windscreen and window glass"`
- Nothing is summarized or paraphrased at this stage — spans hold exact source text
- Output is generic across documents: no AAMI-specific strings hard-coded into the
  parsing logic itself (only the *heuristic thresholds*, e.g. font-size cutoffs, are
  tunable per document if a document's typography differs)

## Procedure

1. Open the PDF with PyMuPDF (`fitz`), one `DocumentVersion` row created up front
   with `content_hash` (sha256 of file bytes) so re-uploading the same file is
   detected rather than silently re-processed.
2. Walk every page's `get_text("dict")` output, which gives text spans with font
   size — this is more reliable than regex-guessing headings from text shape, and
   works across differently-worded documents.
3. Build a font-size histogram across the whole document first. The single most
   common size is body text; sizes meaningfully larger than that are heading
   candidates, ranked into a hierarchy by size descending. This has to run per
   document — don't hard-code "9.5pt is body text," that's specific to how AAMI's
   PDS happens to be typeset.
4. Maintain a heading stack while walking pages in order: when a heading-sized span
   is seen, pop the stack back to its level and push the new heading; every body
   span's `section_path` is the stack joined with " > ".
5. Group consecutive body lines into paragraph/list-item spans (blank line or
   bullet marker = new span), not one span per line — a citation pointing at "the
   fourth line of a six-line bullet" isn't useful to a reviewer.
6. Persist `SourceSpan` rows with page, section_path, raw text, and order_index
   (position within the document, for reconstructing reading order later).

## Anti-patterns

| Don't | Do |
|---|---|
| Hard-code "font size 9.5 = body" for all documents | Compute the histogram per document; only the *method* is fixed |
| One `SourceSpan` per line of text | Group into paragraph/list-item units — matches how a human would cite it |
| Guess headings from text patterns ("looks like Title Case") | Use font size/weight from the PDF's actual layout data |
| Silently skip pages that fail to parse | Record the page as failed on the `DocumentVersion` and surface it, don't drop it quietly |
| Paraphrase text while extracting it here | This stage is verbatim only — paraphrasing is `claim-extraction`'s job, not this one |

## Fallbacks

- If a PDF has no extractable text layer (scanned image only), this skill can't
  proceed without OCR, which isn't built yet — surface that as a document status of
  `failed` with a clear reason, don't attempt a best-effort garbage parse.
- If font-size heuristics produce an implausible heading hierarchy (e.g. every span
  looks like a heading), fall back to treating the whole document as flat body text
  under one section rather than producing a broken hierarchy — flat-but-correct
  beats structured-but-wrong.

## Chains

```
(user uploads a document) → pdf-ingestion → claim-extraction
```
