"""Ingest pipeline: DAM/CMS → Enrich (optional LLM) → Graph + Embeddings."""
from datetime import datetime, timedelta
from typing import Optional

from src.graph import ContentGraph
from src.integration import attach_provenance
from src.models import Asset, ApprovalStatus, PerformedForProps


def ingest_asset(
    graph: ContentGraph,
    embedding_service: Optional[object],
    asset: Asset,
    attach_prov: bool = True,
) -> None:
    """Single asset: provenance → graph → optional embedding index."""
    if attach_prov:
        asset = attach_provenance(asset)
    graph.upsert_asset(asset)
    if embedding_service is not None:
        embedding_service.index_asset(asset)


def _demo_assets(now: datetime) -> list[Asset]:
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


def seed_demo_graph(graph: ContentGraph) -> None:
    """Seed Neo4j graph only (Render precomputed mode)."""
    now = datetime.utcnow()
    assets = _demo_assets(now)
    for a in assets:
        ingest_asset(graph, None, a)
    _seed_demo_relationships(graph, now)


def _seed_demo_relationships(graph: ContentGraph, now: datetime) -> None:
    graph.add_derived_from("asset-002", "asset-001", None)
    graph.add_about_topic("asset-001", "topic-summer", "Summer Sale", 0.9)
    graph.add_about_topic("asset-002", "topic-sustainability", "Sustainability", 0.95)
    graph.add_about_topic("asset-003", "topic-product-launch", "Product Launch", 0.9)
    graph.add_target_audience("asset-001", "aud-us-18-35", "18-35", "US")
    graph.add_target_audience("asset-002", "aud-eu-all", "All", "EU")
    graph.add_target_audience("asset-003", "aud-us-25-54", "25-54", "US")
    graph.add_delivered_in("asset-001", "web")
    graph.add_delivered_in("asset-001", "social")
    graph.add_delivered_in("asset-002", "email")
    graph.add_delivered_in("asset-003", "video")
    graph.add_performed_for("asset-001", "web", PerformedForProps(impressions=1000, clicks=50, conversions=5, last_delivered_at=now))
    graph.add_performed_for("asset-002", "email", PerformedForProps(impressions=500, clicks=80, conversions=10, last_delivered_at=now - timedelta(days=2)))
    graph.add_performed_for("asset-003", "video", PerformedForProps(impressions=2000, clicks=120, conversions=15, last_delivered_at=now - timedelta(days=1)))


def seed_demo_data(graph: ContentGraph, embedding_service: object) -> None:
    """Seed graph + Chroma embeddings (local dev)."""
    now = datetime.utcnow()
    for a in _demo_assets(now):
        ingest_asset(graph, embedding_service, a)
    _seed_demo_relationships(graph, now)
