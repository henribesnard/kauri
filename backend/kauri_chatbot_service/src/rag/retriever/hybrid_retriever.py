"""
Hybrid Retriever combining Vector + BM25 + Reranking
"""
from typing import List, Dict, Any
import structlog

from ...config import settings
from ..embedder.bge_embedder import get_embedder
from ..vector_store.chroma_store import get_chroma_store
from .bm25_retriever import get_bm25_retriever
from ..reranker.cross_encoder_reranker import get_reranker

logger = structlog.get_logger()


class HybridRetriever:
    """
    Hybrid retrieval combining:
    1. Vector search (semantic)
    2. BM25 search (lexical)
    3. Score fusion
    4. Cross-encoder reranking
    """
    
    def __init__(self):
        self.embedder = get_embedder()
        self.vector_store = get_chroma_store()
        self.bm25_retriever = get_bm25_retriever()
        self.reranker = get_reranker()
        
        self.vector_weight = 0.6  # Weight for vector search
        self.bm25_weight = 0.4    # Weight for BM25 search
        
        logger.info(
            "hybrid_retriever_initialized",
            vector_weight=self.vector_weight,
            bm25_weight=self.bm25_weight
        )
    
    def retrieve(
        self,
        query: str,
        top_k: int = None,
        use_reranking: bool = None
    ) -> List[Dict[str, Any]]:
        """
        Hybrid retrieval pipeline
        
        Args:
            query: Search query
            top_k: Final number of results (default: from settings)
            use_reranking: Whether to apply reranking (default: from settings)
            
        Returns:
            List of relevant documents with scores
        """
        top_k = top_k or settings.rag_top_k
        use_reranking = use_reranking if use_reranking is not None else settings.rag_enable_reranking
        
        logger.info("hybrid_retrieval_start", query_length=len(query), top_k=top_k)
        
        # Step 1: Vector Search
        query_embedding = self.embedder.embed_text(query)
        vector_results = self.vector_store.search(
            query_embedding,
            top_k=top_k * 2  # Get more candidates
        )
        logger.info("vector_search_complete", results=len(vector_results))
        
        # Step 2: BM25 Search
        bm25_results = self.bm25_retriever.search(query, top_k=top_k * 2)
        logger.info("bm25_search_complete", results=len(bm25_results))
        
        # Step 3: Fusion
        fused_results = self._fuse_results(vector_results, bm25_results)
        logger.info("fusion_complete", results=len(fused_results))
        
        # Step 4: Reranking (optional)
        if use_reranking and settings.rag_rerank_top_k > 0:
            # Take top candidates for reranking
            candidates = fused_results[:top_k * 2]
            final_results = self.reranker.rerank(
                query,
                candidates,
                top_k=settings.rag_rerank_top_k
            )
            logger.info("reranking_complete", results=len(final_results))
        else:
            final_results = fused_results[:top_k]
        
        logger.info("hybrid_retrieval_complete", final_results=len(final_results))
        
        return final_results
    
    def _fuse_results(
        self,
        vector_results: List[Dict[str, Any]],
        bm25_results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Fuse vector and BM25 results with weighted scoring
        
        Args:
            vector_results: Results from vector search
            bm25_results: Results from BM25 search
            
        Returns:
            Merged and sorted results
        """
        # Normalize scores
        vector_results = self._normalize_scores(vector_results)
        bm25_results = self._normalize_scores(bm25_results)
        
        # Merge by content
        merged = {}
        
        # Add vector results
        for doc in vector_results:
            content = doc['content']
            merged[content] = {
                **doc,
                'vector_score': doc['score'],
                'bm25_score': 0.0,
                'fusion_score': doc['score'] * self.vector_weight
            }
        
        # Add/update with BM25 results
        for doc in bm25_results:
            content = doc['content']
            if content in merged:
                # Update existing
                merged[content]['bm25_score'] = doc['score']
                merged[content]['fusion_score'] += doc['score'] * self.bm25_weight
            else:
                # Add new
                merged[content] = {
                    **doc,
                    'vector_score': 0.0,
                    'bm25_score': doc['score'],
                    'fusion_score': doc['score'] * self.bm25_weight
                }
        
        # Convert to list and sort by fusion score
        fused_list = list(merged.values())
        fused_list.sort(key=lambda x: x['fusion_score'], reverse=True)
        
        # Update scores and ranks
        for i, doc in enumerate(fused_list):
            doc['score'] = doc['fusion_score']
            doc['rank'] = i + 1
        
        return fused_list
    
    def _normalize_scores(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Normalize scores to 0-1 range using min-max normalization
        
        Args:
            results: Results with scores
            
        Returns:
            Results with normalized scores
        """
        if not results:
            return results
        
        scores = [doc['score'] for doc in results]
        min_score = min(scores)
        max_score = max(scores)
        
        if max_score == min_score:
            # All scores are same
            for doc in results:
                doc['score'] = 1.0
        else:
            # Min-max normalization
            for doc in results:
                doc['score'] = (doc['score'] - min_score) / (max_score - min_score)
        
        return results


# Global singleton
_hybrid_retriever = None

def get_hybrid_retriever() -> HybridRetriever:
    """Get global hybrid retriever instance"""
    global _hybrid_retriever
    if _hybrid_retriever is None:
        _hybrid_retriever = HybridRetriever()
    return _hybrid_retriever
