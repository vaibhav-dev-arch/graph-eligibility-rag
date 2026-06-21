# Graph Eligibility RAG — NotebookLM Reference

This document is the single source for architecture, design, and full code-level (module, class, and method) detail for the AI-based marketing system POC.

---

# Part 1 — Architecture & System Design

## 1.1 System Purpose

The system enables marketers to find the **next best content** by:

- **Semantic search** across multimodal creative assets (text, images, video, audio; POC is text-first).
- **Eligibility filtering** by rights, market, channel, and approval status.
- **Explainable recommendations** balancing similarity, performance, fatigue, and trust.
- **Provenance tracking** for content authenticity and compliance (simulated C2PA-style in POC).

## 1.2 End-to-End Flow

**Ingest → Enrich → Eligibility → Next Best Content → Telemetry**

```
DAM/CMS (stub) → Ingest Pipeline (+ Provenance, optional LLM) → Content Graph (Neo4j)
                                                           → Embedding Layer (Chroma)
Next Best Content: (1) Vector top-K by query or reference asset
                  (2) Graph eligibility filter (rights, market, channel, approval)
                  (3) Rank: 0.6×similarity + 0.2×trust + 0.2×recency
                  (4) Explain (rule-based + optional LLM)
Telemetry: event bus stub (impressions, content_render) for fatigue/performance.
```

## 1.3 Content Graph (Neo4j) — Schema

- **Nodes**: `Asset`, `Topic`, `Audience`, `Channel`
- **Relationships**:
  - **DERIVED_FROM**: (Variant/Rendition/Localization) → (Master). Lineage and composition.
  - **ABOUT_TOPIC**: (Asset) → (Topic). Meaning and classification.
  - **TARGET_AUDIENCE**: (Asset) → (Audience). Who can see what; compliance; market/segment.
  - **DELIVERED_IN**: (Asset) → (Channel). Distribution channel eligibility.
  - **PERFORMED_FOR**: (Asset) → (Channel). Performance metrics (impressions, clicks, conversions, last_delivered_at).
  - **SIMILAR_TO**: (Asset) → (Asset). Graph-based similarity (optional complement to vector).

## 1.4 Eligibility (Read-Time)

Enforced in the graph layer when computing eligible asset IDs:

- **Approval status** must be in the allowed list (e.g. `["approved"]`).
- **Rights**: `rights_expiry` is null or greater than current time.
- **Market**: If asset has `TARGET_AUDIENCE`, at least one audience’s `market` must be in the allowed list.
- **Channel**: If asset has `DELIVERED_IN`, at least one channel’s `name` must be in the allowed list.

## 1.5 Embedding Layer

- **Model**: Sentence Transformers (default `all-MiniLM-L6-v2`); configurable.
- **Store**: Chroma (persistent); collection `content_assets`.
- **Scope**: Asset-level embeddings only (single vector per asset).
- **Input for embedding**: Concatenation of asset `name`, `description`, `copy_text`, and string values from `metadata`.

## 1.6 Similarity & Retrieval (Hybrid)

- **Step 1**: Top-K vector retrieval — either by text query (semantic search) or by reference asset (embed its text, then search by vector).
- **Step 2**: Restrict to asset IDs that pass graph eligibility (rights, market, channel, approval).
- **Output**: List of `(asset_id, similarity_score)` plus retrieval explanation and latency (target &lt;500 ms).

## 1.7 Ranking Formula (POC)

- **Similarity score**: From vector search, normalized to 0..1 style (e.g. 1/(1+d) from L2 distance).
- **Trust score**: Heuristic from performance (impressions, clicks, conversions) plus provenance-credentials flag (0..1).
- **Recency score**: From `last_delivered_at`; decay over ~90 days (0..1).
- **Final score**: `similarity × 0.6 + trust × 0.2 + recency × 0.2` (weights configurable in settings).

## 1.8 Optional LLM Layer

- **Metadata enrichment**: Extract topics and tone from asset text (structured JSON).
- **Explanation generation**: Natural-language “why this content was recommended” when `LLM_ENABLED=true` and `explain=true`.
- **API**: OpenAI-compatible (e.g. Ollama); base URL and model name in config.

