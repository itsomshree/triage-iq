from triage_iq.chains.routing_chain import decide_routing
from triage_iq.config import LOW_CONFIDENCE_THRESHOLD
from triage_iq.schemas import (
    RoutingAction,
    TicketCategory,
    TicketClassification,
    TicketUrgency,
)


def make_classification(
    *,
    category: TicketCategory = TicketCategory.GENERAL_INQUIRY,
    urgency: TicketUrgency = TicketUrgency.LOW,
    confidence: float = 0.95,
    summary: str = "Customer has a general question.",
) -> TicketClassification:
    return TicketClassification(
        category=category, urgency=urgency, confidence=confidence, summary=summary
    )


def test_low_confidence_flags_for_review():
    classification = make_classification(confidence=LOW_CONFIDENCE_THRESHOLD - 0.1)

    decision = decide_routing(classification)

    assert decision.action == RoutingAction.FLAG_FOR_REVIEW
    assert "confidence" in decision.reasoning.lower()


def test_critical_urgency_escalates():
    classification = make_classification(urgency=TicketUrgency.CRITICAL)

    decision = decide_routing(classification)

    assert decision.action == RoutingAction.ESCALATE
    assert "critical" in decision.reasoning.lower()


def test_high_urgency_escalates():
    classification = make_classification(urgency=TicketUrgency.HIGH)

    decision = decide_routing(classification)

    assert decision.action == RoutingAction.ESCALATE
    assert "high" in decision.reasoning.lower()


def test_account_category_flags_for_review():
    classification = make_classification(
        category=TicketCategory.ACCOUNT, urgency=TicketUrgency.MEDIUM
    )

    decision = decide_routing(classification)

    assert decision.action == RoutingAction.FLAG_FOR_REVIEW
    assert "account" in decision.reasoning.lower()


def test_default_case_auto_answers():
    classification = make_classification(
        category=TicketCategory.REFUND, urgency=TicketUrgency.LOW, confidence=0.9
    )

    decision = decide_routing(classification)

    assert decision.action == RoutingAction.AUTO_ANSWER
    assert "refund" in decision.reasoning.lower()


def test_low_confidence_takes_precedence_over_account_category():
    classification = make_classification(
        category=TicketCategory.ACCOUNT,
        urgency=TicketUrgency.LOW,
        confidence=LOW_CONFIDENCE_THRESHOLD - 0.1,
    )

    decision = decide_routing(classification)

    assert decision.action == RoutingAction.FLAG_FOR_REVIEW
    assert "confidence" in decision.reasoning.lower()
