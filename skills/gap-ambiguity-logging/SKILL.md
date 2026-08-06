---
name: gap-ambiguity-logging
description: Record something the source document doesn't resolve, without pausing
  the build. Use for "log this gap", "flag this ambiguity", "the document doesn't
  say".
---

# Gap / Ambiguity Logging

Per explicit user instruction for this project: don't pause and ask when a gap or
ambiguity is found — log it and keep going. The human reviews the log afterward.
This skill exists so that instruction is followed consistently rather than
case-by-case judgment calls about whether something "seems worth pausing for."

## Contract

- Every `Issue` has a type (`gap` | `ambiguity` | `low_confidence_extraction`), a
  plain-language description a non-technical reviewer can understand, and a link to
  the process-map task it affects (if any) and the claims involved (if any)
- Logging an issue never blocks synthesis of the task it's attached to — the task
  still gets built, generally as a `human_review` node or with the gap named
  explicitly in its description, per task-description-authoring
- Issues are visible in the UI's issues/gaps panel, not buried in code comments or
  this repo's internal docs

## Procedure

1. When claim-extraction or process-map-synthesis hits something the document
   doesn't answer (a term used but never defined for this context, a benefit
   referenced but not detailed, two clauses that could both apply with no stated
   precedence), don't invent a resolution.
2. Classify it: `gap` (document is silent on something the process needs) vs.
   `ambiguity` (document says something but it's genuinely open to more than one
   reading) vs. `low_confidence_extraction` (the extraction itself is uncertain,
   not the document).
3. Write the description so a reviewer with no PDF in front of them understands the
   issue and what's at stake if it's read one way vs. another.
4. Link it to the relevant claim_ids and process_task_id.
5. Continue the build. The corresponding task node still gets synthesized —
   typically routed toward a `human_review` node, or with the open point named
   directly in its task description (task-description-authoring's "flag it
   explicitly" rule).

## Anti-patterns

| Don't | Do |
|---|---|
| Pause the build to ask the user about a gap | Log it, keep going — per this project's explicit instruction |
| Silently pick the more conservative (or more generous) reading | Log as `ambiguity`, state both readings, let the human decide |
| Bury the issue only in `raw_quote`/claim text | Write a plain-language `description` a non-PDF-reading reviewer can act on |
| Log an issue with no link back to the affected task | Always set `process_task_id` where one applies |

## Fallbacks

None — this skill has no external dependency; it's just discipline about what gets
written down and how, applied consistently rather than skipped when a gap "seems
minor."

## Chains

```
claim-extraction → gap-ambiguity-logging
process-map-synthesis → gap-ambiguity-logging
```
