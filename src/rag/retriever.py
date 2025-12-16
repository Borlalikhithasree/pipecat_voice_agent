"""
Retriever - Handles document retrieval from knowledge base (Milvus + FAISS Support)
"""

from typing import List, Optional, Dict
from src.utils.logger import logging
from .knowledge_base import KnowledgeBase


class Retriever:
    """Retrieve relevant documents from the knowledge base"""

    def __init__(self, knowledge_base: KnowledgeBase, top_k: int = 3):
        """
        Args:
            knowledge_base: KnowledgeBase instance
            top_k: number of top results to retrieve
        """
        self.kb = knowledge_base
        self.top_k = top_k

    # ----------------------------------------------------------------------
    # BASIC RETRIEVAL — return only text chunks
    # ----------------------------------------------------------------------
    def retrieve(self, query: str, n_results: Optional[int] = None) -> List[str]:
        """Retrieve only document contents (text)

        Returns:
            List[str] => list of content strings
        """
        n = n_results or self.top_k

        results = self.kb.query(query, n_results=n)
        if not results or "results" not in results:
            logging.warning("⚠️ No results returned from KnowledgeBase")
            return []

        contents = [item.get("content", "") for item in results["results"]]
        logging.info(f"📚 Retrieved {len(contents)} documents")
        return contents

    # ----------------------------------------------------------------------
    # FULL RETRIEVAL — return content + metadata
    # ----------------------------------------------------------------------
    def retrieve_with_metadata(self, query: str, n_results: Optional[int] = None) -> List[Dict]:
        """Retrieve documents with metadata and distances

        Returns:
            List[Dict] => [{ content, metadata, score }]
        """
        n = n_results or self.top_k

        results = self.kb.query(query, n_results=n)
        if not results or "results" not in results:
            return []

        output = []
        for item in results["results"]:
            output.append({
                "content": item.get("content", ""),
                "metadata": item.get("metadata", {}),
                "score": item.get("score", None),
                "id": item.get("id", None),
            })

        return output