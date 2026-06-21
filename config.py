"""Application configuration."""
from pydantic_settings import BaseSettings
from pathlib import Path


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

    auto_seed_on_startup: bool = True

    class Config:
        env_file = ".env"
        extra = "ignore"


def get_settings() -> Settings:
    return Settings()
