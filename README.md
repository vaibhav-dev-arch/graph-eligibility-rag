# Graph Eligibility RAG

**What this is:** A reference implementation of **hybrid GraphRAG** — vector similarity (Chroma) plus Neo4j graph **eligibility** constraints (rights, market, channel, approval) — with C2PA-style provenance metadata and explainable ranking. The demo domain is **creative content recommendation** (retail/marketing); the pattern generalizes to other eligibility-gated knowledge retrieval (e.g. clinical trial matching).

## Live demo

**Live URL:** _Deploy using steps below — target `https://graph-eligibility-rag.onrender.com`_

- **Landing page:** `/` — one-click demo query
- **API docs:** `/docs`
- **Health:** `/health` — confirms Neo4j + Chroma seeded
- **Demo:** `POST /demo`

_Free tier: may sleep after ~15 min idle; first load after idle can take 60–90s (embedding model load)._

## Quick start

### Try it live (recommended)

Visit your Render URL once deployed (see [Fresh deploy on Render](#fresh-deploy-on-render-from-scratch) below).

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

## Fresh deploy on Render (from scratch)

This app needs **Neo4j Aura** (Render cannot run Neo4j on the web service). Use a **manual Web Service** — it avoids Blueprint sync issues.

### Step 0 — Clean up old Render services

In [Render Dashboard](https://dashboard.render.com/):

1. Delete **graph-eligibility-marketingtech** (and its Blueprint if shown)
2. Delete any other failed `graph-eligibility-*` services

Start with a clean slate.

### Step 1 — Neo4j Aura credentials (~5 min)

If you already have Aura credentials, skip to Step 2.

1. [Neo4j Aura Free](https://neo4j.com/cloud/aura-free/) → create instance
2. Save these three values:

| Variable | Example |
|----------|---------|
| `NEO4J_URI` | `neo4j+s://xxxx.databases.neo4j.io` |
| `NEO4J_USER` | `neo4j` |
| `NEO4J_PASSWORD` | (generated password) |

### Step 2 — Create Web Service on Render

1. **New** → **Web Service** (not Blueprint)
2. Connect GitHub → repo **`vaibhav-dev-arch/graph-eligibility-rag`**
3. Settings:

| Setting | Value |
|---------|-------|
| Name | `graph-eligibility-rag` |
| Region | closest to you |
| Branch | `main` |
| Runtime | Python 3 |
| Build Command | `bash scripts/render_build.sh` |
| Start Command | `python app.py` |
| Plan | Free |

4. **Advanced** → Health Check Path: `/health`

5. **Environment** → add **before** clicking Create:

| Key | Value |
|-----|-------|
| `NEO4J_URI` | your Aura URI (`neo4j+s://...`) |
| `NEO4J_USER` | `neo4j` |
| `NEO4J_PASSWORD` | your Aura password |
| `AUTO_SEED_ON_STARTUP` | `true` |

6. **Create Web Service** → wait 5–10 min for first build

### Step 3 — Verify

```bash
curl https://graph-eligibility-rag.onrender.com/health
```

Success:

```json
{
  "status": "ok",
  "env_detected": { "NEO4J_URI": true, "NEO4J_PASSWORD": true },
  "neo4j": true,
  "chroma_assets": 5
}
```

Open **https://graph-eligibility-rag.onrender.com** → click **Run demo query**.

In Render **Logs**, you should see:

```
[startup] NEO4J_URI set=True NEO4J_PASSWORD set=True
```

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| `env_detected` all `false` | Env vars missing on **Web Service** Environment tab → save → Manual Deploy |
| `status: degraded`, Neo4j error | Check URI starts with `neo4j+s://`, password correct, Aura instance running |
| Build timeout / OOM on deploy | **Clear build cache & redeploy** — build must use CPU-only torch (see `scripts/render_build.sh`). If still OOM on first `/demo`, upgrade to **Starter** ($7/mo). |
| `No open ports detected` then OOM | Fixed in v0.1.2 — app binds port before loading PyTorch. Redeploy latest `main`. |
| First demo slow (~60s) | Normal — embedding model loads on first `/demo` request (deferred for free tier). |

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
