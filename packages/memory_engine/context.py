from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MemoryCandidate:
    text: str
    relevance: float
    recency: float
    importance: float
    confidence: float


def bounded_context(structured_evidence: str, memories: list[MemoryCandidate], max_characters: int = 6000) -> str:
    if max_characters < len(structured_evidence):
        raise ValueError("Context budget cannot hold authoritative structured evidence")
    ranked = sorted(
        memories,
        key=lambda item: 0.45 * item.relevance + 0.25 * item.recency + 0.2 * item.importance + 0.1 * item.confidence,
        reverse=True,
    )
    result = structured_evidence
    for candidate in ranked:
        addition = f"\nPrior valid assessment: {candidate.text}"
        if len(result) + len(addition) > max_characters:
            continue
        result += addition
    return result
