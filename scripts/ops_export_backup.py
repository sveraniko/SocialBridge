#!/usr/bin/env python3
"""Export content-map records to a timestamped backup JSON file."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import httpx


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export content-map backup from admin API")
    parser.add_argument("--base-url", required=True, help="Base API URL, e.g. http://localhost:8000")
    parser.add_argument("--token", required=True, help="Admin token for X-Admin-Token")
    parser.add_argument("--channel", default=None, help="Optional channel filter")
    parser.add_argument(
        "--is-active",
        choices=("true", "false", "all"),
        default="all",
        help="Filter by active flag (default: all)",
    )
    parser.add_argument("--out-dir", default="backups", help="Directory to store backup file")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    endpoint = f"{args.base_url.rstrip('/')}/v1/admin/content-map/export"
    params: dict[str, str] = {}
    if args.channel:
        params["channel"] = args.channel
    if args.is_active != "all":
        params["is_active"] = args.is_active

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(endpoint, params=params, headers={"X-Admin-Token": args.token})
    except httpx.HTTPError as exc:
        print(f"request failed: {exc}", file=sys.stderr)
        return 2

    if response.status_code >= 400:
        print(f"request failed with HTTP {response.status_code}", file=sys.stderr)
        print(response.text)
        return 2

    try:
        items = response.json()
    except json.JSONDecodeError as exc:
        print(f"invalid JSON response: {exc}", file=sys.stderr)
        return 2

    if not isinstance(items, list):
        print("unexpected export format: expected JSON array", file=sys.stderr)
        return 2

    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    channel_part = args.channel or "all"
    active_part = args.is_active
    out_path = out_dir / f"content_map_backup_{channel_part}_{active_part}_{timestamp}.json"
    out_path.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"exported={len(items)}")
    print(f"file={out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
