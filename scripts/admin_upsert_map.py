#!/usr/bin/env python3
"""Upsert a single content map record via admin API."""

from __future__ import annotations

import argparse
import json
import sys

import httpx


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Upsert one content map item")
    parser.add_argument("--base-url", required=True, help="Base API URL, e.g. http://localhost:8000")
    parser.add_argument("--token", required=True, help="Admin token for X-Admin-Token")
    parser.add_argument("--channel", required=True)
    parser.add_argument("--content-ref", required=True)
    parser.add_argument("--slug", default=None)
    parser.add_argument("--start-param", default=None)
    parser.add_argument("--inactive", action="store_true", help="Set is_active=false")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    endpoint = f"{args.base_url.rstrip('/')}/v1/admin/content-map/upsert"

    payload = {
        "channel": args.channel,
        "content_ref": args.content_ref,
        "is_active": not args.inactive,
    }
    if args.slug is not None:
        payload["slug"] = args.slug
    if args.start_param is not None:
        payload["start_param"] = args.start_param

    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.post(endpoint, json=payload, headers={"X-Admin-Token": args.token})
    except httpx.HTTPError as exc:
        print(f"request failed: {exc}", file=sys.stderr)
        return 2

    if response.status_code >= 400:
        print(f"request failed with HTTP {response.status_code}", file=sys.stderr)
        print(response.text)
        return 2

    print(json.dumps(response.json(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
