# POC Architecture

## Flow: Ingest → Enrich → Eligibility → Next Best Content → Telemetry

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│ DAM / CMS       │────▶│ Ingest Pipeline   │────▶│ Content Graph    │
│ (stub)          │     │ + Provenance      │     │ (Neo4j)         │
└─────────────────┘     │ + Optional LLM    │     └────────┬────────┘
                        └────────┬──────────┘              │
                                 │                         │
                                 ▼                         │
                        ┌──────────────────┐               │
                        │ Embedding Layer  │               │
                        │ (SentenceTransform│               │
                        │  + Chroma)       │               │
                        └────────┬──────────┘               │
                                 │                         │
                                 ▼                         ▼
                        ┌─────────────────────────────────────────┐
                        │ Next Best Content                       │
                        │ 1. Vector top-K (query or ref asset)    │
                        │ 2. Graph eligibility filter             │
                        │ 3. Rank: 0.6*sim + 0.2*trust + 0.2*recency │
                        │ 4. Explain (rules + optional LLM)        │
                        └─────────────────────────────────────────┘
                                 │
                                 ▼
                        ┌──────────────────┐
                        │ Event Bus (stub) │  Telemetry: impressions, renders
                        └──────────────────┘
```

## Graph schema (Neo4j)

- **Nodes**: `Asset`, `Topic`, `Audience`, `Channel`
- **Relationships**:
  - `(Variant)-[:DERIVED_FROM]->(Master)` — lineage
  - `(Asset)-[:ABOUT_TOPIC]->(Topic)` — taxonomy
  - `(Asset)-[:TARGET_AUDIENCE]->(Audience)` — eligibility (market/segment)
  - `(Asset)-[:DELIVERED_IN]->(Channel)` — channel eligibility
  - `(Asset)-[:PERFORMED_FOR]->(Channel)` — performance metrics
  - `(Asset)-[:SIMILAR_TO]->(Asset)` — graph-based similarity (optional)

## Eligibility (read-time)

Enforced in `get_eligible_asset_ids()`:

- Approval status in allowed list
- Rights not expired (`rights_expiry > now`)
- If `TARGET_AUDIENCE` exists, market in allowed list
- If `DELIVERED_IN` exists, channel in allowed list

## Ranking formula (POC)

- **Similarity**: from vector search (0..1)
- **Trust**: heuristic from performance (CTR, conversions) + provenance flag
- **Recency**: decay from `last_delivered_at`
- **Final**: `0.6 * similarity + 0.2 * trust + 0.2 * recency`

## Latency

Target &lt;500ms for retrieval + ranking. Response includes `latency_ms` and a warning if over target.
