"""Chatbot — repurposed (per explicit user instruction) as a feedback channel
for BPAs reviewing the process map, NOT a coverage-question answering tool.

Scope, enforced in code (not just prompt wording — see classify_intent):
- explain:  "why is this step here / what does this step do" -> answered from
  the process map + its citations, grounded, same retrieval as before.
- change_request: "add/remove/change a step" -> logged as a ChangeRequest
  (pending review), NEVER applied automatically. See app/pipeline/versioning.py
  for how an approved request becomes a new process map version.
- coverage_question: "is X covered", "what's my excess" -> explicitly refused.
  This app draws the process map; it does not determine claims. Refusing here,
  in code, means this holds even if a user's prompt tries to talk the LLM into
  answering anyway.
- general: anything else about the process/app -> a short grounded answer,
  same scope restriction (no coverage verdicts).
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.claim import AtomicClaim
from app.models.change_request import ChangeRequest
from app.models.process_map import ProcessMapVersion, ProcessTask

_STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "do", "does", "did", "for",
    "of", "to", "in", "on", "and", "or", "my", "i", "what", "how", "if", "will",
    "can", "it", "this", "that", "am", "be", "covered", "cover",
}

_COVERAGE_PATTERNS = [
    r"\bis\b.{0,60}\bcovered\b",
    r"\bam i covered\b",
    r"\bwill (i|this|it) be covered\b",
    r"\bhow much (excess|is my excess)\b",
    r"\bwhat('?s| is) my (excess|payout|claim)\b",
    r"\bshould i lodge a claim\b",
    r"\bwill (my|this) claim be (approved|denied|accepted|rejected)\b",
    r"\bdo i (have|get) cover\b",
]

_CHANGE_PATTERNS = [
    r"\b(add|insert|include)\b.*\b(step|task|node)\b",
    r"\b(remove|delete|drop)\b.*\b(step|task|node)\b",
    r"\b(change|update|rename|edit|fix|reword)\b.*\b(step|task|description|title)\b",
    r"\bwe should (add|remove|change)\b",
    r"\bcan you (add|remove|change)\b",
    r"\bthis step (is wrong|shouldn'?t be|should be)\b",
]

_EXPLAIN_PATTERNS = [
    r"^why\b",
    r"\bwhy (is|did|do|does|are)\b",
    r"\bwhat does .* (step|task) do\b",
    r"\bwalk me through\b",
    r"\bexplain\b",
]


def _tokenize(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9']+", text.lower())
    return {w for w in words if w not in _STOPWORDS and len(w) > 2}


@dataclass
class RetrievedTask:
    task: ProcessTask
    claims: list[AtomicClaim]
    score: int


def retrieve(db: Session, document_id: str, message: str, top_k: int = 3) -> list[RetrievedTask]:
    query_tokens = _tokenize(message)
    if not query_tokens:
        return []

    pm = (
        db.query(ProcessMapVersion)
        .filter_by(document_id=document_id)
        .order_by(ProcessMapVersion.created_at.desc())
        .first()
    )
    if pm is None:
        return []

    tasks = db.query(ProcessTask).filter_by(process_map_id=pm.id).all()
    claims_by_id = {c.id: c for c in db.query(AtomicClaim).filter_by(document_id=document_id).all()}

    scored: list[RetrievedTask] = []
    for t in tasks:
        claim_ids = json.loads(t.claim_refs or "[]")
        task_claims = [claims_by_id[cid] for cid in claim_ids if cid in claims_by_id]

        haystack = _tokenize(t.title + " " + t.description)
        for c in task_claims:
            haystack |= _tokenize(c.statement + " " + c.subject)

        score = len(query_tokens & haystack)
        if score > 0:
            scored.append(RetrievedTask(task=t, claims=task_claims, score=score))

    scored.sort(key=lambda r: r.score, reverse=True)
    return scored[:top_k]


def classify_intent(message: str) -> str:
    """Deterministic, regex-based classification — runs BEFORE any LLM call, so
    the coverage-question refusal can never be argued around by prompt content.
    LLM-assisted refinement (change_type/payload drafting) only happens after
    this gate, and only for the change_request path."""
    lower = message.lower()
    for pat in _COVERAGE_PATTERNS:
        if re.search(pat, lower):
            return "coverage_question"
    for pat in _CHANGE_PATTERNS:
        if re.search(pat, lower):
            return "change_request"
    for pat in _EXPLAIN_PATTERNS:
        if re.search(pat, lower):
            return "explain"
    return "general"


COVERAGE_REFUSAL = (
    "This app doesn't answer coverage questions — it's for reviewing and giving "
    "feedback on the *process map* itself (the steps a handler follows), not for "
    "determining an actual claim. If you're checking whether a specific claim is "
    "covered, that's outside what this tool does. If instead you meant a "
    "question about how the process map is structured, or want to suggest a "
    "change to it, try rephrasing — e.g. \"why is the exclusions check before "
    "the excess step?\" or \"add a step for verifying the incident date.\""
)


def answer_explain(message: str, retrieved: list[RetrievedTask], api_key: str | None) -> str:
    if not retrieved:
        return (
            "I couldn't find a step in the process map that matches this question "
            "well enough to answer confidently. Try naming the step or a term "
            "closer to the map (e.g. 'exclusions check', 'excess', 'escalation')."
        )
    if api_key:
        import anthropic

        context_parts = []
        for r in retrieved:
            context_parts.append(f"Step: {r.task.title}\nDescription: {r.task.description}")
            for c in r.claims:
                context_parts.append(f"  - Supporting source (page {c.source_span.page}): {c.statement}")
        context = "\n\n".join(context_parts)
        client = anthropic.Anthropic(api_key=api_key)
        prompt = (
            "You are explaining ONE STEP of a car-insurance claim-coverage "
            "process map to a Business Process Analyst reviewing it for "
            "accuracy. Explain why the step exists and what it does, grounded "
            "only in the context below. Do NOT determine or imply whether any "
            "specific claim is covered — that is out of scope for this tool. "
            "Keep it concise.\n\n"
            f"Context:\n{context}\n\nQuestion: {message}"
        )
        response = client.messages.create(
            model="claude-sonnet-4-5-20250929", max_tokens=400,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text

    top = retrieved[0]
    lines = [
        f"The most relevant step is \"{top.task.title}\" ({top.task.node_type.replace('_', ' ')}).",
        top.task.description,
    ]
    if len(retrieved) > 1:
        others = ", ".join(f'"{r.task.title}"' for r in retrieved[1:])
        lines.append(f"Related steps: {others}.")
    return "\n\n".join(lines)


def draft_change_request(message: str, retrieved: list[RetrievedTask], api_key: str | None) -> dict:
    """Best-effort structured proposal from a free-text change request. Always
    reviewable/editable by a human before approval — never applied straight
    from this draft. Falls back to change_type='unclear' if it can't confidently
    tell what's being asked, rather than guessing a structural edit."""
    lower = message.lower()
    if api_key:
        import anthropic

        context = "\n".join(f"- {r.task.id}: {r.task.title}" for r in retrieved) or "(no closely matching step found)"
        client = anthropic.Anthropic(api_key=api_key)
        prompt = (
            "A Business Process Analyst is giving feedback on a process map and "
            "wants a change. Read their message and the nearby steps below, then "
            "respond with ONLY a JSON object (no prose) of the shape:\n"
            '{"change_type": "add_task" | "remove_task" | "modify_task" | "unclear", '
            '"payload": {...}, "rationale": "short reason"}\n\n'
            "Payload shapes:\n"
            'add_task: {"after_task_id": "<id>", "node_type": "classification", "title": "...", "description": "..."}\n'
            'remove_task: {"task_id": "<id>"}\n'
            'modify_task: {"task_id": "<id>", "title": "...", "description": "..."}\n'
            "Use \"unclear\" if you can't confidently pick a target step from the list below.\n\n"
            f"Nearby steps:\n{context}\n\nBPA message: {message}"
        )
        response = client.messages.create(
            model="claude-sonnet-4-5-20250929", max_tokens=400,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()
        try:
            # Strip markdown code fences if the model added them anyway.
            text = re.sub(r"^```(json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
            parsed = json.loads(text)
            if parsed.get("change_type") in {"add_task", "remove_task", "modify_task"} and parsed.get("payload"):
                return parsed
        except (json.JSONDecodeError, AttributeError):
            pass
        return {"change_type": "unclear", "payload": {}, "rationale": "Could not confidently parse a structured change from this message."}

    # No LLM key: heuristic-only, deliberately conservative — flags "unclear"
    # rather than guessing structure without a model to help parse free text.
    if any(w in lower for w in ("remove", "delete", "drop")) and retrieved:
        return {
            "change_type": "remove_task", "payload": {"task_id": retrieved[0].task.id},
            "rationale": f"Heuristic match (no LLM key): closest step to the request is \"{retrieved[0].task.title}\".",
        }
    return {
        "change_type": "unclear", "payload": {},
        "rationale": "No LLM key configured — free-text change requests need a human to translate into a structured edit.",
    }


def handle_message(db: Session, document_id: str, message: str) -> tuple[str, str, list[RetrievedTask], ChangeRequest | None]:
    """Returns (answer_text, mode, retrieved_tasks, change_request_or_none)."""
    intent = classify_intent(message)
    api_key = os.environ.get("ANTHROPIC_API_KEY")

    if intent == "coverage_question":
        return COVERAGE_REFUSAL, "out_of_scope", [], None

    retrieved = retrieve(db, document_id, message)

    if intent == "change_request":
        pm = (
            db.query(ProcessMapVersion)
            .filter_by(document_id=document_id)
            .order_by(ProcessMapVersion.created_at.desc())
            .first()
        )
        draft = draft_change_request(message, retrieved, api_key)
        cr = ChangeRequest(
            document_id=document_id,
            base_process_map_id=pm.id if pm else "",
            source="chat",
            request_text=message,
            change_type=draft["change_type"],
            proposed_change=json.dumps(draft["payload"]),
            rationale=draft.get("rationale"),
            status="pending",
        )
        db.add(cr)
        db.flush()

        if draft["change_type"] == "unclear":
            answer = (
                "Thanks — I've logged this as feedback, but I couldn't confidently "
                "turn it into a specific structural change on my own. A reviewer "
                "will need to translate it into a concrete edit (add/remove/modify "
                "a step) before it can be applied. You can also just rephrase, "
                "naming the exact step, e.g. \"remove the 'Check additional and "
                "optional covers' step\"."
            )
        else:
            answer = (
                f"Got it — logged as a pending change request ({draft['change_type'].replace('_', ' ')}). "
                f"{draft.get('rationale', '')} It won't be applied to the process map until a "
                "reviewer approves it in the Feedback tab, and approving it creates a new, "
                "versioned process map rather than editing this one in place."
            )
        return answer, "change_request_logged", retrieved, cr

    if intent == "explain":
        return answer_explain(message, retrieved, api_key), ("llm_grounded" if api_key else "retrieval_only"), retrieved, None

    # general — same grounding, same scope restriction, softer framing
    return answer_explain(message, retrieved, api_key), ("llm_grounded" if api_key else "retrieval_only"), retrieved, None
