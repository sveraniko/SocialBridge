#!/usr/bin/env python3
"""Quick operator health check for SocialBridge."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime, timedelta

import httpx


DYNAMIC_LIMIT_DEFAULT = 5000


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check /health, /ready and dynamic mapping growth")
    parser.add_argument("--base-url", required=True, help="Base API URL, e.g. http://localhost:8000")
    parser.add_argument("--token", required=True, help="Admin token for X-Admin-Token")
    parser.add_argument(
        "--dynamic-limit",
        type=int,
        default=DYNAMIC_LIMIT_DEFAULT,
        help="Operational threshold for dynamic mappings created in last 24h",
    )
    return parser.parse_args()


def _parse_iso8601(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    raw = value.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _count_dynamic_last_24h(items: list[object], now: datetime) -> int:
    threshold = now - timedelta(hours=24)
    count = 0
    for item in items:
        if not isinstance(item, dict):
            continue
        meta = item.get("meta")
        created_at = _parse_iso8601(item.get("created_at"))
        if not isinstance(meta, dict) or meta.get("dynamic") is not True or created_at is None:
            continue
        if created_at >= threshold:
            count += 1
    return count


def main() -> int:
    args = parse_args()
    base = args.base_url.rstrip("/")
    headers = {"X-Admin-Token": args.token}

    try:
        with httpx.Client(timeout=15.0) as client:
            health_response = client.get(f"{base}/health")
            ready_response = client.get(f"{base}/ready")
            export_response = client.get(f"{base}/v1/admin/content-map/export", headers=headers)
    except httpx.HTTPError as exc:
        print(f"request failed: {exc}", file=sys.stderr)
        return 2

    exit_code = 0
    print(f"health_http={health_response.status_code}")
    if health_response.status_code >= 400:
        print("health_status=error")
        exit_code = 2
    else:
        health_body = health_response.json()
        print(f"health_status={health_body.get('status', 'unknown')}")

    print(f"ready_http={ready_response.status_code}")
    if ready_response.status_code >= 400:
        print("ready_status=error")
        exit_code = 2
    else:
        ready_body = ready_response.json()
        print(f"ready_status={ready_body.get('status', 'unknown')}")

    print(f"export_http={export_response.status_code}")
    if export_response.status_code >= 400:
        print("dynamic_last_24h=unknown")
        print("dynamic_vs_limit=unknown")
        return 2

    try:
        export_items = export_response.json()
    except json.JSONDecodeError as exc:
        print(f"invalid JSON response: {exc}", file=sys.stderr)
        return 2

    if not isinstance(export_items, list):
        print("unexpected export format: expected JSON array", file=sys.stderr)
        return 2

    dynamic_count = _count_dynamic_last_24h(export_items, now=datetime.now(UTC))
    print(f"dynamic_last_24h={dynamic_count}")
    print(f"dynamic_limit={args.dynamic_limit}")
    print(f"dynamic_vs_limit={'ok' if dynamic_count <= args.dynamic_limit else 'over_limit'}")
    return exit_code if dynamic_count <= args.dynamic_limit else 2


if __name__ == "__main__":
    raise SystemExit(main())
