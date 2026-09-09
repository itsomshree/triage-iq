from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from triage_iq.db.models import (
    Classification,
    EscalationRecordRow,
    PipelineLog,
    RagAnswerRecord,
    RoutingDecisionRecord,
    Ticket,
)
from triage_iq.schemas import (
    EscalationRecord,
    IncomingTicket,
    RagAnswer,
    RoutingDecision,
    TicketClassification,
)


def create_ticket(session: Session, ticket: IncomingTicket) -> Ticket:
    existing = session.get(Ticket, ticket.ticket_id)
    if existing is not None:
        return existing

    row = Ticket(
        ticket_id=ticket.ticket_id,
        customer_email=ticket.customer_email,
        subject=ticket.subject,
        body=ticket.body,
    )
    session.add(row)
    session.flush()  # assigns/validates without committing the transaction
    return row


def save_classification(
    session: Session, ticket_id: str, classification: TicketClassification
) -> Classification:
    row = Classification(
        ticket_id=ticket_id,
        category=classification.category.value,
        urgency=classification.urgency.value,
        summary=classification.summary,
        confidence=classification.confidence,
    )
    session.add(row)
    session.flush()
    return row


def save_routing_decision(
    session: Session, ticket_id: str, decision: RoutingDecision
) -> RoutingDecisionRecord:
    row = RoutingDecisionRecord(
        ticket_id=ticket_id,
        action=decision.action.value,
        reasoning=decision.reasoning,
    )
    session.add(row)
    session.flush()
    return row


def save_rag_answer(
    session: Session, ticket_id: str, answer: RagAnswer
) -> RagAnswerRecord:
    row = RagAnswerRecord(
        ticket_id=ticket_id,
        answer=answer.answer,
        source_documents=answer.source_documents,
        grounded=answer.grounded,
    )
    session.add(row)
    session.flush()
    return row


def save_escalation(
    session: Session, ticket_id: str, escalation: EscalationRecord
) -> EscalationRecordRow:
    row = EscalationRecordRow(
        escalation_id=escalation.escalation_id,
        ticket_id=ticket_id,
        assigned_team=escalation.assigned_team,
        priority=escalation.priority,
    )
    session.add(row)
    session.flush()
    return row


def add_log(
    session: Session,
    ticket_id: str,
    stage: str,
    message: str,
    latency_ms: float | None = None,
) -> PipelineLog:
    row = PipelineLog(
        ticket_id=ticket_id, stage=stage, message=message, latency_ms=latency_ms
    )
    session.add(row)
    session.flush()
    return row


def get_ticket(session: Session, ticket_id: str) -> Ticket | None:
    return session.get(Ticket, ticket_id)


def get_logs_for_ticket(session: Session, ticket_id: str) -> list[PipelineLog]:
    stmt = (
        select(PipelineLog)
        .where(PipelineLog.ticket_id == ticket_id)
        .order_by(PipelineLog.created_at)
    )
    return list(session.scalars(stmt))
