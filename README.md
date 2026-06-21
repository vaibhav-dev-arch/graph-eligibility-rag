# Graph Eligibility RAG

**What this is:** A reference implementation of **hybrid GraphRAG** — vector similarity (Chroma) plus Neo4j graph **eligibility** constraints (rights, market, channel, approval) — with C2PA-style provenance metadata and explainable ranking. The demo domain is **creative content recommendation** (retail/marketing); the pattern generalizes to other eligibility-gated knowledge retrieval (e.g. clinical trial matching).

## Live demo

**Live URL:** _Deploy pending — see [Deploy on Render (free)](#deploy-on-render-free) below._

Open the link → click **Run demo query**, or use [/docs](https://graph-eligibility-rag.onrender.com/docs) once deployed.

## Quick start

### Try it live (recommended)

Visit the live URL once deployed.

- **Landing page:** `/` — one-click demo query
- **API docs:** `/docs`
- **Health:** `/health` — confirms Neo4j + Chroma seeded
- **Demo:** `POST /demo`

_Free tier: may sleep after ~15 min idle; first load after idle can take 60–90s (embedding model load)._

### Run locally

```bash
git clone https://github.com/vaibhav-dev-arch/graph-eligibility-rag.git
cd graph-eligibility-rag
python3 -m pip install -r requirements.txt

# Start Neo4j (Docker)
docker compose up -d

cp .env.example .env   # set NEO4J_PASSWORD=pocpassword to match docker-compose
python3 app.py
```

Server: **http://127.0.0.1:8000** · Landing: **/** · API docs: **/docs**

```bash
# Another terminal
python3 scripts/run_demo.py
# Or: bash scripts/run_demo.sh
```

## Deploy on Render (free)

This app needs **Neo4j in the cloud** (Render cannot run Neo4j on the free web service). Use **Neo4j Aura Free**:

### Step 1 — Neo4j Aura (free, ~5 min)

1. Go to [Neo4j Aura](https://neo4j.com/cloud/aura-free/) → create free instance
2. Save connection details:
   - `NEO4J_URI` — e.g. `neo4j+s://xxxx.databases.neo4j.io`
   - `NEO4J_USER` — usually `neo4j`
   - `NEO4J_PASSWORD` — generated password

### Step 2 — Render

1. [Render Dashboard](https://dashboard.render.com/) → **New** → **Blueprint**
2. Connect GitHub → select `vaibhav-dev-arch/graph-eligibility-rag`
3. When prompted, set environment variables:
   - `NEO4J_URI`
   - `NEO4J_USER`
   - `NEO4J_PASSWORD`
4. Deploy → copy your `*.onrender.com` URL

Or **Web Service** manually: Python 3, build `pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu && pip install -r requirements.txt`, start `python app.py`, health `/health`.

### Deployment notes

- **Chroma embeddings are ephemeral** on Render — demo data re-seeds automatically on startup (`AUTO_SEED_ON_STARTUP=true`).
- **First deploy build** takes 5–10 min (PyTorch + sentence-transformers). First request after idle loads the embedding model (~30–60s).
- If the service crashes on free tier (memory), upgrade to Render **Starter** ($7/mo) for more headroom.
- No LLM API key required — `LLM_ENABLED=false` by default.

## Features

- **Content graph (Neo4j)** — 5 relationship types: `DERIVED_FROM`, `ABOUT_TOPIC`, `TARGET_AUDIENCE`, `DELIVERED_IN` / `PERFORMED_FOR`, `SIMILAR_TO`
- **Embedding layer** — Sentence Transformers + Chroma
- **Hybrid retrieval** — vector search + graph eligibility filters
- **Ranking** — `similarity × 0.6 + trust × 0.2 + recency × 0.2` with explainable reasons
- **Provenance** — C2PA-style metadata on assets

## Example

```bash
# Demo query (no body)
curl -s -X POST https://YOUR-URL.onrender.com/demo | jq

# Custom query with eligibility
curl -s -X POST https://YOUR-URL.onrender.com/next-best-content \
  -H 'Content-Type: application/json' \
  -d '{"query":"summer sale discount","top_k":5,"explain":true}' | jq
```

## Related portfolio demos

- [agent-observability-demo](https://agent-observability-demo.onrender.com) — traces + eval gates (Pillar 2)
- [ai-bcdr-governance](https://ai-bcdr-governance.onrender.com) — calibrated autonomy + evidence trail (Pillar 3)

## Project layout

```
graph-eligibility-rag/
├── app.py                 # Render entry (reads PORT)
├── main.py                # FastAPI app
├── config.py
├── render.yaml
├── docker-compose.yml     # Local Neo4j only
├── static/index.html      # Landing + demo button
├── src/
│   ├── graph.py           # Neo4j
│   ├── embeddings.py      # Chroma + SentenceTransformers
│   ├── retrieval.py       # Hybrid retriever
│   ├── ranking.py
│   └── next_best.py
└── scripts/run_demo.py
```

## Former name

Previously `ai-marketing-poc`. Renamed to reflect the reusable **graph + eligibility + RAG** pattern.
