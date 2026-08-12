# Workflow alignment reports

Output of `skills/workflow-alignment-testing/SKILL.md` — one dated report per
run, comparing a specific `AgenticWorkflowVersion` against the specific
`ProcessMapVersion` it was generated from. Never overwritten; a new run adds
a new file, so alignment drift over time (as either artifact is re-versioned)
stays inspectable as history rather than only reflecting the latest state.

**Filename pattern**: `{document-slug}__pm-{process_map_version_label}__wf-{agentic_workflow_generator_version}__{run-date}.md`

**Index below is maintained by whoever runs the skill — add a row for every
report as it's produced.**

| Date | Document | Process map version | Workflow version | Verdict | Report |
|---|---|---|---|---|---|
| 2026-08-12 | AAMI Comprehensive Car Insurance | v2 | manual-agent-pass-v1 | **misaligned** — 2 coverage gaps, 2 citation-scope violations, 2/3 scenario mismatches, all traced to 2 root causes | `aami-comprehensive-car-insurance__pm-v2__wf-manual-agent-pass-v1__2026-08-12.md` |
