# How Process Printer turns document text into a process map

This is the human-readable explainer. If you want the machine-executable
version — the exact rules an agent follows at each stage — see
`skills/process-printer/SKILL.md` and the individual skill files it routes to.
This document exists so a Business Process Analyst (or anyone reviewing the
output) can understand *why* the map looks the way it does, without reading
eight separate skill contracts.

## The problem this solves

Given one or more source documents (a policy, procedure, regulation — currently
proven against the AAMI Comprehensive Car Insurance PDS), produce a process map
that a claims handler can actually follow to determine claim coverage, plus a
list of everything the document(s) don't clearly resolve — without inventing
rules that aren't actually in the source, and without hiding the fact that a
document contradicts itself or another document.

Two things make this hard, and the whole design is a response to them:

1. **Plausible-sounding output that isn't actually grounded in the text.** An
   LLM asked to "read this policy and build a process map" will happily produce
   something that looks right and cites nothing, or cites things loosely. If a
   claims handler can't click through to the exact sentence a rule came from,
   the map isn't trustworthy enough to use for a real coverage decision.
2. **Documents disagree with themselves, or with each other, more than people
   expect.** A single 76-page PDS has genuine gaps and ambiguous wording.
   Multiple documents (e.g. a PDS plus a later product update) can flatly
   contradict each other, or look like they contradict when really one just
   narrows the other's scope. A process map that silently picks an answer in
   either case is worse than one that flags it.

Everything below follows from taking those two problems seriously rather than
optimizing for a map that merely looks complete.

## The core idea: separate "what the document says" from "what the process is"

The single most important design decision is **not asking one step to both read
the document and design the process**. That collapses two very different jobs —
faithful extraction, and human-usable synthesis — into one pass, and that's the
most common way this kind of system quietly invents things. Instead, the work is
split into distinct stages, each with one job:

```
source documents  →  citable text spans  →  atomic claims  →  process map + task descriptions
                      (exact quotes)         (structured,       (what a handler
                                              typed, still         actually does)
                                              citable)
                                                    ↓
                                          gaps / contradictions
                                          (logged, never hidden)
```

## Stage by stage

### 1. Ingestion — turn the document into citable pieces

Before anything is interpreted, the raw text is split into small, exactly
quotable units ("spans") — one per paragraph or list item, each tagged with
where it came from (page number for a PDF, or a paragraph position for plain
text) and which section it's under. Nothing is summarized here. This stage's
only job is: make sure every later claim can point at an exact piece of text,
not a vague "somewhere around page 12."

*(Skills: `pdf-ingestion` for PDFs, `text-ingestion` for plain/pasted text —
same output shape either way, so everything downstream doesn't care which kind
of source it started from.)*

### 2. Claim extraction — pull out what the document actually states

Each document is read (independently — one document at a time, even if there
are several) to extract **atomic claims**: single, self-contained statements
like "windscreen damage is covered up to $X" or "modifications not declared to
us void cover for related damage," each one:

- typed (a rule, a definition, an exception, a condition, an exclusion, an
  evidence requirement),
