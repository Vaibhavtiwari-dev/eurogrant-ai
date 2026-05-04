import os
from pinecone import Pinecone, ServerlessSpec
from openai import OpenAI
from langchain_text_splitters import RecursiveCharacterTextSplitter
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

class VectorService:
    def __init__(self):
        self.pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.index_name = os.getenv("PINECONE_INDEX_NAME", "eurogrant")
        self.dimension = 1536 # text-embedding-3-small
        
        # Ensure index exists
        try:
            if self.index_name not in [idx.name for idx in self.pc.list_indexes()]:
                self.pc.create_index(
                    name=self.index_name,
                    dimension=self.dimension,
                    metric='cosine',
                    spec=ServerlessSpec(
                        cloud='aws',
                        region=os.getenv('AWS_REGION', 'eu-central-1')
                    )
                )
        except Exception as e:
            logger.warning(f"Could not check or create Pinecone index: {e}")

        self.index = self.pc.Index(self.index_name)
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=100
        )

    def generate_embeddings(self, text: str) -> List[float]:
        response = self.openai_client.embeddings.create(
            input=text,
            model="text-embedding-3-small"
        )
        return response.data[0].embedding

    def upsert_text(self, text: str, doc_id: int, org_id: int):
        chunks = self.text_splitter.split_text(text)
        vectors = []
        
        for i, chunk in enumerate(chunks):
            embedding = self.generate_embeddings(chunk)
            vectors.append({
                "id": f"doc_{doc_id}_chunk_{i}",
                "values": embedding,
                "metadata": {
                    "doc_id": doc_id,
                    "org_id": org_id,
                    "text": chunk
                }
            })
        
        # Upsert in namespace
        namespace = f"org_{org_id}"
        self.index.upsert(vectors=vectors, namespace=namespace)
        logger.info(f"Upserted {len(vectors)} chunks for document {doc_id} to Pinecone namespace {namespace}")

vector_service = VectorService()
