from __future__ import annotations

import json

from sqlalchemy import event, func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as DbSession

from .models import Assessment, ChatTurn, Session


class MemoryRepository:
    def __init__(self, db: DbSession, user_id: str):
        self.db = db
        self.user_id = user_id
        self.is_postgres = db.bind is not None and db.bind.dialect.name == "postgresql"
        if self.is_postgres:
            # set_config(..., true) is transaction-local, so it must be re-applied for every new
            # transaction; otherwise forced row-level security hides the rows after a commit.
            def apply_user(_session, _transaction, connection):
                # A non-bypass role guarantees row-level security applies even to privileged accounts.
                connection.exec_driver_sql("SET LOCAL ROLE batterymind_app")
                connection.exec_driver_sql("SELECT set_config('app.user_id', %s, true)", (user_id,))

            event.listen(db, "after_begin", apply_user)
            db.connection()

    def create_session(self, battery_id: str, objective: str) -> Session:
        session = Session(user_id=self.user_id, battery_id=battery_id, objective=objective)
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def get_session(self, session_id: str) -> Session | None:
        return self.db.scalar(select(Session).where(Session.id == session_id, Session.user_id == self.user_id))

    def store_assessment(
        self,
        *,
        session_id: str,
        battery_id: str,
        cutoff_cycle: int,
        decision: str,
        explanation: str,
        evidence: dict,
        policy_version: str,
        model_version: str | None,
        idempotency_key: str,
        supersedes_id: str | None = None,
        expected_version: int | None = None,
    ) -> Assessment:
        existing = self.db.scalar(
            select(Assessment).where(Assessment.user_id == self.user_id, Assessment.idempotency_key == idempotency_key)
        )
        if existing:
            return existing
        session = self.get_session(session_id)
        if session is None or session.battery_id != battery_id:
            raise ValueError("Session is unavailable or belongs to a different battery")
        if supersedes_id:
            previous = self.db.scalar(
                select(Assessment)
                .where(Assessment.id == supersedes_id, Assessment.user_id == self.user_id)
                .with_for_update()
            )
            if previous is None:
                raise ValueError("Assessment to supersede was not found")
            if previous.validity != "valid" or expected_version != previous.version:
                raise ValueError("Assessment changed; reload before correcting it")
            previous.validity = "superseded"
        assessment = Assessment(
            session_id=session_id,
            user_id=self.user_id,
            battery_id=battery_id,
            cutoff_cycle=cutoff_cycle,
            decision=decision,
            explanation=explanation,
            evidence_json=json.dumps(evidence, sort_keys=True),
            policy_version=policy_version,
            model_version=model_version,
            idempotency_key=idempotency_key,
            supersedes_id=supersedes_id,
        )
        self.db.add(assessment)
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            concurrent = self.db.scalar(
                select(Assessment).where(
                    Assessment.user_id == self.user_id,
                    Assessment.idempotency_key == idempotency_key,
                )
            )
            if concurrent is None:
                raise
            return concurrent
        self.db.refresh(assessment)
        return assessment

    def valid_history(self, battery_id: str, cutoff_cycle: int) -> list[Assessment]:
        statement = (
            select(Assessment)
            .where(
                Assessment.user_id == self.user_id,
                Assessment.battery_id == battery_id,
                Assessment.validity == "valid",
                Assessment.cutoff_cycle <= cutoff_cycle,
            )
            .order_by(Assessment.created_at.desc())
            .limit(20)
        )
        return list(self.db.scalars(statement))

    def delete_session(self, session_id: str) -> bool:
        """Delete a conversation with its turns and assessments (and their embeddings) by cascade."""
        session = self.get_session(session_id)
        if session is None:
            return False
        self.db.delete(session)
        self.db.commit()
        return True

    def delete_assessment(self, assessment_id: str) -> bool:
        assessment = self.db.scalar(
            select(Assessment).where(Assessment.id == assessment_id, Assessment.user_id == self.user_id)
        )
        if assessment is None:
            return False
        self.db.delete(assessment)
        self.db.commit()
        return True

    def list_sessions(self, battery_id: str) -> list[Session]:
        return list(
            self.db.scalars(
                select(Session)
                .where(Session.user_id == self.user_id, Session.battery_id == battery_id)
                .order_by(Session.created_at.desc())
                .limit(20)
            )
        )

    def all_turns(self, session_id: str, limit: int = 60) -> list[ChatTurn]:
        rows = self.db.scalars(
            select(ChatTurn)
            .where(ChatTurn.session_id == session_id, ChatTurn.user_id == self.user_id)
            .order_by(ChatTurn.created_at.desc())
            .limit(limit)
        )
        return list(reversed(list(rows)))

    def all_assessments(self, battery_id: str) -> list[Assessment]:
        """Every assessment for review, including superseded ones."""
        return list(
            self.db.scalars(
                select(Assessment)
                .where(Assessment.user_id == self.user_id, Assessment.battery_id == battery_id)
                .order_by(Assessment.created_at.desc())
                .limit(100)
            )
        )

    def store_embedding(self, assessment_id: str, vector: list[float], model_id: str) -> None:
        if not self.is_postgres:
            return
        self.db.execute(
            text(
                "INSERT INTO memory_embeddings (assessment_id, user_id, embedding, model_id) "
                "VALUES (:a, :u, CAST(:v AS vector), :m) "
                "ON CONFLICT (assessment_id) DO UPDATE SET embedding = EXCLUDED.embedding, model_id = EXCLUDED.model_id"
            ),
            {"a": assessment_id, "u": self.user_id, "v": _vector_literal(vector), "m": model_id},
        )
        self.db.commit()

    def similar_assessments(
        self, battery_id: str, cutoff_cycle: int, vector: list[float], limit: int = 8
    ) -> list[tuple[Assessment, float]]:
        """Valid assessments at or before the cutoff, nearest first, with cosine similarity."""
        if not self.is_postgres:
            return []
        rows = self.db.execute(
            text(
                "SELECT e.assessment_id, 1 - (e.embedding <=> CAST(:v AS vector)) AS similarity "
                "FROM memory_embeddings e JOIN assessments a ON a.id = e.assessment_id "
                "WHERE e.user_id = :u AND a.user_id = :u AND a.battery_id = :b "
                "AND a.validity = 'valid' AND a.cutoff_cycle <= :c "
                "ORDER BY e.embedding <=> CAST(:v AS vector) LIMIT :n"
            ),
            {"v": _vector_literal(vector), "u": self.user_id, "b": battery_id, "c": cutoff_cycle, "n": limit},
        ).all()
        found = {x.id: x for x in self.db.scalars(select(Assessment).where(Assessment.id.in_([r[0] for r in rows])))}
        return [(found[r[0]], float(r[1])) for r in rows if r[0] in found]

    def add_turn(
        self,
        session_id: str,
        role: str,
        content: str,
        *,
        model_id: str | None = None,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        latency_ms: int | None = None,
    ) -> ChatTurn:
        turn = ChatTurn(
            session_id=session_id,
            user_id=self.user_id,
            role=role,
            content=content,
            model_id=model_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
        )
        self.db.add(turn)
        self.db.commit()
        self.db.refresh(turn)
        return turn

    def recent_turns(self, session_id: str, limit: int = 6) -> list[ChatTurn]:
        rows = self.db.scalars(
            select(ChatTurn)
            .where(ChatTurn.session_id == session_id, ChatTurn.user_id == self.user_id)
            .order_by(ChatTurn.created_at.desc())
            .limit(limit)
        )
        return list(reversed(list(rows)))

    def usage(self) -> dict:
        row = self.db.execute(
            select(
                func.count(ChatTurn.id),
                func.coalesce(func.sum(ChatTurn.input_tokens), 0),
                func.coalesce(func.sum(ChatTurn.output_tokens), 0),
                func.coalesce(func.avg(ChatTurn.latency_ms), 0),
            ).where(ChatTurn.user_id == self.user_id, ChatTurn.role == "assistant")
        ).one()
        return {
            "assistant_replies": int(row[0]),
            "input_tokens": int(row[1]),
            "output_tokens": int(row[2]),
            "mean_latency_ms": round(float(row[3]), 1),
        }


def _vector_literal(vector: list[float]) -> str:
    return "[" + ",".join(f"{x:.7f}" for x in vector) + "]"
