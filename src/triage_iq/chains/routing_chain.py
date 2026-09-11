from triage_iq.config import LOW_CONFIDENCE_THRESHOLD
from triage_iq.schemas import (
    RoutingAction,
    RoutingDecision,
    TicketCategory,
    TicketClassification,
    TicketUrgency,
)


def decide_routing(classification: TicketClassification) -> RoutingDecision:
    if classification.confidence < LOW_CONFIDENCE_THRESHOLD:
        return RoutingDecision(
            action=RoutingAction.FLAG_FOR_REVIEW,
            reasoning=(
                f"Classifier confidence ({classification.confidence: .2f}) is below"
                f"the {LOW_CONFIDENCE_THRESHOLD} threshold; routing to a human "
                f"for review rather than trusting an uncertain classification."
            ),
        )

    if classification.urgency in (TicketUrgency.CRITICAL, TicketUrgency.HIGH):
        return RoutingDecision(
            action=RoutingAction.ESCALATE,
            reasoning=(
                f"Urgency is '{classification.urgency.value}', which needs "
                f"prompt human attention rather than an automated answer."
            ),
        )

    if classification.category == TicketCategory.ACCOUNT:
        return RoutingDecision(
            action=RoutingAction.FLAG_FOR_REVIEW,
            reasoning=(
                "Account-related tickets (login, passowrd reset, security) often "
                "require a human to verify identity or take an account-specific "
                "action that a knowledge-base answer can't safely cover."
            ),
        )

    return RoutingDecision(
        action=RoutingAction.AUTO_ANSWER,
        reasoning=(
            f"Category '{classification.category.value}' at "
            f"'{classification.urgency.value}' urgency is well-covered by the "
            f"knowledge base: attempting an automated answer."
        ),
    )
