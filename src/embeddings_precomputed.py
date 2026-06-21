"""Lightweight embedding store for Render free tier (precomputed vectors, no torch)."""

from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Optional

from src.models import Asset

_DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "demo_embeddings.json"


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    return dot  # vectors are L2-normalized from sentence-transformers


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


class PrecomputedEmbeddingService:
    """In-memory vectors from demo_embeddings.json — fits Render 512Mi."""

    def __init__(self, path: Path | None = None):
        data_path = path or _DATA_PATH
        if not data_path.exists():
            raise FileNotFoundError(
                f"Missing {data_path}. Run: python scripts/precompute_demo_embeddings.py"
            )
        payload = json.loads(data_path.read_text())
        self._model_name = payload["model"]
        self._dim = payload["dim"]
        self._assets: dict[str, dict] = {a["id"]: a for a in payload["assets"]}
        self._query_vectors: dict[str, list[float]] = payload.get("query_vectors", {})

    @property
    def _collection(self):
        """Compat shim for health check asset count."""
        return self

    def count(self) -> int:
        return len(self._assets)

    def _text_for_embedding(self, asset: Asset) -> str:
        parts = [asset.name or "", asset.description or "", asset.copy_text or ""]
        return " ".join(p for p in parts if p).strip() or asset.id

    def _vector_for_query(self, query: str) -> list[float] | None:
        if query in self._query_vectors:
            return self._query_vectors[query]
        q_tokens = _tokenize(query)
        if not q_tokens:
            return None
        # Fallback: average asset vectors weighted by token overlap (no ML runtime).
        weighted = [0.0] * self._dim
        total = 0.0
        for rec in self._assets.values():
            overlap = len(q_tokens & _tokenize(rec["text"]))
            if overlap <= 0:
                continue
            w = float(overlap)
            total += w
            for i, v in enumerate(rec["embedding"]):
                weighted[i] += w * v
        if total <= 0:
            return None
        norm = math.sqrt(sum(v * v for v in weighted)) or 1.0
        return [v / norm for v in weighted]

    def embed_asset(self, asset: Asset) -> list[float]:
        if asset.id in self._assets:
            return self._assets[asset.id]["embedding"]
        raise ValueError(f"Asset {asset.id} not in precomputed store")

    def index_asset(self, asset: Asset) -> None:
        text = self._text_for_embedding(asset)
        self._assets[asset.id] = {"id": asset.id, "text": text, "embedding": self.embed_asset(asset)}

    def embed_text(self, text: str) -> list[float]:
        vec = self._vector_for_query(text)
        if vec is None:
            raise ValueError("Could not embed text in precomputed mode")
        return vec

    def search(
        self,
        query: str,
        top_k: int = 20,
        where: Optional[dict] = None,
    ) -> list[tuple[str, float]]:
        qvec = self._vector_for_query(query)
        if qvec is None:
            return []
        scored = [(aid, _cosine(qvec, rec["embedding"])) for aid, rec in self._assets.items()]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    def search_by_vector(
        self,
        vector: list[float],
        top_k: int = 20,
        exclude_ids: Optional[list[str]] = None,
    ) -> list[tuple[str, float]]:
        exclude = set(exclude_ids or [])
        scored = [
            (aid, _cosine(vector, rec["embedding"]))
            for aid, rec in self._assets.items()
            if aid not in exclude
        ]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]
