from langchain_classic.retrievers import ContextualCompressionRetriever
from langchain_classic.retrievers.document_compressors import LLMChainExtractor
from langchain_core.vectorstores import VectorStoreRetriever
from langchain_groq import ChatGroq
from pydantic import SecretStr

from triage_iq.config import GROQ_API_KEY, GROQ_CLASSIFIER_MODEL, RETRIEVAL_TOP_K
from triage_iq.ingestion.vector_store import get_vector_store


def get_base_retriever() -> VectorStoreRetriever:
    vector_store = get_vector_store()
    return vector_store.as_retriever(search_kwargs={"k": RETRIEVAL_TOP_K})


def get_compression_retriever() -> ContextualCompressionRetriever:
    base_retriever = get_base_retriever()

    llm = ChatGroq(
        api_key=SecretStr(GROQ_API_KEY),
        model=GROQ_CLASSIFIER_MODEL,
        temperature=0.0,
    )
    compressor = LLMChainExtractor.from_llm(llm)

    return ContextualCompressionRetriever(
        base_compressor=compressor,
        base_retriever=base_retriever,
    )
