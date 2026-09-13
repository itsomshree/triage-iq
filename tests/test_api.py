from datetime import UTC, datetime
from types import SimpleNamespace

from tests.conftest import make_ticket_row
from triage_iq.pipeline import PipelineError

VALID_TICKET_PAYLOAD = {
    "ticket_id": "T-1001",
    "subject": "How long does a refund take?",
    "body": "I returned an item and want to know the refund timeline.",
}


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# POST /tickets
def test_submit_ticket_success(client, mock_run_ticket, sample_final_response):
    mock_run_ticket.return_value = sample_final_response

    response = client.post("/tickets", json=VALID_TICKET_PAYLOAD)

    assert response.status_code == 200
    body = response.json()
    assert body["ticket_id"] == "T-1001"
    assert body["classification"]["category"] == "refund"
    assert body["routing_decision"]["action"] == "auto_answer"
    mock_run_ticket.assert_called_once()


def test_submit_ticket_pipeline_error(client, mock_run_ticket):
    original = ValueError("classifier returned malformed output")
    error = PipelineError(ticket_id="T-1001", stage="classification", original=original)
    mock_run_ticket.side_effect = error

    response = client.post("/tickets", json=VALID_TICKET_PAYLOAD)

    assert response.status_code == 500
    body = response.json()
    assert body["ticket_id"] == "T-1001"
    assert body["stage"] == "classification"
    assert "malformed output" in body["detail"]


def test_submit_ticket_validation_error(client, mock_run_ticket):
    response = client.post(
        "/tickets", json={"ticket_id": "T-1001", "subject": "Missing body"}
    )

    assert response.status_code == 422
    mock_run_ticket.assert_not_called()


# GET /tickets/{ticket_id}
def test_get_ticket_not_found(client, mock_crud, mock_get_session):
    mock_crud.get_ticket.return_value = None

    response = client.get("/tickets/does-not-exist")

    assert response.status_code == 404


def test_get_ticket_fully_populated(
    client,
    mock_crud,
    mock_get_session,
    sample_classification,
    sample_routing_decision,
    sample_rag_answer,
    sample_escalation,
):
    row = make_ticket_row(
        classification=SimpleNamespace(
            category=sample_classification.category.value,
            urgency=sample_classification.urgency.value,
            summary=sample_classification.summary,
            confidence=sample_classification.confidence,
        ),
        routing_decision=SimpleNamespace(
            action=sample_routing_decision.action.value,
            reasoning=sample_routing_decision.reasoning,
        ),
        rag_answer=SimpleNamespace(
            answer=sample_rag_answer.answer,
            source_documents=sample_rag_answer.source_documents,
            grounded=sample_rag_answer.grounded,
        ),
        escalation=SimpleNamespace(
            escalation_id=sample_escalation.escalation_id,
            assigned_team=sample_escalation.assigned_team,
            priority=sample_escalation.priority,
        ),
    )
    mock_crud.get_ticket.return_value = row

    response = client.get("/tickets/T-1001")

    assert response.status_code == 200
    body = response.json()
    assert body["classification"]["category"] == "refund"
    assert body["classification"]["urgency"] == "low"
    assert body["routing_decision"]["action"] == "auto_answer"
    assert body["rag_answer"]["grounded"] is True
    assert body["escalation"]["assigned_team"] == "billing"


def test_get_ticket_partially_populated(client, mock_crud, mock_get_session):
    row = make_ticket_row(
        classification=SimpleNamespace(
            category="account",
            urgency="medium",
            summary="Password reset issue.",
            confidence=0.88,
        ),
        routing_decision=SimpleNamespace(
            action="flag_for_review",
            reasoning="Account tickets need human verification.",
        ),
        rag_answer=None,
        escalation=None,
    )
    mock_crud.get_ticket.return_value = row

    response = client.get("/tickets/T-1001")

    assert response.status_code == 200
    body = response.json()
    assert body["classification"]["category"] == "account"
    assert body["rag_answer"] is None
    assert body["escalation"] is None


# GET /tickets/{ticket_id}/logs
def test_get_ticket_logs_not_found(client, mock_crud, mock_get_session):
    mock_crud.get_ticket.return_value = None

    response = client.get("/tickets/does-not-exist/logs")

    assert response.status_code == 404


def test_get_ticket_logs_found(client, mock_crud, mock_get_session):
    mock_crud.get_ticket.return_value = make_ticket_row()
    mock_crud.get_logs_for_ticket.return_value = [
        SimpleNamespace(
            stage="classification",
            message="category=refund urgency=low confidence=0.95",
            latency_ms=1234.5,
            created_at=datetime(2026, 9, 13, 12, 0, 0, tzinfo=UTC),
        )
    ]

    response = client.get("/tickets/T-1001/logs")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["stage"] == "classification"
    assert body[0]["created_at"] == "2026-09-13T12:00:00+00:00"
