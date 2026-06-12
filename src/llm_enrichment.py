"""Optional LLM layer: structured metadata extraction and explanation generation."""
import json
from typing import Any, Optional

import httpx
from openai import OpenAI

from config import get_settings
from src.models import Asset, RecommendationResult


def _client() -> Optional[OpenAI]:
    s = get_settings()
    if not s.llm_enabled:
        return None
    return OpenAI(base_url=s.llm_base_url, api_key="ollama")


def extract_metadata_structured(asset: Asset) -> dict[str, Any]:
    """
    Use LLM to extract topic/tone tags and structured metadata from asset text.
    Returns e.g. {"topics": ["sustainability", "product"], "tone": "professional"}.
    """
    client = _client()
    if not client:
        return {}
    text = (asset.copy_text or asset.description or asset.name or "")[:2000]
    if not text.strip():
        return {}
    try:
        resp = client.chat.completions.create(
            model=get_settings().llm_model,
            messages=[
                {"role": "system", "content": "You output only valid JSON. No markdown."},
                {"role": "user", "content": f"From this marketing content, extract: topics (list of 3-5 keywords), tone (one word). Content:\n{text}\nOutput JSON: {{\"topics\": [...], \"tone\": \"...\"}}"},
            ],
            max_tokens=200,
        )
        out = resp.choices[0].message.content
        return json.loads(out.strip())
    except Exception:
        return {}


def generate_why_recommendation(result: RecommendationResult) -> str:
    """Generate natural language explanation for why this content was recommended."""
    client = _client()
    if not client:
        return "; ".join(result.explanation) if result.explanation else ""
    parts = [
        f"Asset: {result.asset_id}",
        f"Similarity: {result.similarity_score:.2f}, Trust: {result.trust_score:.2f}, Recency: {result.recency_score:.2f}",
        "Reasons: " + "; ".join(result.explanation),
    ]
    try:
        resp = client.chat.completions.create(
            model=get_settings().llm_model,
            messages=[
                {"role": "system", "content": "You are a concise marketing analyst. In 1-2 sentences explain why this content was recommended."},
                {"role": "user", "content": "\n".join(parts)},
            ],
            max_tokens=150,
        )
        return resp.choices[0].message.content.strip()
    except Exception:
        return "; ".join(result.explanation) if result.explanation else ""
