"""
BGE-M3 Embedder for semantic search
"""
from typing import List, Union
import numpy as np
import structlog
from sentence_transformers import SentenceTransformer

from ...config import settings

logger = structlog.get_logger()


class BGEEmbedder:
    """
    BGE-M3 embedder (1024 dimensions)
    Optimized for multilingual and long context
    """
    
    def __init__(self):
        self.model = None
        self.model_name = settings.embedding_model
        self.dimension = settings.embedding_dimension
        self.device = settings.embedding_device
        logger.info("embedder_initialized_lazy", model=self.model_name)
    
    def _load_model(self):
        """Lazy load model on first use"""
        if self.model is None:
            logger.info("loading_embedding_model", model=self.model_name, device=self.device)
            self.model = SentenceTransformer(self.model_name, device=self.device)
            logger.info("embedding_model_loaded", model=self.model_name)
    
    def embed_text(self, text: str, normalize: bool = True) -> List[float]:
        """
        Embed single text
        
        Args:
            text: Input text
            normalize: Apply L2 normalization (for cosine similarity)
            
        Returns:
            Embedding vector as list of floats
        """
        self._load_model()
        
        embedding = self.model.encode(
            text,
            normalize_embeddings=normalize,
            show_progress_bar=False
        )
        
        return embedding.tolist()
    
    def embed_batch(
        self, 
        texts: List[str], 
        normalize: bool = True,
        batch_size: int = None
    ) -> List[List[float]]:
        """
        Embed multiple texts in batch
        
        Args:
            texts: List of input texts
            normalize: Apply L2 normalization
            batch_size: Batch size for processing
            
        Returns:
            List of embedding vectors
        """
        self._load_model()
        
        batch_size = batch_size or settings.embedding_batch_size
        
        logger.info("embedding_batch_start", count=len(texts), batch_size=batch_size)
        
        embeddings = self.model.encode(
            texts,
            normalize_embeddings=normalize,
            batch_size=batch_size,
            show_progress_bar=len(texts) > 10
        )
        
        logger.info("embedding_batch_complete", count=len(texts))
        
        return embeddings.tolist()
    
    def similarity(self, text1: str, text2: str) -> float:
        """
        Compute cosine similarity between two texts
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            Similarity score (0-1)
        """
        emb1 = np.array(self.embed_text(text1))
        emb2 = np.array(self.embed_text(text2))
        
        # Cosine similarity
        similarity = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
        
        return float(similarity)


# Global singleton instance
_embedder = None

def get_embedder() -> BGEEmbedder:
    """Get global embedder instance (singleton)"""
    global _embedder
    if _embedder is None:
        _embedder = BGEEmbedder()
    return _embedder
