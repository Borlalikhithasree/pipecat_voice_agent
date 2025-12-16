"""
Embedder - SentenceTransformer based
"""

from typing import List
from sentence_transformers import SentenceTransformer


class Embedder:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)

    def embed_batch(self, texts: List[str]):
        """
        Returns List[List[float]]
        """
        return self.model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True
        ).tolist()