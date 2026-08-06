"""Gap/ambiguity logging — see skills/gap-ambiguity-logging/SKILL.md.

Loads the manually-logged issues for this run and validates their references
resolve to real tasks/claims, same discipline as synthesis.py's validators.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from app.pipeline.extraction import ClaimDraft
from app.pipeline.synthesis import ProcessMapDraft

DATA_DIR = Path(__file__).parent.parent.parent / "data"

VALID_ISSUE_TYPES = {"gap", "ambiguity", "low_confidence_extraction"}


@dataclass
class IssueDraft:
    issue_type: str
    title: str
    description: str
    process_task_id: str | None
    claim_refs: list[str]


def load_manual_issues(path: Path | None = None) -> list[IssueDraft]:
    path = path or (DATA_DIR / "aami_issues.json")
    raw = json.loads(path.read_text())
    return [
        IssueDraft(
            issue_type=i["issue_type"],
            title=i["title"],
            description=i["description"],
            process_task_id=i.get("process_task_id"),
            claim_refs=i.get("claim_refs", []),
        )
        for i in raw
    ]


@dataclass
class ValidationReport:
    errors: list[str] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return not self.errors


def validate_issues(
    issues: list[IssueDraft], process_map: ProcessMapDraft, claims: list[ClaimDraft]
) -> ValidationReport:
    report = ValidationReport()
    known_task_ids = {t.id for t in process_map.tasks}
    known_subjects = {c.subject for c in claims}

    for idx, issue in enumerate(issues):
        if issue.issue_type not in VALID_ISSUE_TYPES:
            report.errors.append(f"issue #{idx} ({issue.title!r}) has invalid issue_type {issue.issue_type!r}")
        if issue.process_task_id is not None and issue.process_task_id not in known_task_ids:
            report.errors.append(
                f"issue #{idx} ({issue.title!r}) references unknown task {issue.process_task_id!r}"
            )
        for ref in issue.claim_refs:
            if ref not in known_subjects:
                report.errors.append(f"issue #{idx} ({issue.title!r}) references unknown claim subject {ref!r}")
        if not issue.description.strip():
            report.errors.append(f"issue #{idx} ({issue.title!r}) has an empty description")

    return report
