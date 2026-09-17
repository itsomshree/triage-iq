from triage_iq.db import crud
from triage_iq.schemas import (
    EscalationRecord,
    IncomingTicket,
    RagAnswer,
    RoutingAction,
    RoutingDecision,
    TicketCategory,
    TicketClassification,
    TicketUrgency,
)

SAMPLE_TICKET = IncomingTicket(
    ticket_id="T-1001",
    customer_email="test@example.com",
    subject="How long does a refund take?",
    body="I returned an item two weeks ago.",
)


def test_create_ticket_creates_row(db_session):
    row = crud.create_ticket(db_session, SAMPLE_TICKET)

    assert row.ticket_id == "T-1001"
    assert row.subject == SAMPLE_TICKET.subject


def test_create_ticket_is_idempotent(db_session):
    first = crud.create_ticket(db_session, SAMPLE_TICKET)
    second = crud.create_ticket(db_session, SAMPLE_TICKET)

    assert first.ticket_id == second.ticket_id
    assert crud.get_ticket(db_session, "T-1001") is not None


def test_save_classification_inserts_then_updates(db_session):
    crud.create_ticket(db_session, SAMPLE_TICKET)

    first = TicketClassification(
        category=TicketCategory.REFUND,
        urgency=TicketUrgency.LOW,
        summary="Wants refund status.",
        confidence=0.9,
    )
    crud.save_classification(db_session, "T-1001", first)

    second = TicketClassification(
        category=TicketCategory.SHIPPING,
        urgency=TicketUrgency.HIGH,
        summary="Package never arrived.",
        confidence=0.8,
    )
    crud.save_classification(db_session, "T-1001", second)

    ticket = crud.get_ticket(db_session, "T-1001")
    assert ticket is not None
    assert ticket.classification is not None
    assert ticket.classification.category == "shipping"
    assert ticket.classification.urgency == "high"


def test_save_routing_decision_inserts_then_updates(db_session):
    crud.create_ticket(db_session, SAMPLE_TICKET)

    crud.save_routing_decision(
        db_session,
        "T-1001",
        RoutingDecision(action=RoutingAction.AUTO_ANSWER, reasoning="first"),
    )
    crud.save_routing_decision(
        db_session,
        "T-1001",
        RoutingDecision(action=RoutingAction.ESCALATE, reasoning="second"),
    )

    ticket = crud.get_ticket(db_session, "T-1001")
    assert ticket is not None
    assert ticket.routing_decision is not None
    assert ticket.routing_decision.action == "escalate"
    assert ticket.routing_decision.reasoning == "second"


def test_save_rag_answer_inserts_then_updates(db_session):
    crud.create_ticket(db_session, SAMPLE_TICKET)

    crud.save_rag_answer(
        db_session,
        "T-1001",
        RagAnswer(answer="first answer", source_documents=["a.txt"], grounded=True),
    )
    crud.save_rag_answer(
        db_session,
        "T-1001",
        RagAnswer(
            answer="second answer",
            source_documents=["b.txt", "c.txt"],
            grounded=False,
        ),
    )

    ticket = crud.get_ticket(db_session, "T-1001")
    assert ticket is not None
    assert ticket.rag_answer is not None
    assert ticket.rag_answer.answer == "second answer"
    assert ticket.rag_answer.source_documents == ["b.txt", "c.txt"]
    assert ticket.rag_answer.grounded is False


def test_save_escalation_inserts_then_updates(db_session):
    crud.create_ticket(db_session, SAMPLE_TICKET)

    crud.save_escalation(
        db_session,
        "T-1001",
        EscalationRecord(
            escalation_id="esc-1",
            assigned_team="billing",
            priority="P2",
            trello_card_url="https://trello.com/c/first",
        ),
    )
    crud.save_escalation(
        db_session,
        "T-1001",
        EscalationRecord(
            escalation_id="esc-2",
            assigned_team="engineering",
            priority="P1",
            trello_card_url="https://trello.com/c/second",
        ),
    )

    ticket = crud.get_ticket(db_session, "T-1001")
    assert ticket is not None
    assert ticket.escalation is not None
    assert ticket.escalation.escalation_id == "esc-2"
    assert ticket.escalation.assigned_team == "engineering"
    assert ticket.escalation.trello_card_url == "https://trello.com/c/second"


def test_add_log_is_insert_only(db_session):
    crud.create_ticket(db_session, SAMPLE_TICKET)

    crud.add_log(db_session, "T-1001", stage="classification", message="first")
    crud.add_log(db_session, "T-1001", stage="classification", message="second")

    logs = crud.get_logs_for_ticket(db_session, "T-1001")
    assert len(logs) == 2
    assert {log.message for log in logs} == {"first", "second"}


def test_get_ticket_returns_none_for_unknown_id(db_session):
    assert crud.get_ticket(db_session, "does-not-exist") is None


def test_get_logs_for_ticket_ordered_by_created_at(db_session):
    crud.create_ticket(db_session, SAMPLE_TICKET)

    crud.add_log(db_session, "T-1001", stage="classification", message="step 1")
    crud.add_log(db_session, "T-1001", stage="routing", message="step 2")
    crud.add_log(db_session, "T-1001", stage="rag_answer", message="step 3")

    logs = crud.get_logs_for_ticket(db_session, "T-1001")
    assert [log.message for log in logs] == ["step 1", "step 2", "step 3"]
