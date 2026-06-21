#!/usr/bin/env python3
"""Generate data/demo_embeddings.json for Render free tier (no torch at runtime)."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.models import ApprovalStatus, Asset  # noqa: E402

OUT = ROOT / "data" / "demo_embeddings.json"


def demo_assets() -> list[Asset]:
    now = datetime.utcnow()
    return [
        Asset(
            id="asset-001",
            name="Summer Campaign Hero",
            modality="text",
            description="Hero banner for summer sale campaign.",
            copy_text="Get 30% off this summer. Limited time offer on all seasonal items.",
            approval_status=ApprovalStatus.APPROVED,
            rights_expiry=now + timedelta(days=90),
            created_at=now,
            updated_at=now,
        ),
        Asset(
            id="asset-002",
            name="Sustainability Story",
            modality="text",
            description="Blog post about eco-friendly products.",
            copy_text="Our commitment to sustainability. Eco-friendly materials and carbon-neutral shipping.",
            approval_status=ApprovalStatus.APPROVED,
            rights_expiry=now + timedelta(days=180),
            created_at=now,
            updated_at=now,
        ),
        Asset(
            id="asset-003",
            name="Product Launch Video CTA",
            modality="text",
            description="Call to action for new product video.",
            copy_text="New product launch. Discover the latest innovation. Watch the video and shop now.",
            approval_status=ApprovalStatus.APPROVED,
            rights_expiry=now + timedelta(days=60),
            created_at=now,
            updated_at=now,
        ),
        Asset(
            id="asset-004",
            name="Holiday Gift Guide",
            modality="text",
            description="Gift guide email subject and preview.",
            copy_text="Holiday gift guide. Find the perfect gift for everyone. Free shipping on orders over 50.",
            approval_status=ApprovalStatus.DRAFT,
            rights_expiry=now + timedelta(days=120),
            created_at=now,
            updated_at=now,
        ),
        Asset(
            id="asset-005",
            name="Flash Sale Alert",
            modality="text",
            description="Flash sale notification.",
            copy_text="Flash sale 24 hours only. Extra 20% off with code FLASH. Limited time offer.",
            approval_status=ApprovalStatus.APPROVED,
            rights_expiry=now + timedelta(days=30),
            created_at=now,
            updated_at=now,
        ),
    ]


def text_for_asset(asset: Asset) -> str:
    parts = [asset.name or "", asset.description or "", asset.copy_text or ""]
    return " ".join(p for p in parts if p).strip() or asset.id


def main() -> None:
    from sentence_transformers import SentenceTransformer

    model_name = "sentence-transformers/all-MiniLM-L6-v2"
    model = SentenceTransformer(model_name)
    assets = demo_assets()
    records = []
    for asset in assets:
        text = text_for_asset(asset)
        vec = model.encode(text, normalize_embeddings=True).tolist()
        records.append({"id": asset.id, "text": text, "embedding": vec})

    demo_queries = ["summer sale discount"]
    query_vectors = {}
    for q in demo_queries:
        query_vectors[q] = model.encode(q, normalize_embeddings=True).tolist()

    OUT.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "model": model_name,
        "dim": len(records[0]["embedding"]),
        "assets": records,
        "query_vectors": query_vectors,
    }
    OUT.write_text(json.dumps(payload, indent=2))
    print(f"Wrote {OUT} ({len(records)} assets, {len(query_vectors)} query vectors)")


if __name__ == "__main__":
    main()
