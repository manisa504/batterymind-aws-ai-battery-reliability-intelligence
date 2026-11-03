from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(128), index=True)
    battery_id: Mapped[str] = mapped_column(String(32), index=True)
    objective: Mapped[str] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now().astimezone())
    assessments: Mapped[list[Assessment]] = relationship(back_populates="session", cascade="all, delete-orphan")
    turns: Mapped[list[ChatTurn]] = relationship(cascade="all, delete-orphan")


class Assessment(Base):
    __tablename__ = "assessments"
    __table_args__ = (UniqueConstraint("user_id", "idempotency_key"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[str] = mapped_column(String(128), index=True)
    battery_id: Mapped[str] = mapped_column(String(32), index=True)
    cutoff_cycle: Mapped[int] = mapped_column(Integer)
    decision: Mapped[str] = mapped_column(String(64))
    explanation: Mapped[str] = mapped_column(Text)
    evidence_json: Mapped[str] = mapped_column(Text)
    policy_version: Mapped[str] = mapped_column(String(64))
    model_version: Mapped[str | None] = mapped_column(String(128), nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(128))
    validity: Mapped[str] = mapped_column(String(32), default="valid")
    supersedes_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now().astimezone())
    session: Mapped[Session] = relationship(back_populates="assessments")


class ChatTurn(Base):
    """Short-term conversational memory: one row per user or assistant message."""

    __tablename__ = "chat_turns"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[str] = mapped_column(String(128), index=True)
    role: Mapped[str] = mapped_column(String(16))
    content: Mapped[str] = mapped_column(Text)
    model_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now().astimezone())