## 1.9 API Endpoints (FastAPI)

| Method | Path | Purpose |
|--------|------|--------|
| POST | /ingest | Ingest one asset (graph + embeddings). |
| POST | /seed | Initialize schema and seed demo data. |
| POST | /next-best-content | Next best content (query or reference_asset_id + eligibility + top_k + explain). |
| GET | /telemetry | Return buffered telemetry events (stub). |
| GET | /health | Health check. |

---

# Part 2 — Configuration

**File**: `config.py`

**Class**: `Settings(BaseSettings)`

- **Purpose**: Central configuration from environment and `.env`.
- **Fields**:
  - `neo4j_uri`, `neo4j_user`, `neo4j_password`: Neo4j connection.
  - `chroma_persist_dir`: Chroma persistence path.
  - `embedding_model`, `embedding_dim`: Sentence Transformer model and dimension.
  - `llm_base_url`, `llm_model`, `llm_enabled`: Optional LLM (e.g. Ollama).
  - `event_bus_enabled`: Enable/disable telemetry stub.
  - `retrieval_top_k`, `retrieval_latency_target_ms`: Retrieval defaults and latency target (e.g. 500 ms).
  - `ranking_similarity_weight`, `ranking_trust_weight`, `ranking_recency_weight`: Ranking formula weights (e.g. 0.6, 0.2, 0.2).

**Function**: `get_settings() -> Settings`  
Returns the singleton settings instance.

---

# Part 3 — Domain Models

**File**: `src/models.py`

## 3.1 Enums

- **AssetType**: `MASTER`, `VARIANT`, `RENDITION`, `LOCALIZATION`
- **ApprovalStatus**: `DRAFT`, `PENDING`, `APPROVED`, `REJECTED`
- **Channel**: `WEB`, `SOCIAL`, `EMAIL`, `DISPLAY`, `VIDEO`
- **Market**: `US`, `EU`, `APAC`, `GLOBAL`

## 3.2 Class: Asset (BaseModel)

Canonical content node in the graph.

- **id**: str (required)
- **external_id**: Optional[str] — DAM/CMS id
- **name**: str
- **asset_type**: AssetType = MASTER
- **modality**: str = "text" (e.g. text | image | video | audio)
- **description**, **copy_text**: Optional[str] — used for embedding
- **metadata**: dict[str, Any] — arbitrary metadata
- **approval_status**: ApprovalStatus = DRAFT
- **rights_expiry**: Optional[datetime]
- **created_at**, **updated_at**: Optional[datetime]
- **provenance**: Optional[ProvenanceInfo]

## 3.3 Class: ProvenanceInfo (BaseModel)

Simulated C2PA-style provenance (POC: metadata only).

- **creator**, **tool**, **model_version**: Optional[str]
- **captured_at**: Optional[datetime]
- **credentials_present**: bool = False

## 3.4 Relationship payload models

- **DerivedFromProps**: `relationship_type` (e.g. variant | rendition | localization), `created_at`
- **AboutTopicProps**: `topic_id`, `topic_label`, `confidence`
- **TargetAudienceProps**: `audience_id`, `segment`, `market`
- **DeliveredInProps**: `channel`, `campaign_id`, `started_at`
- **PerformedForProps**: `impressions`, `clicks`, `conversions`, `last_delivered_at`
- **SimilarToProps**: `score`, `source` (e.g. "graph"), `updated_at`

## 3.5 Class: EligibilityFilter (BaseModel)

Read-time filter for recommendations.

- **markets**: list[str] — e.g. ["US", "EU", "APAC", "GLOBAL"]
- **channels**: list[str] — e.g. ["web", "social", "email", "display", "video"]
- **approval_statuses**: list[str] — e.g. ["approved"]
- **require_rights_valid**: bool = True
- **require_provenance**: bool = False

## 3.6 Class: RecommendationResult (BaseModel)

Single next-best-content result with explainability.

