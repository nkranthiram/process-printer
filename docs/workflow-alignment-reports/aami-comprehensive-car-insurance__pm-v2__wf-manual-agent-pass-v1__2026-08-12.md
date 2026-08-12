# Workflow alignment report — AAMI Comprehensive Car Insurance

Run per `skills/workflow-alignment-testing/SKILL.md`, triggered by rebuilding
the Agentic Workflow frontend view and needing to confirm it's actually a
faithful replica of the process map before presenting it — not assumed.

**Process map under test**: `ProcessMapVersion` id `f130ceda-0dba-4e39-9c58-ab0563a154dc`,
label **v2**, status `draft`, 11 tasks.
**Agentic workflow under test**: generated from the *same exact* process-map
version id (confirmed programmatically, not assumed) — `generator_version`
**manual-agent-pass-v1**, 16 nodes, 29 edges.
**Run date**: 2026-08-12.

## 1. Coverage table

| Source task | Derived node(s) | Result |
|---|---|---|
| Capture the claim description | SVC-02 (Extract & normalize facts) | pass |
| Verify policyholder identity against certificate of insurance | BR-00 | pass |
| Confirm policy and incident validity | BR-01, GW-01 | pass |
| Check general exclusions | AG-02B | pass |
| Classify which specific cover applies | AG-02A | pass |
| Check the specific cover's own conditions | BR-02 | pass (see §3 — citation scope issue) |
| **Verify the claim is adequately evidenced** | **none** | **FAIL — no derived node** |
| **Determine at-fault status and applicable excess** | **none** | **FAIL — no derived node** |
| Determine settlement path: repair or total loss | AG-03, AG-04 | pass (see §3 — citation scope issue) |
| Reach the coverage decision | GW-02, GW-03, SVC-03 | pass |
| Escalate to manual review | HUM-02 | pass |

**9/11 covered, 2/11 failed.**

### Workflow-only nodes (no `source_task_title`)

| Node | Justification |
|---|---|
| SVC-01 — Ingest FNOL, documents & photos | Legitimate infra step the human map doesn't need to state explicitly (a handler receiving a claim implicitly has the documents already) |
| HUM-01 — Data Correction queue / info-request loop | Legitimate decomposition of "what happens when a fact is missing," which the human map handles implicitly via a human just asking for it |
| QA-01 — Async sampled QA lane | Legitimate — a governance control with no equivalent in a human map (see `docs/agentic-workflow-design.md` §6, §9.1) |
| AG-04 — Draft customer-facing explanation | Legitimate decide/draft split from AG-03, per the skill's own non-negotiable |

All four are justified; none flagged as suspicious.

## 2. Coverage gap detail — both real, not edge cases

- **"Verify the claim is adequately evidenced"** has zero derived nodes. Per
  its description, this task governs whether an exclusion-exception (e.g.
  "not aware further damage could occur," the reckless-act exception) can
  even be tested, and gates whether a claim is payable at all when it can't
  be evidenced. It's on the traced path of a real `ValidationCase`
  ("mobile phone" scenario) in the process map, but no agentic-workflow node
  performs this check — the workflow currently jumps from AG-02B straight to
  BR-02/GW-02 with no evidence-sufficiency gate at all.
- **"Determine at-fault status and applicable excess"** has zero derived
  nodes. This is not a minor omission: its content (the not-at-fault
  three-detail waiver test, stacking excess types) turns out to have been
  **folded into BR-02 instead** — see §3.

## 3. Description & citation alignment table

| Source-task group | Mechanical claim-scope result | Judgment note |
|---|---|---|
| Confirm policy and incident validity | pass | consistent |
| Check general exclusions | pass — node claims are an exact subset of the task's own claims | consistent |
| Classify which specific cover applies | pass | consistent |
| Escalate to manual review | pass (no citations either side) | consistent |
| Reach the coverage decision | pass (no citations either side) | consistent |
| Verify policyholder identity... | pass (no citations either side) | consistent |
| Capture the claim description → SVC-02 | **borderline pass** — SVC-02 cites `incident_definition`, which belongs to the immediately-*next* task ("Confirm policy and incident validity"), not its own source task | Judged acceptable: SVC-02's stated job is "extract & normalize facts," which plausibly needs to know what "incident" means to extract it — but this is exactly the kind of borderline case this check exists to surface for a human call, not silently pass |
| **Check the specific cover's own conditions → BR-02** | **FAIL** — BR-02 cites `excess`, `excess_types`, `not_at_fault_excess_waiver`, none of which belong to its own source task. All three belong to **"Determine at-fault status and applicable excess"** — a task **two hops away in the graph** (not directly adjacent) and itself uncovered (§2) | BR-02's actual spec content ("Sub-limits, excess & waiting-period check") *is* genuinely about excess — but this means the at-fault-determination judgment itself (driver contribution, the not-at-fault three-detail test) is **not represented as a decision anywhere in the workflow** — its output (the excess figure) appears in BR-02, but the reasoning that produces it doesn't |
| **Determine settlement path → AG-03, AG-04** | **FAIL** — AG-03 cites `transport_cover`, `new_car_after_total_loss`, `hire_car_after_theft`. None belong to any *current* v2 task. All three belong to **"Check additional and optional covers"** — a task that **was removed from the process map in v2** (see `backend/data/change_log/0001_identity_check_and_remove_additional_covers.json`) | This is stale-version drift, not a scope error: the agentic workflow was generated against v2 (confirmed in the header), but its underlying spec content (`data/aami_agentic_workflow.json`) predates the additional-covers removal and was never regenerated to match. AG-03/AG-04 need to either drop these citations or the workflow needs regenerating post-removal |

