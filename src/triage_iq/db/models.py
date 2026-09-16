from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def _uuid() -> str:
    return str(uuid.uuid4())


class Ticket(Base):
    __tablename__ = "tickets"

    ticket_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    customer_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    subject: Mapped[str] = mapped_column(Text, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    classification: Mapped[Classification | None] = relationship(
        back_populates="ticket", uselist=False, cascade="all, delete-orphan"
    )
    routing_decision: Mapped[RoutingDecisionRecord | None] = relationship(
        back_populates="ticket", uselist=False, cascade="all, delete-orphan"
    )
    rag_answer: Mapped[RagAnswerRecord | None] = relationship(
        back_populates="ticket", uselist=False, cascade="all, delete-orphan"
    )
    escalation: Mapped[EscalationRecordRow | None] = relationship(
        back_populates="ticket", uselist=False, cascade="all, delete-orphan"
    )
    logs: Mapped[list[PipelineLog]] = relationship(
        back_populates="ticket", cascade="all, delete-orphan"
    )


class Classification(Base):
    __tablename__ = "classifications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    ticket_id: Mapped[str] = mapped_column(ForeignKey("tickets.ticket_id"), unique=True)
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    urgency: Mapped[str] = mapped_column(String(16), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    ticket: Mapped[Ticket] = relationship(back_populates="classification")


class RoutingDecisionRecord(Base):
    __tablename__ = "routing_decisions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    ticket_id: Mapped[str] = mapped_column(ForeignKey("tickets.ticket_id"), unique=True)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    reasoning: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    ticket: Mapped[Ticket] = relationship(back_populates="routing_decision")


class RagAnswerRecord(Base):
    __tablename__ = "rag_answers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    ticket_id: Mapped[str] = mapped_column(ForeignKey("tickets.ticket_id"), unique=True)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    source_documents: Mapped[list[str]] = mapped_column(JSON, default=list)
    grounded: Mapped[bool] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    ticket: Mapped[Ticket] = relationship(back_populates="rag_answer")


class EscalationRecordRow(Base):
    __tablename__ = "escalations"

    escalation_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    ticket_id: Mapped[str] = mapped_column(ForeignKey("tickets.ticket_id"), unique=True)
    assigned_team: Mapped[str] = mapped_column(String(64), nullable=False)
    priority: Mapped[str] = mapped_column(String(16), nullable=False)
    trello_card_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    ticket: Mapped[Ticket] = relationship(back_populates="escalation")


class PipelineLog(Base):
    __tablename__ = "pipeline_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    ticket_id: Mapped[str] = mapped_column(ForeignKey("tickets.ticket_id"))
    stage: Mapped[str] = mapped_column(String(32), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    ticket: Mapped[Ticket] = relationship(back_populates="logs")
