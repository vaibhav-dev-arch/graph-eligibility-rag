# Graph Eligibility RAG — Tech Stack & Tools Reference

Comprehensive table of tools and technologies: **used in POC**, **alternatives**, **purpose**, **license**, and **cost**.

---

## Legend

| Abbreviation | Meaning |
|--------------|--------|
| **Used** | Currently used in this POC |
| **Alternative** | Spec or ecosystem alternative; not implemented in POC |
| **OSS** | Open source |
| **Closed** | Proprietary / closed source |
| **Hybrid** | Open core + commercial offerings |
| **Free** | Free to use (self-hosted or free tier) |
| **Paid** | Requires paid license or subscription |
| **Freemium** | Free tier + paid tiers |

---

## Master Table: Tools, Tech Stack, Purpose, License, Cost

| Category | Tool / Technology | Used in POC? | Purpose | Open Source vs Closed | Free vs Paid | Notes |
|----------|-------------------|-------------|---------|----------------------|--------------|--------|
| **Graph database** | **Neo4j** | ✅ Used | System of record for assets, relationships (DERIVED_FROM, ABOUT_TOPIC, TARGET_AUDIENCE, DELIVERED_IN, PERFORMED_FOR, SIMILAR_TO); eligibility queries | OSS (Community) / Closed (Enterprise) | Free (Community, self-hosted); Paid (Enterprise, Aura) | Community Edition is GPL; Enterprise commercial. |
| | Neo4j Aura | Alternative | Managed Neo4j (hosted) | Closed | Paid | SaaS graph DB. |
| | Amazon Neptune | Alternative | Managed graph DB | Closed | Paid | AWS-only. |
| | Apache Age (PostgreSQL) | Alternative | Graph extension for PostgreSQL | OSS (Apache 2.0) | Free | Graph on Postgres. |
| **Vector database** | **Chroma** | ✅ Used | Store asset embeddings; similarity search (top-K by query or vector) | OSS (Apache 2.0) | Free | Embedded / persistent; no separate server in POC. |
| | Qdrant | Alternative | Vector search, filtering | OSS (Apache 2.0) / Commercial | Free (self-hosted); Paid (Cloud) | Rust; good for production scale. |
| | Weaviate | Alternative | Vector DB + optional graph | OSS (BSD-3) / Commercial | Free (self-hosted); Paid (Cloud) | Graph + vector in one. |
| | Milvus | Alternative | Vector search at scale | OSS (Apache 2.0) | Free (self-hosted) | LF project. |
| | Pinecone | Alternative | Managed vector DB | Closed | Freemium / Paid | Serverless vector search. |
| | pgvector (PostgreSQL) | Alternative | Vector extension in Postgres | OSS | Free | Simple vector in existing DB. |
| **Embedding model (text)** | **Sentence Transformers (all-MiniLM-L6-v2)** | ✅ Used | Asset-level text embeddings; semantic search | OSS (Apache 2.0) | Free | Hugging Face; 384-dim; fast. |
| | sentence-transformers (other models) | Alternative | Larger / multilingual models | OSS | Free | e.g. all-mpnet-base-v2, paraphrase-multilingual. |
| | OpenAI Embeddings (text-embedding-3) | Alternative | Cloud text embeddings | Closed | Paid (per token) | High quality; vendor lock-in. |
| | Cohere Embed | Alternative | Cloud embeddings | Closed | Freemium / Paid | REST API. |
| **Embedding model (multimodal)** | OpenCLIP | Alternative | Text + image embeddings | OSS (MIT) | Free | For image/hero visuals. |
| | BLIP / BLIP-2 | Alternative | Image understanding + captions | OSS (BSD) | Free | Salesforce; image + text. |
| | SigLIP | Alternative | Image-text similarity | OSS | Free | Alternative to CLIP. |
| **Deep learning runtime** | **PyTorch (torch)** | ✅ Used | Backend for Sentence Transformers; no direct `import torch` in app code | OSS (BSD) | Free | Required by sentence-transformers. |
| | **TensorFlow (tensorflow)** | Alternative | Can power embeddings via TF Hub / Keras (see PyTorch vs TensorFlow below) | OSS (Apache 2.0) | Free | Swap embedding backend; same Chroma/API. |
| | Pillow | ✅ Used | Image loading (for future multimodal) | OSS (HPND) | Free | Optional in POC for images. |
| **API framework** | **FastAPI** | ✅ Used | REST API (ingest, seed, next-best-content, telemetry, health) | OSS (MIT) | Free | Async; OpenAPI; Pydantic integration. |
| | Flask | Alternative | WSGI REST API | OSS (BSD) | Free | Synchronous; simpler. |
| | Django + DRF | Alternative | Full-stack + REST | OSS (BSD) | Free | Heavier; admin, ORM. |
| **ASGI server** | **Uvicorn** | ✅ Used | Run FastAPI app (ASGI) | OSS (BSD) | Free | Async; production-grade. |
| | Gunicorn + Uvicorn workers | Alternative | Process manager + Uvicorn | OSS | Free | Multi-worker production. |
| **Config & validation** | **Pydantic** | ✅ Used | Request/response and domain models (Asset, EligibilityFilter, etc.) | OSS (MIT) | Free | Data validation; JSON schema. |
| | **pydantic-settings** | ✅ Used | Load settings from env / .env | OSS (MIT) | Free | BaseSettings for config. |
| | python-dotenv | ✅ Used | Load .env into environment | OSS (BSD) | Free | Used by Pydantic settings. |
| **LLM (local / self-hosted)** | **Ollama** | ✅ Used (optional) | Run local LLMs; OpenAI-compatible API; enrichment & explanation | OSS (MIT) | Free | Local inference; e.g. llama3.2. |
| | llama.cpp | Alternative | Local LLM inference (C++) | OSS (MIT) | Free | No server; library. |
| | LM Studio | Alternative | Local LLM UI + server | OSS | Free | Desktop app. |
| | vLLM | Alternative | Fast server for LLMs | OSS (Apache 2.0) | Free | High throughput. |
| **LLM (cloud / API)** | OpenAI API (GPT-4, etc.) | Alternative | Enrichment; explanations; structured output | Closed | Paid (per token) | Via openai package with api_key. |
| | Anthropic Claude | Alternative | Same use cases | Closed | Paid | REST API. |
| | Google Gemini | Alternative | Same use cases | Closed | Freemium / Paid | Google AI. |
| | Groq | Alternative | Fast inference API | Closed | Freemium / Paid | LPU-based. |
| **LLM client** | **openai (Python package)** | ✅ Used | Call OpenAI-compatible endpoints (Ollama or OpenAI) | OSS (Apache 2.0) | Free | base_url for Ollama. |
| | httpx | ✅ Used | HTTP client (optional for LLM/custom calls) | OSS (BSD) | Free | Async/sync. |
| **Provenance / C2PA** | Custom metadata (ProvenanceInfo) | ✅ Used | Simulated C2PA-style creator/tool/credentials | N/A (in-app) | Free | POC: no real C2PA yet. |
| | c2pa-rs / py-c2pa | Alternative | Real C2PA signing/verification | OSS | Free | Content Credentials. |
| | Open C2PA (Content Authenticity) | Alternative | Standard + reference impl. | OSS | Free | CAI ecosystem. |
| **Event bus / streaming** | In-memory list (stub) | ✅ Used | Telemetry buffer (content_render, impression) | N/A (in-app) | Free | POC only. |
| | Apache Kafka | Alternative | Event streaming | OSS (Apache 2.0) | Free (self-hosted); Paid (Confluent) | Production event bus. |
| | Redis Streams | Alternative | Lightweight streaming | OSS (BSD) | Free | Simple alternative. |
| | AWS Kinesis / EventBridge | Alternative | Managed streaming / events | Closed | Paid | AWS ecosystem. |
| **Language & runtime** | **Python 3.x** | ✅ Used | Application language | OSS (PSF) | Free | 3.10+ typical. |
| **Numerical / data** | **numpy** | ✅ Used | Array ops for embeddings/scores | OSS (BSD) | Free | Dependency of ML stack. |
| **Logging** | structlog | ✅ Used | Structured logging (optional) | OSS (MIT) | Free | In requirements. |
| **Container / orchestration** | Docker | Optional (docs) | Run Neo4j via docker-compose | OSS (Apache 2.0) | Free | Not required for app code. |
| | docker-compose | Optional (docs) | Define Neo4j service | OSS (Apache 2.0) | Free | Compose v2. |