## 4. Outcome-equivalence mapping (stated explicitly, per the skill's contract)

| Process-map terminal category | Agentic-workflow terminal state |
|---|---|
| "Not covered", auto (no escalation in the traced path) | Auto-processed close via `GW-02`'s **`deterministic decline`** branch → `SVC-03` → `QA-01` (async sample) |
| "Escalate to manual review" | Routed to `HUM-02` (Action Center) via **any** `agent-judgment adverse` edge |

**A structural finding surfaced by writing this mapping down, not by eyeballing it**: `GW-02`'s own `decision_logic` states its `deterministic decline` branch is fed *only* by `BR-01`'s fail edge — never by `AG-02B`. Every `AG-02B` exclusion hit (`excluded or needs_human`) routes to `GW-02`'s `agent-judgment adverse` branch → `HUM-02`, with **no path for an agent-screened exclusion to auto-decline**, regardless of how clean or unambiguous the case is. This is a deliberate reading of the design doc's escalation-scoping rule (an *agent* applying an exclusion is agent interpretation, full stop, even when the specific instance is unambiguous) — but it's a real behavioral divergence from how the process map's two clean-exclusion scenarios below actually run.

## 5. Scenario outcome table

Reused the process map's existing `ValidationCase`s (3 of the original 5 currently carry forward to v2 — 2 were dropped when "Check additional and optional covers" was removed, per `docs/process-map-snapshots/README.md`). Traced by hand against the workflow graph, per the skill's procedure (no automated test-runner exists yet — disclosed, not hidden).

| Scenario | Process-map outcome | Workflow-traced outcome | Result |
|---|---|---|---|
| Driver over legal alcohol limit, single-vehicle crash | Not covered, **auto**, no escalation | `AG-02B` clean exclusion hit → `GW-02` → **`HUM-02`** (per §4's finding — no auto-decline path exists) | **FAIL** on escalation behavior (financial substance — "not covered" — would still match once a human approves it, but the process diverges: the map's clean auto-decline has no equivalent auto path in the workflow) |
| Unattended, unlocked, keys-in-car theft | Not covered, **auto**, no escalation | Same as above — `AG-02B` → `GW-02` → `HUM-02` | **FAIL**, same reason |
| Illegal mobile phone use, causal link unclear | Escalate to manual review | `AG-02B` low-confidence/discretionary flag → `GW-02` → `HUM-02` | **PASS** |

**1/3 pass, 2/3 fail** under the strict process-fidelity reading of the mapping above. Both failures share the same root cause (§4's finding), not two independent bugs.

## 6. Summary

| Check | Score |
|---|---|
| Coverage | 9/11 (2 gaps) |
| Description/citation alignment | 7/9 groups clean, 1 borderline-accepted, 2 fail |
| Outcome equivalence | 1/3 pass, 2/3 fail |

**Overall verdict: `misaligned`.**

This is not a marginal call — three independent findings converge on the
same two underlying causes:

1. **"Determine at-fault status and applicable excess" has no node**, and
   its content leaked into `BR-02` under someone else's citation scope
   (§3), which is exactly the kind of drift the coverage check exists to
   catch before it's invisible.
2. **The agentic workflow spec predates the v2 process-map edit** that
   removed "Check additional and optional covers" — `AG-03` still carries
   citations to claims that belong to a task that no longer exists.
3. **`GW-02` structurally cannot auto-decline an agent-screened exclusion**,
   which is arguably the *correct*, more conservative reading of the design
   doc's own escalation-scoping rule — but it means 2 of 3 live regression
   scenarios no longer reproduce the process map's literal auto-decline
   path, and that's worth a deliberate BPA decision, not a silent
   divergence.

## Recommendation

Regenerate the agentic workflow (or hand-patch it) to: (a) add a node for
"Determine at-fault status and applicable excess" and move the
`excess`/`excess_types`/`not_at_fault_excess_waiver` citations onto it
rather than `BR-02`; (b) add a node for "Verify the claim is adequately
evidenced"; (c) drop or re-scope `AG-03`'s stale additional-covers
citations; (d) get an explicit BPA decision on whether a clean,
high-confidence agent-screened exclusion should ever auto-decline, or
whether the current always-escalate behavior is intentional and the process
map's original "not covered, auto" framing for those two scenarios should
be corrected instead (since the process map predates the workflow's more
conservative design).

Until these are addressed, the "Agentic workflow" view in the app should be
read as a **draft**, not a validated replica of the current process map.