- tied to exactly one exact quote from the source (checked mechanically — a
  quote that doesn't literally appear in the document is rejected, not "close
  enough"),
- scoped to the process being mapped. A 76-page policy has sections on premium
  calculation, complaints handling, and a dozen other things irrelevant to
  "does this claim get covered" — those are deliberately left out, not missed.

If the document is silent on something the process would need (e.g. it never
actually says how many days you have to report a claim), **no claim is
invented to fill the gap.** That silence becomes a logged gap instead (see
Stage 4) — a plausible-sounding invented rule is far more dangerous than an
honest blank.

### 3. Reconciliation — only when there's more than one document

Single-document runs (like the AAMI build) skip this stage — there's nothing
to reconcile against. When two or more documents are involved, their claims
are compared to catch three different situations that all *look* similar from
a distance but need very different handling:

- **Genuine duplication** — two documents say the same thing; treated as one
  claim.
- **Real contradiction** — two documents can't both be right as written. Never
  resolved automatically. Logged for a human to decide, citing both sources.
- **False alarm** — two claims look like they conflict but actually don't,
  because one is just a narrower case of the other (an exception to a general
  rule), or they apply to different products/dates/conditions, or one document
  explicitly says it replaces the other (a "supersession" — this is the *one*
  case that gets resolved automatically, and only because the resolution is
  itself quoted directly from the text, not inferred).

Claims are never compared against every other claim in the whole corpus — that
doesn't scale and produces noise. They're grouped by subject first (e.g. all
claims about "windscreen cover" together), and only compared within that
group.

### 4. Gap and contradiction logging — surfaced, not buried

Every unresolved thing from Stages 2 and 3 — a missing rule, ambiguous
wording, a genuine cross-document contradiction — becomes an entry in an issue
log with a plain-language description and a reference back to the exact
source text involved. Per this project's standing rule: **the build never
pauses to ask about these mid-flight.** It logs everything and keeps going;
a human reviews the full list afterward and can course-correct in one pass,
rather than the build stalling on every individual ambiguity.

### 5. Process map synthesis — from claims to something a handler can follow

This is where the actual process map gets built: a small number of task-level
steps (not one node per clause — a "map" with 80 nodes isn't usable by a
person). Related claims are grouped into a step a handler recognizes as one
piece of work — "check whether the incident type is covered," "check for
applicable exclusions," "determine the excess" — connected by the paths a
handler would actually take (e.g. "if excluded, stop here"; "if ambiguous,
escalate"). Every node still carries the claims (and through them, the exact
quotes) it was built from — nothing in the map exists without a citation trail
back to Stage 1.

The map is deliberately kept at this level of detail — not a full
rule-engine-ready decision tree — because the target reader is a claims
handler or BPA understanding and validating the process, not a machine
executing it clause by clause.

### 6. Task descriptions — how to actually do each step

For every task node, a short handler-facing description explains how to carry
it out — written in plain instructional language, grounded in that task's
underlying claims, with citations available on click rather than cluttering
the prose inline. This is what makes the map usable on its own, not just a
diagram someone still has to go read the original document to act on. It's
also written with an eye to becoming the seed of a formal Process Design
Document later, once the map has been reviewed.

### 7. Testing — proving the map actually works, not just looks right

Three different checks, because each catches a different class of mistake:

- **Citation verification** — mechanically confirm every claim's quote really
  appears in its source document. Catches fabrication.
- **Structural validity** — confirm the map has no cycles and every path ends
  in a real outcome or an explicit "escalate to a human" node, never a dead
  end. Catches broken process logic.
- **Scenario tracing** — walk realistic, specific claim descriptions through
  the finished map exactly as a handler would, step by step, and record
  where each one ends up (covered / excluded / escalated) as evidence. Catches
  the case where the map is structurally fine but gives the wrong answer for a
  real situation. This is the closest thing to "does this actually work,"
  and it's why the AAMI build traced 5 concrete scenarios rather than relying
  on the map "looking" correct.

All three are proven with **red-before-green**: before trusting a test, it has
to first fail against a deliberately broken version of what it's checking —
otherwise a test that has never failed isn't evidence of anything.

## What this deliberately does *not* do

- It does not build or run an automated coverage-decision engine. The output
  is a map and task descriptions for a *person* to use — not a black box that
  decides claims on its own.
- It does not silently resolve genuine contradictions or fill genuine gaps
  with a plausible guess. Every such case is logged with its source citation
  and left for a human.
- It does not treat every difference between two documents as a contradiction
  — most cross-document "conflicts" turn out to be scope differences or
  documented exceptions once actually classified, and treating them all the
  same way would flood the reviewer with false alarms.

## Where each stage lives

| Stage | Skill file |
|---|---|
| Entry point / router | `skills/process-printer/SKILL.md` |
| Ingestion (PDF) | `skills/pdf-ingestion/SKILL.md` |
| Ingestion (plain text) | `skills/text-ingestion/SKILL.md` |
| Claim extraction | `skills/claim-extraction/SKILL.md` |
| Cross-document reconciliation (2+ docs only) | `skills/cross-document-reconciliation/SKILL.md` |
| Process map synthesis | `skills/process-map-synthesis/SKILL.md` |
| Task description authoring | `skills/task-description-authoring/SKILL.md` |
| Gap/ambiguity logging | `skills/gap-ambiguity-logging/SKILL.md` |
| Testing/validation | `skills/scenario-validation/SKILL.md` |

For the data model these stages populate and the concrete architectural
decisions behind them, see `architecture.md`. For what's actually been built
and tested so far, see `PROGRESS.md` and `docs/evidence/`.
