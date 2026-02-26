#!/usr/bin/env python3
"""Import content map records via admin API."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import httpx


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import content map seed file into SocialBridge admin API")
    parser.add_argument("--base-url", required=True, help="Base API URL, e.g. http://localhost:8000")
    parser.add_argument("--token", required=True, help="Admin token for X-Admin-Token")
    parser.add_argument("--file", required=True, help="Path to seed JSON file")
    return parser.parse_args()


def load_payload(path: Path) -> object:
    with path.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get("items"), list):
        return payload

    raise ValueError("seed file must contain a JSON array or an object with items[]")


def main() -> int:
    args = parse_args()
    seed_path = Path(args.file)

    try:
        payload = load_payload(seed_path)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    endpoint = f"{args.base_url.rstrip('/')}/v1/admin/content-map/import"
    headers = {"X-Admin-Token": args.token}

    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.post(endpoint, json=payload, headers=headers)
    except httpx.HTTPError as exc:
        print(f"request failed: {exc}", file=sys.stderr)
        return 2

    if response.status_code >= 400:
        print(f"request failed with HTTP {response.status_code}", file=sys.stderr)
        print(response.text)
        return 2

    body = response.json()
    created = int(body.get("created", 0))
    updated = int(body.get("updated", 0))
    failed = int(body.get("failed", 0))

    print(f"created={created}")
    print(f"updated={updated}")
    print(f"failed={failed}")

    errors = body.get("errors") or []
    if errors:
        print("errors:")
        for item in errors:
            print(json.dumps(item, ensure_ascii=False))

    return 0 if failed == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
