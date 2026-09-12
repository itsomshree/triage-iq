import uuid

from langchain_core.tools import tool

from triage_iq.db import crud
from triage_iq.db.connection import get_session
from triage_iq.schemas import EscalationRecord

_TEAM_BY_CATEGORY = {
    "billing": "billing",
    "shipping": "logistics",
    "refund": "billing",
    "technical": "engineering",
    "account": "account_security",
    "general_inquiry": "support",
    "other": "support",
}

_PRIORITY_BY_URGENCY = {"critical": "PQ", "high": "P1", "medium": "P2", "low": "P3"}


@tool
def escalate_ticket(
    ticket_id: str, category: str, urgency: str, reasoning: str
) -> EscalationRecord:
    """
    Create an escalation record for a support ticket that needs human
    handling, ssigning it to the correct team with an appropriate priority,
    and persist it to the database.
    """
    assigned_team = _TEAM_BY_CATEGORY.get(category, "support")
    priority = _PRIORITY_BY_URGENCY.get(urgency, "P2")
    escalation_id = str(uuid.uuid4())

    escalation = EscalationRecord(
        escalation_id=escalation_id, assigned_team=assigned_team, priority=priority
    )

    with get_session() as session:
        crud.save_escalation(session, ticket_id=ticket_id, escalation=escalation)

    return escalation
