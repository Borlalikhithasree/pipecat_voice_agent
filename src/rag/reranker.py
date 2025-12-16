
"""
Reranker - Optional reranking of retrieved documents
"""
from typing import List, Dict
from loguru import logger
from src.utils.logger import logging


class Reranker:
    """Rerank retrieved documents for better relevance"""
    
    def __init__(self, method: str = "simple"):
        """Initialize reranker
        
        Args:
            method: Reranking method ('simple', 'distance', etc.)
        """
        self.method = method
    
    def rerank(self, query: str, documents: List[Dict]) -> List[Dict]:
        """Rerank documents based on relevance
        
        Args:
            query: Original query
            documents: List of documents with metadata
            
        Returns:
            Reranked list of documents
        """
        if self.method == "simple":
            # Simple keyword-based reranking
            return self._simple_rerank(query, documents)
        elif self.method == "distance":
            # Sort by distance (already done by retriever)
            return documents
        else:
            return documents
    
    def _simple_rerank(self, query: str, documents: List[Dict]) -> List[Dict]:
        """Simple keyword-based reranking"""
        query_words = set(query.lower().split())
        
        # Calculate keyword overlap score
        for doc in documents:
            content_words = set(doc['content'].lower().split())
            overlap = len(query_words & content_words)
            doc['rerank_score'] = overlap
        
        # Sort by score
        reranked = sorted(documents, key=lambda x: x.get('rerank_score', 0), reverse=True)
        
        logging.debug(f"Reranked {len(documents)} documents")
        return reranked