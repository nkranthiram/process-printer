"""AtomicClaim — the smallest citable unit extracted from a document.

See skills/claim-extraction/SKILL.md for how these get produced.
"""
from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class AtomicClaim(Base):
    __tablename__ = "atomic_claims"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    document_id: Mapped[str] = mapped_column(ForeignKey("document_versions.id"), nullable=False, index=True)
    source_span_id: Mapped[str] = mapped_column(ForeignKey("source_spans.id"), nullable=False, index=True)

    claim_type: Mapped[str] = mapped_column(String, nullable=False)
    # rule | definition | exception | condition | exclusion | actor | data_requirement

    subject: Mapped[str] = mapped_column(String, nullable=False)
    predicate: Mapped[str] = mapped_column(String, nullable=False)
    modality: Mapped[str] = mapped_column(String, nullable=False)
    # covers | excludes | requires | permits | denies | defines

    statement: Mapped[str] = mapped_column(Text, nullable=False)  # plain-language paraphrase
    raw_quote: Mapped[str] = mapped_column(Text, nullable=False)  # exact source text, never paraphrased

    conditions: Mapped[str] = mapped_column(Text, nullable=True)  # JSON-encoded list of condition strings

    extraction_confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    extractor_version: Mapped[str] = mapped_column(String, nullable=False)
    extracted_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)
    explicit: Mapped[bool] = mapped_column(default=True)  # False if inferred rather than stated

    source_span: Mapped["object"] = relationship("SourceSpan")
