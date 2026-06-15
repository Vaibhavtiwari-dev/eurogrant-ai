import logging
import typing

from langchain_text_splitters import RecursiveCharacterTextSplitter
from openai import OpenAI
from pinecone import Pinecone, ServerlessSpec

from ..config import settings

logger = logging.getLogger(__name__)


class VectorService:
    def __init__(self):
        api_key = settings.PINECONE_API_KEY
        if not api_key:
            logger.warning("PINECONE_API_KEY not set — running without vector store")
            self.pc = None
            self.index = None
        else:
            self.pc = Pinecone(api_key=api_key)
            self.index_name = settings.PINECONE_INDEX_NAME
            self.dimension = int(settings.EMBEDDING_DIMENSION)

        self.openai_client = OpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
        )
        self.embedding_model = settings.EMBEDDING_MODEL

        # If Pinecone was configured, ensure the index exists and connect
        if self.pc is not None:
            self._ensure_index_and_connect()
        elif not hasattr(self, "index"):
            self.index = None

        self.text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)

    def _ensure_index_and_connect(self):
        if self.pc is None:
            return
        """Ensure the Pinecone index exists and initialise the connection."""
        try:
            active_indexes = [idx.name for idx in self.pc.list_indexes()]
            if self.index_name not in active_indexes:
                self.pc.create_index(
                    name=self.index_name,
                    dimension=self.dimension,
                    metric="cosine",
                    spec=ServerlessSpec(cloud="aws", region=settings.PINECONE_ENVIRONMENT),
                )
                logger.info("Created new Pinecone index: %s. Waiting for readiness...", self.index_name)
                import time

                # Poll for readiness instead of fixed sleep (M11)
                for _attempt in range(10):
                    time.sleep(1)
                    stats = self.pc.Index(self.index_name).describe_index_stats()
                    if stats.get("total_vector_count", 0) > 0:
                        break
        except Exception as e:
            logger.warning("Could not check or create Pinecone index: %s", e)

        try:
            self.index = self.pc.Index(self.index_name)  # type: ignore
        except Exception as e:
            logger.error("Failed to connect to Pinecone index: %s", e)
            self.index = None

    def generate_embeddings(self, text: str) -> list[float]:
        try:
            response = self.openai_client.embeddings.create(input=text, model=self.embedding_model)
            return response.data[0].embedding
        except Exception as e:
            logger.error("Embedding generation failed: %s", e)
            raise

    def upsert_text(self, text: str, doc_id: int, org_id: int):
        chunks = self.text_splitter.split_text(text)
        vectors = []

        for i, chunk in enumerate(chunks):
            embedding = self.generate_embeddings(chunk)
            vectors.append(
                {
                    "id": f"doc_{doc_id}_chunk_{i}",
                    "values": embedding,
                    "metadata": {"doc_id": doc_id, "org_id": org_id, "text": chunk},
                }
            )

        # Upsert in namespace
        namespace = f"org_{org_id}"
        if not self.index:
            logger.warning("Pinecone index not initialized. Bypassed upserting %s chunks to namespace %s (offline mock active)", len(vectors), namespace)
            return

        try:
            self.index.upsert(
                vectors=vectors,  # type: ignore
                namespace=namespace,
            )
            logger.info("Upserted %s chunks for document %s to Pinecone namespace %s", len(vectors), doc_id, namespace)
        except Exception as e:
            logger.error("Pinecone upsert failed for document %s: %s. Bypassed gracefully.", doc_id, e)

    def upsert_grant(self, grant_id: int, text: str, metadata: dict):
        chunks = self.text_splitter.split_text(text)
        vectors = []
        for i, chunk in enumerate(chunks):
            embedding = self.generate_embeddings(chunk)
            vectors.append(
                {
                    "id": f"grant_{grant_id}_chunk_{i}",
                    "values": embedding,
                    "metadata": {"grant_id": grant_id, **metadata, "text": chunk},
                }
            )

        if not self.index:
            logger.warning("Pinecone index not initialized. Bypassed indexing %s chunks to grants namespace (offline mock active)", len(vectors))
            return

        try:
            self.index.upsert(
                vectors=vectors,  # type: ignore
                namespace="grants",
            )
            logger.info("Upserted %s chunks for grant %s to Pinecone namespace grants", len(vectors), grant_id)
        except Exception as e:
            logger.error("Pinecone upsert failed for grant %s: %s. Bypassed gracefully.", grant_id, e)

    def query_grants(self, query_text: str, limit: int = 10) -> list[int]:
        # 1. Generate embedding for query
        try:
            embedding = self.generate_embeddings(query_text)
        except Exception as e:
            logger.error("Could not generate query embeddings: %s", e)
            return []

        if not self.index:
            logger.warning(
                "Pinecone index not initialized. Querying is unavailable (offline mock active)"
            )
            return []

        try:
            # 2. Query Pinecone grants namespace
            results = typing.cast(typing.Any, self.index).query(
                vector=embedding, namespace="grants", top_k=limit, include_metadata=True
            )
            # 3. Extract and standard return grant IDs from metadata
            grant_ids = []
            for match in results.get("matches", []):
                metadata = match.get("metadata", {})
                grant_id = metadata.get("grant_id")
                if grant_id is not None:
                    grant_ids.append(int(grant_id))
            return grant_ids
        except Exception as e:
            logger.error("Pinecone query failed in grants namespace: %s", e)
            return []

    def search_grants(self, query_text: str, top_k: int = 10) -> list[dict]:
        try:
            embedding = self.generate_embeddings(query_text)
        except Exception as e:
            logger.error("Could not generate query embeddings for search_grants: %s", e)
            return []

        if not self.index:
            logger.warning("Pinecone index not initialized for search_grants (offline mock active)")
            return []

        try:
            results = typing.cast(typing.Any, self.index).query(
                vector=embedding, namespace="grants", top_k=top_k, include_metadata=True
            )
            matches = []
            for match in results.get("matches", []):
                metadata = match.get("metadata", {})
                grant_id = metadata.get("grant_id")
                score = match.get("score")
                if grant_id is not None and score is not None:
                    matches.append(
                        {
                            "grant_id": int(grant_id),
                            "score": float(score),
                            "text": metadata.get("text", ""),
                        }
                    )
            return matches
        except Exception as e:
            logger.error("Pinecone query failed in search_grants grants namespace: %s", e)
            return []

    def query_namespace(self, query_text: str, namespace: str, top_k: int = 5) -> list[str]:
        """Retrieve relevant text chunks from a specific Pinecone namespace for RAG.

        Args:
            query_text: The natural-language query to embed and search with.
            namespace: The Pinecone namespace to search within (e.g. ``org_5``).
            top_k: Maximum number of chunks to return.

        Returns:
            A list of text strings from the top-k matching chunks, or an empty
            list if the index is unavailable or the query fails.
        """
        try:
            embedding = self.generate_embeddings(query_text)
        except Exception as e:
            logger.error("Could not generate query embeddings for namespace %s: %s", namespace, e)
            return []

        if not self.index:
            logger.warning(
                "Pinecone index not initialised. query_namespace unavailable (offline mock active)."
            )
            return []

        try:
            results = typing.cast(typing.Any, self.index).query(
                vector=embedding,
                namespace=namespace,
                top_k=top_k,
                include_metadata=True,
            )
            texts = []
            for match in results.get("matches", []):
                metadata = match.get("metadata", {})
                text = metadata.get("text")
                if text:
                    texts.append(text)
            return texts
        except Exception as e:
            logger.error("Pinecone query failed in namespace %s: %s", namespace, e)
            return []


_vector_service: "VectorService | None" = None


def get_vector_service() -> "VectorService":
    """Lazy singleton: initialises the Pinecone client on first use, not at import time.

    This prevents FastAPI boot failures when PINECONE_API_KEY is absent or invalid,
    and avoids expensive network calls during module-load in test contexts.
    """
    global _vector_service
    if _vector_service is None:
        _vector_service = VectorService()
    return _vector_service


def reset_vector_service() -> None:
    """Reset the lazy singleton. Exists solely for test isolation — do NOT call in production."""
    global _vector_service
    _vector_service = None
