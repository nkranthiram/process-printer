# Skill Resolver — Process Printer (project-local)

Domain-specific skills for this project. See the parent ways-of-working repo's
`skills/RESOLVER.md` for generic, cross-project skills (ask-user, skill-creator,
etc.) — this table only covers what's specific to turning source document(s) into
a process map.

**Start at `process-printer/SKILL.md`** — it's the master/router skill and tells
you which stage to begin at and when to branch. This table is the quick-reference
underneath it.

| Trigger | Skill |
|---|---|
| Entry point — routes to everything below | `process-printer/SKILL.md` |
| Parsing an uploaded policy PDF into page/section/span-anchored text | `pdf-ingestion/SKILL.md` |
| Parsing raw/pasted text (no PDF) into paragraph/section-anchored text | `text-ingestion/SKILL.md` |
| Pulling atomic, citable claims out of parsed document text | `claim-extraction/SKILL.md` |
| Comparing claims across 2+ documents for duplicates/contradictions/supersession | `cross-document-reconciliation/SKILL.md` |
| Grouping atomic claims into a task-level process map (DAG) | `process-map-synthesis/SKILL.md` |
| Writing the handler/BPA-facing description for a process map task | `task-description-authoring/SKILL.md` |
| Recording something the document doesn't resolve, without pausing the build | `gap-ambiguity-logging/SKILL.md` |
| Sanity-checking a process map against a real claim scenario | `scenario-validation/SKILL.md` |
| Turning an approved process map into a builder-ready agentic workflow spec (deterministic/agent/human/gateway nodes) | `agentic-workflow-synthesis/SKILL.md` |

## Chain

```
                     ┌─ pdf-ingestion ──┐
(source documents) ─►│                  ├─► claim-extraction (per document)
                     └─ text-ingestion ─┘              │
                                            1 document  │  2+ documents
                                                ▼        ▼
                                     process-map-synthesis ◄── cross-document-reconciliation
                                        │              ↘                ↘
                                        ▼            gap-ambiguity-logging (throughout)
                             task-description-authoring
                                        │
                                        ▼
                             scenario-validation
                                        │
                                        ▼  (downstream, optional -- run once the
                                        │   human-facing map is approved, not before)
                             agentic-workflow-synthesis
```
