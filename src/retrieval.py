"""Hybrid retrieval: top-K vector similarity + graph eligibility constraints."""
import time
from typing import Any, Optional

from src.graph import ContentGraph
from src.models import EligibilityFilter


class HybridRetriever:
    """Vector similarity + graph-based eligibility; explainable results."""

    def __init__(self, embedding_service: Any, graph: ContentGraph):
        self._emb = embedding_service
        self._graph = graph

    def retrieve(
        self,
        query: Optional[str] = None,
        reference_asset_id: Optional[str] = None,
        eligibility: Optional[EligibilityFilter] = None,
        top_k: int = 20,
    ) -> tuple[list[tuple[str, float]], list[str], float]:
        """
        Returns:
            (candidate_list, explanation_lines, latency_ms)
            candidate_list: [(asset_id, similarity_score), ...]
            explanation_lines: why each was included/excluded
        """
        eligibility = eligibility or EligibilityFilter()
        start = time.perf_counter()
        explanation: list[str] = []

        # 1) Top-K vector retrieval
        if query:
            candidates = self._emb.search(query, top_k=top_k * 2)
            explanation.append(f"Semantic search for query: '{query[:80]}...' returned {len(candidates)} candidates.")
        elif reference_asset_id:
            ref_asset = self._graph.get_asset(reference_asset_id)
            if not ref_asset:
                return [], [f"Reference asset {reference_asset_id} not found."], (time.perf_counter() - start) * 1000
            ref_text = (ref_asset.get("copy_text") or ref_asset.get("description") or ref_asset.get("name") or "")
            if not ref_text:
                ref_text = reference_asset_id
            ref_vec = self._emb.embed_text(ref_text)
            candidates = self._emb.search_by_vector(ref_vec, top_k=top_k * 2, exclude_ids=[reference_asset_id])
            explanation.append(f"Similar-to-asset search for '{reference_asset_id}' returned {len(candidates)} candidates.")
        else:
            return [], ["Provide query or reference_asset_id."], (time.perf_counter() - start) * 1000

        if not candidates:
            return [], explanation + ["No similar content found in vector store."], (time.perf_counter() - start) * 1000

        # 2) Graph eligibility filter
        eligible_ids = self._graph.get_eligible_asset_ids(
            markets=eligibility.markets,
            channels=eligibility.channels,
            approval_statuses=eligibility.approval_statuses,
            require_rights_valid=eligibility.require_rights_valid,
        )
        explanation.append(f"Eligibility filter: {len(eligible_ids)} assets pass rights/market/channel/approval.")

        filtered: list[tuple[str, float]] = []
        for aid, score in candidates:
            if aid in eligible_ids:
                filtered.append((aid, score))
            if len(filtered) >= top_k:
                break
        explanation.append(f"After eligibility: {len(filtered)} candidates in top-{top_k}.")

        latency_ms = (time.perf_counter() - start) * 1000
        return filtered, explanation, latency_ms
