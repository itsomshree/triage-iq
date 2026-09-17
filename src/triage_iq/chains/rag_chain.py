from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from pydantic import SecretStr

from triage_iq.config import GROQ_API_KEY, GROQ_REASONING_MODEL
from triage_iq.schemas import IncomingTicket, RagAnswer

_SYSTEM_PROMTP = """You are a support agent answering customer tickets using
ONLY the provided knowledge base context. You are not allowed to use outside
knowledge, general assumptions, or anything not explicitly stated in the
context below.

Rules:
- If the context fully or mostly answers the customer's question, write a
  clear, concise, helpful answer grounded in that context. Set grounded=true.
- If the context is missing, irrelevant, or does not actually address what
  the customer is asking, do NOT guess or improvise an answer. Instead,
  write a short message saying this needs a human to look into it, and set
  grounded=false.
- The context must directly address the customer's specific topic, not just
  be loosely related to it. Retrieved text about a neighboring topic (e.g.
  refund or shipping policy) does NOT ground an answer to a different kind
  of question (e.g. a billing/charge-amount question) just because it
  mentions similar words like "refund" or "charge." If you find yourself
  extrapolating, inferring, or combining unrelated policy statements to
  construct an answer, that is not grounding -- set grounded=false instead.
- Never state something as fact unless it's supported by the context. When
  in doubt, prefer grounded=false over a plausible-sounding guess -- a wrong
  answer is worse than admitting you don't know.

Context from knowledge base:
{context}"""

_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", _SYSTEM_PROMTP),
        ("human", "Subject: {subject}\n\nBody: {body}"),
    ]
)

_llm = ChatGroq(
    api_key=SecretStr(GROQ_API_KEY), model=GROQ_REASONING_MODEL, temperature=0.0
)

_structured_llm = _llm.with_structured_output(RagAnswer)

_rag_chain = _prompt | _structured_llm


def answer_ticket(ticket: IncomingTicket) -> RagAnswer:
    from triage_iq.retrievers import get_compression_retriever

    retriever = get_compression_retriever()
    query = f"{ticket.subject}\n{ticket.body}"
    retrieved_docs = retriever.invoke(query)

    if not retrieved_docs:
        return RagAnswer(
            answer=(
                "I wasn't able to find relevant information to answer this "
                "automatically. A member of our support team will follow up."
            ),
            source_documents=[],
            grounded=False,
        )

    context = "\n\n".join(doc.page_content for doc in retrieved_docs)
    source_documents = sorted(
        {doc.metadata["source"] for doc in retrieved_docs if "source" in doc.metadata}
    )

    result = _rag_chain.invoke(
        {"context": context, "subject": ticket.subject, "body": ticket.body}
    )
    assert isinstance(result, RagAnswer)  # for mypy/pyance

    result.source_documents = source_documents
    return result
