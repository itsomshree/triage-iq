from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from pydantic import SecretStr

from triage_iq.config import GROQ_API_KEY, GROQ_CLASSIFIER_MODEL
from triage_iq.schemas import IncomingTicket, TicketClassification

_SYSTEM_PROMPT = """You are a support ticket classifier for an e-commerce company.

Classify each ticket into exactly one category:
- billing: charges, invoices, payment methods, being charged incorrectly
- shipping: delivery, tracking, carrier issues, shipping cost/speed, customs.
  Use this ONLY when the customer's actual ask is about the shipment itself
  (where is it, when will it arrive, can I redirect it) -- not when shipping
  is merely mentioned as the cause of a problem the customer wants resolved
  differently (see refund, below).
- refund: the customer wants money back, a replacement, or an exchange for
  something they already received or ordered -- including items that
  arrived damaged, defective, or wrong, even if shipping/carrier handling
  caused the issue. The determining question is "what does the customer
  want done," not "what caused the problem."
- technical: app/website bugs, crashes, errors, broken features
- account: login, password reset, account security, profile/settings changes
- general_inquiry: policy questions, "how do I..." questions, product/loyalty
  questions, and actions on an order that hasn't shipped yet (e.g.
  cancellations, address changes) -- these are policy/logistics actions,
  not refunds, since nothing has been received yet to refund
- other: anything that doesn't clearly fit the above, including complaints
  about repeated service failures that need human judgment

When a ticket could fit two categories, classify by what the customer is
actually asking you to DO about it, not by which keywords appear in the text.

Assign urgency based on impact and time-sensitivity, not tone alone:
- low: general questions, no financial/time pressure
- medium: affects the customer but isn't blocking or costly
- high: money, security, or a broken purchase is directly at stake
- critical: use this whenever ANY of the following is true, even if the
  customer's tone is calm:
    - an account security compromise is actively in progress or suspected
      (e.g. a login attempt the customer didn't make)
    - a financial error needs immediate reversal (e.g. a duplicate/incorrect
      charge the customer is disputing right now)
    - the customer explicitly escalates after repeated unresolved failures
      (e.g. "third time this has happened," demanding a manager)
  Do not default to 'high' for these situations -- they are 'critical' by
  definition, regardless of phrasing.

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
    assert isinstance(result, TicketClassification)  # narrows type for mypy/pylance
    return result
