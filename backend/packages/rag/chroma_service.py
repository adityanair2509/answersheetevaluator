import os
import uuid
import io
from typing import List

import chromadb
from sentence_transformers import SentenceTransformer
import pypdf
from structlog import get_logger

logger = get_logger(__name__)

CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./.chroma_db")

class ChromaService:
    def __init__(self):
        # Initialize persistent Chroma client
        self.client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
        
        # Use a lightweight sentence transformer for local embeddings
        # This model is fast and performant for basic RAG tasks
        try:
            self.embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
        except Exception as e:
            logger.error("Failed to load SentenceTransformer", error=str(e))
            raise e
            
        self.collection_name = "textbook_references"
        
        # Get or create the collection for exams
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"}
        )
    
    def extract_text_from_pdf(self, file_bytes: bytes) -> str:
        """Extract text from a PDF file in memory."""
        try:
            reader = pypdf.PdfReader(io.BytesIO(file_bytes))
            text = ""
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
            return text
        except Exception as e:
            logger.error("Failed to extract text from PDF", error=str(e))
            return ""

    def chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """Chunks text by trying to preserve paragraph and sentence boundaries."""
        if not text:
            return []

        # First, split by paragraphs
        paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
        chunks = []
        current_chunk = ""

        for p in paragraphs:
            # If paragraph fits in current chunk, add it
            if len(current_chunk) + len(p) + 1 <= chunk_size:
                current_chunk += ("\n" if current_chunk else "") + p
            else:
                # Paragraph doesn't fit; push current chunk and start new one
                if current_chunk:
                    chunks.append(current_chunk)

                # If paragraph itself is larger than chunk_size, split it
                if len(p) > chunk_size:
                    start = 0
                    while start < len(p):
                        end = min(start + chunk_size, len(p))
                        chunks.append(p[start:end])
                        start += (chunk_size - overlap)
                    current_chunk = ""
                else:
                    current_chunk = p

        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    def index_document(self, exam_id: int, file_bytes: bytes) -> int:
        """
        Extracts text from PDF, chunks it, generates embeddings, 
        and stores it in ChromaDB linked to exam_id.
        Returns the number of chunks indexed.
        """
        logger.info(f"Indexing reference document for exam {exam_id}")
        text = self.extract_text_from_pdf(file_bytes)
        if not text.strip():
            logger.warning(f"No text extracted for exam {exam_id}")
            return 0
        
        chunks = self.chunk_text(text)
        if not chunks:
            return 0
        
        logger.info(f"Generated {len(chunks)} chunks. Embedding now...")
        
        # Generate embeddings
        embeddings = self.embedding_model.encode(chunks).tolist()
        
        # Prepare metadata and IDs
        ids = [f"exam_{exam_id}_chunk_{uuid.uuid4().hex}" for _ in chunks]
        metadatas = [{"exam_id": exam_id, "chunk_index": i} for i in range(len(chunks))]
        
        # Insert into ChromaDB
        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=chunks,
            metadatas=metadatas
        )
        logger.info(f"Successfully indexed {len(chunks)} chunks for exam {exam_id} in ChromaDB")
        return len(chunks)

    def retrieve_context(self, exam_id: int, query: str, top_k: int = 3) -> str:
        """
        Retrieves top K most relevant chunks for a given query and exam_id.
        """
        logger.info(f"Retrieving context for exam {exam_id} with query '{query[:30]}...'")
        
        query_embedding = self.embedding_model.encode([query]).tolist()
        
        # Query ChromaDB, filtering by exam_id
        results = self.collection.query(
            query_embeddings=query_embedding,
            n_results=top_k,
            where={"exam_id": exam_id}
        )
        
        documents = results.get("documents")
        if not documents or not documents[0]:
            logger.info("No relevant context found.")
            return ""
            
        # Combine retrieved chunks into a single context string
        context = "\n\n---\n\n".join(documents[0])
        logger.info(f"Retrieved {len(documents[0])} context chunks.")
        return context

# Singleton instance
chroma_service = ChromaService()
