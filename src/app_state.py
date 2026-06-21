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


def graph_ready() -> bool:
    return _graph is not None and _startup_error is None


def _set_startup_error(message: str) -> None:
    global _startup_error
    _startup_error = message


def _neo4j_env_ok() -> bool:
    import os

    return bool(os.environ.get("NEO4J_URI", "").strip()) and bool(
        os.environ.get("NEO4J_PASSWORD", "").strip()
    )


def _graph_is_empty(graph: ContentGraph) -> bool:
    with graph._driver.session() as session:
        record = session.run("MATCH (a:Asset) RETURN count(a) AS c").single()
        return bool(record and record["c"] == 0)


def initialize_graph() -> None:
    """Connect Neo4j and init schema only."""
    global _graph, _startup_error
    if _graph is not None:
        return

    from src.graph import ContentGraph

    if not _neo4j_env_ok():
        _set_startup_error(
            "Neo4j not configured. Set NEO4J_URI, NEO4J_USER, and NEO4J_PASSWORD in Render env."
        )
        return

    try:
        graph = ContentGraph()
        graph.init_schema()
        _graph = graph
        _startup_error = None
    except Exception as exc:
        _graph = None
        _set_startup_error(f"Neo4j startup failed: {exc}")


def ensure_embeddings(*, seed_if_empty: bool = True) -> None:
    """Load embedding backend on first use."""
    global _embeddings
    if _embeddings is not None:
        return

    from config import get_settings
    from src.embedding_factory import create_embedding_service
    from src.ingest import seed_demo_data, seed_demo_graph

    if _graph is None:
        initialize_graph()
    if _graph is None:
        return

    settings = get_settings()
    try:
        embeddings = create_embedding_service()
        if seed_if_empty and settings.auto_seed_on_startup:
            if settings.embedding_backend.lower() == "precomputed":
                if _graph_is_empty(_graph):
                    seed_demo_graph(_graph)
            else:
                try:
                    count = embeddings._collection.count()
                except Exception:
                    count = 0
                if count == 0:
                    seed_demo_data(_graph, embeddings)
        _embeddings = embeddings
    except Exception as exc:
        _embeddings = None
        _set_startup_error(f"Embedding load failed: {exc}")


def initialize_services(*, seed_if_empty: bool = True) -> None:
    initialize_graph()
    ensure_embeddings(seed_if_empty=seed_if_empty)


def get_graph() -> ContentGraph:
    if _graph is None:
        initialize_graph()
    if _graph is None:
        raise RuntimeError(_startup_error or "ContentGraph not initialized")
    return _graph


def get_embeddings() -> EmbeddingService:
    if _embeddings is None:
        ensure_embeddings()
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
