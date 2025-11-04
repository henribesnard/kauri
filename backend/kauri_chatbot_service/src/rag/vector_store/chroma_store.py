"""
ChromaDB Vector Store for document embeddings
"""
from typing import List, Dict, Any, Optional
import structlog
import chromadb
from chromadb.config import Settings as ChromaSettings

from ...config import settings

logger = structlog.get_logger()


class ChromaStore:
    """
    ChromaDB vector store interface
    Stores document embeddings and performs similarity search
    """
    
    def __init__(self, collection_name: str = "kauri_ohada_knowledge"):
        self.collection_name = collection_name
        self.client = None
        self.collection = None
        self._connect()
    
    def _connect(self):
        """Connect to ChromaDB server"""
        try:
            logger.info(
                "connecting_to_chromadb",
                host=settings.vector_db_host,
                port=settings.vector_db_port
            )
            
            self.client = chromadb.HttpClient(
                host=settings.vector_db_host,
                port=settings.vector_db_port,
                settings=ChromaSettings(anonymized_telemetry=False)
            )
            
            # Test connection
            self.client.heartbeat()
            
            # Get or create collection
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name
            )
            
            logger.info(
                "chromadb_connected",
                collection=self.collection_name,
                count=self.collection.count()
            )
            
        except Exception as e:
            logger.error("chromadb_connection_failed", error=str(e))
            raise
    
    def add_documents(
        self,
        ids: List[str],
        documents: List[str],
        embeddings: List[List[float]],
        metadatas: Optional[List[Dict[str, Any]]] = None
    ):
        """
        Add documents with embeddings to the collection
        
        Args:
            ids: Unique IDs for each document
            documents: Document texts
            embeddings: Pre-computed embedding vectors
            metadatas: Optional metadata for each document
        """
        try:
            logger.info("adding_documents_to_chromadb", count=len(ids))
            
            self.collection.add(
                ids=ids,
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas or [{} for _ in ids]
            )
            
            logger.info("documents_added_to_chromadb", count=len(ids))
            
        except Exception as e:
            logger.error("chromadb_add_failed", error=str(e))
            raise
    
    def search(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        where: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar documents
        
        Args:
            query_embedding: Query embedding vector
            top_k: Number of results to return
            where: Optional metadata filter
            
        Returns:
            List of results with content, score, metadata
        """
        try:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=where
            )
            
            # Format results
            formatted_results = []
            if results and results["documents"]:
                for i, (doc, metadata, distance) in enumerate(zip(
                    results["documents"][0],
                    results["metadatas"][0],
                    results["distances"][0]
                )):
                    formatted_results.append({
                        "content": doc,
                        "score": 1.0 - distance,  # Convert distance to similarity
                        "metadata": metadata,
                        "rank": i + 1
                    })
            
            logger.info("chromadb_search_complete", results=len(formatted_results))
            
            return formatted_results
            
        except Exception as e:
            logger.error("chromadb_search_failed", error=str(e))
            return []
    
    def delete_documents(self, ids: List[str]):
        """Delete documents by IDs"""
        try:
            self.collection.delete(ids=ids)
            logger.info("documents_deleted", count=len(ids))
        except Exception as e:
            logger.error("chromadb_delete_failed", error=str(e))
            raise
    
    def count(self) -> int:
        """Get total number of documents in collection"""
        return self.collection.count()
    
    def clear(self):
        """Clear all documents from collection"""
        try:
            self.client.delete_collection(name=self.collection_name)
            self.collection = self.client.create_collection(
                name=self.collection_name
            )
            logger.info("chromadb_collection_cleared")
        except Exception as e:
            logger.error("chromadb_clear_failed", error=str(e))
            raise


# Global singleton
_chroma_store = None

def get_chroma_store() -> ChromaStore:
    """Get global ChromaDB store instance"""
    global _chroma_store
    if _chroma_store is None:
        _chroma_store = ChromaStore()
    return _chroma_store
