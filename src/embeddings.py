"""Embedding layer: single model, asset-level embeddings stored in Chroma."""
from typing import Optional

import chromadb
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer

from config import get_settings
from src.models import Asset


class EmbeddingService:
    """Asset-level embeddings; single model (text-first for POC)."""

    def __init__(self):
        s = get_settings()
        self._model = SentenceTransformer(s.embedding_model)
        self._dim = s.embedding_dim
        self._client = chromadb.PersistentClient(
            path=s.chroma_persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self._collection = self._client.get_or_create_collection(
            name="content_assets",
        )

    def _text_for_embedding(self, asset: Asset) -> str:
        """Build single text representation for embedding."""
        parts = [
            asset.name or "",
            asset.description or "",
            asset.copy_text or "",
        ]
        if asset.metadata:
            for k, v in (asset.metadata or {}).items():
                if isinstance(v, str):
                    parts.append(v)
        return " ".join(p for p in parts if p).strip() or asset.id

    def embed_asset(self, asset: Asset) -> list[float]:
        """Compute embedding vector for one asset."""
        text = self._text_for_embedding(asset)
        vec = self._model.encode(text, normalize_embeddings=True)
        return vec.tolist()

    def index_asset(self, asset: Asset) -> None:
        """Store embedding in Chroma linked to asset id."""
        vec = self.embed_asset(asset)
        doc = self._text_for_embedding(asset)
        self._collection.upsert(
            ids=[asset.id],
            embeddings=[vec],
            documents=[doc],
            metadatas=[{"name": asset.name, "modality": asset.modality}],
        )

    def search(
        self,
        query: str,
        top_k: int = 20,
        where: Optional[dict] = None,
    ) -> list[tuple[str, float]]:
        """Return list of (asset_id, similarity_score) for query."""
        qvec = self._model.encode(query, normalize_embeddings=True).tolist()
        result = self._collection.query(
            query_embeddings=[qvec],
            n_results=top_k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        ids = result["ids"][0]
        distances = result["distances"][0]
        # Chroma returns L2 distance; convert to similarity (1 / (1 + d)) or use negative distance for ordering
        scores = [1.0 / (1.0 + d) for d in distances] if distances else []
        return list(zip(ids, scores))

    def embed_text(self, text: str) -> list[float]:
        """Encode text to vector (e.g. for reference asset or query)."""
        vec = self._model.encode(text, normalize_embeddings=True)
        return vec.tolist()

    def search_by_vector(
        self,
        vector: list[float],
        top_k: int = 20,
        exclude_ids: Optional[list[str]] = None,
    ) -> list[tuple[str, float]]:
        """Find similar assets by embedding vector."""
        where = None
        if exclude_ids:
            # Chroma doesn't support NOT IN directly; we filter after
            pass
        result = self._collection.query(
            query_embeddings=[vector],
            n_results=top_k + (len(exclude_ids) if exclude_ids else 0),
            where=where,
            include=["distances"],
        )
        ids = result["ids"][0]
        distances = result["distances"][0]
        scores = [1.0 / (1.0 + d) for d in distances] if distances else []
        out = list(zip(ids, scores))
        if exclude_ids:
            exclude = set(exclude_ids)
            out = [(i, s) for i, s in out if i not in exclude][:top_k]
        else:
            out = out[:top_k]
        return out
