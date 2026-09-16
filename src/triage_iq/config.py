import os

from dotenv import load_dotenv

load_dotenv()


def _require(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(
            f"Missing required environment variable: {name}. "
            f"Check your .env file against .env.example."
        )
    return value


# Groq (LLM)
GROQ_API_KEY = _require("GROQ_API_KEY")
GROQ_CLASSIFIER_MODEL = os.getenv("GROQ_CLASSIFIER_MODEL", "openai/gpt-oss-120b")
GROQ_REASONING_MODEL = os.getenv("GROQ_REASONING_MODEL", "openai/gpt-oss-120b")

# Pinecone (vector store)
PINECONE_API_KEY = _require("PINECONE_API_KEY")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "triage-iq-kb")
EMBEDDING_MODEL_NAME = os.getenv(
    "EMBEDDING_MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2"
)
EMBEDDING_DIMENSIONS = 384  # match all-MiniLM-L6-v2 output dimension

# Supabase / Postgres
SUPABASE_URL = _require("SUPABASE_URL")
SUPABASE_KEY = _require("SUPABASE_KEY")
DATABASE_URL = _require("DATABASE_URL")

# Retrieval / chunking
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "500"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "50"))
RETRIEVAL_TOP_K = int(os.getenv("RETRIEVAL_TOP_K", "4"))

# Routing thresholds
LOW_CONFIDENCE_THRESHOLD = float(os.getenv("LOW_CONFIDENCE_THRESHOLD", "0.6"))
