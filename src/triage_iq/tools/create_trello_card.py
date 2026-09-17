import logging

from langchain_core.tools import tool

from triage_iq.config import TRELLO_ENABLED
from triage_iq.integrations.trello_board import create_card, get_label_id, get_list_id

logger = logging.getLogger("triage_iq")


@tool
def create_trello_card(
    ticket_id: str,
    subject: str,
    body: str,
    customer_email: str | None,
    category: str,
    urgency: str,
    summary: str,
    confidence: float,
    assigned_team: str,
    priority: str,
) -> str | None:
    """
    Create a Trello card for an escalated ticket so a human can pick it up
    and work it. Returns the card's URL, or None if Trello isn't configured
    (TRELLO_API_KEY/TRELLO_API_TOKEN unset) or the Trello API call fails --
    this is additive on top of the DB escalation record, never required for
    escalation to succeed.
    """
    if not TRELLO_ENABLED:
        return None

    description = (
        f"**Customer:** {customer_email or 'unknown'}\n"
        f"**Category:** {category}\n"
        f"**Urgency:** {urgency}\n"
        f"**Classifier confidence:** {confidence:.2f}\n\n"
        f"**Summary:** {summary}\n\n"
        f"**Customer message:**\n{body}\n\n"
        f"**View full trace:** {{your deployed URL}}/tickets/{ticket_id}"
    )

    try:
        card = create_card(
            list_id=get_list_id(assigned_team),
            label_id=get_label_id(priority),
            name=subject,
            description=description,
        )
        return card.get("shortUrl") or card.get("url")
    except Exception:
        logger.exception("Trello card creation failed for ticket %s", ticket_id)
        return None
