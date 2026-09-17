from unittest.mock import patch

from triage_iq.tools.create_trello_card import create_trello_card

_PAYLOAD = {
    "ticket_id": "T-1",
    "subject": "Charged twice",
    "body": "customer message",
    "category": "billing",
    "urgency": "critical",
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
