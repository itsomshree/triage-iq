from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from pydantic import SecretStr

from triage_iq.config import GROQ_API_KEY, GROQ_CLASSIFIER_MODEL
from triage_iq.schemas import IncomingTicket, TicketClassification

_SYSTEM_PROMPT = """You are a support ticket classifier for an e-commerce company.

Classify each ticket into exactly one category:
- billing: charges, invoices, payment methods, being charged incorrectly
- shipping: delivery, tracking, carrier issues, shipping cost/speed, customs
- refund: return requests, refund status, exchanges
- technical: app/website bugs, crashes, errors, broken features
- account: login, password reset, account security, profile/settings changes
- general_inquiry: policy questions, "how do I..." questions, product/loyalty
  questions that don't require looking up this specific customer's order
- other: anything that doesn't clearly fit the above, including complaints
  about repeated service failures that need human judgment

Assign urgency based on impact and time-sensitivity, not tone alone:
- low: general questions, no financial/time pressure
- medium: affects the customer but isn't blocking or costly
- high: money, security, or a broken purchase is directly at stake
- critical: active security compromise, or the customer is explicitly
  escalating after repeated failures

Also provide a one-to-two sentence summary of what the customer wants, and a
confidence score (0-1) reflecting how certain you are in this classification.
Give a lower confidence score when the ticket is ambiguous or could
reasonably fit more than one category."""

_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", _SYSTEM_PROMPT),
        ("human", "Subject: {subject}\n\nBody: {body}"),
    ]
)

_llm = ChatGroq(
    api_key=SecretStr(GROQ_API_KEY),
    model=GROQ_CLASSIFIER_MODEL,
    temperature=0.0,
)

_structured_llm = _llm.with_structured_output(TicketClassification)

_classifier_chain = _prompt | _structured_llm


def classify_ticket(ticket: IncomingTicket) -> TicketClassification:
    result = _classifier_chain.invoke({"subject": ticket.subject, "body": ticket.body})
    assert isinstance(result, TicketClassification)  # narrow type for mypy/pylance
    return result
