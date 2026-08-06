"""Tests for claim-extraction. The load-bearing check here is verify_citations:
every raw_quote in the manually-produced AAMI seed set must be a real substring of
the actual parsed document — this is what stops a plausible-sounding but fabricated
citation from ever reaching a claims handler.
"""
from pathlib import Path

import pytest

from app.pipeline.extraction import load_manual_seed, verify_citations, ClaimDraft
from app.pipeline.ingestion import parse_pdf

AAMI_PDF = Path(__file__).parent.parent.parent.parent / "docs" / "aami-comprehensive-car-insurance-pds.pdf"


@pytest.fixture(scope="module")
def parsed_aami():
    return parse_pdf(AAMI_PDF.read_bytes(), title_hint="AAMI Comprehensive Car Insurance PDS")


def test_manual_seed_loads():
    claims = load_manual_seed()
    assert len(claims) >= 30
    for c in claims:
        assert c.raw_quote.strip() != ""
        assert c.page >= 1
        assert c.extractor_version == "manual-agent-pass-v1"


def test_all_seed_claims_pass_citation_verification(parsed_aami):
    claims = load_manual_seed()
    result = verify_citations(claims, parsed_aami.spans)
    if result.failures:
        # Surface every failure, not just the first — matches output-rules.md:
        # show the actual error, not a paraphrase.
        pytest.fail("Citation verification failures:\n" + "\n".join(result.failures))
    assert result.all_verified
    assert result.verified == result.total


def test_verify_citations_catches_a_fabricated_quote(parsed_aami):
    """Red-before-green as a permanent regression test, not just a one-off manual
    check: a claim with a quote that does NOT appear in the source must fail
    verification, proving the checker actually checks something."""
    fake_claim = ClaimDraft(
        claim_type="rule",
        subject="fabricated_subject",
        predicate="fabricated_predicate",
        modality="covers",
        statement="This claim was never in the document.",
        raw_quote="We will pay unlimited claims with no excess ever under any circumstances",
        page=1,
        section_path="",
        conditions=[],
        extraction_confidence=0.99,
        extractor_version="manual-agent-pass-v1",
    )
    result = verify_citations([fake_claim], parsed_aami.spans)
    assert not result.all_verified
    assert result.verified == 0
    assert len(result.failures) == 1
    assert "fabricated_subject" in result.failures[0]


def test_wrong_page_reference_is_caught(parsed_aami):
    """A quote that's real, but attributed to the wrong page, must also fail —
    citation accuracy means page AND text both correct."""
    claims = load_manual_seed()
    real_claim = claims[0]
    mismatched = ClaimDraft(**{**real_claim.__dict__, "page": real_claim.page + 5})
    result = verify_citations([mismatched], parsed_aami.spans)
    assert result.verified == 0
