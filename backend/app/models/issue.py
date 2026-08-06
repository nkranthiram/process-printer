"""Issue — a gap or ambiguity the source document doesn't resolve.

Per user instruction: don't pause on these, log them and let the user review/confirm
afterwards (see skills/gap-ambiguity-logging/SKILL.md).
"""
from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class Issue(Base):
    __tablename__ = "issues"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    document_id: Mapped[str] = mapped_column(ForeignKey("document_versions.id"), nullable=False, index=True)
    process_task_id: Mapped[str] = mapped_column(ForeignKey("process_tasks.id"), nullable=True)

    issue_type: Mapped[str] = mapped_column(String, nullable=False)
    # gap | ambiguity | low_confidence_extraction

    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    claim_refs: Mapped[str] = mapped_column(Text, nullable=True)  # JSON list of AtomicClaim ids, if any
    status: Mapped[str] = mapped_column(String, nullable=False, default="open")  # open | resolved | deferred
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)
