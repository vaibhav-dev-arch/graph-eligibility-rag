"""Factory for embedding backends (chroma+torch locally, precomputed on Render)."""

from config import get_settings


def create_embedding_service():
    backend = get_settings().embedding_backend.lower()
    if backend == "precomputed":
        from src.embeddings_precomputed import PrecomputedEmbeddingService

        return PrecomputedEmbeddingService()
    from src.embeddings import EmbeddingService

    return EmbeddingService()