---

## Summary: What This POC Uses

| Layer | Technology | License | Cost |
|-------|------------|---------|------|
| Graph | Neo4j (Community) | OSS (GPL) | Free (self-hosted) |
| Vector store | Chroma | OSS (Apache 2.0) | Free |
| Embeddings | Sentence Transformers + PyTorch | OSS | Free |
| API | FastAPI + Uvicorn | OSS | Free |
| Config | Pydantic + pydantic-settings + python-dotenv | OSS | Free |
| LLM (optional) | Ollama + openai client | OSS | Free |
| Provenance | Custom (stub) | N/A | Free |
| Telemetry | In-memory stub | N/A | Free |

**Overall**: The POC is built to run **fully open source and free** (self-hosted Neo4j, local Chroma, local embeddings, optional local Ollama). Paid options (Neo4j Enterprise, cloud vector DBs, cloud LLMs) are alternatives for production or scale.

---

## PyTorch vs TensorFlow in This POC

| | PyTorch | TensorFlow |
|---|--------|------------|
| **Used in POC?** | ✅ Yes (indirectly) | ❌ No |
| **Where** | Pulled in by `sentence-transformers`; no direct `import torch` in project code. | Not a dependency. |
| **Purpose** | Runs the embedding model (encode text → vector). | — |
| **Can TensorFlow be used?** | — | ✅ Yes. You can use TensorFlow as an alternative embedding backend. |