- **asset_id**, **score**, **similarity_score**, **trust_score**, **recency_score**
- **explanation**: list[str] — why recommended
- **eligibility_reasons**: list[str]
- **asset_summary**: Optional[dict] — e.g. name, modality

## 3.7 Class: NextBestContentRequest (BaseModel)

Request for the next-best-content API.

- **query**: Optional[str] — text for semantic search
- **reference_asset_id**: Optional[str] — “content like this” (alternative to query)
- **eligibility**: EligibilityFilter (default: all markets/channels, approved only)
- **top_k**: int = 10
- **explain**: bool = True

---

# Part 4 — Content Graph (Neo4j)

**File**: `src/graph.py`

## 4.1 Class: ContentGraph

**Purpose**: System of record for assets and the five relationship types. Wraps Neo4j driver.

### Method: `__init__(self)`

- Reads settings and creates `GraphDatabase.driver(neo4j_uri, auth=(user, password))`.
- No parameters.

### Method: `close(self)`

- Closes the Neo4j driver. Call when done with the graph (e.g. after API handler).

### Method: `init_schema(self) -> None`

- Creates constraints and indexes: unique constraint on `Asset.id`; indexes on `Asset.approval_status`, `Asset.updated_at`; unique constraints on `Topic.id`, `Audience.id`, `Channel.name`.
- Uses `IF NOT EXISTS` / equivalent so safe to call on startup.

### Method: `upsert_asset(self, asset: Asset) -> None`

- MERGE Asset node by `id`; SET all scalar fields (name, external_id, asset_type, modality, description, copy_text, approval_status, rights_expiry, updated_at, metadata, provenance_creator, provenance_tool, provenance_credentials); SET created_at via COALESCE so it is only set on first create.
- Serializes datetime to ISO string; metadata to string for storage.

### Method: `add_derived_from(self, child_id: str, parent_id: str, props: Optional[DerivedFromProps] = None) -> None`

- Matches child and parent Asset by id; MERGE (child)-[:DERIVED_FROM]->(parent); sets relationship_type and created_at on the relationship.

### Method: `add_about_topic(self, asset_id: str, topic_id: str, topic_label: str, confidence: float = 1.0) -> None`

- MERGE Topic by id, set label; MATCH Asset by asset_id; MERGE (Asset)-[:ABOUT_TOPIC]->(Topic); set confidence on relationship.

### Method: `add_target_audience(self, asset_id: str, audience_id: str, segment: str, market: str) -> None`

- MERGE Audience by id; set segment, market; MERGE (Asset)-[:TARGET_AUDIENCE]->(Audience).

### Method: `add_delivered_in(self, asset_id: str, channel_name: str, props: Optional[DeliveredInProps] = None) -> None`

- MERGE Channel by name; MERGE (Asset)-[:DELIVERED_IN]->(Channel); set campaign_id, started_at on relationship if provided.

### Method: `add_performed_for(self, asset_id: str, channel_name: str, props: PerformedForProps) -> None`

- MERGE Channel by name; MERGE (Asset)-[:PERFORMED_FOR]->(Channel); set impressions, clicks, conversions, last_delivered_at on relationship.

### Method: `add_similar_to(self, asset_id: str, other_id: str, score: float, source: str = "graph") -> None`

- MERGE (Asset)-[:SIMILAR_TO]->(Asset) between the two assets; set score, source, updated_at on relationship.

### Method: `get_asset(self, asset_id: str) -> Optional[dict[str, Any]]`

- MATCH (a:Asset {id}); RETURN a; converts node to dict of properties (using node.keys() and node[k]); returns None if not found.

### Method: `get_eligible_asset_ids(self, markets, channels, approval_statuses, require_rights_valid) -> set[str]`

- Cypher: MATCH Asset WHERE approval_status IN list AND (rights_expiry IS NULL OR rights_expiry > now); OPTIONAL MATCH TARGET_AUDIENCE, filter by market in list or no audience; OPTIONAL MATCH DELIVERED_IN to Channel, filter by channel name in list or no channel. Returns set of asset ids passing all filters.

### Method: `get_asset_ids_with_performance(self) -> dict[str, dict]`

