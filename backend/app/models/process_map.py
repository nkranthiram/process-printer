"""ProcessTask / ProcessEdge — the task-level process map (a DAG).

Deliberately task-level, not clause-level (see skills/process-map-synthesis) — the
map is meant to be readable by a claims handler / BPA, not an execution engine.
"""
from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class ProcessMapVersion(Base):
    __tablename__ = "process_map_versions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    document_id: Mapped[str] = mapped_column(ForeignKey("document_versions.id"), nullable=False, index=True)
    version_label: Mapped[str] = mapped_column(String, nullable=False)  # "v0-draft", "v1", ...
    status: Mapped[str] = mapped_column(String, nullable=False, default="draft")  # draft | validated
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)

    tasks: Mapped[list["ProcessTask"]] = relationship(back_populates="process_map", cascade="all, delete-orphan")
    edges: Mapped[list["ProcessEdge"]] = relationship(back_populates="process_map", cascade="all, delete-orphan")


class ProcessTask(Base):
    __tablename__ = "process_tasks"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    process_map_id: Mapped[str] = mapped_column(ForeignKey("process_map_versions.id"), nullable=False, index=True)

    node_type: Mapped[str] = mapped_column(String, nullable=False)
    # input_required | eligibility_test | exclusion_test | exception_test |
    # time_window_test | evidence_sufficiency_test | human_review | decision

    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)  # how to carry out this task
    position_x: Mapped[float] = mapped_column(default=0.0)
    position_y: Mapped[float] = mapped_column(default=0.0)

    # JSON-encoded list of AtomicClaim ids that support this task's description
    claim_refs: Mapped[str] = mapped_column(Text, nullable=True)

    process_map: Mapped[ProcessMapVersion] = relationship(back_populates="tasks")


class ProcessEdge(Base):
    __tablename__ = "process_edges"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    process_map_id: Mapped[str] = mapped_column(ForeignKey("process_map_versions.id"), nullable=False, index=True)
    from_task_id: Mapped[str] = mapped_column(ForeignKey("process_tasks.id"), nullable=False)
    to_task_id: Mapped[str] = mapped_column(ForeignKey("process_tasks.id"), nullable=False)
    condition_label: Mapped[str] = mapped_column(String, nullable=True)  # e.g. "Yes", "No", "Days > 90"

    process_map: Mapped[ProcessMapVersion] = relationship(back_populates="edges")
