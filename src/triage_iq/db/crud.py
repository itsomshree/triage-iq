from __future__ import annotations

from sqlalchemy import func, select
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
    session.flush()
    return row


def save_classification(
    session: Session, ticket_id: str, classification: TicketClassification
) -> Classification:
    existing = session.scalars(
        select(Classification).where(Classification.ticket_id == ticket_id)
    ).first()

    if existing is not None:
        existing.category = classification.category.value
        existing.urgency = classification.urgency.value
        existing.summary = classification.summary
        existing.confidence = classification.confidence
        session.flush()
        return existing

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
    existing = session.scalars(
        select(RoutingDecisionRecord).where(
            RoutingDecisionRecord.ticket_id == ticket_id
        )
    ).first()

    if existing is not None:
        existing.action = decision.action.value
        existing.reasoning = decision.reasoning
        session.flush()
        return existing

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
    existing = session.scalars(
        select(RagAnswerRecord).where(RagAnswerRecord.ticket_id == ticket_id)
    ).first()

    if existing is not None:
        existing.answer = answer.answer
        existing.source_documents = answer.source_documents
        existing.grounded = answer.grounded
        session.flush()
        return existing

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
    existing = session.scalars(
        select(EscalationRecordRow).where(EscalationRecordRow.ticket_id == ticket_id)
    ).first()

    if existing is not None:
        existing.escalation_id = escalation.escalation_id
        existing.assigned_team = escalation.assigned_team
        existing.priority = escalation.priority
        session.flush()
        return existing

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


# Dashboard aggregate queries
def get_total_ticket_count(session: Session) -> int:
    stmt = select(func.count()).select_from(Ticket)
    return session.execute(stmt).scalar_one()


def get_routing_action_counts(session: Session) -> dict[str, int]:
    stmt = select(RoutingDecisionRecord.action, func.count()).group_by(
        RoutingDecisionRecord.action
    )
    return {action: count for action, count in session.execute(stmt)}


def get_category_counts(session: Session) -> dict[str, int]:
    stmt = select(Classification.category, func.count()).group_by(
        Classification.category
    )
    return {category: count for category, count in session.execute(stmt)}


def get_urgency_counts(session: Session) -> dict[str, int]:
    stmt = select(Classification.urgency, func.count()).group_by(Classification.urgency)
    return {urgency: count for urgency, count in session.execute(stmt)}


def get_avg_confidence(session: Session) -> float | None:
    stmt = select(func.avg(Classification.confidence))
    return session.execute(stmt).scalar()


def get_avg_pipeline_latency_ms(session: Session) -> float | None:
    per_ticket = (
        select(
            PipelineLog.ticket_id,
            func.sum(PipelineLog.latency_ms).label("total_latency_ms"),
        )
        .where(PipelineLog.stage != "pipeline_error")
        .group_by(PipelineLog.ticket_id)
        .subquery()
    )
    stmt = select(func.avg(per_ticket.c.total_latency_ms))
    return session.execute(stmt).scalar()


def get_recent_tickets(session: Session, limit: int = 25) -> list[Ticket]:
    stmt = select(Ticket).order_by(Ticket.created_at.desc()).limit(limit)
    return list(session.scalars(stmt))
