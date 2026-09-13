from contextlib import contextmanager
from unittest.mock import patch

import pytest

from triage_iq.db import crud
from triage_iq.pipeline import PipelineError, run_ticket
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
    ticket_id="T-2001",
    customer_email="test@example.com",
    subject="How long does a refund take?",
    body="I returned an item two weeks ago and want a status update.",
)


@pytest.fixture
def pipeline_db_session(db_session):
    @contextmanager
    def _fake_get_session():
        yield db_session

    with patch("triage_iq.pipeline.get_session", _fake_get_session):
        yield db_session


@pytest.fixture
def mock_classify():
    with patch("triage_iq.pipeline.classify_ticket") as mock:
        yield mock


@pytest.fixture
def mock_route():
    with patch("triage_iq.pipeline.decide_routing") as mock:
        yield mock


@pytest.fixture
def mock_answer():
    with patch("triage_iq.pipeline.answer_ticket") as mock:
        yield mock


@pytest.fixture
def mock_escalate():
    with patch("triage_iq.pipeline.escalate") as mock:
        yield mock


def make_classification(
    *,
    category: TicketCategory = TicketCategory.REFUND,
    urgency: TicketUrgency = TicketUrgency.LOW,
    summary: str = "Wants a refund status update.",
    confidence: float = 0.95,
) -> TicketClassification:
    return TicketClassification(
        category=category, urgency=urgency, summary=summary, confidence=confidence
    )


# auto_answer, grounded
def test_auto_answer_grounded_path(
    pipeline_db_session, mock_classify, mock_route, mock_answer, mock_escalate
):
    mock_classify.return_value = make_classification()
    mock_route.return_value = RoutingDecision(
        action=RoutingAction.AUTO_ANSWER, reasoning="well covered by KB"
    )
    mock_answer.return_value = RagAnswer(
        answer="Refunds take 5-10 business days.",
        source_documents=["refund_policy.txt"],
        grounded=True,
    )

    response = run_ticket(SAMPLE_TICKET)

    assert response.routing_decision.action == RoutingAction.AUTO_ANSWER
    assert response.rag_answer is not None
    assert response.rag_answer.grounded is True
    assert response.escalation is None
    mock_escalate.assert_not_called()

    ticket = crud.get_ticket(pipeline_db_session, SAMPLE_TICKET.ticket_id)
    assert ticket is not None
    assert ticket.classification is not None
    assert ticket.routing_decision is not None
    assert ticket.routing_decision.action == "auto_answer"
    assert ticket.rag_answer is not None
    assert ticket.escalation is None

    logs = crud.get_logs_for_ticket(pipeline_db_session, SAMPLE_TICKET.ticket_id)
    stages = [log.stage for log in logs]
    assert "classification" in stages
    assert "routing" in stages
    assert "rag_answer" in stages
    assert "pipeline_error" not in stages


# auto_answer overridden to escalate when ungrounded
def test_auto_answer_ungrounded_overrides_to_escalate(
    pipeline_db_session, mock_classify, mock_route, mock_answer, mock_escalate
):
    mock_classify.return_value = make_classification()
    mock_route.return_value = RoutingDecision(
        action=RoutingAction.AUTO_ANSWER, reasoning="well covered by KB"
    )
    mock_answer.return_value = RagAnswer(
        answer="Not sure, needs a human.",
        source_documents=[],
        grounded=False,
    )
    mock_escalate.return_value = EscalationRecord(
        escalation_id="esc-1", assigned_team="billing", priority="P2"
    )

    response = run_ticket(SAMPLE_TICKET)

    assert response.routing_decision.action == RoutingAction.ESCALATE
    assert response.rag_answer is not None
    assert response.rag_answer.grounded is False
    assert response.escalation is not None
    mock_escalate.assert_called_once()

    ticket = crud.get_ticket(pipeline_db_session, SAMPLE_TICKET.ticket_id)
    assert ticket is not None
    assert ticket.routing_decision is not None
    assert ticket.routing_decision.action == "escalate"
    assert ticket.rag_answer is not None

    logs = crud.get_logs_for_ticket(pipeline_db_session, SAMPLE_TICKET.ticket_id)
    stages = [log.stage for log in logs]
    assert "routing_override" in stages
    assert "escalation" in stages


# direct escalate path
def test_escalate_path(
    pipeline_db_session, mock_classify, mock_route, mock_answer, mock_escalate
):
    mock_classify.return_value = make_classification(
        urgency=TicketUrgency.CRITICAL, confidence=0.9
    )
    mock_route.return_value = RoutingDecision(
        action=RoutingAction.ESCALATE, reasoning="critical urgency"
    )
    mock_escalate.return_value = EscalationRecord(
        escalation_id="esc-2", assigned_team="billing", priority="PQ"
    )

    response = run_ticket(SAMPLE_TICKET)

    assert response.routing_decision.action == RoutingAction.ESCALATE
    assert response.rag_answer is None
    assert response.escalation is not None
    mock_answer.assert_not_called()
    mock_escalate.assert_called_once()

    ticket = crud.get_ticket(pipeline_db_session, SAMPLE_TICKET.ticket_id)
    assert ticket is not None
    assert ticket.rag_answer is None


# flag_for_review path
def test_flag_for_review_path(
    pipeline_db_session, mock_classify, mock_route, mock_answer, mock_escalate
):
    mock_classify.return_value = make_classification(confidence=0.3)
    mock_route.return_value = RoutingDecision(
        action=RoutingAction.FLAG_FOR_REVIEW, reasoning="low confidence"
    )

    response = run_ticket(SAMPLE_TICKET)

    assert response.routing_decision.action == RoutingAction.FLAG_FOR_REVIEW
    assert response.rag_answer is None
    assert response.escalation is None
    mock_answer.assert_not_called()
    mock_escalate.assert_not_called()

    ticket = crud.get_ticket(pipeline_db_session, SAMPLE_TICKET.ticket_id)
    assert ticket is not None
    assert ticket.rag_answer is None
    assert ticket.escalation is None


# error handling
def test_classification_failure_raises_pipeline_error_and_logs(
    pipeline_db_session, mock_classify, mock_route, mock_answer, mock_escalate
):
    mock_classify.side_effect = ValueError("groq timed out")

    with pytest.raises(PipelineError) as exc_info:
        run_ticket(SAMPLE_TICKET)

    err = exc_info.value
    assert err.ticket_id == SAMPLE_TICKET.ticket_id
    assert err.stage == "classification"
    assert "groq timed out" in str(err.original)

    mock_route.assert_not_called()
    mock_answer.assert_not_called()
    mock_escalate.assert_not_called()

    logs = crud.get_logs_for_ticket(pipeline_db_session, SAMPLE_TICKET.ticket_id)
    error_logs = [log for log in logs if log.stage == "pipeline_error"]
    assert len(error_logs) == 1
    assert "FAILED" in error_logs[0].message
