---
name: claim-extraction
description: Pull atomic, citable claims (rules, conditions, exceptions, definitions)
  out of parsed document spans, for a specific process the user wants to automate.
  Use for "extract the rules", "what does the document say about X", "build the
  claim set".
---

# Claim Extraction

Turns raw `SourceSpan` text into `AtomicClaim` rows — structured, typed, individually
citable statements. This is the step that separates "what the document literally
says" from "what we think the process should be" (that's `process-map-synthesis`'s
job, one stage later). Collapsing the two stages is the single most common way this
kind of system produces plausible-sounding but ungrounded output.

## Contract

- Every claim has exactly one `raw_quote` that is a **verbatim substring** of a real
  `SourceSpan`'s text (not a paraphrase) — this is mechanically checkable and should
  be checked, not just asserted
- `statement` is a plain-language paraphrase for readability; `raw_quote` is the
  ground truth a reviewer can verify against
- A claim is only extracted for something the document actually states. Where the
  document is silent on something the process needs (e.g. a submission deadline),
  that's a job for `gap-ambiguity-logging`, not a claim with an invented value
- Claims are scoped to what's relevant to the process being mapped (e.g. "claim
  coverage determination"), not an exhaustive extraction of the entire document —
  extracting the whole PDS into claims when only the coverage-determination process
  is being mapped is scope creep with a real cost (noise the reviewer has to wade
  through)

## Procedure

1. Identify which sections of the parsed document are relevant to the target
   process. For "determine claim coverage from a claim description," that's
   materially: cover descriptions, general exclusions, benefit-specific exclusions,
   excess rules, definitions of key terms, and the claim-evidence requirements. It
   is *not*, for example, premium-calculation or complaints-handling sections —
   name what's out of scope rather than silently including or excluding it.
2. For each relevant span, decide if it contains one or more atomic claims. A
   single span (e.g. a bulleted exclusions list) often yields several claims — one
   per bullet, not one per span, because reconciliation and the process map both
   need claim-level granularity to work.
3. Classify each claim: `claim_type` (rule/definition/exception/condition/
   exclusion/data_requirement), `modality` (covers/excludes/requires/permits/
   denies/defines), `subject` and `predicate` in normalized short form so related
   claims can be grouped later.
4. Copy the `raw_quote` verbatim — don't clean up whitespace beyond collapsing
   runs, don't fix apparent typos, don't reorder clauses.
5. If genuinely automated (an LLM call): record `extractor_version` as the actual
   model/prompt version. If done directly by an agent session because no LLM API
   key is configured (see architecture.md's disclosed constraint): tag
   `extractor_version: manual-agent-pass-v1` so it's never confused with an
   automated run, and note the session date.
6. Run the citation verifier (`verify_citations.py` or equivalent) against every
   claim before considering the extraction pass complete — a claim whose
   `raw_quote` doesn't appear verbatim in the source document is a fabrication, not
   an extraction, no matter how plausible it reads.

## Anti-patterns

| Don't | Do |
|---|---|
| Paraphrase into `raw_quote` "for readability" | Paraphrase goes in `statement`; `raw_quote` is always verbatim |
| Invent a plausible value for something undocumented (e.g. "claims must be lodged within 30 days") when the text doesn't say so | Emit no claim, and log a gap via `gap-ambiguity-logging` instead |
| Extract the entire document because "more data can't hurt" | Scope to the target process; name what's excluded and why |
| One claim per source span regardless of how many distinct statements it contains | One claim per atomic statement — split bulleted lists |
| Trust the extraction because it "sounds right" | Run the verbatim-quote check programmatically; that's the actual verification, not a read-through |

## Fallbacks

- No LLM API key configured: extraction is done directly by the building agent,
  reading the parsed spans and producing the same schema an automated pass would —
  disclosed explicitly, never silently presented as an automated run.
- Ambiguous claim boundaries (a sentence that's arguably one claim or two): prefer
  splitting further rather than merging — a claim that's too granular still cites
  correctly; a claim that bundles two distinct conditions makes later contradiction/
  gap detection miss things.

## Chains

```
pdf-ingestion → claim-extraction → process-map-synthesis
                                 ↘ gap-ambiguity-logging
```