**How TensorFlow can be used**

- **sentence-transformers** is PyTorch-only; it does not support a TensorFlow backend.
- To use **TensorFlow** for embeddings you would:
  1. Add `tensorflow` and optionally `tensorflow-hub` to `requirements.txt`.
  2. Implement an alternative embedding path in `src/embeddings.py` (or a new module) that uses a TF model, e.g.:
     - **TensorFlow Hub**: e.g. Universal Sentence Encoder (`https://tfhub.dev/google/universal-sentence-encoder/4`) — load with `tensorflow_hub`, encode text, return a list of floats.
     - **Keras NLP**: use a Keras embedding model and call it in the same way (input text → output vector).
  3. Keep the rest unchanged: Chroma still stores vectors; retrieval and ranking stay the same. Vector dimension may change (e.g. USE is 512-dim), so ensure `embedding_dim` in config matches.
- **Using both**: You could support both backends behind a config flag (e.g. `embedding_backend: "pytorch" | "tensorflow"`) and instantiate either SentenceTransformer or a TF-based encoder. Same API: `embed_text(text) -> list[float]`, `embed_asset(asset) -> list[float]`.

---

## Quick Reference: Alternatives by Use Case

| Use case | POC choice | Alternative (OSS/Free) | Alternative (Paid) |
|----------|------------|------------------------|---------------------|
| Graph DB | Neo4j Community | Apache Age (Postgres) | Neo4j Aura, Neptune |
| Vector DB | Chroma | Qdrant, Weaviate, pgvector | Pinecone, Weaviate Cloud |
| Text embeddings | Sentence Transformers | Other HF models | OpenAI Embeddings, Cohere |
| Multimodal embeddings | — | OpenCLIP, BLIP, SigLIP | OpenAI CLIP API |
| API | FastAPI | Flask, Django | — |
| LLM | Ollama (local) | llama.cpp, vLLM | OpenAI, Anthropic, Gemini |
| Provenance | Stub metadata | C2PA open source libs | — |
| Event bus | In-memory stub | Kafka, Redis Streams | Confluent, AWS Kinesis |
