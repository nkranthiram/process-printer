"""Chatbot — answers from the generated process map + claim store (per
architecture.md: grounded in the validated graph, not raw document RAG).

Two modes:
- retrieval_only: no ANTHROPIC_API_KEY configured (this sandbox's actual state) —
  keyword-overlap retrieval over tasks/claims, returns the best-matching task(s)
  and their citations without generating free-text prose beyond a templated
  summary. Honest about being retrieval-only, not a stub pretending to be a full
  answer.
- llm_grounded: ANTHROPIC_API_KEY present — retrieval feeds a real LLM call that
  answers in natural language, still constrained to cite only retrieved sources.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.claim import AtomicClaim
from app.models.process_map import ProcessMapVersion, ProcessTask

_STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "do", "does", "did", "for",
    "of", "to", "in", "on", "and", "or", "my", "i", "what", "how", "if", "will",
    "can", "does", "it", "this", "that", "am", "be", "covered", "cover",
}


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


def answer_retrieval_only(message: str, retrieved: list[RetrievedTask]) -> str:
    if not retrieved:
        return (
            "I couldn't find a task in the process map that matches this question "
            "well enough to answer confidently. Try rephrasing with terms closer to "
            "the policy (e.g. 'windscreen', 'excess', 'total loss', 'not at fault')."
        )
    top = retrieved[0]
    lines = [
        f"The most relevant step is \"{top.task.title}\" ({top.task.node_type.replace('_', ' ')}).",
        top.task.description,
    ]
    if len(retrieved) > 1:
        others = ", ".join(f'"{r.task.title}"' for r in retrieved[1:])
        lines.append(f"Related steps that may also matter: {others}.")
    lines.append(
        "(Retrieval-only mode: no LLM API key is configured, so this is the best-"
        "matching task's own description, not a freshly composed answer — see "
        "the citations below for the underlying source text.)"
    )
    return "\n\n".join(lines)


def answer_llm_grounded(message: str, retrieved: list[RetrievedTask], api_key: str) -> str:
    import anthropic

    context_parts = []
    for r in retrieved:
        context_parts.append(f"Task: {r.task.title}\nDescription: {r.task.description}")
        for c in r.claims:
            context_parts.append(f"  - Claim ({c.subject}, page {c.source_span.page}): {c.statement}")
    context = "\n\n".join(context_parts) if context_parts else "(no matching process-map content found)"

    client = anthropic.Anthropic(api_key=api_key)
    prompt = (
        "You are answering a claims handler's question about a car insurance "
        "coverage-determination process map. Answer ONLY using the context below "
        "— if the context doesn't cover the question, say so plainly rather than "
        "guessing. Keep the answer concise.\n\n"
        f"Context:\n{context}\n\nQuestion: {message}"
    )
    response = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


def answer_question(db: Session, document_id: str, message: str) -> tuple[str, str, list[RetrievedTask]]:
    retrieved = retrieve(db, document_id, message)
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if api_key:
        return answer_llm_grounded(message, retrieved, api_key), "llm_grounded", retrieved
    return answer_retrieval_only(message, retrieved), "retrieval_only", retrieved
