from __future__ import annotations

import logging
from typing import List, Protocol, Union, cast

logger = logging.getLogger(__name__)

MODEL_NAME = "BAAI/bge-m3"


class _EmbeddingResult(Protocol):
    def tolist(self) -> Union[List[float], List[List[float]]]:
        ...


class _SentenceTransformerModel(Protocol):
    max_seq_length: int

    def encode(
        self,
        texts: Union[str, List[str]],
        *,
        batch_size: int,
        normalize_embeddings: bool,
        convert_to_numpy: bool,
    ) -> _EmbeddingResult:
        ...


class _SentenceTransformerFactory(Protocol):
    def __call__(self, model_name: str) -> _SentenceTransformerModel:
        ...


try:
    from sentence_transformers import SentenceTransformer as _SentenceTransformer
except ModuleNotFoundError as exc:
    _sentence_transformer_import_error: ModuleNotFoundError | None = exc
    _sentence_transformer_factory: _SentenceTransformerFactory | None = None
else:
    _sentence_transformer_import_error = None
    _sentence_transformer_factory = cast(
        _SentenceTransformerFactory, _SentenceTransformer
    )


class EmbeddingService:
    """Singleton wrapper around SentenceTransformer for BGE-M3 embeddings."""

    _instance: "EmbeddingService" | None = None
    _model: _SentenceTransformerModel | None = None

    def __new__(cls) -> "EmbeddingService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _load_model(self) -> None:
        if self._model is None:
            if _sentence_transformer_factory is None:
                raise RuntimeError(
                    "sentence-transformers is required for embedding generation"
                ) from _sentence_transformer_import_error
            logger.info("Loading embedding model: %s ...", MODEL_NAME)
            self._model = _sentence_transformer_factory(MODEL_NAME)
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
        model = self._model
        if model is None:
            raise RuntimeError("embedding model was not loaded")
        embeddings = model.encode(
            texts,
            batch_size=batch_size,
            normalize_embeddings=True,
            convert_to_numpy=True,
        )
        return embeddings.tolist()


# Export global singleton
embedding_service = EmbeddingService()
