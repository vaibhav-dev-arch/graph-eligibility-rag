"""Eligibility-aware ranking with heuristic scoring and explainability."""
from datetime import datetime
from typing import Optional

from config import get_settings
from src.graph import ContentGraph
from src.models import EligibilityFilter, RecommendationResult


def _trust_score(perf: dict, has_provenance: bool) -> float:
    """Simple trust: performance + credentials. 0..1."""
    impressions = perf.get("impressions", 0) or 0
    clicks = perf.get("clicks", 0) or 0
    conversions = perf.get("conversions", 0) or 0
    # Heuristic: some weight for engagement and conversions
    perf_score = min(1.0, (clicks * 0.1 + conversions * 0.5) / max(1, impressions) * 100)
    if impressions > 0:
        perf_score = min(1.0, 0.3 + 0.7 * (clicks / max(1, impressions) * 10))
    cred = 0.2 if has_provenance else 0.0
    return min(1.0, perf_score * 0.8 + cred)


def _recency_score(last_delivered_at: Optional[str]) -> float:
    """Favor recently delivered (fatigue-aware: not overused recently). Inverse recency as freshness."""
    if not last_delivered_at:
        return 0.5
    try:
        dt = datetime.fromisoformat(last_delivered_at.replace("Z", "+00:00"))
        now = datetime.utcnow()
        if dt.tzinfo:
            from datetime import timezone
            now = now.replace(tzinfo=timezone.utc)
        delta_days = (now - dt.replace(tzinfo=None) if dt.tzinfo else now - dt).days
        if delta_days < 0:
            return 1.0
        return max(0.0, 1.0 - delta_days / 90)
    except Exception:
        return 0.5


def rank_candidates(
    candidates: list[tuple[str, float]],
    graph: ContentGraph,
    eligibility: EligibilityFilter,
    top_k: int = 10,
    explain: bool = True,
) -> list[RecommendationResult]:
    """
    Weighted score: similarity * w_sim + trust * w_trust + recency * w_recency.
    Build explanation for each result.
    """
    s = get_settings()
    w_sim = s.ranking_similarity_weight
    w_trust = s.ranking_trust_weight
    w_recency = s.ranking_recency_weight

    performance = graph.get_asset_ids_with_performance()
    results: list[RecommendationResult] = []

    for asset_id, sim_score in candidates[: top_k * 2]:
        node = graph.get_asset(asset_id)
        if not node:
            continue
        perf = performance.get(asset_id, {})
        has_provenance = bool(node.get("provenance_credentials"))
        trust = _trust_score(perf, has_provenance)
        recency = _recency_score(perf.get("last_delivered_at"))

        final_score = sim_score * w_sim + trust * w_trust + recency * w_recency
        expl: list[str] = []
        if explain:
            expl.append(f"Similarity: {sim_score:.3f} (semantic match).")
            expl.append(f"Trust: {trust:.3f} (performance + provenance).")
            expl.append(f"Recency: {recency:.3f} (last delivered).")
            expl.append(f"Eligible: {eligibility.approval_statuses} approval, markets {eligibility.markets}, channels {eligibility.channels}.")
        results.append(
            RecommendationResult(
                asset_id=asset_id,
                score=final_score,
                similarity_score=sim_score,
                trust_score=trust,
                recency_score=recency,
                explanation=expl,
                eligibility_reasons=["Passed graph eligibility filter."],
                asset_summary={"name": node.get("name"), "modality": node.get("modality")},
            )
        )

    results.sort(key=lambda r: r.score, reverse=True)
    return results[:top_k]
