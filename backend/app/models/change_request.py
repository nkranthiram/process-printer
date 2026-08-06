"""ChangeRequest — a BPA's feedback on the process map, captured through the
chatbot, proposing a concrete edit (add/remove/modify a task or edge).

Never applied automatically. A change request always starts `pending`; applying
it (via app/pipeline/versioning.py) creates a brand-new ProcessMapVersion rather
than mutating the current one in place — the whole point is an auditable version
history, not silent edits (see docs/process-methodology.md and architecture.md).
"""
from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class ChangeRequest(Base):
    __tablename__ = "change_requests"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    document_id: Mapped[str] = mapped_column(ForeignKey("document_versions.id"), nullable=False, index=True)
    base_process_map_id: Mapped[str] = mapped_column(ForeignKey("process_map_versions.id"), nullable=False)

    source: Mapped[str] = mapped_column(String, nullable=False, default="chat")  # chat | manual
    request_text: Mapped[str] = mapped_column(Text, nullable=False)  # the BPA's original message

    change_type: Mapped[str] = mapped_column(String, nullable=False)
    # add_task | remove_task | modify_task | modify_edge | unclear

    # JSON payload describing the proposed edit — shape depends on change_type,
    # see app/pipeline/versioning.py for the contract each shape must satisfy.
    proposed_change: Mapped[str] = mapped_column(Text, nullable=False)

    rationale: Mapped[str] = mapped_column(Text, nullable=True)  # why the BPA/LLM believes this is needed

    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    # pending | approved | rejected | apply_failed

    decision_notes: Mapped[str] = mapped_column(Text, nullable=True)
    resulting_process_map_id: Mapped[str] = mapped_column(
        ForeignKey("process_map_versions.id"), nullable=True
    )

    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)
    decided_at: Mapped[dt.datetime] = mapped_column(DateTime, nullable=True)
