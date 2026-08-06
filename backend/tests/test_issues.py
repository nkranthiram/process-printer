from app.pipeline.extraction import load_manual_seed
from app.pipeline.synthesis import load_process_map
from app.pipeline.issues import load_manual_issues, validate_issues, IssueDraft


def test_aami_issue_log_is_valid():
    issues = load_manual_issues()
    process_map = load_process_map()
    claims = load_manual_seed()
    report = validate_issues(issues, process_map, claims)
    if not report.valid:
        raise AssertionError("Issue log validation failed:\n" + "\n".join(report.errors))
    assert len(issues) >= 3  # a real single-document PDS should still surface some gaps/ambiguities


def test_issue_types_are_gap_or_ambiguity_or_low_confidence():
    issues = load_manual_issues()
    for i in issues:
        assert i.issue_type in {"gap", "ambiguity", "low_confidence_extraction"}


def test_validate_issues_catches_unknown_task_reference():
    process_map = load_process_map()
    claims = load_manual_seed()
    bad = IssueDraft(
        issue_type="gap",
        title="test",
        description="test description",
        process_task_id="task-does-not-exist",
        claim_refs=[],
    )
    report = validate_issues([bad], process_map, claims)
    assert not report.valid
    assert any("task-does-not-exist" in e for e in report.errors)


def test_validate_issues_catches_unknown_claim_reference():
    process_map = load_process_map()
    claims = load_manual_seed()
    bad = IssueDraft(
        issue_type="ambiguity",
        title="test",
        description="test description",
        process_task_id=None,
        claim_refs=["subject_does_not_exist"],
    )
    report = validate_issues([bad], process_map, claims)
    assert not report.valid
    assert any("subject_does_not_exist" in e for e in report.errors)


def test_validate_issues_catches_empty_description():
    process_map = load_process_map()
    claims = load_manual_seed()
    bad = IssueDraft(issue_type="gap", title="test", description="   ", process_task_id=None, claim_refs=[])
    report = validate_issues([bad], process_map, claims)
    assert not report.valid
