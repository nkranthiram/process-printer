# Evidence — Task 4: claim-extraction

## What ran
`build_aami_claims.py` produced 35 `AtomicClaim` drafts covering: base cover scope,
19 general exclusions (Section 3), excess rules incl. the not-at-fault waiver,
windscreen/window glass cover, Third Party Property Damage cross-cover rule, claim
evidence requirements, total-loss/write-off rules, and 4 key definitions (excess,
incident, market value, amount covered) — scoped to what's needed for coverage
determination, per the skill's contract (not an exhaustive extraction of all 76
pages, e.g. premium calculation and complaints-handling sections were left out).

Every `raw_quote` was sliced directly from the real parsed spans (never hand-retyped
into the JSON), so citation accuracy is a property of the tooling, not of careful
typing.

## Automated verification (the actual proof, not a read-through)
```
tests/test_extraction.py::test_manual_seed_loads PASSED
tests/test_extraction.py::test_all_seed_claims_pass_citation_verification PASSED
tests/test_extraction.py::test_verify_citations_catches_a_fabricated_quote PASSED
tests/test_extraction.py::test_wrong_page_reference_is_caught PASSED
4 passed in 0.84s
```

`test_all_seed_claims_pass_citation_verification`: all 35/35 claims' raw_quote
strings found verbatim (ligature/quote-normalized) in the real parsed AAMI document
on the page each claim cites.

`test_verify_citations_catches_a_fabricated_quote` and `test_wrong_page_reference_is_caught`
are the red-before-green proof, kept as permanent regression tests rather than a
one-off manual check: a fabricated quote and a real-quote-wrong-page both fail
verification (0/1 verified, failure message names the offending claim), proving the
checker can actually fail rather than rubber-stamping everything.

## Known limitation (disclosed)
No `ANTHROPIC_API_KEY` in this sandbox — extraction was performed directly by the
building agent reading the parsed document, not by the automated `AnthropicLLMClient`
path in `extraction.py`. Every claim is tagged `extractor_version:
manual-agent-pass-v1` to keep this visible in the data itself, not just in this doc.
The automated path is implemented and ready to use once a key is supplied.
