"""FastAPI app: ingest, next-best-content, telemetry."""
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from config import get_settings
from src.graph import ContentGraph
from src.embeddings import EmbeddingService
from src.ingest import ingest_asset, seed_demo_data
from src.integration import get_telemetry_events
from src.models import Asset, NextBestContentRequest
from src.next_best import get_next_best_content


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure schema and optional seed
    s = get_settings()
    graph = ContentGraph()
    try:
        graph.init_schema()
    finally:
        graph.close()
    yield
    # Shutdown
    pass


app = FastAPI(title="Graph Eligibility RAG", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.post("/ingest")
def api_ingest(asset: Asset):
    """Ingest one asset into graph + embeddings."""
    graph = ContentGraph()
    emb = EmbeddingService()
    try:
        ingest_asset(graph, emb, asset)
        return {"status": "ok", "asset_id": asset.id}
    finally:
        graph.close()


@app.post("/seed")
def api_seed():
    """Seed demo data (minimal graph + embeddings)."""
    graph = ContentGraph()
    emb = EmbeddingService()
    try:
        graph.init_schema()
        seed_demo_data(graph, emb)
        return {"status": "ok", "message": "Demo data seeded."}
    finally:
        graph.close()


@app.post("/next-best-content")
def api_next_best_content(request: NextBestContentRequest):
    """Next best content: semantic + eligibility + ranking + explain."""
    out = get_next_best_content(request)
    if out.get("latency_ms", 0) > get_settings().retrieval_latency_target_ms:
        out["latency_warning"] = f"Latency {out['latency_ms']}ms exceeds target {get_settings().retrieval_latency_target_ms}ms"
    return out


@app.get("/telemetry")
def api_telemetry():
    """Return buffered telemetry events (stub)."""
    return {"events": get_telemetry_events()}


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
