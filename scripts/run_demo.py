#!/usr/bin/env python3
"""CLI walkthrough for Graph Eligibility RAG."""

import json
import os
import sys

import httpx

BASE = os.environ.get("GRAPH_RAG_API_URL", "http://127.0.0.1:8000")


def main() -> None:
    client = httpx.Client(base_url=BASE, timeout=120.0)

    print("Graph Eligibility RAG — Demo")
    print("=" * 40)

    print("\n1) Health...")
    health = client.get("/health").json()
    print(json.dumps(health, indent=2))
    if health.get("status") != "ok":
        print("\nWarning: service degraded — is Neo4j running?")
        sys.exit(1)

    print("\n2) Demo query (summer sale)...")
    demo = client.post("/demo").json()
    print(f"   Results: {len(demo.get('results', []))}")
    print(f"   Latency: {demo.get('latency_ms')}ms")
    for r in demo.get("results", [])[:3]:
        print(f"   - {r.get('asset_id')}: score={r.get('score', 0):.3f}")

    print("\n3) Eligibility-filtered query...")
    filtered = client.post(
        "/next-best-content",
        json={
            "query": "sustainability",
            "eligibility": {
                "markets": ["US", "EU"],
                "channels": ["web", "email"],
                "approval_statuses": ["approved"],
            },
            "top_k": 5,
            "explain": True,
        },
    ).json()
    print(f"   Results: {len(filtered.get('results', []))}")
    print(json.dumps(filtered.get("results", [])[:2], indent=2))

    print("\nDone. Open /docs for interactive API.")


if __name__ == "__main__":
    try:
        main()
    except httpx.ConnectError:
        print("Error: server not running. Start with: python app.py", file=sys.stderr)
        sys.exit(1)
