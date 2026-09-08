from enum import Enum

from pydantic import BaseModel, Field


class TicketCategory(str, Enum):
    BILLING = "billing"
    SHIPPING = "shipping"
    REFUND = "refund"
    TECHNICAL = "technical"
    ACCOUNT = "account"
    GENERAL_INQUIRY = "general_inquiry"
    OTHER = "other"


class TicketUrgency(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IncomingTicket(BaseModel):
    ticket_id: str = Field(..., description="Unique identifier for the ticket")
    customer_email: str | None = Field(
        default=None, description="Email of the customer who submitted the ticket"
    )
    subject: str = Field(..., description="Subject line of the ticket")
    body: str = Field(..., description="Full text of the customer's message")


class TicketClassification(BaseModel):
    category: TicketCategory = Field(
        ..., description="The primary category this ticket belongs to"
    )
    urgency: TicketUrgency = Field(
        ..., description="How urgently this ticket needs to be handled"
    )
    summary: str = Field(
        ..., description="A one-to-two sentence summary of what the customer wants"
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Model's confidence in this classification, from 0 to 1",
    )
