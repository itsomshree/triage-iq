from triage_iq.ingestion.loaders import load_knowledge_base
from triage_iq.ingestion.splitters import split_documents
from triage_iq.ingestion.vector_store import upsert_documents


def main() -> None:
    print("Loading knowledge base documents...")
    documents = load_knowledge_base()
    print(f" Loaded {len(documents)} document(s):")
    for doc in documents:
        print(f"  - {doc.metadata['source']}")

    print("Splitting into chunks...")
    chunks = split_documents(documents)
    print(f" Produced {len(chunks)} chunk(s).")

    print("Embedding and upserting into Pinecone...")
    ids = upsert_documents(chunks)
    print(f" Upserted {len(ids)} vector(s).")

    print("Knowledge base ingestion complete.")


if __name__ == "__main__":
    main()
