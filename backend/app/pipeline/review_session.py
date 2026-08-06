"""Consolidation pass for the "Review & Apply Changes" flow — see
docs/evidence for the claude/gpt debate this design resolves.

Contract (non-negotiable per that debate):
- The LLM may compress, cluster, and propose; it may NEVER originate an
  ungrounded edit. Every item must cite the transcript turns it came from.
- A revised/contradicted earlier request becomes `superseded_by_item_id`, not
  a silent overwrite.
- A genuinely ambiguous request becomes `needs_clarification`, never a guess.
- No cold cross-message dedup magic beyond what's described here — this is a
  deliberately simple v1 (see the "known simplifications" note at the bottom
  of this file).
"""
from __future__ import annotations

import json
import os
import re

from sqlalchemy.orm import Session

from app.models.claim import AtomicClaim  # noqa: F401  (kept for type clarity in docstrings)
from app.models.process_map import ProcessMapVersion, ProcessTask
from app.models.review_session import DraftChangeItem, ReviewSession

VALID_CHANGE_TYPES = {"add_task", "remove_task", "modify_task", "modify_edge", "needs_clarification"}


def get_or_create_open_session(db: Session, document_id: str) -> ReviewSession:
    """Reuses the current open session for a document if one exists (so items
    keep accumulating across chat turns within one review), otherwise creates
    a new one pinned to the current HEAD version — see the "stale base
    version" pitfall from the design debate: a session's base is fixed at
    creation, and confirm-time re-checks it hasn't moved (see routes.py)."""
    existing = (
        db.query(ReviewSession)
        .filter_by(document_id=document_id, status="open")
        .order_by(ReviewSession.created_at.desc())
        .first()
    )
    if existing:
        return existing

    base_pm = (
        db.query(ProcessMapVersion)
        .filter_by(document_id=document_id)
        .order_by(ProcessMapVersion.created_at.desc())
        .first()
    )
    if base_pm is None:
        raise ValueError(f"No process map exists yet for document {document_id}")

    session = ReviewSession(document_id=document_id, base_process_map_id=base_pm.id, status="open")
    db.add(session)
    db.flush()
    return session


def _task_context(db: Session, process_map_id: str) -> str:
    tasks = db.query(ProcessTask).filter_by(process_map_id=process_map_id).all()
    return "\n".join(f"- {t.id}: {t.title}" for t in tasks)


def _strip_code_fence(text: str) -> str:
    return re.sub(r"^```(json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()


def consolidate_transcript(
    db: Session, session: ReviewSession, transcript: list[dict],
) -> list[DraftChangeItem]:
    """Runs a reconciliation pass over the full conversation transcript
    (`[{"role": "user"|"assistant", "text": str, "ref": str}, ...]`) plus any
    already-drafted items for this session, and returns the resulting active
    (non-superseded) DraftChangeItem rows for the session.

    This is a RECONCILIATION pass, not a from-scratch summarization — it's
    told about existing items and asked to reuse/supersede/extend them, not
    re-derive everything blind (see the debate's "incremental over cold-read"
    conclusion). Since this app's chat endpoint is currently stateless
    per-message (no server-side transcript persistence), the frontend is the
    one accumulating and supplying the transcript here — this call is what
    actually reads it and turns it into grounded, structured items.
    """
    existing_items = db.query(DraftChangeItem).filter_by(session_id=session.id).filter(
        DraftChangeItem.status.notin_(["superseded"])
    ).all()

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    task_context = _task_context(db, session.base_process_map_id)

    if api_key:
        drafted = _consolidate_with_llm(api_key, transcript, task_context, existing_items)
    else:
        drafted = _consolidate_heuristic(transcript, existing_items)

    return _persist_consolidation(db, session, drafted)


def _consolidate_with_llm(api_key: str, transcript: list[dict], task_context: str,
                           existing_items: list[DraftChangeItem]) -> list[dict]:
    import anthropic

    transcript_text = "\n".join(
        f"[{t.get('ref', '?')}] {t.get('role', 'user')}: {t.get('text', '')}" for t in transcript
    )
    existing_text = "\n".join(
        f"- {it.id}: {it.change_type} — {it.rationale or '(no rationale)'} (status={it.status})"
        for it in existing_items
    ) or "(none yet)"

    prompt = (
        "You are consolidating a Business Process Analyst's feedback conversation "
        "about a claim-coverage process map into a structured, reviewable list of "
        "proposed changes. This is a RECONCILIATION pass: some items may already "
        "exist from earlier in the conversation (listed below) — reuse them where "
        "still valid, supersede them if a later message changed the ask, and only "
        "add genuinely new items for material not already covered.\n\n"
        "Rules (non-negotiable):\n"
        "- Every item must be grounded in specific transcript turns — never invent "
        "an edit that isn't actually requested.\n"
        "- If a message is ambiguous or contradicts an earlier one without "
        "resolving it, emit a needs_clarification item instead of guessing.\n"
        "- If this item supersedes an existing item above, set supersedes_item_id "
        "to that item's id.\n"
        "- Ignore coverage-determination questions and pure explanations — only "
        "extract genuine requests to add/remove/modify a process-map step.\n\n"
        "Respond with ONLY a JSON array (no prose), each element:\n"
        '{"change_type": "add_task"|"remove_task"|"modify_task"|"modify_edge"|"needs_clarification", '
        '"payload": {...}, "rationale": "short reason", '
        '"source_message_refs": ["turn-1", "turn-3"], "supersedes_item_id": "<id>|null"}\n\n'
        "Payload shapes:\n"
        'add_task: {"after_task_id": "<id>", "node_type": "classification", "title": "...", "description": "..."}\n'
        'remove_task: {"task_id": "<id>"}\n'
        'modify_task: {"task_id": "<id>", "title": "...", "description": "..."}\n'
        'needs_clarification: {"note": "what is unclear"}\n\n'
        f"Existing draft items for this session:\n{existing_text}\n\n"
        f"Process map steps (id: title):\n{task_context}\n\n"
        f"Transcript:\n{transcript_text}"
    )
    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model="claude-sonnet-4-5-20250929", max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )
    text = _strip_code_fence(response.content[0].text)
    try:
        parsed = json.loads(text)
        if not isinstance(parsed, list):
            return []
        return [p for p in parsed if isinstance(p, dict) and p.get("change_type") in VALID_CHANGE_TYPES]
    except (json.JSONDecodeError, AttributeError):
        return []


