"""ReviewSession / DraftChangeItem — the "Review & Apply Changes" consolidated
feedback flow.

Distinct from ChangeRequest (app/models/change_request.py), which stays as-is
for the direct, single-message "propose one change now" path. This is the
layered-on-top conversational flow: a BPA has a free-flowing conversation,
draft items accumulate, and only when they explicitly confirm does anything
get applied — as exactly ONE new ProcessMapVersion for whatever set of items
they approved together (see app/pipeline/versioning.py::apply_change_set and
the claude/gpt debate this design resolves).
"""
from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class ReviewSession(Base):
    __tablename__ = "review_sessions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    document_id: Mapped[str] = mapped_column(ForeignKey("document_versions.id"), nullable=False, index=True)
    base_process_map_id: Mapped[str] = mapped_column(ForeignKey("process_map_versions.id"), nullable=False)

    status: Mapped[str] = mapped_column(String, nullable=False, default="open")
    # open (accumulating draft items) | reconciled (consolidation pass run,
    # ready for BPA review) | confirmed (applied, produced a version) |
    # discarded

    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)
    confirmed_at: Mapped[dt.datetime] = mapped_column(DateTime, nullable=True)
    # Not a real FK to avoid the same circular-table issue noted on
    # ProcessMapVersion.change_request_id — this is a plain string id for
    # display/lookup once confirmed.
    resulting_process_map_id: Mapped[str] = mapped_column(String, nullable=True)

    items: Mapped[list["DraftChangeItem"]] = relationship(back_populates="session", cascade="all, delete-orphan")


class DraftChangeItem(Base):
    __tablename__ = "draft_change_items"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(ForeignKey("review_sessions.id"), nullable=False, index=True)

    change_type: Mapped[str] = mapped_column(String, nullable=False)
    # add_task | remove_task | modify_task | modify_edge | needs_clarification

    proposed_change: Mapped[str] = mapped_column(Text, nullable=False)  # JSON payload, see versioning.py
    rationale: Mapped[str] = mapped_column(Text, nullable=True)

    # JSON list of transcript turn refs (e.g. "turn-3") this item was drafted
    # from — the evidence trail back to what the BPA actually said.
    source_message_refs: Mapped[str] = mapped_column(Text, nullable=True)

    status: Mapped[str] = mapped_column(String, nullable=False, default="draft")
    # draft | approved | rejected | needs_clarification | superseded |
    # apply_failed | applied

    # Set when a later consolidation pass or BPA edit replaces this item's
    # intent — the old item is kept (never deleted) with status=superseded and
    # this points at what replaced it, so the history stays honest.
    superseded_by_item_id: Mapped[str] = mapped_column(String, nullable=True)

    # True if a BPA directly edited this item's wording/payload at review time
    # — distinguishes a human override from LLM-derived-from-transcript
    # content, per the "review-gaming" pitfall named in the design debate.
    human_override: Mapped[bool] = mapped_column(default=False)

    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow, onupdate=dt.datetime.utcnow)

    session: Mapped[ReviewSession] = relationship(back_populates="items")
