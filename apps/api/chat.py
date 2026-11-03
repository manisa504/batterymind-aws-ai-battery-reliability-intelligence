"""Evidence-grounded engineering assistant.

Pipeline: authoritative measurements (always from structured data) -> valid prior assessments
(semantic similarity + recency) -> ranking -> token-budgeted compression -> Bedrock generation.
Vector search never supplies numerical truth; it only selects which prior assessments to recall.
"""

from __future__ import annotations

import logging

from packages.memory_engine import MemoryRepository
from packages.memory_engine.context import MemoryCandidate, bounded_context
from packages.memory_engine.embeddings import TitanEmbedder

from . import llm
from .explainer import DECISION_BANDS
from .settings import settings

log = logging.getLogger(__name__)

CONTEXT_BUDGET_CHARS = 5000
IMPORTANCE = {
    "EOL_REVIEW": 1.0,
    "ENGINEERING_REVIEW": 0.8,
    "INCREASE_TESTING": 0.5,
    "CONTINUE_MONITORING": 0.3,
    "INSUFFICIENT_EVIDENCE": 0.2,
}
SYSTEM = (
    "You are BatteryMind, an engineering assistant for battery reliability. Answer only from the EVIDENCE "
    "block. Rules: (1) numbers must come from the evidence; never invent measurements or thresholds. "
    "(2) Label values as measured (NASA laboratory discharge capacity), derived (state of health), or "
    "predicted (RUL baseline estimate). (3) These are laboratory observations, not field safety or "
    "maintenance outcomes. (4) If prior assessments are listed, you may compare with them and cite their "
    "id; if none are listed, say there is no prior assessment. (5) If the evidence cannot answer, say so. "
    "Keep answers under 150 words."
)


def structured_evidence(analysis: dict) -> str:
    rul = analysis["rul"]
    if rul.get("status") == "available":
        rul_text = (
            f"predicted remaining cycles {rul['estimated_remaining_cycles']:.0f} (linear baseline; "
            f"90% interval {rul.get('interval_90_cycles')})"
        )
    else:
        rul_text = f"unavailable ({rul.get('status')})"
    cls = analysis["classification"]
    return (
        f"EVIDENCE (authoritative, NASA Ames laboratory data)\n"
        f"Battery: {analysis['battery_id']}; cutoff cycle: {analysis['cutoff_cycle']}; "
        f"valid discharge measurements used: {len(analysis['measurements'])}\n"
        f"Measured latest discharge capacity: {analysis['latest_capacity_ah']:.3f} Ah "
        f"(rated {analysis['rated_capacity_ah']} Ah)\n"
        f"Derived state of health: {analysis['soh_percent']:.1f}%\n"
        f"Measured degradation rate: {analysis['degradation_rate_ah_per_cycle']:.5f} Ah/cycle\n"
        f"Deterministic decision: {cls['decision']} (policy {cls['policy_version']})\n"
        f"{DECISION_BANDS}\nRUL: {rul_text}"
    )


def rank_candidates(similar: list, recent: list) -> tuple[list[MemoryCandidate], dict[str, str]]:
    """Merge semantic hits with recent assessments into scored, de-duplicated candidates."""
    candidates: dict[str, MemoryCandidate] = {}
    for rank, record in enumerate(recent):
        candidates[record.id] = _candidate(record, relevance=0.0, recency=1.0 / (1 + rank))
    for record, similarity in similar:
        recency = candidates[record.id].recency if record.id in candidates else 0.2
        candidates[record.id] = _candidate(record, relevance=max(0.0, similarity), recency=recency)
    index = {cid: cid for cid in candidates}
    return list(candidates.values()), index


def _candidate(record, relevance: float, recency: float) -> MemoryCandidate:
    text = (
        f"[{record.id[:8]}] cutoff {record.cutoff_cycle}, decision {record.decision}, "
        f"policy {record.policy_version}: {record.explanation}"
    )
    return MemoryCandidate(
        text=text,
        relevance=relevance,
        recency=recency,
        importance=IMPORTANCE.get(record.decision, 0.3),
        confidence=1.0,
    )


def respond(repo: MemoryRepository, session, analysis: dict, message: str) -> dict:
    evidence = structured_evidence(analysis)
    cutoff = analysis["cutoff_cycle"]
    similar: list = []
    try:
        if settings.bedrock_embedding_model_id:
            vector = TitanEmbedder(settings.bedrock_embedding_model_id, settings.aws_region).embed(message)
            similar = repo.similar_assessments(session.battery_id, cutoff, vector, limit=8)
    except Exception:  # noqa: BLE001 - recall degrades to recency; evidence is unaffected
        log.exception("Semantic recall failed; falling back to recency only")
    recent = repo.valid_history(session.battery_id, cutoff)[:5]
    candidates, _ = rank_candidates(similar, recent)
    raw_chars = len(evidence) + sum(len(c.text) + 28 for c in candidates)
    context = bounded_context(evidence, candidates, CONTEXT_BUDGET_CHARS)
    included = context.count("\nPrior valid assessment:")
    history = [{"role": t.role, "content": t.content} for t in repo.recent_turns(session.id, 6)]
    messages = [*history, {"role": "user", "content": f"{context}\n\nQUESTION: {message}"}]
    reply = llm.converse(SYSTEM, messages, max_tokens=500)
    repo.add_turn(session.id, "user", message)
    repo.add_turn(
        session.id,
        "assistant",
        reply["text"],
        model_id=reply["model_id"],
        input_tokens=reply["input_tokens"],
        output_tokens=reply["output_tokens"],
        latency_ms=reply["latency_ms"],
    )
    return {
        "answer": reply["text"],
        "model_id": reply["model_id"],
        "usage": {"input_tokens": reply["input_tokens"], "output_tokens": reply["output_tokens"]},
        "latency_ms": reply["latency_ms"],
        "context": {
            "battery_id": session.battery_id,
            "cutoff_cycle": cutoff,
            "measurements_used": len(analysis["measurements"]),
            "semantic_hits": len(similar),
            "prior_assessments_available": len(candidates),
            "prior_assessments_included": included,
            "characters_before_compression": raw_chars,
            "characters_after_compression": len(context),
        },
    }
