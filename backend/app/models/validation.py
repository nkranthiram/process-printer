"""ValidationCase — a traced claim scenario used to sanity-check the process map.

Not an execution engine (out of scope) — this records a manually-traced scenario and
its outcome as evidence, per skills/scenario-validation/SKILL.md.
"""
from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class ValidationCase(Base):
    __tablename__ = "validation_cases"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    process_map_id: Mapped[str] = mapped_column(ForeignKey("process_map_versions.id"), nullable=False, index=True)

    scenario_name: Mapped[str] = mapped_column(String, nullable=False)
    claim_description: Mapped[str] = mapped_column(Text, nullable=False)
    expected_outcome: Mapped[str] = mapped_column(Text, nullable=False)
    traced_path: Mapped[str] = mapped_column(Text, nullable=False)  # JSON list of task ids, in order walked
    actual_outcome: Mapped[str] = mapped_column(Text, nullable=False)
    result: Mapped[str] = mapped_column(String, nullable=False)  # pass | fail
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    recorded_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)