- MATCH (Asset)-[PERFORMED_FOR]->(); aggregate sum(impressions), sum(clicks), sum(conversions), max(last_delivered_at) per asset id. Returns dict asset_id -> {impressions, clicks, conversions, last_delivered_at}.

---

# Part 5 — Embedding Layer

**File**: `src/embeddings.py`

## 5.1 Class: EmbeddingService

**Purpose**: Asset-level embeddings with a single Sentence Transformer model; store and search in Chroma.

### Method: `__init__(self)`

- Loads SentenceTransformer from config (`embedding_model`); creates Chroma PersistentClient at `chroma_persist_dir`; gets or creates collection `content_assets`.

### Method: `_text_for_embedding(self, asset: Asset) -> str`

- Builds one string from asset.name, asset.description, asset.copy_text, and string values in asset.metadata. Returns that string or asset.id if empty.

### Method: `embed_asset(self, asset: Asset) -> list[float]`

- Calls _text_for_embedding(asset), encodes with model (normalize_embeddings=True), returns vector as list of floats.

### Method: `index_asset(self, asset: Asset) -> None`

- Computes embedding and document text; upserts into Chroma with id=asset.id, embeddings=[vec], documents=[doc], metadatas=[{name, modality}].

### Method: `search(self, query: str, top_k: int = 20, where: Optional[dict] = None) -> list[tuple[str, float]]`

- Encodes query to vector; queries Chroma with query_embeddings, n_results=top_k, optional where; converts L2 distances to similarity as 1/(1+d); returns list of (asset_id, similarity_score).

### Method: `embed_text(self, text: str) -> list[float]`

- Encodes arbitrary text to normalized vector. Used for reference-asset similarity (get asset text, embed, then search_by_vector).

### Method: `search_by_vector(self, vector: list[float], top_k: int = 20, exclude_ids: Optional[list[str]] = None) -> list[tuple[str, float]]`

- Queries Chroma by vector; converts distances to similarity; if exclude_ids provided, filters them out and returns up to top_k. Used for “content like this” without re-embedding the reference asset each time from graph.

---

# Part 6 — Integration Layer (Stubs & Telemetry)

**File**: `src/integration.py`

## 6.1 DAM stubs

- **stub_fetch_dam_asset(external_id: str) -> Optional[dict]**: Simulates DAM API; POC returns None.
- **stub_dam_to_asset(dam_record: dict) -> Asset**: Maps a DAM record to the Asset model (id, name, asset_type, modality, description, copy_text, metadata, approval_status, rights_expiry, etc.).

## 6.2 Provenance (C2PA-style, metadata only)

- **attach_provenance(asset: Asset, creator="", tool="", model_version="") -> Asset**: Sets asset.provenance to ProvenanceInfo with creator, tool, model_version, captured_at=now, credentials_present=bool(creator or tool). Returns the same asset.
- **check_provenance_eligible(asset: Asset, require_credentials: bool) -> bool**: If require_credentials is False returns True; else returns True only if asset has provenance and credentials_present.

## 6.3 Event bus (telemetry stub)

- **Module-level**: `_events: list[dict]` — in-memory buffer.
- **emit_telemetry(event_type: str, payload: dict) -> None**: If event_bus_enabled, appends {type, payload, ts} to _events.
- **stub_content_render(asset_id, channel, session_id)**: Calls emit_telemetry("content_render", {...}).
- **stub_impression(asset_id, channel, campaign_id=None)**: Calls emit_telemetry("impression", {...}).
- **get_telemetry_events() -> list[dict]**: Returns copy of _events (for GET /telemetry).

---

# Part 7 — Hybrid Retrieval

**File**: `src/retrieval.py`

## 7.1 Class: HybridRetriever

**Purpose**: Combine vector similarity (top-K) with graph-based eligibility; return candidates plus explanation and latency.

### Method: `__init__(self, embedding_service: EmbeddingService, graph: ContentGraph)`

- Stores references to embedding service and graph.

### Method: `retrieve(self, query=None, reference_asset_id=None, eligibility=None, top_k=20) -> tuple[list[tuple[str, float]], list[str], float]`

