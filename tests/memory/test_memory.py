import json

from sqlalchemy import create_engine
from sqlalchemy.orm import Session as DbSession

from packages.memory_engine import Base, MemoryRepository
from packages.memory_engine.context import MemoryCandidate, bounded_context


def repository(user_id="user-a"):
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    return engine, DbSession(engine), user_id


def test_cross_user_isolation_correction_and_deletion():
    engine, db, user_id = repository()
    first = MemoryRepository(db, user_id)
    session = first.create_session("B0005", "Assess degradation")
    assessment = first.store_assessment(
        session_id=session.id,
        battery_id="B0005",
        cutoff_cycle=20,
        decision="CONTINUE_MONITORING",
        explanation="Measured evidence through cycle 20.",
        evidence={"capacity_ah": 1.8},
        policy_version="v1",
        model_version=None,
        idempotency_key="request-0001",
    )
    with DbSession(engine) as other_db:
        assert MemoryRepository(other_db, "user-b").valid_history("B0005", 100) == []
    replacement = first.store_assessment(
        session_id=session.id,
        battery_id="B0005",
        cutoff_cycle=20,
        decision="INCREASE_TESTING",
        explanation="Corrected assessment.",
        evidence={"capacity_ah": 1.8},
        policy_version="v1",
        model_version=None,
        idempotency_key="request-0002",
        supersedes_id=assessment.id,
        expected_version=assessment.version,
    )
    history = first.valid_history("B0005", 20)
    assert [item.id for item in history] == [replacement.id]
    assert json.loads(history[0].evidence_json)["capacity_ah"] == 1.8
    assert first.delete_assessment(replacement.id)
    assert first.valid_history("B0005", 20) == []


def test_idempotency_and_historical_cutoff():
    _, db, user_id = repository()
    memory = MemoryRepository(db, user_id)
    session = memory.create_session("B0005", "Assess degradation")
    values = dict(
        session_id=session.id,
        battery_id="B0005",
        cutoff_cycle=50,
        decision="CONTINUE_MONITORING",
        explanation="Evidence.",
        evidence={},
        policy_version="v1",
        model_version=None,
        idempotency_key="same-request",
    )
    assert memory.store_assessment(**values).id == memory.store_assessment(**values).id
    assert memory.valid_history("B0005", 49) == []


def test_context_preserves_structured_evidence_and_budget():
    memories = [
        MemoryCandidate("less relevant", 0.1, 0.1, 0.1, 1),
        MemoryCandidate("most relevant", 1, 1, 1, 1),
    ]
    context = bounded_context("MEASURED: 1.8 Ah", memories, max_characters=80)
    assert context.startswith("MEASURED: 1.8 Ah")
    assert "most relevant" in context
