from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from triage_iq.config import CHUNK_OVERLAP, CHUNK_SIZE


def split_documents(documents: list[Document]) -> list[Document]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", " ", ""],
    )

    chunks: list[Document] = []
    for doc in documents:
        doc_chunks = splitter.split_documents([doc])
        for index, chunk in enumerate(doc_chunks):
            chunk.metadata["chunk_index"] = index
            chunks.append(chunk)

    return chunks