- **Returns**: (candidate_list, explanation_lines, latency_ms). candidate_list is [(asset_id, similarity_score), ...].
- **Logic**:
  1. If query: semantic search via embedding_service.search(query, top_k*2). If reference_asset_id: get asset from graph, get text (copy_text/description/name), embed_text, then search_by_vector with exclude_ids=[reference_asset_id]. If neither, return empty with explanation “Provide query or reference_asset_id.”
  2. Get eligible asset IDs from graph (get_eligible_asset_ids with eligibility’s markets, channels, approval_statuses, require_rights_valid).
  3. Filter vector candidates to those in eligible_ids, up to top_k.
  4. Build explanation strings (query/ref, candidate count, eligibility count, filtered count); measure latency from start; return filtered list, explanation, latency_ms.

---

# Part 8 — Ranking

**File**: `src/ranking.py`

## 8.1 Function: _trust_score(perf: dict, has_provenance: bool) -> float

- **Purpose**: 0..1 trust from performance and credentials.
- **Logic**: Reads impressions, clicks, conversions from perf; computes a heuristic engagement score (e.g. 0.3 + 0.7 * (clicks/impressions)*10 capped at 1); adds 0.2 if has_provenance; returns min(1.0, ...).

## 8.2 Function: _recency_score(last_delivered_at: Optional[str]) -> float

- **Purpose**: Favor freshness; decay over ~90 days.
- **Logic**: If no last_delivered_at return 0.5; else parse datetime, compute days since delivery, return max(0, 1 - days/90).

## 8.3 Function: rank_candidates(candidates, graph, eligibility, top_k=10, explain=True) -> list[RecommendationResult]

- **Purpose**: Weighted scoring and explainability.
- **Logic**: Load ranking weights from settings; get performance dict from graph (get_asset_ids_with_performance). For each (asset_id, sim_score) in candidates (up to top_k*2): get asset node and performance; compute trust and recency; final_score = sim*w_sim + trust*w_trust + recency*w_recency; build explanation list (similarity, trust, recency, eligibility summary) if explain; append RecommendationResult(asset_id, score, similarity_score, trust_score, recency_score, explanation, eligibility_reasons, asset_summary). Sort by score descending; return first top_k.

---

# Part 9 — LLM Enrichment (Optional)

**File**: `src/llm_enrichment.py`

## 9.1 Function: _client() -> Optional[OpenAI]

- Returns OpenAI client with base_url and api_key from settings if llm_enabled; else None.

## 9.2 Function: extract_metadata_structured(asset: Asset) -> dict[str, Any]

- **Purpose**: Extract topics and tone from asset text via LLM.
- **Logic**: If no client or no text, return {}. Otherwise call chat completions with system “output only valid JSON”, user prompt asking for topics (list) and tone (one word); parse JSON from response; return dict (e.g. {"topics": [...], "tone": "..."}) or {} on error.

## 9.3 Function: generate_why_recommendation(result: RecommendationResult) -> str

- **Purpose**: Natural-language explanation for why this content was recommended.
- **Logic**: If no client, return "; ".join(result.explanation). Otherwise build user message from asset_id, scores, and explanation list; call chat completions with “concise marketing analyst” system prompt; return response text or fallback to joined explanation on error.

---

# Part 10 — Ingest Pipeline

**File**: `src/ingest.py`

## 10.1 Function: ingest_asset(graph, embedding_service, asset, attach_prov=True) -> None

- **Purpose**: Single-asset ingest: provenance → graph → embedding index.
- **Logic**: If attach_prov, call attach_provenance(asset); graph.upsert_asset(asset); embedding_service.index_asset(asset).

## 10.2 Function: seed_demo_data(graph, embedding_service) -> None

- **Purpose**: Minimal data for thin-slice demo.
- **Logic**: Create five Asset instances (asset-001 through asset-005) with names, copy_text, approval_status (four APPROVED, one DRAFT), rights_expiry, etc. For each, call ingest_asset. Then create relationships: add_derived_from(asset-002, asset-001); add_about_topic for summer, sustainability, product-launch; add_target_audience for US/EU segments; add_delivered_in for web, social, email, video; add_performed_for with impressions/clicks/conversions/last_delivered_at for asset-001, asset-002, asset-003.

