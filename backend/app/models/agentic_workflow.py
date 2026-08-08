"""AgenticWorkflowVersion / AgenticWorkflowNode / AgenticWorkflowEdge --
the downstream, optional artifact that turns a human-facing ProcessMapVersion
into a builder-ready agentic-workflow spec. See
skills/agentic-workflow-synthesis/SKILL.md and docs/agentic-workflow-design.md
for the method and rationale.

Deliberately a SEPARATE artifact from ProcessTask/ProcessEdge, not a new
column on them: the human process map stays the thing a BPA reviews and signs
off on; this is what an implementer (e.g. a Maestro builder) consumes once
that map is approved. Versioned against the exact ProcessMapVersion it was
generated from, so it's always traceable to a specific, known map state.
"""
from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

# Node kinds, per skills/agentic-workflow-synthesis/SKILL.md's Q1-Q3 test.
# "gateway" nodes carry the routing logic between other nodes and have no
# spec_json fields beyond the decision-logic/downstream-edges ones.
NODE_KINDS = {"deterministic", "agent", "agent_escalation", "human", "service", "gateway"}


def _uuid() -> str:
    return str(uuid.uuid4())


class AgenticWorkflowVersion(Base):
    __tablename__ = "agentic_workflow_versions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    document_id: Mapped[str] = mapped_column(ForeignKey("document_versions.id"), nullable=False, index=True)
    # Which process-map version this was generated from -- not a live FK
    # (same reasoning as ProcessMapVersion.change_request_id: avoids a
    # circular table-creation dependency; the id is still real and queryable).
    process_map_version_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    process_map_version_label: Mapped[str] = mapped_column(String, nullable=False)  # denormalized for display

    generator_version: Mapped[str] = mapped_column(String, nullable=False)  # e.g. "manual-agent-pass-v1"
    status: Mapped[str] = mapped_column(String, nullable=False, default="draft")  # draft | validated
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)

    nodes: Mapped[list["AgenticWorkflowNode"]] = relationship(
        back_populates="workflow", cascade="all, delete-orphan"
    )
    edges: Mapped[list["AgenticWorkflowEdge"]] = relationship(
        back_populates="workflow", cascade="all, delete-orphan"
    )


class AgenticWorkflowNode(Base):
    __tablename__ = "agentic_workflow_nodes"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    workflow_id: Mapped[str] = mapped_column(
        ForeignKey("agentic_workflow_versions.id"), nullable=False, index=True
    )

    node_kind: Mapped[str] = mapped_column(String, nullable=False)  # see NODE_KINDS
    title: Mapped[str] = mapped_column(String, nullable=False)
    goal: Mapped[str] = mapped_column(Text, nullable=False)  # stated as an output, not an activity

    # Title of the source ProcessTask this node was derived from, if any --
    # a gateway or a second/third node split out of one source task will
    # share the same source_task_title as its siblings. Title, not id, for
    # the same reason change_log.py uses titles: ProcessTask row ids are
    # regenerated on every fresh seed.
    source_task_title: Mapped[str] = mapped_column(String, nullable=True)

    # The full §3 field set (inputs, outputs, decision_logic, grounding,
    # confidence/escalation trigger + calibration metadata, escalation
    # target, error_handling, sla, audit, agent-specific fields) as JSON.
    # Kept as one JSON blob rather than a wide column set: the field shape
    # genuinely differs by node_kind (a gateway has no "tools list"; a
    # deterministic task has no "confidence"), and forcing every possible
    # field into dedicated nullable columns would be worse than a validated
    # JSON blob with a schema-checked shape per kind (see pipeline/agentic_workflow.py).
    spec_json: Mapped[str] = mapped_column(Text, nullable=False)

    # JSON list of AtomicClaim ids this node's decision logic / authority
    # boundary actually cites -- same citation discipline as ProcessTask,
    # extended one layer downstream. Empty list is valid for pure gateway/
    # service nodes that cite nothing themselves.
    claim_refs: Mapped[str] = mapped_column(Text, nullable=False, default="[]")

    workflow: Mapped[AgenticWorkflowVersion] = relationship(back_populates="nodes")


class AgenticWorkflowEdge(Base):
    __tablename__ = "agentic_workflow_edges"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    workflow_id: Mapped[str] = mapped_column(
        ForeignKey("agentic_workflow_versions.id"), nullable=False, index=True
    )
    from_node_id: Mapped[str] = mapped_column(ForeignKey("agentic_workflow_nodes.id"), nullable=False)
    to_node_id: Mapped[str] = mapped_column(ForeignKey("agentic_workflow_nodes.id"), nullable=False)
    # Named condition, e.g. "deterministic decline", "agent-judgment adverse",
    # "clean / within authority" -- must belong to a finite, exhaustive,
    # mutually-exclusive set per source gateway (see the validator).
    condition_label: Mapped[str] = mapped_column(String, nullable=True)

    workflow: Mapped[AgenticWorkflowVersion] = relationship(back_populates="edges")
