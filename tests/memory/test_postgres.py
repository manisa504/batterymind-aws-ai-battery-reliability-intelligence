"""Real PostgreSQL + pgvector tests. Opt in with BATTERYMIND_TEST_PG_URL (see scripts/test_postgres.sh)."""

import json
import os

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session as DbSession

from packages.memory_engine import Base, MemoryRepository, apply_schema

URL = os.environ.get("BATTERYMIND_TEST_PG_URL")
pytestmark = pytest.mark.skipif(not URL, reason="BATTERYMIND_TEST_PG_URL is not set")


def unit_vector(axis: int) -> list[float]:
    """Fixture vectors for exercising nearest-neighbour ordering; not battery data."""
    return [1.0 if i == axis else 0.0 for i in range(1024)]


@pytest.fixture()
def engine():
    engine = create_engine(URL)
    with engine.begin() as c:
        c.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public;"))
    apply_schema(engine)
    apply_schema(engine)  # idempotent
    Base.metadata.create_all(engine)
    return engine


def store(repo, session_id, key, cutoff, decision="ENGINEERING_REVIEW"):
    return repo.store_assessment(
        session_id=session_id,
        battery_id="B0005",
        cutoff_cycle=cutoff,
        decision=decision,
        explanation=key,
        evidence={"soh_percent": 70.0},
        policy_version="p",
        model_version=None,
        idempotency_key=key * 8,
    )


def test_row_level_security_isolates_users_across_commits(engine):
    with DbSession(engine) as db:
        a = MemoryRepository(db, "user-a")
        sess_id = a.create_session("B0005", "objective").id
        record_id = store(a, sess_id, "alpha", 50).id
        a.store_embedding(record_id, unit_vector(0), "test")
        a.add_turn(sess_id, "user", "hello")
        assert len(a.valid_history("B0005", 200)) == 1  # visible after several commits
    with DbSession(engine) as db:
        b = MemoryRepository(db, "user-b")
        assert b.valid_history("B0005", 200) == []
        assert b.get_session(sess_id) is None
        assert b.similar_assessments("B0005", 200, unit_vector(0)) == []
        assert b.recent_turns(sess_id) == []
        assert b.delete_assessment(record_id) is False
    with engine.begin() as c:  # even a direct query as the privileged account is filtered after SET ROLE
        c.execute(text("SET LOCAL ROLE batterymind_app"))
        assert c.execute(text("SELECT count(*) FROM assessments")).scalar() == 0


def test_similarity_respects_cutoff_validity_and_ordering(engine):
    with DbSession(engine) as db:
        repo = MemoryRepository(db, "user-a")
        sess = repo.create_session("B0005", "objective")
        near = store(repo, sess.id, "near", 40)
        far = store(repo, sess.id, "far", 50)
        late = store(repo, sess.id, "late", 150)
        repo.store_embedding(near.id, unit_vector(0), "t")
        repo.store_embedding(far.id, unit_vector(1), "t")
        repo.store_embedding(late.id, unit_vector(0), "t")
        hits = repo.similar_assessments("B0005", 100, unit_vector(0))
        assert [h[0].id for h in hits] == [near.id, far.id]  # late (cutoff 150) is excluded
        assert hits[0][1] > hits[1][1]
        repo.delete_assessment(near.id)
        assert [h[0].id for h in repo.similar_assessments("B0005", 100, unit_vector(0))] == [far.id]


def test_memory_survives_new_connection_pool(engine):
    with DbSession(engine) as db:
        repo = MemoryRepository(db, "user-a")
        sess = repo.create_session("B0005", "objective")
        store(repo, sess.id, "persisted", 60)
    engine.dispose()  # simulates a container restart: all connections are gone
    fresh = create_engine(URL)
    with DbSession(fresh) as db:
        items = MemoryRepository(db, "user-a").valid_history("B0005", 100)
        assert [json.loads(i.evidence_json)["soh_percent"] for i in items] == [70.0]