---

# Part 11 — Next Best Content Orchestration

**File**: `src/next_best.py`

## 11.1 Function: get_next_best_content(request: NextBestContentRequest) -> dict

- **Purpose**: End-to-end next-best-content: retrieve → rank → optional LLM explanation.
- **Logic**: Instantiate ContentGraph, EmbeddingService, HybridRetriever. Call retriever.retrieve(query, reference_asset_id, eligibility, top_k*2). If no candidates, return {results: [], retrieval_explanation, latency_ms, error: None}. Else call rank_candidates(candidates, graph, eligibility, top_k, explain). If llm_enabled and explain, for each result replace result.explanation with [generate_why_recommendation(r)]. Return {results: [r.model_dump() for r in results], retrieval_explanation, latency_ms, error: None}. In finally, graph.close().

---

# Part 12 — FastAPI Application

**File**: `main.py`

## 12.1 Lifespan

- **Startup**: Create ContentGraph, call init_schema(), close graph.
- **Shutdown**: No-op.

## 12.2 App setup

- FastAPI(title="AI Marketing POC", lifespan=lifespan); CORS middleware allow_origins=["*"], allow_methods=["*"], allow_headers=["*"].

## 12.3 Endpoints

- **POST /ingest (api_ingest(asset: Asset))**: Create ContentGraph and EmbeddingService; call ingest_asset(graph, emb, asset); return {status: "ok", asset_id}; close graph in finally.
- **POST /seed (api_seed())**: Create graph and emb; init_schema(); seed_demo_data(graph, emb); return {status: "ok", message: "Demo data seeded."}; close graph.
- **POST /next-best-content (api_next_best_content(request: NextBestContentRequest))**: Call get_next_best_content(request); if latency_ms > retrieval_latency_target_ms, add latency_warning to response; return response.
- **GET /telemetry (api_telemetry())**: Return {events: get_telemetry_events()}.
- **GET /health (health())**: Return {status: "ok"}.

---

# Part 13 — Code Snippets (Key Logic)

## Config (config.py)

```python
class Settings(BaseSettings):
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = ""
    chroma_persist_dir: str = "./data/chroma"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dim: int = 384
    llm_base_url: str = "http://localhost:11434/v1"
    llm_model: str = "llama3.2"
    llm_enabled: bool = False
    event_bus_enabled: bool = True
    retrieval_top_k: int = 20
    retrieval_latency_target_ms: int = 500
    ranking_similarity_weight: float = 0.6
    ranking_trust_weight: float = 0.2
    ranking_recency_weight: float = 0.2
    class Config:
        env_file = ".env"
        extra = "ignore"
```

## Eligibility Cypher (graph.py — get_eligible_asset_ids)

```cypher
MATCH (a:Asset)
WHERE a.approval_status IN $approval_statuses
  AND (a.rights_expiry IS NULL OR a.rights_expiry > $now)
WITH a
OPTIONAL MATCH (a)-[:TARGET_AUDIENCE]->(aud:Audience)
WITH a, aud
WHERE aud IS NULL OR aud.market IN $markets
WITH DISTINCT a
OPTIONAL MATCH (a)-[:DELIVERED_IN]->(ch:Channel)
WITH a, ch
WHERE ch IS NULL OR ch.name IN $channels
RETURN DISTINCT a.id AS id
```

## Ranking formula (ranking.py)

```python
final_score = sim_score * w_sim + trust * w_trust + recency * w_recency
# w_sim=0.6, w_trust=0.2, w_recency=0.2 by default
```

## Chroma similarity from L2 distance (embeddings.py)

```python
scores = [1.0 / (1.0 + d) for d in distances]  # L2 distance -> similarity
return list(zip(ids, scores))
```

---

End of NotebookLM Reference. Use this document as the single source for architecture, design, and code/class/method-level detail when querying in NotebookLM.
