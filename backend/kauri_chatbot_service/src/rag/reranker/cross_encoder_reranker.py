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
        top_k: int = None,
        use_dynamic_filtering: bool = True,
        requested_count: int = None
    ) -> List[Dict[str, Any]]:
        """
        Rerank documents based on query-document relevance with dynamic filtering

        Args:
            query: Search query
            documents: List of candidate documents
            top_k: Number of top results to return (default: from settings, used as fallback)
            use_dynamic_filtering: Use score-based dynamic filtering (default: True)
            requested_count: Explicitly requested number of sources by user (overrides all other logic)

        Returns:
            Reranked list of documents with updated scores

        Priority Logic:
            1. If requested_count is provided -> return exactly that many (user explicit request)
            2. Else if use_dynamic_filtering -> apply dynamic score-based filtering
            3. Else -> return top_k (traditional fixed count)

        Dynamic Filtering Logic (when no explicit request):
            1. Filter documents above min_score_threshold
            2. If < min_documents pass threshold -> keep top min_documents
            3. If > max_documents pass threshold -> limit to max_documents
            4. Otherwise -> keep all documents above threshold
        """
        if not documents:
            return []

        self._load_model()

        top_k = top_k or settings.rag_rerank_top_k

        logger.info("reranking_documents",
                   query_length=len(query),
                   candidates=len(documents),
                   use_dynamic_filtering=use_dynamic_filtering)

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

        # Priority 1: User explicit request
        if requested_count is not None:
            final_docs = reranked[:requested_count]
            logger.info("reranking_user_requested",
                       requested=requested_count,
                       kept=len(final_docs))
            reranked = final_docs

        # Priority 2: Dynamic filtering
        elif use_dynamic_filtering:
            min_threshold = settings.rag_min_score_threshold
            min_docs = settings.rag_min_documents
            max_docs = settings.rag_max_documents

            # Filter documents above threshold
            above_threshold = [doc for doc in reranked if doc['score'] >= min_threshold]

            # Apply logic
            if len(above_threshold) < min_docs:
                # Keep minimum documents even if below threshold
                final_docs = reranked[:min_docs]
                logger.info("reranking_dynamic_min",
                           above_threshold=len(above_threshold),
                           kept=len(final_docs),
                           threshold=min_threshold)
            elif len(above_threshold) > max_docs:
                # Limit to maximum
                final_docs = above_threshold[:max_docs]
                logger.info("reranking_dynamic_max",
                           above_threshold=len(above_threshold),
                           kept=len(final_docs),
                           threshold=min_threshold)
            else:
                # Keep all above threshold
                final_docs = above_threshold
                logger.info("reranking_dynamic_threshold",
                           kept=len(final_docs),
                           threshold=min_threshold)

            reranked = final_docs
        else:
            # Traditional fixed top-k
            reranked = reranked[:top_k]
            logger.info("reranking_fixed_topk", kept=top_k)

        # Update ranks
        for i, doc in enumerate(reranked):
            doc['rank'] = i + 1

        logger.info("reranking_complete",
                   results=len(reranked),
                   scores=[f"{doc['score']:.3f}" for doc in reranked])

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
