"""
Knowledge Base - Milvus Server + FAISS fallback
"""

from typing import List, Dict, Optional
import json
import numpy as np
from loguru import logger
from src.utils.logger import logging
from .embedder import Embedder

from pymilvus import (
    connections,
    FieldSchema,
    CollectionSchema,
    DataType,
    Collection,
    utility,
)


class KnowledgeBase:
    def __init__(
        self,
        collection_name: str = "loan_recovery_kb",
        embedder: Optional[Embedder] = None,
        host: str = "127.0.0.1",
        port: str = "19530",
    ):
        self.collection_name = collection_name
        self.embedder = embedder or Embedder()
        self.backend = "milvus"

        try:
            connections.connect(
                alias="default",
                host=host,
                port=port,
            )
            logger.info("🔵 Connected to Milvus Server")

        except Exception as e:
            logger.error(f"❌ Milvus not reachable: {e}")
            self._init_faiss()

    # --------------------------------------------------
    # FAISS FALLBACK
    # --------------------------------------------------
    def _init_faiss(self):
        import faiss
        self.backend = "faiss"
        self.faiss = faiss
        self.index = None
        self.documents = []
        self.metadatas = []
        self.ids = []
        logger.info("🟠 Using FAISS backend")

    # --------------------------------------------------
    # CREATE COLLECTION
    # --------------------------------------------------
    def create_collection(self, documents: List[Dict]) -> bool:
        try:
            contents = [d["content"] for d in documents]
            metadatas = [json.dumps(d["metadata"]) for d in documents]
            ids = [f"doc_{i}" for i in range(len(documents))]

            embeddings = self.embedder.embed_batch(contents)
            embeddings_np = np.array(embeddings, dtype="float32")
            dim = embeddings_np.shape[1]

            # ---------------- MILVUS ----------------
            if self.backend == "milvus":

                if utility.has_collection(self.collection_name):
                    utility.drop_collection(self.collection_name)

                fields = [
                    FieldSchema(
                        name="id",
                        dtype=DataType.VARCHAR,
                        max_length=64,
                        is_primary=True,
                    ),
                    FieldSchema(
                        name="embedding",
                        dtype=DataType.FLOAT_VECTOR,
                        dim=dim,
                    ),
                    FieldSchema(
                        name="content",
                        dtype=DataType.VARCHAR,
                        max_length=65535,
                    ),
                    FieldSchema(
                        name="metadata",
                        dtype=DataType.VARCHAR,
                        max_length=2048,
                    ),
                ]

                schema = CollectionSchema(fields, "Loan Recovery KB")

                collection = Collection(
                    name=self.collection_name,
                    schema=schema,
                )

                collection.insert([
                    ids,
                    embeddings_np.tolist(),
                    contents,
                    metadatas,
                ])

                # ✅ REQUIRED INDEX
                collection.create_index(
                    field_name="embedding",
                    index_params={
                        "index_type": "IVF_FLAT",
                        "metric_type": "L2",
                        "params": {"nlist": 128},
                    },
                )

                collection.load()

                logging.info(f"✅ Milvus: Stored {len(documents)} documents")
                return True

            # ---------------- FAISS ----------------
            self.index = self.faiss.IndexFlatL2(dim)
            self.index.add(embeddings_np)
            self.documents = contents
            self.metadatas = metadatas
            self.ids = ids

            logging.info(f"✅ FAISS: Stored {len(documents)} documents")
            return True

        except Exception as e:
            logger.exception("❌ Knowledge base creation failed")
            return False

    # --------------------------------------------------
    # QUERY
    # --------------------------------------------------
    def query(self, query_text: str, n_results: int = 3):
        try:
            query_emb = np.array(
                self.embedder.embed_batch([query_text]),
                dtype="float32"
            )

            if self.backend == "milvus":
                collection = Collection(self.collection_name)

                results = collection.search(
                    data=query_emb.tolist(),
                    anns_field="embedding",
                    param={"metric_type": "L2", "params": {"nprobe": 10}},
                    limit=n_results,
                    output_fields=["content", "metadata"],
                )

                output = []
                for hit in results[0]:
                    output.append({
                        "score": hit.distance,
                        "content": hit.entity.get("content"),
                        "metadata": json.loads(hit.entity.get("metadata")),
                    })

                return {"results": output}

            # FAISS
            distances, indices = self.index.search(query_emb, n_results)
            output = []
            for idx in indices[0]:
                output.append({
                    "content": self.documents[idx],
                    "metadata": json.loads(self.metadatas[idx]),
                })
            return {"results": output}

        except Exception as e:
            logger.exception("❌ Query failed")
            return None