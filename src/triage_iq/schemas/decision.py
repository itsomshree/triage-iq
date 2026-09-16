from enum import Enum

from pydantic import BaseModel, Field

from triage_iq.schemas.ticket import TicketClassification


class RoutingAction(str, Enum):
    AUTO_ANSWER = "auto_answer"
    ESCALATE = "escalate"
    FLAG_FOR_REVIEW = "flag_for_review"


class RoutingDecision(BaseModel):
    action: RoutingAction = Field(
        ..., description="Which path the ticket should be routed down"
    )
    reasoning: str = Field(
        ..., description="Short explanation of why this action was chosen"
    )


class RagAnswer(BaseModel):
    answer: str = Field(..., description="The grounded answer given to the customer")
    source_documents: list[str] = Field(
        default_factory=list,
        description="Identifiers or titles of the knowledge base documents used",
    )
    grounded: bool = Field(
        ...,
        description="Whether the retrieved context actually supported an answer",
    )


class EscalationRecord(BaseModel):
    escalation_id: str = Field(..., description="ID of the created escalation record")
    assigned_team: str = Field(...)
    priority: str = Field(...)
    trello_card_url: str | None = Field(
        default=None,
        description="URL of the Trello card created for this escalation, if configured",
    )


class FinalResponse(BaseModel):
    ticket_id: str
    classification: TicketClassification
    routing_decision: RoutingDecision
    rag_answer: RagAnswer | None = Field(
        default=None, description="Populated only when action == auto_answer"
    )
    escalation: EscalationRecord | None = Field(
        default=None, description="Populated only when action == escalate"
    )
    latency_ms: float | None = Field(
        default=None, description="End-to-end pipeline latency in milliseconds"
    )


class TicketRecord(BaseModel):
    ticket_id: str
    subject: str
    body: str
    classification: TicketClassification | None = None
    routing_decision: RoutingDecision | None = None
    rag_answer: RagAnswer | None = None
    escalation: EscalationRecord | None = None
