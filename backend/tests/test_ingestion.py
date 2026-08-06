"""Tests for pdf-ingestion. Uses the REAL AAMI PDS PDF (not a synthetic stub) for
the main assertions, per verification.md: "test the user's path, not the code's
path" — a synthetic single-paragraph PDF wouldn't exercise the heading-hierarchy or
multi-page logic this document actually needs.
"""
from pathlib import Path

import fitz
import pytest

from app.pipeline.ingestion import parse_pdf, content_hash

AAMI_PDF = Path(__file__).parent.parent.parent.parent / "docs" / "aami-comprehensive-car-insurance-pds.pdf"


@pytest.fixture(scope="module")
def aami_bytes():
    assert AAMI_PDF.exists(), f"expected the real source PDF at {AAMI_PDF}"
    return AAMI_PDF.read_bytes()


def test_parses_real_aami_pds(aami_bytes):
    result = parse_pdf(aami_bytes, title_hint="AAMI Comprehensive Car Insurance PDS")

    assert result.page_count == 76
    assert result.failed_pages == []
    # A 76-page insurance PDS should yield hundreds of spans, not a handful —
    # catches the "flush never fires, everything collapses into one span" failure
    # mode directly instead of just checking spans is non-empty.
    assert len(result.spans) > 300

    # Every span must carry a real page number and non-empty text — the citation
    # primitive is worthless without both.
    for span in result.spans:
        assert 1 <= span.page <= 76
        assert span.text.strip() != ""

    # Spot-check: windscreen cover should exist somewhere in the document, and the
    # span containing it should carry a section_path (proves heading tracking ran,
    # not just flat body text).
    windscreen_spans = [s for s in result.spans if "windscreen" in s.text.lower()]
    assert windscreen_spans, "expected at least one span mentioning windscreen cover"
    assert any(s.section_path for s in windscreen_spans), (
        "expected at least one windscreen span to have a non-empty section_path "
        "(heading detection may have fallen back to flat mode)"
    )


def test_content_hash_stable(aami_bytes):
    h1 = content_hash(aami_bytes)
    h2 = content_hash(aami_bytes)
    assert h1 == h2
    assert len(h1) == 64  # sha256 hex digest


def test_order_index_is_monotonic(aami_bytes):
    result = parse_pdf(aami_bytes)
    indices = [s.order_index for s in result.spans]
    assert indices == sorted(indices)
    assert indices == list(range(len(indices)))


def _make_synthetic_pdf_bytes(paragraphs: list[tuple[str, float]]) -> bytes:
    """(text, font_size) pairs on one page, for testing edge behavior a real PDF
    doesn't conveniently exercise (e.g. an empty page)."""
    doc = fitz.open()
    page = doc.new_page()
    y = 50
    for text, size in paragraphs:
        page.insert_text((50, y), text, fontsize=size)
        y += size + 10
    b = doc.tobytes()
    doc.close()
    return b


def test_empty_page_produces_no_spans_not_a_crash():
    doc = fitz.open()
    doc.new_page()  # blank page, no text at all
    pdf_bytes = doc.tobytes()
    doc.close()

    result = parse_pdf(pdf_bytes)
    assert result.page_count == 1
    assert result.spans == []
    assert result.failed_pages == []
