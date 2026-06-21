"""Integration layer: DAM/CMS stubs, provenance metadata, event bus telemetry."""
from datetime import datetime
from typing import Any, Optional

from src.models import Asset, AssetType, ApprovalStatus, ProvenanceInfo


# --- DAM stub: system of record for master assets, renditions, rights ---
def stub_fetch_dam_asset(external_id: str) -> Optional[dict[str, Any]]:
    """Simulate DAM API: return asset record by external id."""
    # POC: return None (caller uses seed data) or a dict with name, rights_expiry, etc.
    return None


def stub_dam_to_asset(dam_record: dict[str, Any]) -> Asset:
    """Map DAM record to our Asset model."""
    return Asset(
        id=dam_record.get("id", ""),
        external_id=dam_record.get("external_id"),
        name=dam_record.get("name", ""),
        asset_type=AssetType(dam_record.get("asset_type", "master")),
        modality=dam_record.get("modality", "text"),
        description=dam_record.get("description"),
        copy_text=dam_record.get("copy_text"),
        metadata=dam_record.get("metadata", {}),
        approval_status=ApprovalStatus(dam_record.get("approval_status", "draft")),
        rights_expiry=datetime.fromisoformat(dam_record["rights_expiry"]) if dam_record.get("rights_expiry") else None,
    )


# --- Provenance (C2PA-style; POC: metadata only) ---
def attach_provenance(asset: Asset, creator: str = "", tool: str = "", model_version: str = "") -> Asset:
    """Attach provenance metadata to asset (simulated C2PA)."""
    asset.provenance = ProvenanceInfo(
        creator=creator or "poc_ingest",
        tool=tool or "graph-eligibility-rag",
        model_version=model_version,
        captured_at=datetime.utcnow(),
        credentials_present=bool(creator or tool),
    )
    return asset


def check_provenance_eligible(asset: Asset, require_credentials: bool) -> bool:
    """Policy checker: block activation if credentials missing when required."""
    if not require_credentials:
        return True
    return bool(asset.provenance and asset.provenance.credentials_present)


# --- Event bus (telemetry stub): sessions, impressions, conversions ---
_events: list[dict] = []


def emit_telemetry(event_type: str, payload: dict[str, Any]) -> None:
    """Push event to streaming layer (stub: in-memory list)."""
    from config import get_settings
    if not get_settings().event_bus_enabled:
        return
    _events.append({
        "type": event_type,
        "payload": payload,
        "ts": datetime.utcnow().isoformat(),
    })


def stub_content_render(asset_id: str, channel: str, session_id: str) -> None:
    """Record content render event for fatigue/performance."""
    emit_telemetry("content_render", {
        "asset_id": asset_id,
        "channel": channel,
        "session_id": session_id,
    })


def stub_impression(asset_id: str, channel: str, campaign_id: Optional[str] = None) -> None:
    """Record impression."""
    emit_telemetry("impression", {
        "asset_id": asset_id,
        "channel": channel,
        "campaign_id": campaign_id,
    })


def get_telemetry_events() -> list[dict]:
    """Return buffered events (for POC inspection)."""
    return list(_events)
