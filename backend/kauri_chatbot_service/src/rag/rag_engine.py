"""
Simplified RAG Engine - combines embedder, retriever, reranker
"""
from typing import List, Dict, Any, Optional
import structlog
from sentence_transformers import SentenceTransformer
import chromadb
from rank_bm25 import BM25Okapi
import numpy as np

from ..config import settings

logger = structlog.get_logger()


class RAGEngine:
    """Unified RAG engine with vector + BM25 hybrid search"""

    def __init__(self):
        # Embedder
        logger.info("loading_embedding_model", model=settings.embedding_model)
        self.embedder = SentenceTransformer(settings.embedding_model)
        
        # Vector Store (ChromaDB)
        self.chroma_client = chromadb.HttpClient(
            host=settings.vector_db_host,
            port=settings.vector_db_port
        )
        
        try:
            self.collection = self.chroma_client.get_or_create_collection(
                name="kauri_ohada_knowledge",
                metadata={"hnsw:space": "cosine"}
            )
            logger.info("chromadb_connected", collection="kauri_ohada_knowledge")
        except Exception as e:
            logger.warning("chromadb_connection_failed", error=str(e))
            self.collection = None
        
        # BM25 (will be built when documents are indexed)
        self.bm25 = None
        self.documents = []
        
        logger.info("rag_engine_initialized")

    def embed_text(self, text: str) -> List[float]:
        """Embed text using BGE-M3"""
        return self.embedder.encode(text, normalize_embeddings=True).tolist()

    def add_documents(self, documents: List[Dict[str, Any]]):
        """
        Index documents into vector store and BM25
        
        Args:
            documents: List of dicts with 'id', 'content', 'metadata'
        """
        if not documents:
            return
        
        # Store for BM25
        self.documents = documents
        
        # Build BM25 index
        tokenized_docs = [doc["content"].lower().split() for doc in documents]
        self.bm25 = BM25Okapi(tokenized_docs)
        
        # Add to ChromaDB
        if self.collection:
            try:
                ids = [doc["id"] for doc in documents]
                texts = [doc["content"] for doc in documents]
                metadatas = [doc.get("metadata", {}) for doc in documents]
                
                # Embed texts
                embeddings = self.embedder.encode(texts, normalize_embeddings=True).tolist()
                
                self.collection.add(
                    ids=ids,
                    documents=texts,
                    embeddings=embeddings,
                    metadatas=metadatas
                )
                
                logger.info("documents_indexed", count=len(documents))
            except Exception as e:
                logger.error("indexing_failed", error=str(e))

    def retrieve(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """
        Hybrid retrieval: Vector + BM25
        
        Args:
            query: Search query
            top_k: Number of results
            
        Returns:
            List of documents with scores
        """
        results = []
        
        # Vector search
        if self.collection:
            try:
                query_embedding = self.embed_text(query)
                vector_results = self.collection.query(
                    query_embeddings=[query_embedding],
                    n_results=top_k
                )
                
                if vector_results and vector_results["documents"]:
                    for i, (doc, metadata, distance) in enumerate(zip(
                        vector_results["documents"][0],
                        vector_results["metadatas"][0],
                        vector_results["distances"][0]
                    )):
                        results.append({
                            "content": doc,
                            "score": 1.0 - distance,  # Convert distance to similarity
                            "metadata": metadata,
                            "source": "vector"
                        })
                        
                logger.info("vector_search_complete", results=len(results))
            except Exception as e:
                logger.error("vector_search_failed", error=str(e))
        
        # BM25 search (if no vector results or as supplement)
        if self.bm25 and self.documents:
            try:
                tokenized_query = query.lower().split()
                bm25_scores = self.bm25.get_scores(tokenized_query)
                top_indices = np.argsort(bm25_scores)[::-1][:top_k]
                
                for idx in top_indices:
                    if bm25_scores[idx] > 0:
                        results.append({
                            "content": self.documents[idx]["content"],
                            "score": float(bm25_scores[idx]),
                            "metadata": self.documents[idx].get("metadata", {}),
                            "source": "bm25"
                        })
                        
                logger.info("bm25_search_complete", results=len(results))
            except Exception as e:
                logger.error("bm25_search_failed", error=str(e))
        
        # Deduplicate and sort by score
        seen_content = set()
        unique_results = []
        for doc in sorted(results, key=lambda x: x["score"], reverse=True):
            if doc["content"] not in seen_content:
                seen_content.add(doc["content"])
                unique_results.append(doc)
                if len(unique_results) >= top_k:
                    break
        
        return unique_results[:top_k]


# Global instance
rag_engine = RAGEngine()
