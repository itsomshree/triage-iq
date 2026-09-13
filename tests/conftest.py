from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.main import app
from triage_iq.db.models import Base
from triage_iq.schemas import (
    EscalationRecord,
    FinalResponse,
    RagAnswer,
    RoutingAction,
    RoutingDecision,
    TicketCategory,
    TicketClassification,
    TicketUrgency,
)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def mock_run_ticket():
    with patch("api.main.run_ticket") as mock:
        yield mock


@pytest.fixture
def mock_crud():
    with patch("api.main.crud") as mock:
        yield mock


@pytest.fixture
def mock_get_session():
    with patch("api.main.get_session") as mock:
        mock.return_value.__enter__.return_value = MagicMock()
        yield mock


@pytest.fixture
def sample_classification() -> TicketClassification:
    return TicketClassification(
        category=TicketCategory.REFUND,
        urgency=TicketUrgency.LOW,
        summary="Customer wants a refund status update.",
        confidence=0.95,
    )


@pytest.fixture
def sample_routing_decision() -> RoutingDecision:
    return RoutingDecision(
        action=RoutingAction.AUTO_ANSWER,
        reasoning="Well-covered by the knowledge base.",
    )


@pytest.fixture
def sample_rag_answer() -> RagAnswer:
    return RagAnswer(
        answer="Refunds typically post within 5-10 business days.",
        source_documents=["refund_policy.txt"],
        grounded=True,
    )


@pytest.fixture
def sample_escalation() -> EscalationRecord:
    return EscalationRecord(
        escalation_id="esc-123",
        assigned_team="billing",
        priority="P2",
    )


@pytest.fixture
def sample_final_response(
    sample_classification, sample_routing_decision, sample_rag_answer
) -> FinalResponse:
    return FinalResponse(
        ticket_id="T-1001",
        classification=sample_classification,
        routing_decision=sample_routing_decision,
        rag_answer=sample_rag_answer,
        escalation=None,
        latency_ms=1234.5,
    )


@pytest.fixture
def db_session():

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def make_ticket_row(
    *,
    ticket_id: str = "T-1001",
    subject: str = "How long does a refund take?",
    body: str = "I returned an item and want to know the refund timeline.",
    classification=None,
    routing_decision=None,
    rag_answer=None,
    escalation=None,
) -> SimpleNamespace:
    """Lightweight stand-in for a Ticket ORM row, with just the attributes
    api.main.get_ticket actually reads. Avoids needing a real SQLAlchemy
    model or database for these tests."""
    return SimpleNamespace(
        ticket_id=ticket_id,
        subject=subject,
        body=body,
        classification=classification,
        routing_decision=routing_decision,
        rag_answer=rag_answer,
        escalation=escalation,
    )
