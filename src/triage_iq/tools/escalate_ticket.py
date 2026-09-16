import uuid

from langchain_core.tools import tool

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
    Decide the correct team and priority for a support ticket that needs
    human handling, and build an escalation record for it.

    This tool is intentionally compute-only and does not touch the
    database: it's invoked from inside triage_iq.pipeline's ticket-level
    transaction, and persisting from a second, independent session there
    would try to write a row referencing a ticket that transaction can't
    see yet. The caller (triage_iq.pipeline.run_ticket) is responsible for
    persisting the returned record via triage_iq.db.crud.save_escalation
    using its own session.
    """
    assigned_team = _TEAM_BY_CATEGORY.get(category, "support")
    priority = _PRIORITY_BY_URGENCY.get(urgency, "P2")
    escalation_id = str(uuid.uuid4())

    return EscalationRecord(
        escalation_id=escalation_id, assigned_team=assigned_team, priority=priority
    )
