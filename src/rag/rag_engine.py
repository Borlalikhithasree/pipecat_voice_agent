
"""
RAG Engine - Main orchestrator for RAG pipeline
"""
from typing import List, Optional
from loguru import logger
from .document_loader import DocumentLoader
from .knowledge_base import KnowledgeBase
from .retriever import Retriever
from .reranker import Reranker
from .embedder import Embedder
from src.utils.logger import logging


class RAGEngine:
    """Complete RAG pipeline orchestrator"""
    
    def __init__(
        self,
        collection_name: str = "knowledge_base",
        top_k: int = 3,
        use_reranker: bool = False
    ):
        """Initialize RAG engine
        
        Args:
            collection_name: Name of the vector store collection
            top_k: Number of documents to retrieve
            use_reranker: Whether to use reranking
        """
        self.collection_name = collection_name
        self.top_k = top_k
        self.use_reranker = use_reranker
        
        self.embedder = Embedder()
        self.knowledge_base = KnowledgeBase(collection_name, self.embedder)
        self.retriever = Retriever(self.knowledge_base, top_k)
        self.reranker = Reranker() if use_reranker else None
        
        self.is_initialized = False
    
    def initialize(self, file_paths: List[str], force_recreate: bool = False) -> bool:
        """Initialize the RAG engine with documents
        
        Args:
            file_paths: List of document file paths
            force_recreate: Force recreation of knowledge base
            
        Returns:
            bool: Success status
        """
        logging.info("🔧 Initializing RAG engine...")
        
        # Try to load existing collection
        if not force_recreate and self.knowledge_base.load_collection():
            self.is_initialized = True
            return True
        
        # Load documents
        logging.info("📄 Loading documents...")
        documents = DocumentLoader.load_documents(file_paths)
        
        if not documents:
            logging.error("No documents loaded")
            return False
        
        # Create knowledge base
        success = self.knowledge_base.create_collection(documents)
        self.is_initialized = success
        
        return success
    
    def get_context(self, query: str, n_results: Optional[int] = None) -> str:
        """Get relevant context for a query
        
        Args:
            query: User query
            n_results: Number of results to retrieve
            
        Returns:
            str: Combined context from retrieved documents
        """
        if not self.is_initialized:
            logging.warning("RAG engine not initialized")
            return ""
        
        # Retrieve documents
        if self.use_reranker:
            docs = self.retriever.retrieve_with_metadata(query, n_results)
            docs = self.reranker.rerank(query, docs)
            context_parts = [doc['content'] for doc in docs]
        else:
            context_parts = self.retriever.retrieve(query, n_results)
        
        if not context_parts:
            return ""
        
        # Combine context
        context = "\n\n".join(context_parts)
        return context
    
    def query(self, query: str, n_results: Optional[int] = None) -> dict:
        """Full RAG query with metadata
        
        Args:
            query: User query
            n_results: Number of results
            
        Returns:
            dict with 'context', 'sources', and 'num_docs'
        """
        if not self.is_initialized:
            return {"context": "", "sources": [], "num_docs": 0}
        
        docs = self.retriever.retrieve_with_metadata(query, n_results)
        
        if self.use_reranker and docs:
            docs = self.reranker.rerank(query, docs)
        
        context = "\n\n".join([doc['content'] for doc in docs])
        sources = [doc['metadata'].get('source', 'unknown') for doc in docs]
        
        return {
            "context": context,
            "sources": list(set(sources)),
            "num_docs": len(docs)
        }