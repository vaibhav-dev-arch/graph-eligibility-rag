"""FastAPI app: ingest, next-best-content, telemetry."""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from config import get_settings
from src.app_state import clear_services, get_embeddings, get_graph, set_services
from src.embeddings import EmbeddingService
from src.graph import ContentGraph
from src.ingest import ingest_asset, seed_demo_data
from src.integration import get_telemetry_events
from src.models import Asset, NextBestContentRequest
from src.next_best import get_next_best_content

STATIC_DIR = Path(__file__).resolve().parent / "static"


def _needs_seed(embeddings: EmbeddingService) -> bool:
    try:
        return embeddings._collection.count() == 0
    except Exception:
        return True


def _verify_neo4j(graph: ContentGraph) -> bool:
    try:
        with graph._driver.session() as session:
            session.run("RETURN 1")
        return True
    except Exception:
        return False


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    graph = ContentGraph()
    embeddings = EmbeddingService()
    try:
        graph.init_schema()
        if settings.auto_seed_on_startup and _needs_seed(embeddings):
            seed_demo_data(graph, embeddings)
        set_services(graph, embeddings)
    except Exception as exc:
        graph.close()
        raise RuntimeError(f"Startup failed (check Neo4j env vars): {exc}") from exc
    yield
    clear_services()


app = FastAPI(title="Graph Eligibility RAG", lifespan=lifespan, version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.get("/")
def index():
    """Landing page with demo links."""
    html_path = STATIC_DIR / "index.html"
    if html_path.exists():
        return FileResponse(html_path)
    return {"message": "Graph Eligibility RAG", "docs": "/docs", "health": "/health"}


@app.post("/ingest")
def api_ingest(asset: Asset):
    """Ingest one asset into graph + embeddings."""
    graph = get_graph()
    emb = get_embeddings()
    ingest_asset(graph, emb, asset)
    return {"status": "ok", "asset_id": asset.id}


@app.post("/seed")
def api_seed():
    """Seed demo data (minimal graph + embeddings)."""
    graph = get_graph()
    emb = get_embeddings()
    graph.init_schema()
    seed_demo_data(graph, emb)
    return {"status": "ok", "message": "Demo data seeded."}


@app.post("/next-best-content")
def api_next_best_content(request: NextBestContentRequest):
    """Next best content: semantic + eligibility + ranking + explain."""
    out = get_next_best_content(request)
    if out.get("latency_ms", 0) > get_settings().retrieval_latency_target_ms:
        out["latency_warning"] = (
            f"Latency {out['latency_ms']}ms exceeds target "
            f"{get_settings().retrieval_latency_target_ms}ms"
        )
    return out


@app.post("/demo")
def api_demo():
    """Run a sample next-best-content query (no body required)."""
    request = NextBestContentRequest(
        query="summer sale discount",
        top_k=5,
        explain=True,
    )
    return api_next_best_content(request)


@app.get("/telemetry")
def api_telemetry():
    """Return buffered telemetry events (stub)."""
    return {"events": get_telemetry_events()}


@app.get("/health")
def health():
    settings = get_settings()
    neo4j_ok = False
    chroma_count = 0
    error = None
    try:
        graph = get_graph()
        emb = get_embeddings()
        neo4j_ok = _verify_neo4j(graph)
        chroma_count = emb._collection.count()
    except Exception as exc:
        error = str(exc)
    status = "ok" if neo4j_ok and chroma_count > 0 else "degraded"
    return {
        "status": status,
        "neo4j": neo4j_ok,
        "chroma_assets": chroma_count,
        "embedding_model": settings.embedding_model,
        "error": error,
    }


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
