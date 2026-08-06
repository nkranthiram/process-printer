---
name: task-description-authoring
description: Write the handler/BPA-facing description for a single process-map
  task, grounded in its linked claims. Use for "write the task description",
  "explain how to carry out this step".
---

# Task Description Authoring

Every task in the process map needs a description a claims handler can act on
without going back to the source PDF — but the description has to stay
traceable to the claims that support it. This skill is the bridge between "what the
document says" (claims) and "what a person does" (a task description).

## Contract

- Written for the audience: a claims handler or BPA, not a developer. Plain
  language, second person or imperative ("Check whether...", "Confirm that...").
- Every substantive statement in the description is backed by at least one linked
  claim — no description states a rule, threshold, or condition that isn't in
  `claim_refs`.
- Citations are available on click/expand, not inline in the prose — the user
  explicitly asked for this UX (keeps the description readable; the audit trail
  is one click away, in `claim_refs` → `SourceSpan` → page/quote).
- Descriptions stay short enough to scan — a paragraph or a short list per task, not
  a restatement of every linked claim's full text.

## Procedure

1. Read every claim linked to the task. Group them by what they tell the handler to
   *do* (check X, confirm Y, calculate Z) versus what they tell the handler as
   *background* (a definition, a cross-reference).
2. Write the description as an instruction: what to check, in what order if it
   matters, and what outcome each check leads to (in plain terms — "if the driver
   was unlicensed, cover may still apply to the owner if they can show X").
3. Don't restate every exclusion verbatim — summarize the category and let the
   claim citations carry the specifics. E.g. "Check the general exclusions
   (impairment, unlawful use, unregistered vehicle, reckless driving, and others —
   see linked clauses)" beats pasting all nineteen bullet points into the task.
4. Flag anywhere the underlying claims leave a real judgment call to the handler
   (e.g. "reasonable distance", "not aware this could lead to further damage") —
   naming this explicitly is more useful to a BPA than papering over it, and it's
   exactly the kind of thing a Process Design Document reviewer needs to see.
5. Keep the description independent of any one process-map rendering — it should
   read sensibly as plain text pasted into a PDD, not rely on surrounding diagram
   context to make sense.

## Anti-patterns

| Don't | Do |
|---|---|
| Paste the full raw_quote of every linked claim into the description | Summarize; let citations (click-through) carry verbatim detail |
| State a number, threshold or rule not present in any linked claim | Trace every concrete statement to a claim_id, or don't state it |
| Write for a developer/rules-engine ("if condition_a AND NOT condition_b") | Write for a person: "Check whether... unless..." |
| Bury a genuine judgment-call term ("reasonable", "promptly") without flagging it | Name it explicitly — the BPA needs to know where discretion is required |

## Fallbacks

- A task with claims that pull in slightly different directions (e.g. a general
  rule and a narrower exception) — describe the general rule then the exception
  explicitly, don't average them into a blurred middle statement.

## Chains

```
process-map-synthesis → task-description-authoring → scenario-validation
```
