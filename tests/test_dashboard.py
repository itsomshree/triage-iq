from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def mock_dashboard_crud():
    with patch("api.dashboard.crud") as mock:
        yield mock


@pytest.fixture
def mock_dashboard_session():
    with patch("api.dashboard.get_session") as mock:
        mock.return_value.__enter__.return_value = MagicMock()
        yield mock


def test_summary(client, mock_dashboard_crud, mock_dashboard_session):
    mock_dashboard_crud.get_total_ticket_count.return_value = 10
    mock_dashboard_crud.get_routing_action_counts.return_value = {
        "auto_answer": 6,
        "escalate": 3,
        "flag_for_review": 1,
    }
    mock_dashboard_crud.get_avg_confidence.return_value = 0.95
    mock_dashboard_crud.get_avg_pipeline_latency_ms.return_value = 1200.5

    response = client.get("/dashboard/summary")

    assert response.status_code == 200
    body = response.json()
    assert body["total_tickets"] == 10
    assert body["auto_answer_count"] == 6
    assert body["escalate_count"] == 3
    assert body["flag_for_review_count"] == 1
    assert body["avg_confidence"] == 0.95
    assert body["avg_latency_ms"] == 1200.5


def test_category_breakdown_sorted_desc(
    client, mock_dashboard_crud, mock_dashboard_session
):
    mock_dashboard_crud.get_category_counts.return_value = {
        "shipping": 3,
        "billing": 7,
        "refund": 5,
    }

    response = client.get("/dashboard/category-breakdown")

    assert response.status_code == 200
    assert response.json() == [
        {"category": "billing", "count": 7},
        {"category": "refund", "count": 5},
        {"category": "shipping", "count": 3},
    ]


def test_urgency_breakdown_ordered_by_severity(
    client, mock_dashboard_crud, mock_dashboard_session
):
    mock_dashboard_crud.get_urgency_counts.return_value = {
        "low": 4,
        "critical": 1,
        "medium": 2,
        "high": 3,
    }

    response = client.get("/dashboard/urgency-breakdown")

    assert response.status_code == 200
    body = response.json()
    assert [row["urgency"] for row in body] == ["critical", "high", "medium", "low"]


def test_recent_tickets_handles_missing_classification(
    client, mock_dashboard_crud, mock_dashboard_session
):
    ticket_with_data = SimpleNamespace(
        ticket_id="T-1",
        subject="Refund question",
        classification=SimpleNamespace(
            category="refund", urgency="low", confidence=0.9
        ),
        routing_decision=SimpleNamespace(action="auto_answer"),
        created_at=datetime(2026, 9, 16, 10, 0, 0, tzinfo=UTC),
    )
    ticket_without_data = SimpleNamespace(
        ticket_id="T-2",
        subject="New ticket",
        classification=None,
        routing_decision=None,
        created_at=None,
    )
    mock_dashboard_crud.get_recent_tickets.return_value = [
        ticket_with_data,
        ticket_without_data,
    ]

    response = client.get("/dashboard/recent-tickets?limit=10")

    assert response.status_code == 200
    body = response.json()
    assert body[0]["category"] == "refund"
    assert body[0]["confidence"] == 0.9
    assert body[1]["category"] is None
    assert body[1]["action"] is None
    assert mock_dashboard_crud.get_recent_tickets.call_args.kwargs["limit"] == 10
