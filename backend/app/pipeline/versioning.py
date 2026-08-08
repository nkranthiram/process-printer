"""Applies approved change(s) as a brand-new ProcessMapVersion.

Core rule (see docs/process-methodology.md, architecture.md): the process map is
never edited in place. Every applied change (or set of changes, approved
together) clones the current version's tasks and edges into a new
ProcessMapVersion row, applies the mutation(s) to the clone, validates the
result with the same structural checks used at build time
(app/pipeline/synthesis.py's DAG validator), and only commits if it's still a
valid DAG. The old version is left completely untouched.

Two entry points:
- apply_change: one edit -> one version (the original per-message ChangeRequest
  flow, unchanged behavior).
- apply_change_set: N edits, approved together in one BPA confirm action (the
  "Review & Apply Changes" consolidated flow) -> exactly ONE version if every
  edit validates; if any edit fails, nothing is committed and the caller learns
  exactly which edit failed. This is the versioning granularity the
  claude/gpt debate converged on: the unit of a version is "whatever a human
  approved together," not "one edit" or "one whole chat session" by default.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.process_map import ProcessEdge, ProcessMapVersion, ProcessTask
from app.models.validation import ValidationCase
from app.pipeline.synthesis import (
    EdgeDraft,
    ProcessMapDraft,
    TaskDraft,
    VALID_NODE_TYPES,
    validate_dag_structure,
    validate_node_types,
)


class ChangeApplyError(Exception):
    """Raised when a proposed change would break the process map (invalid DAG,
    unknown node type, references a task that doesn't exist, etc). The caller
    catches this and marks the request/item apply_failed with the reason,
    rather than silently committing a broken map."""

    def __init__(self, message: str, item_id: str | None = None):
        super().__init__(message)
        self.item_id = item_id  # set by apply_change_set so the API layer can
        # report exactly which DraftChangeItem broke the batch


@dataclass
class AppliedChange:
    new_version: ProcessMapVersion
    change_summary: str


@dataclass
class AppliedChangeSet:
    new_version: ProcessMapVersion
    change_summaries: list[str]


def _next_label(current_label: str) -> str:
    if current_label.startswith("v") and current_label[1:].split("-")[0].isdigit():
        n = int(current_label[1:].split("-")[0])
        return f"v{n + 1}"
    return f"{current_label}-revised"


def _draft_from_version(db: Session, pm: ProcessMapVersion) -> ProcessMapDraft:
    tasks = db.query(ProcessTask).filter_by(process_map_id=pm.id).all()
    edges = db.query(ProcessEdge).filter_by(process_map_id=pm.id).all()
    return ProcessMapDraft(
        process_name="",
        tasks=[
            TaskDraft(
                id=t.id, node_type=t.node_type, title=t.title, description=t.description,
                claim_refs=json.loads(t.claim_refs or "[]"), position=(t.position_x, t.position_y),
            )
            for t in tasks
        ],
        edges=[EdgeDraft(from_id=e.from_task_id, to_id=e.to_task_id, label=e.condition_label or "") for e in edges],
    )


def _validate_structure_only(draft: ProcessMapDraft) -> list[str]:
    """Same structural checks as the build-time validator, minus claim-ref
    validation — claim_refs on a chat-proposed task aren't required to resolve
    to existing AtomicClaim rows (a BPA-added step may have no document backing
    at all, which is fine and expected; it just won't carry citations)."""
    errors: list[str] = []
    errors += validate_node_types(draft).errors
    errors += validate_dag_structure(draft).errors
    return errors


def _apply_single_change(draft: ProcessMapDraft, change_type: str, payload: dict) -> str:
    """Mutates `draft` IN PLACE to apply one edit, validates the result, and
    returns a human-readable summary. Raises ChangeApplyError (leaving draft
    partially mutated — callers that need atomicity across multiple edits must
    operate on a throwaway copy, see apply_change_set) if the edit is invalid
    or the resulting structure would be invalid.

    Payload shapes:
      add_task:    {"after_task_id": str, "node_type": str, "title": str,
                     "description": str, "condition_label": str | None}
      remove_task: {"task_id": str}
      modify_task: {"task_id": str, "title": str | None, "description": str | None,
                     "node_type": str | None}
      modify_edge: {"edge_from": str, "edge_to": str, "condition_label": str}
    """
    task_by_id = {t.id: t for t in draft.tasks}
    summary: str

    if change_type == "add_task":
        after_id = payload["after_task_id"]
        if after_id not in task_by_id:
            raise ChangeApplyError(f"after_task_id {after_id!r} does not exist in the current map")
        node_type = payload.get("node_type", "classification")
        if node_type not in VALID_NODE_TYPES:
            raise ChangeApplyError(f"invalid node_type {node_type!r}")
        new_id = f"new-{payload.get('title', 'task')[:12].lower().replace(' ', '-')}-{len(draft.tasks)}-{uuid.uuid4().hex[:6]}"
        anchor = task_by_id[after_id]
        new_task = TaskDraft(
            id=new_id, node_type=node_type, title=payload["title"],
            description=payload.get("description", ""), claim_refs=[],
            position=(anchor.position[0], anchor.position[1] + 0.5),
        )
        outgoing = [e for e in draft.edges if e.from_id == after_id]
        draft.edges = [e for e in draft.edges if e.from_id != after_id]
        draft.edges.append(EdgeDraft(from_id=after_id, to_id=new_id, label=payload.get("condition_label") or ""))
        for e in outgoing:
            draft.edges.append(EdgeDraft(from_id=new_id, to_id=e.to_id, label=e.label))
        draft.tasks.append(new_task)
        summary = f"Added step \"{new_task.title}\" after \"{anchor.title}\""

    elif change_type == "remove_task":
        task_id = payload["task_id"]
        if task_id not in task_by_id:
            raise ChangeApplyError(f"task_id {task_id!r} does not exist in the current map")
        removed = task_by_id[task_id]
        incoming = [e for e in draft.edges if e.to_id == task_id]
        outgoing = [e for e in draft.edges if e.from_id == task_id]
        draft.edges = [e for e in draft.edges if e.from_id != task_id and e.to_id != task_id]
        for inc in incoming:
            for out in outgoing:
                draft.edges.append(EdgeDraft(from_id=inc.from_id, to_id=out.to_id, label=inc.label))
        draft.tasks = [t for t in draft.tasks if t.id != task_id]
        summary = f"Removed step \"{removed.title}\""

    elif change_type == "modify_task":
        task_id = payload["task_id"]
        if task_id not in task_by_id:
            raise ChangeApplyError(f"task_id {task_id!r} does not exist in the current map")
        t = task_by_id[task_id]
        old_title = t.title
        if payload.get("title"):
            t.title = payload["title"]
        if payload.get("description"):
            t.description = payload["description"]
        if payload.get("node_type"):
            if payload["node_type"] not in VALID_NODE_TYPES:
                raise ChangeApplyError(f"invalid node_type {payload['node_type']!r}")
            t.node_type = payload["node_type"]
        summary = f"Updated step \"{old_title}\""

    elif change_type == "modify_edge":
        matched = False
        for e in draft.edges:
            if e.from_id == payload["edge_from"] and e.to_id == payload["edge_to"]:
                e.label = payload["condition_label"]
                matched = True
        if not matched:
            raise ChangeApplyError("no matching edge found to modify")
        summary = "Updated a transition condition"

    else:
        raise ChangeApplyError(f"unknown change_type {change_type!r}")

    errors = _validate_structure_only(draft)
    if errors:
        raise ChangeApplyError("resulting process map would be invalid: " + "; ".join(errors))

    return summary


def _persist_new_version(db: Session, document_id: str, base_version: ProcessMapVersion,
                          draft: ProcessMapDraft, change_summary: str, changed_by: str) -> ProcessMapVersion:
    new_version = ProcessMapVersion(
        document_id=document_id,
        version_label=_next_label(base_version.version_label),
        status="draft",
        change_summary=change_summary,
        changed_by=changed_by,
    )
    db.add(new_version)
    db.flush()  # assign new_version.id

    # process_tasks.id is a global primary key across every version, not scoped
    # per process_map_id — cloning a task into a new version with its OLD id
    # would collide with the still-existing row from the base version. Every
    # task in the new version (carried-over or newly added) gets a fresh id;
    # edges are rewritten through this map so they still point at the right
    # (new) rows.
    id_map = {t.id: str(uuid.uuid4()) for t in draft.tasks}

    for t in draft.tasks:
        db.add(ProcessTask(
            id=id_map[t.id], process_map_id=new_version.id,
            node_type=t.node_type, title=t.title, description=t.description,
            position_x=t.position[0], position_y=t.position[1],
            claim_refs=json.dumps(t.claim_refs),
        ))
    for e in draft.edges:
        db.add(ProcessEdge(
            process_map_id=new_version.id,
            from_task_id=id_map[e.from_id], to_task_id=id_map[e.to_id],
            condition_label=e.label or None,
        ))

    # Carry forward scenario validation cases whose traced path is still fully
    # intact in the new structure (every task on the path survived, remapped
    # via id_map). A case whose path walked through a task this edit removed
    # is no longer a valid trace of anything -- silently carrying it forward
    # with the same pass/fail verdict would misrepresent a scenario that was
    # never actually re-traced, so it's dropped instead and named in the
    # returned summary (see apply_change/apply_change_set callers) rather than
    # left for a human to discover missing later. Re-tracing broken scenarios
    # against the new map is manual, per scenario-validation/SKILL.md -- this
    # only carries forward what's still provably true.
    prior_cases = db.query(ValidationCase).filter_by(process_map_id=base_version.id).all()
    dropped_case_names: list[str] = []
    for case in prior_cases:
        old_path = json.loads(case.traced_path)
        if all(tid in id_map for tid in old_path):
            db.add(ValidationCase(
                process_map_id=new_version.id,
                scenario_name=case.scenario_name,
                claim_description=case.claim_description,
                expected_outcome=case.expected_outcome,
                traced_path=json.dumps([id_map[tid] for tid in old_path]),
                actual_outcome=case.actual_outcome,
                result=case.result,
                notes=case.notes,
            ))
        else:
            dropped_case_names.append(case.scenario_name)
    new_version._dropped_validation_case_names = dropped_case_names  # not persisted; read by callers for the summary
    return new_version


def apply_change(db: Session, document_id: str, base_version: ProcessMapVersion,
                  change_type: str, payload: dict, changed_by: str) -> AppliedChange:
    """One edit -> one version. Unchanged behavior for the per-message
    ChangeRequest approval flow."""
    draft = _draft_from_version(db, base_version)
    summary = _apply_single_change(draft, change_type, payload)
    new_version = _persist_new_version(db, document_id, base_version, draft, summary, changed_by)
    dropped = getattr(new_version, "_dropped_validation_case_names", [])
    if dropped:
        summary += f" (dropped {len(dropped)} validation case(s) whose traced path no longer exists: {', '.join(dropped)})"
        new_version.change_summary = summary
    return AppliedChange(new_version=new_version, change_summary=summary)


@dataclass
class ChangeSetItemInput:
    item_id: str  # DraftChangeItem.id, for identifying the failing item on error
    change_type: str
    payload: dict


def apply_change_set(db: Session, document_id: str, base_version: ProcessMapVersion,
                      items: list[ChangeSetItemInput], changed_by: str) -> AppliedChangeSet:
    """N edits, approved together -> exactly ONE version if every edit
    validates. Applies each edit sequentially to a single in-memory draft
    (never persisted mid-sequence — nothing is written to the DB until the
    whole set succeeds), so a mid-set failure leaves the database completely
    untouched rather than a half-applied state. On failure, raises
    ChangeApplyError tagged with which item failed (via args[1]) so the caller
    can surface that specific item back into the review UI without discarding
    the others.
    """
    draft = _draft_from_version(db, base_version)
    summaries: list[str] = []

    for item in items:
        try:
            summary = _apply_single_change(draft, item.change_type, item.payload)
        except ChangeApplyError as e:
            # Re-raise with the failing item_id attached so the API layer can
            # report exactly which item broke the batch, not just "it failed."
            raise ChangeApplyError(str(e), item_id=item.item_id) from e
        summaries.append(summary)

    combined_summary = "; ".join(summaries)
    new_version = _persist_new_version(db, document_id, base_version, draft, combined_summary, changed_by)
    dropped = getattr(new_version, "_dropped_validation_case_names", [])
    if dropped:
        combined_summary += f" (dropped {len(dropped)} validation case(s) whose traced path no longer exists: {', '.join(dropped)})"
        new_version.change_summary = combined_summary
    return AppliedChangeSet(new_version=new_version, change_summaries=summaries)
