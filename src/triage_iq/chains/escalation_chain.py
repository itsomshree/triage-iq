from triage_iq.schemas import IncomingTicket, RoutingDecision, TicketClassification
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
            "resoning": routing_decision.reasoning,
        }
    )
    assert isinstance(result, EscalationRecord)
    return result