def _consolidate_heuristic(transcript: list[dict], existing_items: list[DraftChangeItem]) -> list[dict]:
    """No-LLM-key fallback: deliberately conservative, same discipline as
    chat.py's heuristic draft_change_request — never guess structure without a
    model to help parse free text. Flags every user turn that looks like
    feedback as needs_clarification rather than fabricating a structured edit,
    so nothing ungrounded ever reaches the DAG."""
    drafted: list[dict] = []
    for t in transcript:
        if t.get("role") != "user":
            continue
        text = t.get("text", "")
        if any(w in text.lower() for w in ("add", "remove", "delete", "change", "modify", "update")):
            drafted.append({
                "change_type": "needs_clarification",
                "payload": {"note": "No LLM key configured — needs a human to translate this into a structured edit."},
                "rationale": text[:200],
                "source_message_refs": [t.get("ref", "?")],
                "supersedes_item_id": None,
            })
    return drafted


def _persist_consolidation(db: Session, session: ReviewSession, drafted: list[dict]) -> list[DraftChangeItem]:
    for d in drafted:
        supersedes_id = d.get("supersedes_item_id")
        if supersedes_id:
            old = db.query(DraftChangeItem).filter_by(id=supersedes_id, session_id=session.id).first()
            if old is not None:
                old.status = "superseded"

        item = DraftChangeItem(
            session_id=session.id,
            change_type=d["change_type"],
            proposed_change=json.dumps(d.get("payload", {})),
            rationale=d.get("rationale"),
            source_message_refs=json.dumps(d.get("source_message_refs", [])),
            status="needs_clarification" if d["change_type"] == "needs_clarification" else "draft",
        )
        db.add(item)
        db.flush()
        if supersedes_id:
            item.superseded_by_item_id = None  # this item supersedes, not superseded
            old_item = db.query(DraftChangeItem).filter_by(id=supersedes_id).first()
            if old_item:
                old_item.superseded_by_item_id = item.id

    session.status = "reconciled"
    db.flush()

    return db.query(DraftChangeItem).filter_by(session_id=session.id).filter(
        DraftChangeItem.status.notin_(["superseded"])
    ).all()


# Known simplifications in this v1 (disclosed, not hidden):
# - No dependency-aware clustering of coupled edits (e.g. a rename that also
#   touches an edge label) — each item is applied independently in
#   apply_change_set. Flagged in architecture.md as a follow-up.
# - The LLM consolidation prompt sees the whole transcript each call rather
#   than a true incremental per-turn update — a pragmatic compromise given
#   this app's chat endpoint has no server-side transcript persistence yet
#   (the frontend supplies the transcript). A real incremental pipeline would
#   need chat messages persisted server-side; see architecture.md.
