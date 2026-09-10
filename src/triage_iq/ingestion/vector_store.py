import hashlib

from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone, ServerlessSpec

from triage_iq.config import (
    EMBEDDING_DIMENSIONS,
    EMBEDDING_MODEL_NAME,
    PINECONE_API_KEY,
    PINECONE_INDEX_NAME,
)

_pc = Pinecone(api_key=PINECONE_API_KEY)


def _ensure_index_exists() -> None:
    existing = {index.name for index in _pc.list_indexes()}
    if PINECONE_INDEX_NAME not in existing:
        _pc.create_index(
            name=PINECONE_INDEX_NAME,
            dimension=EMBEDDING_DIMENSIONS,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
        )


def get_vector_store() -> PineconeVectorStore:
    _ensure_index_exists()
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)
    index = _pc.Index(PINECONE_INDEX_NAME)
    return PineconeVectorStore(index=index, embedding=embeddings)


def _chunk_id(chunk: Document) -> str:
    source = chunk.metadata["source"]
    chunk_index = chunk.metadata["chunk_index"]
    raw = f"{source}::{chunk_index}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def upsert_documents(chunks: list[Document]) -> list[str]:
    vector_store = get_vector_store()
    ids = [_chunk_id(chunk) for chunk in chunks]
    vector_store.add_documents(documents=chunks, ids=ids)
    return ids
