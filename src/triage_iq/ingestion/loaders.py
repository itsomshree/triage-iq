from pathlib import Path

from langchain_core.documents import Document

DEFAULT_KB_DIR = Path("data/knowledge_base")


def load_knowledge_base(kb_dir: Path | str = DEFAULT_KB_DIR) -> list[Document]:
    kb_dir = Path(kb_dir)

    if not kb_dir.exists():
        raise FileNotFoundError(f"Knowledge base directory not found: {kb_dir}")

    txt_paths = sorted(kb_dir.glob("*.txt"))

    if not txt_paths:
        raise ValueError(
            f"No .txt files found in {kb_dir}."
            f"Ingestion would silently produce zero vectors, refusing to continue."
        )

    documents: list[Document] = []
    for path in txt_paths:
        text = path.read_text(encoding="utf-8").strip()
        documents.append(
            Document(
                page_content=text,
                metadata={"source": path.name},
            )
        )

    return documents
