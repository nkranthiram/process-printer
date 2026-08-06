"""DocumentVersion and SourceSpan — the raw-truth layer.

Every extracted claim and every task in the process map must trace back to a
SourceSpan. This is the citation primitive (see architecture.md, provenance.md).
"""
from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class DocumentVersion(Base):
    __tablename__ = "document_versions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    filename: Mapped[str] = mapped_column(String, nullable=False)
    content_hash: Mapped[str] = mapped_column(String, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    uploaded_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)
    page_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Status of the ingestion/extraction pipeline for this document version.
    # queued -> parsing -> extracting -> synthesizing -> ready -> failed
    status: Mapped[str] = mapped_column(String, nullable=False, default="queued")

    spans: Mapped[list["SourceSpan"]] = relationship(back_populates="document", cascade="all, delete-orphan")


class SourceSpan(Base):
    __tablename__ = "source_spans"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    document_id: Mapped[str] = mapped_column(ForeignKey("document_versions.id"), nullable=False, index=True)
    page: Mapped[int] = mapped_column(Integer, nullable=False)
    section_path: Mapped[str] = mapped_column(String, nullable=True)  # e.g. "Section 4 > Windscreen cover"
    bbox: Mapped[str] = mapped_column(String, nullable=True)  # "x0,y0,x1,y1" — nullable if not layout-parsed
    text: Mapped[str] = mapped_column(Text, nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    document: Mapped[DocumentVersion] = relationship(back_populates="spans")
