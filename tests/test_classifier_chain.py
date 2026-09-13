from unittest.mock import patch

import pytest

from triage_iq.chains.classifier_chain import classify_ticket
from triage_iq.schemas import (
    IncomingTicket,
    TicketCategory,
    TicketClassification,
    TicketUrgency,
)

SAMPLE_TICKET = IncomingTicket(
    ticket_id="T-1001",
    customer_email="test@example.com",
    subject="How long does a refund take?",
    body="I returned an item two weeks ago and want to know when I'll see the refund.",
)


def test_classify_ticket_returns_chain_output():
    expected = TicketClassification(
        category=TicketCategory.REFUND,
        urgency=TicketUrgency.LOW,
        summary="Customer wants a refund status update.",
        confidence=0.95,
    )

    with patch("triage_iq.chains.classifier_chain._classifier_chain") as mock_chain:
        mock_chain.invoke.return_value = expected

        result = classify_ticket(SAMPLE_TICKET)

    assert result == expected


def test_classify_ticket_passes_subject_and_body_to_chain():
    expected = TicketClassification(
        category=TicketCategory.GENERAL_INQUIRY,
        urgency=TicketUrgency.LOW,
        summary="A question.",
        confidence=0.9,
    )

    with patch("triage_iq.chains.classifier_chain._classifier_chain") as mock_chain:
        mock_chain.invoke.return_value = expected

        classify_ticket(SAMPLE_TICKET)

        mock_chain.invoke.assert_called_once_with(
            {"subject": SAMPLE_TICKET.subject, "body": SAMPLE_TICKET.body}
        )


def test_classify_ticket_raises_if_chain_returns_wrong_type():
    with patch("triage_iq.chains.classifier_chain._classifier_chain") as mock_chain:
        mock_chain.invoke.return_value = {
            "category": "refund"
        }  # not a TicketClassification

        with pytest.raises(AssertionError):
            classify_ticket(SAMPLE_TICKET)
