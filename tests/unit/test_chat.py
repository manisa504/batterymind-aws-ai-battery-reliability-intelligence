from types import SimpleNamespace

from apps.api import chat

ANALYSIS = {
    "battery_id": "B0005",
    "cutoff_cycle": 120,
    "latest_capacity_ah": 1.433,
    "rated_capacity_ah": 2.0,
    "soh_percent": 71.7,
    "degradation_rate_ah_per_cycle": -0.0039,
    "measurements": [{"cycle": 1}] * 120,
    "rul": {"status": "available", "estimated_remaining_cycles": 12.0, "interval_90_cycles": [8, 20]},
    "classification": {"decision": "ENGINEERING_REVIEW", "policy_version": "experimental-soh-v1", "rationale": "r"},
}


def record(rid, decision="ENGINEERING_REVIEW", cutoff=100):
    return SimpleNamespace(id=rid * 36, cutoff_cycle=cutoff, decision=decision, policy_version="p", explanation="e")


def test_evidence_separates_measured_derived_and_predicted():
    text = chat.structured_evidence(ANALYSIS)
    assert "Measured latest discharge capacity: 1.433 Ah" in text
    assert "Derived state of health: 71.7%" in text
    assert "predicted remaining cycles 12" in text


def test_semantic_hit_outranks_recent_only_and_is_deduplicated():
    a, b = record("a"), record("b", "EOL_REVIEW")
    candidates, _ = chat.rank_candidates(similar=[(b, 0.9)], recent=[a, b])
    assert len(candidates) == 2
    by_text = {c.text[1:9]: c for c in candidates}
    assert by_text["bbbbbbbb"].relevance == 0.9
    assert by_text["aaaaaaaa"].relevance == 0.0
    assert by_text["bbbbbbbb"].importance > by_text["aaaaaaaa"].importance
