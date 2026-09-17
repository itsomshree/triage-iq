from unittest.mock import patch

from triage_iq.tools.create_trello_card import create_trello_card

_PAYLOAD = {
    "ticket_id": "T-1",
    "subject": "Charged twice",
    "body": "I was charged $89.97 twice for the same order, please reverse one.",
    "customer_email": "kwilliams@example.com",
    "category": "billing",
    "urgency": "critical",
    "summary": "Customer was double-charged for order #77104 and wants one charge reversed.",
    "confidence": 0.9,
    "assigned_team": "billing",
    "priority": "PQ",
}


def test_returns_none_when_trello_disabled():
    with patch("triage_iq.tools.create_trello_card.TRELLO_ENABLED", False):
        result = create_trello_card.invoke(_PAYLOAD)
    assert result is None


def test_returns_card_url_on_success():
    with (
        patch("triage_iq.tools.create_trello_card.TRELLO_ENABLED", True),
        patch("triage_iq.tools.create_trello_card.get_list_id", return_value="list-1"),
        patch(
            "triage_iq.tools.create_trello_card.get_label_id", return_value="label-1"
        ),
        patch("triage_iq.tools.create_trello_card.create_card") as mock_create,
    ):
        mock_create.return_value = {"shortUrl": "https://trello.com/c/abc123"}
        result = create_trello_card.invoke(_PAYLOAD)

    assert result == "https://trello.com/c/abc123"

    description = mock_create.call_args.kwargs["description"]
    assert _PAYLOAD["customer_email"] in description
    assert _PAYLOAD["summary"] in description


def test_missing_customer_email_falls_back_to_unknown():
    payload = {**_PAYLOAD, "customer_email": None}
    with (
        patch("triage_iq.tools.create_trello_card.TRELLO_ENABLED", True),
        patch("triage_iq.tools.create_trello_card.get_list_id", return_value="list-1"),
        patch(
            "triage_iq.tools.create_trello_card.get_label_id", return_value="label-1"
        ),
        patch("triage_iq.tools.create_trello_card.create_card") as mock_create,
    ):
        create_trello_card.invoke(payload)

    description = mock_create.call_args.kwargs["description"]
    assert "unknown" in description


def test_swallows_failure_and_returns_none():
    with (
        patch("triage_iq.tools.create_trello_card.TRELLO_ENABLED", True),
        patch(
            "triage_iq.tools.create_trello_card.get_list_id",
            side_effect=RuntimeError("Trello down"),
        ),
    ):
        result = create_trello_card.invoke(_PAYLOAD)
    assert result is None
