# AI Marketing POC

Proof-of-concept for an AI-based marketing system that connects **creative assets**, **cultural signals**, **provenance credentials**, and **performance data** to enable **intelligent content recommendation** via hybrid retrieval (embedding similarity + graph-based eligibility).

## Features

- **Content graph (Neo4j)**  
  System of record with 5 relationship types: `DERIVED_FROM`, `ABOUT_TOPIC`, `TARGET_AUDIENCE`, `DELIVERED_IN` / `PERFORMED_FOR`, `SIMILAR_TO`.

- **Embedding layer**  
  Asset-level semantic embeddings (Sentence Transformers) stored in **Chroma**; single model, text-first for POC.

- **Integration layer**  
  Stubbed DAM/CMS, provenance metadata (C2PA-style), and event-bus telemetry (in-memory).

- **Hybrid retrieval**  
  Top-K vector search + graph eligibility (rights, market, channel, approval). Latency target &lt;500ms.

- **Ranking**  
  Weighted score: `similarity × 0.6 + trust × 0.2 + recency × 0.2` with explainable reasons.

- **Optional LLM**  
  Metadata enrichment and natural-language “why recommended” (OpenAI-compatible / Ollama).

## Setup

### 1. Python environment

```bash
cd ai-marketing-poc
python -m venv .venv
source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
```

### 2. Neo4j

Run Neo4j 5.x (Docker example):

```bash
docker run -d --name neo4j -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/your_password neo4j:5
```

Set `.env` (copy from `.env.example`):

- `NEO4J_URI=bolt://localhost:7687`
- `NEO4J_USER=neo4j`
- `NEO4J_PASSWORD=your_password`

### 3. Optional: LLM (Ollama)

For enrichment and explanation generation:

```bash
ollama pull llama3.2
```

In `.env`: `LLM_ENABLED=true`, `LLM_BASE_URL=http://localhost:11434/v1`, `LLM_MODEL=llama3.2`.

## Run

1. **Seed demo data** (creates schema, assets, relationships, embeddings):

```bash
curl -X POST http://localhost:8000/seed
```

2. **Start API** (from project root):

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

3. **Next best content**

- By **query**:

```bash
curl -X POST http://localhost:8000/next-best-content \
  -H "Content-Type: application/json" \
  -d '{"query": "summer sale discount", "top_k": 5, "explain": true}'
```

- By **reference asset** (“content like this”):

```bash
curl -X POST http://localhost:8000/next-best-content \
  -H "Content-Type: application/json" \
  -d '{"reference_asset_id": "asset-001", "top_k": 5, "explain": true}'
```

- With **eligibility**:

```bash
curl -X POST http://localhost:8000/next-best-content \
  -H "Content-Type: application/json" \
  -d '{"query": "sustainability", "eligibility": {"markets": ["US","EU"], "channels": ["web","email"], "approval_statuses": ["approved"]}, "top_k": 5}'
```

Response includes `results` (ranked list with `score`, `similarity_score`, `trust_score`, `recency_score`, `explanation`), `retrieval_explanation`, and `latency_ms`.

## Project layout

```
ai-marketing-poc/
├── config.py              # Settings (env)
├── main.py                # FastAPI app
├── requirements.txt
├── .env.example
├── src/
│   ├── models.py          # Asset, relationships, eligibility, request/result
│   ├── graph.py           # Neo4j schema + CRUD + eligibility query
│   ├── embeddings.py      # SentenceTransformer + Chroma
│   ├── integration.py     # DAM/provenance/telemetry stubs
│   ├── retrieval.py       # Hybrid retriever
│   ├── ranking.py         # Heuristic ranking + explain
│   ├── llm_enrichment.py  # Optional LLM metadata + explanation
│   ├── ingest.py          # Ingest + seed
│   └── next_best.py       # Next-best-content orchestration
└── data/
    └── chroma/            # Chroma persistence (created at runtime)
```

## Design notes

- **Eligibility** is enforced at read time: only assets passing rights, market, channel, and approval filters are returned.
- **Provenance** is simulated with metadata; C2PA can be wired in later via open-source C2PA libraries.
- **Telemetry** is stubbed; replace with Kafka/CDC for production.
- **Multimodal**: POC uses text-only embeddings; OpenCLIP/BLIP can be added for image/video keyframes with the same pipeline pattern.
