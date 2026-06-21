"""Application-scoped service singletons with lazy initialization for Render."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.embeddings import EmbeddingService
    from src.graph import ContentGraph

_graph: ContentGraph | None = None
_embeddings: EmbeddingService | None = None
_startup_error: str | None = None


def startup_error() -> str | None:
    return _startup_error


def services_ready() -> bool:
    return _graph is not None and _embeddings is not None and _startup_error is None


def _set_startup_error(message: str) -> None:
    global _startup_error
    _startup_error = message


def initialize_services(*, seed_if_empty: bool = True) -> None:
    """Connect Neo4j, load embedding model, optionally seed demo data."""
    global _graph, _embeddings, _startup_error
    import os

    from config import get_settings
    from src.embeddings import EmbeddingService
    from src.graph import ContentGraph
    from src.ingest import seed_demo_data

    settings = get_settings()
    if not os.environ.get("NEO4J_PASSWORD", "").strip():
        _set_startup_error(
            "Neo4j not configured. Set NEO4J_URI, NEO4J_USER, and NEO4J_PASSWORD in Render env."
        )
        return
    if not os.environ.get("NEO4J_URI", "").strip():
        _set_startup_error("NEO4J_URI is missing from environment.")
        return

    graph: ContentGraph | None = None
    try:
        graph = ContentGraph()
        embeddings = EmbeddingService()
        graph.init_schema()
        if seed_if_empty and settings.auto_seed_on_startup:
            try:
                count = embeddings._collection.count()
            except Exception:
                count = 0
            if count == 0:
                seed_demo_data(graph, embeddings)
        _graph = graph
        _embeddings = embeddings
        _startup_error = None
    except Exception as exc:
        if graph is not None:
            graph.close()
        _graph = None
        _embeddings = None
        _set_startup_error(f"Startup failed: {exc}")


def get_graph() -> ContentGraph:
    if _graph is None:
        initialize_services()
    if _graph is None:
        raise RuntimeError(_startup_error or "ContentGraph not initialized")
    return _graph


def get_embeddings() -> EmbeddingService:
    if _embeddings is None:
        initialize_services()
    if _embeddings is None:
        raise RuntimeError(_startup_error or "EmbeddingService not initialized")
    return _embeddings


def clear_services() -> None:
    global _graph, _embeddings, _startup_error
    if _graph is not None:
        _graph.close()
    _graph = None
    _embeddings = None
    _startup_error = None
