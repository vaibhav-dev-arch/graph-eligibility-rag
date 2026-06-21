"""Neo4j content graph: schema, assets, and relationship types."""
from datetime import datetime
from typing import Any, Optional

from neo4j import GraphDatabase

from config import get_settings
from src.models import (
    Asset,
    AssetType,
    ApprovalStatus,
    DeliveredInProps,
    DerivedFromProps,
    PerformedForProps,
    TargetAudienceProps,
    AboutTopicProps,
    SimilarToProps,
)


class ContentGraph:
    """System of record for assets and 5 relationship types."""

    def __init__(self):
        s = get_settings()
        self._driver = GraphDatabase.driver(
            s.neo4j_uri,
            auth=(s.neo4j_user, s.neo4j_password),
        )

    def close(self):
        self._driver.close()

    def init_schema(self) -> None:
        """Create constraints and indexes for Asset and relationship types."""
        with self._driver.session() as session:
            session.run(
                "CREATE CONSTRAINT asset_id IF NOT EXISTS FOR (a:Asset) REQUIRE a.id IS UNIQUE"
            )
            session.run(
                "CREATE INDEX asset_approval IF NOT EXISTS FOR (a:Asset) ON (a.approval_status)"
            )
            session.run(
                "CREATE INDEX asset_updated IF NOT EXISTS FOR (a:Asset) ON (a.updated_at)"
            )
            session.run(
                "CREATE CONSTRAINT topic_id IF NOT EXISTS FOR (t:Topic) REQUIRE t.id IS UNIQUE"
            )
            session.run(
                "CREATE CONSTRAINT audience_id IF NOT EXISTS FOR (aud:Audience) REQUIRE aud.id IS UNIQUE"
            )
            session.run(
                "CREATE CONSTRAINT channel_name IF NOT EXISTS FOR (c:Channel) REQUIRE c.name IS UNIQUE"
            )

    def upsert_asset(self, asset: Asset) -> None:
        """Create or update Asset node."""
        now = datetime.utcnow()
        with self._driver.session() as session:
            session.run(
                """
                MERGE (a:Asset {id: $id})
                SET a.name = $name, a.external_id = $external_id, a.asset_type = $asset_type,
                    a.modality = $modality, a.description = $description, a.copy_text = $copy_text,
                    a.approval_status = $approval_status, a.rights_expiry = $rights_expiry,
                    a.updated_at = $updated_at,
                    a.metadata = $metadata,
                    a.provenance_creator = $p_creator, a.provenance_tool = $p_tool,
                    a.provenance_credentials = $p_creds
                SET a.created_at = COALESCE(a.created_at, $created_at)
                """,
                id=asset.id,
                name=asset.name,
                external_id=asset.external_id,
                asset_type=asset.asset_type.value,
                modality=asset.modality,
                description=asset.description or "",
                copy_text=asset.copy_text or "",
                approval_status=asset.approval_status.value,
                rights_expiry=asset.rights_expiry.isoformat() if asset.rights_expiry else None,
                updated_at=now.isoformat(),
                created_at=(asset.created_at or now).isoformat(),
                metadata=str(asset.metadata) if isinstance(asset.metadata, dict) else "{}",
                p_creator=asset.provenance.creator if asset.provenance else None,
                p_tool=asset.provenance.tool if asset.provenance else None,
                p_creds=asset.provenance.credentials_present if asset.provenance else False,
            )

    def add_derived_from(self, child_id: str, parent_id: str, props: Optional[DerivedFromProps] = None) -> None:
        """Variant/rendition/localization -> master."""
        p = props or DerivedFromProps()
        with self._driver.session() as session:
            session.run(
                """
                MATCH (child:Asset {id: $child_id}), (parent:Asset {id: $parent_id})
                MERGE (child)-[r:DERIVED_FROM]->(parent)
                SET r.relationship_type = $rel_type, r.created_at = $created_at
                """,
                child_id=child_id,
                parent_id=parent_id,
                rel_type=p.relationship_type,
                created_at=datetime.utcnow().isoformat(),
            )

    def add_about_topic(self, asset_id: str, topic_id: str, topic_label: str, confidence: float = 1.0) -> None:
        """Asset -[:ABOUT_TOPIC]-> Topic (merge Topic if not exists)."""
        with self._driver.session() as session:
            session.run(
                """
                MERGE (t:Topic {id: $topic_id}) SET t.label = $topic_label
                WITH t
                MATCH (a:Asset {id: $asset_id})
                MERGE (a)-[r:ABOUT_TOPIC]->(t)
                SET r.confidence = $confidence
                """,
                asset_id=asset_id,
                topic_id=topic_id,
                topic_label=topic_label,
                confidence=confidence,
            )

    def add_target_audience(self, asset_id: str, audience_id: str, segment: str, market: str) -> None:
        """Asset -[:TARGET_AUDIENCE]-> Audience."""
        with self._driver.session() as session:
            session.run(
                """
                MERGE (aud:Audience {id: $audience_id})
                SET aud.segment = $segment, aud.market = $market
                WITH aud
                MATCH (a:Asset {id: $asset_id})
                MERGE (a)-[r:TARGET_AUDIENCE]->(aud)
                """,
                asset_id=asset_id,
                audience_id=audience_id,
                segment=segment,
                market=market,
            )

    def add_delivered_in(self, asset_id: str, channel_name: str, props: Optional[DeliveredInProps] = None) -> None:
        """Asset -[:DELIVERED_IN]-> Channel."""
        p = props or DeliveredInProps(channel=channel_name)
        with self._driver.session() as session:
            session.run(
                """
                MERGE (c:Channel {name: $channel})
                WITH c
                MATCH (a:Asset {id: $asset_id})
                MERGE (a)-[r:DELIVERED_IN]->(c)
                SET r.campaign_id = $campaign_id, r.started_at = $started_at
                """,
                asset_id=asset_id,
                channel=channel_name,
                campaign_id=p.campaign_id,
                started_at=p.started_at.isoformat() if p.started_at else None,
            )

    def add_performed_for(self, asset_id: str, channel_name: str, props: PerformedForProps) -> None:
        """Asset -[:PERFORMED_FOR]-> Channel with metrics."""
        with self._driver.session() as session:
            session.run(
                """
                MERGE (c:Channel {name: $channel})
                WITH c
                MATCH (a:Asset {id: $asset_id})
                MERGE (a)-[r:PERFORMED_FOR]->(c)
                SET r.impressions = $impressions, r.clicks = $clicks, r.conversions = $conversions,
                    r.last_delivered_at = $last_delivered_at
                """,
                asset_id=asset_id,
                channel=channel_name,
                impressions=props.impressions,
                clicks=props.clicks,
                conversions=props.conversions,
                last_delivered_at=props.last_delivered_at.isoformat() if props.last_delivered_at else None,
            )

    def add_similar_to(self, asset_id: str, other_id: str, score: float, source: str = "graph") -> None:
        """Asset -[:SIMILAR_TO]-> Asset (graph-based similarity)."""
        with self._driver.session() as session:
            session.run(
                """
                MATCH (a:Asset {id: $asset_id}), (b:Asset {id: $other_id})
                MERGE (a)-[r:SIMILAR_TO]->(b)
                SET r.score = $score, r.source = $source, r.updated_at = $updated_at
                """,
                asset_id=asset_id,
                other_id=other_id,
                score=score,
                source=source,
                updated_at=datetime.utcnow().isoformat(),
            )

    def get_asset(self, asset_id: str) -> Optional[dict[str, Any]]:
        """Return asset node as dict or None."""
        with self._driver.session() as session:
            result = session.run("MATCH (a:Asset {id: $id}) RETURN a", id=asset_id)
            record = result.single()
            if not record or not record["a"]:
                return None
            node = record["a"]
            return {k: node[k] for k in node.keys()} if hasattr(node, "keys") else dict(node)

    def get_eligible_asset_ids(
        self,
        markets: list[str],
        channels: list[str],
        approval_statuses: list[str],
        require_rights_valid: bool,
    ) -> set[str]:
        """Return set of asset IDs that pass eligibility (rights, market, channel, approval)."""
        with self._driver.session() as session:
            now = datetime.utcnow().isoformat()
            result = session.run(
                """
                MATCH (a:Asset)
                WHERE a.approval_status IN $approval_statuses
                  AND (a.rights_expiry IS NULL OR a.rights_expiry > $now)
                WITH a
                OPTIONAL MATCH (a)-[:TARGET_AUDIENCE]->(aud:Audience)
                WITH a, aud
                WHERE aud IS NULL OR aud.market IN $markets
                WITH DISTINCT a
                OPTIONAL MATCH (a)-[:DELIVERED_IN]->(ch:Channel)
                WITH a, ch
                WHERE ch IS NULL OR ch.name IN $channels
                RETURN DISTINCT a.id AS id
                """,
                approval_statuses=approval_statuses,
                markets=markets,
                channels=channels,
                now=now,
            )
            return {r["id"] for r in result if r["id"]}

    def get_asset_ids_with_performance(self) -> dict[str, dict]:
        """Return asset_id -> {impressions, clicks, conversions, last_delivered_at} for ranking."""
        with self._driver.session() as session:
            result = session.run(
                """
                MATCH (a:Asset)-[r:PERFORMED_FOR]->()
                WITH a.id AS id,
                     sum(r.impressions) AS impressions,
                     sum(r.clicks) AS clicks,
                     sum(r.conversions) AS conversions,
                     max(r.last_delivered_at) AS last_delivered_at
                RETURN id, impressions, clicks, conversions, last_delivered_at
                """
            )
            return {
                r["id"]: {
                    "impressions": r["impressions"] or 0,
                    "clicks": r["clicks"] or 0,
                    "conversions": r["conversions"] or 0,
                    "last_delivered_at": r["last_delivered_at"],
                }
                for r in result
            }
