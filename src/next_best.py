"""Next Best Content: hybrid retrieval + eligibility-aware ranking + optional LLM explain."""
from config import get_settings
from src.embeddings import EmbeddingService
from src.graph import ContentGraph
from src.llm_enrichment import generate_why_recommendation
from src.models import NextBestContentRequest, RecommendationResult
from src.ranking import rank_candidates
from src.retrieval import HybridRetriever


def get_next_best_content(request: NextBestContentRequest) -> dict:
    """
    End-to-end: retrieve (vector + eligibility) → rank → optional LLM explanation.
    """
    graph = ContentGraph()
    emb = EmbeddingService()
    retriever = HybridRetriever(emb, graph)
    try:
        candidates, retrieval_explanation, latency_ms = retriever.retrieve(
            query=request.query,
            reference_asset_id=request.reference_asset_id,
            eligibility=request.eligibility,
            top_k=request.top_k * 2,
        )
        if not candidates:
            return {
                "results": [],
                "retrieval_explanation": retrieval_explanation,
                "latency_ms": round(latency_ms, 2),
                "error": None,
            }
        results = rank_candidates(
            candidates,
            graph,
            request.eligibility,
            top_k=request.top_k,
            explain=request.explain,
        )
        if get_settings().llm_enabled and request.explain:
            for r in results:
                r.explanation = [generate_why_recommendation(r)]
        return {
            "results": [r.model_dump() for r in results],
            "retrieval_explanation": retrieval_explanation,
            "latency_ms": round(latency_ms, 2),
            "error": None,
        }
    finally:
        graph.close()
