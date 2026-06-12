"""Domain models for content assets, relationships, and eligibility."""
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field


class AssetType(str, Enum):
    MASTER = "master"
    VARIANT = "variant"
    RENDITION = "rendition"
    LOCALIZATION = "localization"


class ApprovalStatus(str, Enum):
    DRAFT = "draft"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class Channel(str, Enum):
    WEB = "web"
    SOCIAL = "social"
    EMAIL = "email"
    DISPLAY = "display"
    VIDEO = "video"


class Market(str, Enum):
    US = "US"
    EU = "EU"
    APAC = "APAC"
    GLOBAL = "GLOBAL"


# --- Asset (canonical node in graph) ---
class Asset(BaseModel):
    id: str
    external_id: Optional[str] = None  # DAM/CMS id
    name: str
    asset_type: AssetType = AssetType.MASTER
    modality: str = "text"  # text | image | video | audio
    description: Optional[str] = None
    copy_text: Optional[str] = None  # For text/embedding
    metadata: dict[str, Any] = Field(default_factory=dict)
    approval_status: ApprovalStatus = ApprovalStatus.DRAFT
    rights_expiry: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    provenance: Optional["ProvenanceInfo"] = None


class ProvenanceInfo(BaseModel):
    """Simulated C2PA-style provenance (POC: metadata only)."""
    creator: Optional[str] = None
    tool: Optional[str] = None
    model_version: Optional[str] = None
    captured_at: Optional[datetime] = None
    credentials_present: bool = False


# --- Relationship payloads (for graph edges) ---
class DerivedFromProps(BaseModel):
    relationship_type: str = "rendition"  # variant | rendition | localization
    created_at: Optional[datetime] = None


class AboutTopicProps(BaseModel):
    topic_id: str
    topic_label: str
    confidence: float = 1.0


class TargetAudienceProps(BaseModel):
    audience_id: str
    segment: str
    market: str  # US | EU | APAC | GLOBAL


class DeliveredInProps(BaseModel):
    channel: str
    campaign_id: Optional[str] = None
    started_at: Optional[datetime] = None


class PerformedForProps(BaseModel):
    """Performance metrics attached to (Asset)-[:PERFORMED_FOR]->(Campaign/Channel)."""
    impressions: int = 0
    clicks: int = 0
    conversions: int = 0
    last_delivered_at: Optional[datetime] = None


class SimilarToProps(BaseModel):
    score: float = 0.0
    source: str = "graph"  # graph | vector
    updated_at: Optional[datetime] = None


# --- Eligibility filter (read-time) ---
class EligibilityFilter(BaseModel):
    markets: list[str] = Field(default_factory=lambda: ["US", "EU", "APAC", "GLOBAL"])
    channels: list[str] = Field(default_factory=lambda: ["web", "social", "email", "display", "video"])
    approval_statuses: list[str] = Field(default_factory=lambda: ["approved"])
    require_rights_valid: bool = True
    require_provenance: bool = False  # POC: optional


# --- Retrieval & ranking ---
class RecommendationResult(BaseModel):
    asset_id: str
    score: float
    similarity_score: float
    trust_score: float
    recency_score: float
    explanation: list[str] = Field(default_factory=list)
    eligibility_reasons: list[str] = Field(default_factory=list)
    asset_summary: Optional[dict[str, Any]] = None


class NextBestContentRequest(BaseModel):
    query: Optional[str] = None  # Text query for semantic search
    reference_asset_id: Optional[str] = None  # Or "content like this"
    eligibility: EligibilityFilter = Field(default_factory=EligibilityFilter)
    top_k: int = 10
    explain: bool = True
