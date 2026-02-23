from __future__ import annotations

import logging
from typing import List, Union

from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

MODEL_NAME = "BAAI/bge-m3"


class EmbeddingService:
    """Singleton wrapper around SentenceTransformer for BGE-M3 embeddings."""

    _instance: "EmbeddingService" | None = None
    _model: SentenceTransformer | None = None

    def __new__(cls) -> "EmbeddingService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _load_model(self) -> None:
        if self._model is None:
            logger.info("Loading embedding model: %s ...", MODEL_NAME)
            self._model = SentenceTransformer(MODEL_NAME)
            # Explicitly set max length to leverage BGE-M3 long context
            self._model.max_seq_length = 8192
            logger.info("Embedding model loaded.")

    def encode(
        self, texts: Union[str, List[str]], batch_size: int = 32
    ) -> Union[List[float], List[List[float]]]:
        """
        Generate normalized embeddings for a single string or list of strings.

        Returns native Python lists for easy JSON/DB persistence.
        """
        self._load_model()
        embeddings = self._model.encode(
            texts,
            batch_size=batch_size,
            normalize_embeddings=True,
            convert_to_numpy=True,
        )
        return embeddings.tolist()


# Export global singleton
embedding_service = EmbeddingService()
