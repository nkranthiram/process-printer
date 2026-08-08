"""Replays a committed, version-controlled log of approved process-map edits on
top of the freshly-seeded v1 baseline, so the CURRENT state of the process map
(v2, v3, ...) is reproducible from a clean clone/DB, not just something that
happens to exist in someone's local, gitignored SQLite file.

Why this exists: apply_change_set() (see versioning.py) already applies a set
of edits atomically to produce a new ProcessMapVersion -- but it has only ever
been invoked live, through the API, against whatever task/edge row ids happen
to exist in that runtime's database. Those ids are regenerated on every fresh
seed (see _persist_new_version's id_map), so they can't be committed directly
into a change-log file and expected to still resolve on the next machine/run.

The fix: change-log entries reference tasks by their STABLE, human-readable
title (unique within a process map, same as what a BPA sees in the UI) instead
of a database row id. This module translates title references into whatever
the current run's real ids are, immediately before calling apply_change_set,
and keeps that title->id index up to date after each entry is applied so a
later entry in the log can reference a task that an earlier entry just added.

Change-log files live in backend/data/change_log/, one JSON file per approved
change set, applied in filename order (numeric prefix, e.g. 0001_*.json). Each
file is intentionally kept as the literal historical record of a real BPA
approval -- see docs/process-map-snapshots/README.md for how these get
authored from a live review session.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.orm import Session

from app.models.process_map import ProcessMapVersion, ProcessTask
from app.pipeline.versioning import ChangeApplyError, ChangeSetItemInput, apply_change_set

CHANGE_LOG_DIR = Path(__file__).parent.parent.parent / "data" / "change_log"

# Payload keys that reference a task BY TITLE in a change-log file, mapped to
# the id-based key apply_change_set's underlying payload actually expects.
_TITLE_KEYS_BY_CHANGE_TYPE: dict[str, dict[str, str]] = {
    "remove_task": {"task_title": "task_id"},
    "modify_task": {"task_title": "task_id"},
    "add_task": {"after_task_title": "after_task_id"},
    "modify_edge": {"edge_from_title": "edge_from", "edge_to_title": "edge_to"},
}


class ChangeLogError(Exception):
    """Raised when a committed change-log entry can't be replayed -- e.g. it
    references a task title that doesn't exist in the map at that point in
    the log. Distinct from ChangeApplyError (a structurally invalid edit)
    so callers can tell "the log file is stale/wrong" apart from "the edit
    itself would break the DAG"."""


@dataclass
class ChangeLogEntry:
    filename: str
    changed_by: str
    items: list[dict]


def load_change_log(path: Path | None = None) -> list[ChangeLogEntry]:
    """Loads all committed change-log files in deterministic (filename) order.
    Returns [] if the directory doesn't exist or is empty -- replaying an
    empty log is a no-op, not an error, so a document with no approved edits
    yet still seeds cleanly at v1."""
    directory = path or CHANGE_LOG_DIR
    if not directory.exists():
        return []
    entries = []
    for f in sorted(directory.glob("*.json")):
        data = json.loads(f.read_text())
        entries.append(ChangeLogEntry(filename=f.name, changed_by=data["changed_by"], items=data["items"]))
    return entries


def _title_index(db: Session, process_map_id: str) -> dict[str, str]:
    return {t.title: t.id for t in db.query(ProcessTask).filter_by(process_map_id=process_map_id).all()}


def _resolve_payload(change_type: str, payload: dict, title_index: dict[str, str], entry_filename: str) -> dict:
    key_map = _TITLE_KEYS_BY_CHANGE_TYPE.get(change_type, {})
    resolved = dict(payload)
    for title_key, id_key in key_map.items():
        if title_key not in resolved:
            continue
        title = resolved.pop(title_key)
        if title not in title_index:
            raise ChangeLogError(
                f"{entry_filename}: change_type={change_type!r} references task title {title!r}, "
                f"which does not exist in the process map at this point in the log. "
                f"Known titles: {sorted(title_index)}"
            )
        resolved[id_key] = title_index[title]
    return resolved


def apply_change_log(db: Session, document_id: str, base_version: ProcessMapVersion) -> ProcessMapVersion:
    """Replays every committed change-log entry, in order, on top of
    base_version. Returns the final ProcessMapVersion (base_version itself if
    the log is empty). Each entry becomes exactly one new ProcessMapVersion,
    matching how it was actually approved live (apply_change_set semantics:
    all-or-nothing per entry)."""
    current = base_version
    for entry in load_change_log():
        title_index = _title_index(db, current.id)
        items = [
            ChangeSetItemInput(
                item_id=f"{entry.filename}:{i}",
                change_type=item["change_type"],
                payload=_resolve_payload(item["change_type"], item["payload"], title_index, entry.filename),
            )
            for i, item in enumerate(entry.items)
        ]
        try:
            result = apply_change_set(db, document_id, current, items, entry.changed_by)
        except ChangeApplyError as e:
            raise ChangeLogError(f"{entry.filename}: replay failed on item {e.item_id!r}: {e}") from e
        # SessionLocal is configured with autoflush=False (see app/database.py),
        # so the new version's task/edge rows aren't visible to a query yet --
        # flush explicitly before the next entry's title_index is built off them.
        db.flush()
        current = result.new_version
    return current
