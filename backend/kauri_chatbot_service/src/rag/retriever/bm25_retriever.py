"""
BM25 Retriever for keyword-based search
"""
from typing import List, Dict, Any
import structlog
from rank_bm25 import BM25Okapi
import numpy as np

from ...config import settings

logger = structlog.get_logger()


class BM25Retriever:
    """
    BM25 retriever for keyword-based document search
    Complements vector search with lexical matching
    """
    
    def __init__(self):
        self.bm25 = None
        self.documents = []
        self.document_ids = []
        self.tokenized_corpus = []
        self.k1 = settings.bm25_k1
        self.b = settings.bm25_b
        
        logger.info("bm25_retriever_initialized", k1=self.k1, b=self.b)
    
    def build_index(self, documents: List[Dict[str, Any]]):
        """
        Build BM25 index from documents
        
        Args:
            documents: List of dicts with 'id', 'content', 'metadata'
        """
        logger.info("building_bm25_index", count=len(documents))
        
        self.documents = documents
        self.document_ids = [doc['id'] for doc in documents]
        
        # Tokenize corpus
        self.tokenized_corpus = [
            self._tokenize(doc['content'])
            for doc in documents
        ]
        
        # Build BM25 index
        self.bm25 = BM25Okapi(
            self.tokenized_corpus,
            k1=self.k1,
            b=self.b
        )
        
        logger.info("bm25_index_built", documents=len(documents))
    
    def add_documents(self, documents: List[Dict[str, Any]]):
        """
        Add documents to existing index (rebuild)
        
        Args:
            documents: New documents to add
        """
        all_docs = self.documents + documents
        self.build_index(all_docs)
    
    def search(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """
        Search for relevant documents using BM25
        
        Args:
            query: Search query
            top_k: Number of results to return
            
        Returns:
            List of results with content, score, metadata
        """
        if self.bm25 is None:
            logger.warning("bm25_index_not_built")
            return []
        
        # Tokenize query
        tokenized_query = self._tokenize(query)
        
        # Get BM25 scores
        scores = self.bm25.get_scores(tokenized_query)
        
        # Get top-k indices
        top_indices = np.argsort(scores)[::-1][:top_k]
        
        # Build results
        results = []
        for idx in top_indices:
            if scores[idx] > 0:  # Only include if score > 0
                results.append({
                    'content': self.documents[idx]['content'],
                    'score': float(scores[idx]),
                    'metadata': self.documents[idx].get('metadata', {}),
                    'id': self.document_ids[idx],
                    'rank': len(results) + 1
                })
        
        logger.info("bm25_search_complete", query_length=len(tokenized_query), results=len(results))
        
        return results
    
    def _tokenize(self, text: str) -> List[str]:
        """
        Tokenize text for BM25
        Simple whitespace tokenization with lowercasing
        
        Args:
            text: Input text
            
        Returns:
            List of tokens
        """
        # Simple tokenization: lowercase + split
        # TODO: Add stop words removal, stemming if needed
        return text.lower().split()
    
    def _normalize_scores(self, scores: List[float]) -> List[float]:
        """
        Normalize BM25 scores to 0-1 range
        
        Args:
            scores: Raw BM25 scores
            
        Returns:
            Normalized scores
        """
        if not scores or max(scores) == 0:
            return scores
        
        max_score = max(scores)
        return [score / max_score for score in scores]


# Global singleton
_bm25_retriever = None

def get_bm25_retriever() -> BM25Retriever:
    """Get global BM25 retriever instance"""
    global _bm25_retriever
    if _bm25_retriever is None:
        _bm25_retriever = BM25Retriever()
    return _bm25_retriever
