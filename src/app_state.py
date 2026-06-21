"""Application-scoped service singletons (one embedding model load per process)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.embeddings import EmbeddingService
    from src.graph import ContentGraph

_graph: ContentGraph | None = None
_embeddings: EmbeddingService | None = None


def set_services(graph: ContentGraph, embeddings: EmbeddingService) -> None:
    global _graph, _embeddings
    _graph = graph
    _embeddings = embeddings


def get_graph() -> ContentGraph:
    if _graph is None:
        raise RuntimeError("ContentGraph not initialized")
    return _graph


def get_embeddings() -> EmbeddingService:
    if _embeddings is None:
        raise RuntimeError("EmbeddingService not initialized")
    return _embeddings


def clear_services() -> None:
    global _graph, _embeddings
    if _graph is not None:
        _graph.close()
    _graph = None
    _embeddings = None
