"""PDF ingestion — see skills/pdf-ingestion/SKILL.md for the design rationale.

Turns a PDF's bytes into (DocumentVersion, list[SourceSpan]) without touching the
database directly, so it's testable in isolation and callable from the API layer.
"""
from __future__ import annotations

import hashlib
import re
from collections import Counter
from dataclasses import dataclass, field

import fitz  # PyMuPDF


@dataclass
class ParsedSpan:
    page: int
    section_path: str
    bbox: str
    text: str
    order_index: int


@dataclass
class ParsedDocument:
    title: str
    content_hash: str
    page_count: int
    spans: list[ParsedSpan] = field(default_factory=list)
    failed_pages: list[int] = field(default_factory=list)


def content_hash(pdf_bytes: bytes) -> str:
    return hashlib.sha256(pdf_bytes).hexdigest()


def _body_size_and_heading_thresholds(doc: fitz.Document) -> tuple[float, list[float]]:
    """Compute the body-text font size and a ranked list of heading sizes, specific
    to this document's own typography (see skill anti-patterns: never hard-code)."""
    sizes: Counter[float] = Counter()
    for page in doc:
        d = page.get_text("dict")
        for block in d.get("blocks", []):
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    sizes[round(span["size"], 1)] += 1

    if not sizes:
        return 9.0, []

    body_size = sizes.most_common(1)[0][0]
    heading_sizes = sorted([s for s in sizes if s > body_size + 0.4], reverse=True)
    return body_size, heading_sizes


def _heading_level(size: float, heading_sizes: list[float]) -> int | None:
    """1-indexed level, or None if not a heading size."""
    for i, hs in enumerate(heading_sizes):
        if abs(size - hs) < 0.15:
            return i + 1
    return None


_BULLET_RE = re.compile(r"^[•–\-\*\t]\s*")


def parse_pdf(pdf_bytes: bytes, title_hint: str = "") -> ParsedDocument:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    body_size, heading_sizes = _body_size_and_heading_thresholds(doc)

    # Guard against a broken heading hierarchy (skill fallback: flat-but-correct
    # beats structured-but-wrong) — if "headings" would be most of the document,
    # something's off with the size histogram; treat everything as flat body text.
    total_spans = sum(1 for page in doc for b in page.get_text("dict").get("blocks", []) for l in b.get("lines", []) for _ in l.get("spans", []))
    heading_span_count = 0
    for page in doc:
        for block in page.get_text("dict").get("blocks", []):
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    if _heading_level(round(span["size"], 1), heading_sizes) is not None:
                        heading_span_count += 1
    if total_spans and heading_span_count / total_spans > 0.5:
        heading_sizes = []  # fall back to flat

    heading_stack: list[tuple[int, str]] = []  # (level, text)
    spans: list[ParsedSpan] = []
    failed_pages: list[int] = []
    order_index = 0

    for page_index in range(doc.page_count):
        page_num = page_index + 1
        try:
            d = doc[page_index].get_text("dict")
        except Exception:
            failed_pages.append(page_num)
            continue

        current_para: list[str] = []
        current_bbox = None

        def flush_para():
            nonlocal current_para, current_bbox, order_index
            if current_para:
                text = " ".join(t.strip() for t in current_para if t.strip())
                text = re.sub(r"\s+", " ", text).strip()
                if text:
                    section_path = " > ".join(h[1] for h in heading_stack)
                    spans.append(
                        ParsedSpan(
                            page=page_num,
                            section_path=section_path,
                            bbox=",".join(str(round(v, 1)) for v in current_bbox) if current_bbox else "",
                            text=text,
                            order_index=order_index,
                        )
                    )
                    order_index += 1
            current_para = []
            current_bbox = None

        for block in d.get("blocks", []):
            for line in block.get("lines", []):
                line_text = "".join(span.get("text", "") for span in line.get("spans", []))
                if not line_text.strip():
                    flush_para()
                    continue
                sizes_in_line = [round(s["size"], 1) for s in line.get("spans", [])]
                max_size = max(sizes_in_line) if sizes_in_line else body_size
                level = _heading_level(max_size, heading_sizes)

                if level is not None:
                    candidate = line_text.strip()
                    # Filter out decorative/false-positive heading candidates: bare
                    # numbers (section-number graphics rendered separately from their
                    # title text) and very short fragments are noise rather than real
                    # headings — pushing them corrupts every subsequent span's
                    # section_path until a same-level heading resets it.
                    is_plausible_heading = (
                        len(candidate) >= 4
                        and not candidate.replace(" ", "").isdigit()
                        and page_num > 1  # page 1 is almost always cover art/title, not a real section heading
                    )
                    if is_plausible_heading:
                        flush_para()
                        heading_stack[:] = [h for h in heading_stack if h[0] < level]
                        heading_stack.append((level, candidate))
                        continue
                    # Not plausible as a heading — fall through, treat as body text.

                is_bullet_start = bool(_BULLET_RE.match(line_text.strip()))
                if is_bullet_start:
                    flush_para()

                current_para.append(line_text)
                bbox = line.get("bbox")
                if bbox:
                    if current_bbox is None:
                        current_bbox = list(bbox)
                    else:
                        current_bbox = [
                            min(current_bbox[0], bbox[0]),
                            min(current_bbox[1], bbox[1]),
                            max(current_bbox[2], bbox[2]),
                            max(current_bbox[3], bbox[3]),
                        ]
        flush_para()

    return ParsedDocument(
        title=title_hint or "Untitled document",
        content_hash=content_hash(pdf_bytes),
        page_count=doc.page_count,
        spans=spans,
        failed_pages=failed_pages,
    )
