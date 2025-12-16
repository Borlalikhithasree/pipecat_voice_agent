"""
Document Loader - PDF + TXT loader
"""

import os
from typing import List, Dict
from loguru import logger
from src.utils.logger import logging


class DocumentLoader:

    @staticmethod
    def load_pdf(file_path: str) -> List[Dict]:
        """Load PDF and return page-wise documents"""

        if not os.path.exists(file_path):
            logging.error(f"❌ PDF not found: {file_path}")
            return []

        try:
            from langchain_community.document_loaders import PyPDFLoader
        except ImportError:
            logging.error("❌ langchain_community not installed")
            return []

        loader = PyPDFLoader(file_path)
        pages = loader.load()

        documents = []
        for i, page in enumerate(pages):
            documents.append({
                "content": page.page_content.strip(),
                "metadata": {
                    "source": os.path.basename(file_path),
                    "page": i + 1
                }
            })

        logging.info(f"✅ Loaded {len(documents)} pages from PDF")
        return documents