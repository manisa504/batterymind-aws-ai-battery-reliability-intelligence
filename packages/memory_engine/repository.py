from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as DbSession

from .models import Assessment, Session


class MemoryRepository:
    def __init__(self, db: DbSession, user_id: str):
        self.db = db
        self.user_id = user_id
        if db.bind is not None and db.bind.dialect.name == "postgresql":
            db.connection().exec_driver_sql("SELECT set_config('app.user_id', %s, true)", (user_id,))

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

    def delete_assessment(self, assessment_id: str) -> bool:
        assessment = self.db.scalar(
            select(Assessment).where(Assessment.id == assessment_id, Assessment.user_id == self.user_id)
        )
        if assessment is None:
            return False
        self.db.delete(assessment)
        self.db.commit()
        return True
