"""
Cross-Encoder Reranker for improving retrieval quality
"""
from typing import List, Dict, Any
import structlog
from sentence_transformers import CrossEncoder

from ...config import settings

logger = structlog.get_logger()


class CrossEncoderReranker:
    """
    Cross-encoder reranker using BAAI bge-reranker
    Scores query-document pairs for better ranking
    """
    
    def __init__(self):
        self.model = None
        self.model_name = settings.reranker_model
        logger.info("reranker_initialized_lazy", model=self.model_name)
    
    def _load_model(self):
        """Lazy load model on first use"""
        if self.model is None:
            logger.info("loading_reranker_model", model=self.model_name)
            self.model = CrossEncoder(self.model_name)
            logger.info("reranker_model_loaded")
    
    def rerank(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        top_k: int = None
    ) -> List[Dict[str, Any]]:
        """
        Rerank documents based on query-document relevance
        
        Args:
            query: Search query
            documents: List of candidate documents
            top_k: Number of top results to return (default: from settings)
            
        Returns:
            Reranked list of documents with updated scores
        """
        if not documents:
            return []
        
        self._load_model()
        
        top_k = top_k or settings.rag_rerank_top_k
        
        logger.info("reranking_documents", query_length=len(query), candidates=len(documents), top_k=top_k)
        
        # Prepare query-document pairs
        pairs = [[query, doc['content']] for doc in documents]
        
        # Get cross-encoder scores
        scores = self.model.predict(pairs)
        
        # Add scores to documents and sort
        for doc, score in zip(documents, scores):
            doc['rerank_score'] = float(score)
            doc['original_score'] = doc.get('score', 0.0)
            doc['score'] = float(score)  # Replace with rerank score
        
        # Sort by rerank score
        reranked = sorted(documents, key=lambda x: x['rerank_score'], reverse=True)
        
        # Take top-k
        reranked = reranked[:top_k]
        
        # Update ranks
        for i, doc in enumerate(reranked):
            doc['rank'] = i + 1
        
        logger.info("reranking_complete", results=len(reranked))
        
        return reranked
    
    def score_pair(self, query: str, document: str) -> float:
        """
        Score a single query-document pair
        
        Args:
            query: Query text
            document: Document text
            
        Returns:
            Relevance score
        """
        self._load_model()
        score = self.model.predict([[query, document]])
        return float(score[0])


# Global singleton
_reranker = None

def get_reranker() -> CrossEncoderReranker:
    """Get global reranker instance"""
    global _reranker
    if _reranker is None:
        _reranker = CrossEncoderReranker()
    return _reranker
