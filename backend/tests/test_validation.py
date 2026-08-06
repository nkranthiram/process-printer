from app.pipeline.synthesis import load_process_map
from app.pipeline.validation import (
    load_manual_validation_cases,
    validate_traced_paths,
    ValidationCaseDraft,
)


def test_aami_validation_cases_traced_paths_are_real():
    cases = load_manual_validation_cases()
    process_map = load_process_map()
    report = validate_traced_paths(cases, process_map)
    if not report.valid:
        raise AssertionError("Validation case traces are invalid:\n" + "\n".join(report.errors))
    assert report.valid


def test_at_least_five_scenarios_and_not_all_happy_path():
    """Per the skill's contract: cover more than just the easy path."""
    cases = load_manual_validation_cases()
    assert len(cases) >= 5
    outcomes = [c.traced_path[-1] for c in cases]
    # t10 = decision, t11 = human_review in the AAMI map — at least one case should
    # NOT end at the straightforward decision node.
    assert len(set(outcomes)) > 1, "every scenario ends at the same terminal node — no exclusion/escalation case?"


def test_all_cases_pass():
    """The seeded scenarios are asserted to actually pass — if a future edit to the
    process map breaks one of these traces, this is what should go red."""
    cases = load_manual_validation_cases()
    failed = [c.scenario_name for c in cases if c.result != "pass"]
    assert not failed, f"expected all seeded scenarios to pass, but these did not: {failed}"


def test_validate_traced_paths_catches_a_nonexistent_edge():
    process_map = load_process_map()
    bad = ValidationCaseDraft(
        scenario_name="broken trace",
        claim_description="x",
        expected_outcome="x",
        traced_path=["t1", "t8"],  # not a real edge — skips the whole middle of the map
        actual_outcome="x",
        result="pass",
    )
    report = validate_traced_paths([bad], process_map)
    assert not report.valid
    assert any("no real edge" in e for e in report.errors)


def test_validate_traced_paths_catches_wrong_start_node():
    process_map = load_process_map()
    bad = ValidationCaseDraft(
        scenario_name="wrong start",
        claim_description="x",
        expected_outcome="x",
        traced_path=["t2", "t3", "t10"],
        actual_outcome="x",
        result="pass",
    )
    report = validate_traced_paths([bad], process_map)
    assert not report.valid
    assert any("expected start node" in e for e in report.errors)


def test_validate_traced_paths_catches_non_terminal_ending():
    process_map = load_process_map()
    bad = ValidationCaseDraft(
        scenario_name="dangling trace",
        claim_description="x",
        expected_outcome="x",
        traced_path=["t1", "t2", "t3"],  # ends mid-process, not at a decision/human_review node
        actual_outcome="x",
        result="pass",
    )
    report = validate_traced_paths([bad], process_map)
    assert not report.valid
    assert any("not a terminal node" in e for e in report.errors)
