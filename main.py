"""FastAPI app: ingest, next-best-content, telemetry."""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from config import get_settings
from src.app_state import (
    clear_services,
    ensure_embeddings,
    get_embeddings,
    get_graph,
    graph_ready,
    initialize_graph,
    initialize_services,
    services_ready,
    startup_error,
)
from src.ingest import ingest_asset, seed_demo_data
from src.integration import get_telemetry_events
from src.models import Asset, NextBestContentRequest
from src.next_best import get_next_best_content

STATIC_DIR = Path(__file__).resolve().parent / "static"


def _verify_neo4j(graph) -> bool:
    try:
        with graph._driver.session() as session:
            session.run("RETURN 1")
        return True
    except Exception:
        return False


def _require_services():
    initialize_services()
    if not services_ready():
        detail = startup_error() or "Services not initialized"
        raise HTTPException(
            status_code=503,
            detail=f"{detail} — add NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD in Render Environment, then redeploy.",
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    uri_set = bool(os.environ.get("NEO4J_URI", "").strip())
    pwd_set = bool(os.environ.get("NEO4J_PASSWORD", "").strip())
    print(f"[startup] NEO4J_URI set={uri_set} NEO4J_PASSWORD set={pwd_set}", flush=True)
    print("[startup] deferring embedding model load until first /demo request", flush=True)
    yield
    clear_services()


app = FastAPI(title="Graph Eligibility RAG", lifespan=lifespan, version="0.1.2")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.get("/")
def index():
    html_path = STATIC_DIR / "index.html"
    if html_path.exists():
        return FileResponse(html_path)
    return {"message": "Graph Eligibility RAG", "docs": "/docs", "health": "/health"}


@app.post("/ingest")
def api_ingest(asset: Asset):
    _require_services()
    graph = get_graph()
    emb = get_embeddings()
    ingest_asset(graph, emb, asset)
    return {"status": "ok", "asset_id": asset.id}


@app.post("/seed")
def api_seed():
    _require_services()
    graph = get_graph()
    emb = get_embeddings()
    graph.init_schema()
    seed_demo_data(graph, emb)
    return {"status": "ok", "message": "Demo data seeded."}


@app.post("/next-best-content")
def api_next_best_content(request: NextBestContentRequest):
    _require_services()
    out = get_next_best_content(request)
    if out.get("latency_ms", 0) > get_settings().retrieval_latency_target_ms:
        out["latency_warning"] = (
            f"Latency {out['latency_ms']}ms exceeds target "
            f"{get_settings().retrieval_latency_target_ms}ms"
        )
    return out


@app.post("/demo")
def api_demo():
    _require_services()
    request = NextBestContentRequest(
        query="summer sale discount",
        top_k=5,
        explain=True,
    )
    return api_next_best_content(request)


@app.get("/telemetry")
def api_telemetry():
    return {"events": get_telemetry_events()}


@app.get("/health")
def health():
    """Always returns 200 so Render health checks pass during Neo4j setup."""
    settings = get_settings()
    env_uri = bool(os.environ.get("NEO4J_URI", "").strip())
    env_password = bool(os.environ.get("NEO4J_PASSWORD", "").strip())
    neo4j_configured = env_uri and env_password
    neo4j_ok = False
    chroma_count = 0
    err = startup_error()

    if neo4j_configured and not graph_ready():
        initialize_graph()

    if graph_ready():
        try:
            neo4j_ok = _verify_neo4j(get_graph())
        except Exception as exc:
            err = str(exc)

    if services_ready():
        try:
            emb = get_embeddings()
            chroma_count = emb._collection.count()
        except Exception as exc:
            err = err or str(exc)

    if neo4j_ok and chroma_count > 0:
        status = "ok"
    elif neo4j_ok and chroma_count == 0:
        status = "warming"
    elif not neo4j_configured:
        status = "setup_required"
    else:
        status = "degraded"

    return {
        "status": status,
        "neo4j_configured": neo4j_configured,
        "neo4j": neo4j_ok,
        "chroma_assets": chroma_count,
        "embedding_model": settings.embedding_model,
        "error": err,
        "env_detected": {
            "NEO4J_URI": env_uri,
            "NEO4J_USER": bool(os.environ.get("NEO4J_USER", "").strip()),
            "NEO4J_PASSWORD": env_password,
        },
        "setup_hint": (
            "Neo4j connected — click Run demo query (first run loads embedding model ~60s)."
            if status == "warming"
            else None
            if neo4j_configured and status != "setup_required"
            else "Set NEO4J_URI and NEO4J_PASSWORD on the web service Environment tab, then Manual Deploy."
        ),
    }


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
