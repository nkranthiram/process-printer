"""Claim extraction — see skills/claim-extraction/SKILL.md.

Two things live here:
1. An LLMClient protocol + a real Anthropic-backed implementation, so a future run
   against a NEW document can extract claims automatically once ANTHROPIC_API_KEY is
   set. This is the generic, reusable path (user requirement: swap the document, the
   pipeline still works).
2. A loader for the manually-produced AAMI seed data (data/aami_claims.json, built by
   build_aami_claims.py), used for THIS run since no API key is configured here — see
   architecture.md's disclosed constraint.
3. verify_citations(): the mechanical check every extraction pass — automated or
   manual — must pass before being considered done. A raw_quote that isn't a real
   substring of its cited SourceSpan is a fabrication, not an extraction.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

DATA_DIR = Path(__file__).parent.parent.parent / "data"


@dataclass
class ClaimDraft:
    claim_type: str
    subject: str
    predicate: str
    modality: str
    statement: str
    raw_quote: str
    page: int
    section_path: str
    conditions: list[str]
    extraction_confidence: float
    extractor_version: str
    explicit: bool = True


class LLMClient(Protocol):
    """What any extraction backend must provide. Swap implementations without
    touching pipeline code that calls this."""

    def extract_claims(self, document_title: str, spans_text: str) -> list[dict]:
        ...


class AnthropicLLMClient:
    """Real implementation for automated extraction on a NEW document. Requires
    ANTHROPIC_API_KEY. Not exercised in this build (no key in this sandbox) — see
    architecture.md. Kept here so the pipeline is genuinely swap-in-a-new-document
    generic, per the user's explicit requirement, not just generic in theory."""

    def __init__(self, model: str = "claude-sonnet-4-5-20250929"):
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY not set — automated extraction unavailable in this "
                "environment. Use load_manual_seed() for a pre-extracted document, or "
                "set the key to run this client for real."
            )
        import anthropic  # deferred import: only required if this path is used

        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

    def extract_claims(self, document_title: str, spans_text: str) -> list[dict]:
        prompt = (
            "You are extracting atomic, citable claims from an insurance policy "
            "document for a claim-coverage-determination process map. For each "
            "distinct rule, condition, exception, exclusion or definition in the "
            "text below, emit one JSON object with fields: claim_type "
            "(rule|definition|exception|condition|exclusion|data_requirement), "
            "subject, predicate, modality (covers|excludes|requires|permits|denies|"
            "defines), statement (plain-language paraphrase), raw_quote (VERBATIM "
            "substring of the source text — never paraphrase this field), "
            "conditions (list of strings), extraction_confidence (0-1). "
            "Only extract what the text actually states — do not infer unstated "
            "values. Return a JSON array only.\n\n"
            f"Document: {document_title}\n\nText:\n{spans_text}"
        )
        response = self._client.messages.create(
            model=self._model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text
        return json.loads(text)


def load_manual_seed(path: Path | None = None) -> list[ClaimDraft]:
    path = path or (DATA_DIR / "aami_claims.json")
    raw = json.loads(path.read_text())
    return [
        ClaimDraft(
            claim_type=c["claim_type"],
            subject=c["subject"],
            predicate=c["predicate"],
            modality=c["modality"],
            statement=c["statement"],
            raw_quote=c["raw_quote"],
            page=c["page"],
            section_path=c.get("section_path", ""),
            conditions=c.get("conditions", []),
            extraction_confidence=c["extraction_confidence"],
            extractor_version=c["extractor_version"],
            explicit=c.get("explicit", True),
        )
        for c in raw
    ]


@dataclass
class CitationCheckResult:
    total: int
    verified: int
    failures: list[str]

    @property
    def all_verified(self) -> bool:
        return self.total > 0 and not self.failures


def _normalize(s: str) -> str:
    return (
        s.lower()
        .replace("ﬁ", "fi")
        .replace("ﬂ", "fl")
        .replace("’", "'")
        .replace("‘", "'")
    )


def verify_citations(claims: list[ClaimDraft], parsed_spans) -> CitationCheckResult:
    """Mechanically check that every claim's raw_quote is a real (normalized)
    substring of SOME span on the page it cites. This is what actually verifies
    extraction accuracy — a read-through cannot catch a subtly-altered quote the
    way this does."""
    by_page: dict[int, list[str]] = {}
    for s in parsed_spans:
        by_page.setdefault(s.page, []).append(_normalize(s.text))

    failures = []
    verified = 0
    for c in claims:
        page_texts = by_page.get(c.page, [])
        quote_norm = _normalize(c.raw_quote)
        if any(quote_norm in text for text in page_texts):
            verified += 1
        else:
            failures.append(
                f"claim subject={c.subject!r} page={c.page}: raw_quote not found "
                f"verbatim in any span on that page — {c.raw_quote[:80]!r}..."
            )
    return CitationCheckResult(total=len(claims), verified=verified, failures=failures)
