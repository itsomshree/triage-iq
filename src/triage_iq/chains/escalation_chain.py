from triage_iq.schemas import IncomingTicket, RoutingDecision, TicketClassification
from triage_iq.tools.create_trello_card import create_trello_card
from triage_iq.tools.escalate_ticket import EscalationRecord, escalate_ticket


def escalate(
    ticket: IncomingTicket,
    classification: TicketClassification,
    routing_decision: RoutingDecision,
) -> EscalationRecord:
    result = escalate_ticket.invoke(
        {
            "ticket_id": ticket.ticket_id,
            "category": classification.category.value,
            "urgency": classification.urgency.value,
            "reasoning": routing_decision.reasoning,
        }
    )
    assert isinstance(result, EscalationRecord)

    result.trello_card_url = create_trello_card.invoke(
        {
            "ticket_id": ticket.ticket_id,
            "subject": ticket.subject,
            "body": ticket.body,
            "category": classification.category.value,
            "urgency": classification.urgency.value,
            "confidence": classification.confidence,
            "assigned_team": result.assigned_team,
            "priority": result.priority,
        }
    )
    return result
