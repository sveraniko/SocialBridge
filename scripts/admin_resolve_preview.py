#!/usr/bin/env python3
"""Preview resolve output via admin API."""

from __future__ import annotations

import argparse
import json
import sys

import httpx


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Call /v1/admin/resolve-preview")
    parser.add_argument("--base-url", required=True, help="Base API URL, e.g. http://localhost:8000")
    parser.add_argument("--token", required=True, help="Admin token for X-Admin-Token")
    parser.add_argument("--channel", required=True)
    parser.add_argument("--content-ref", required=False, default=None)
    parser.add_argument("--text", required=False, default="")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    endpoint = f"{args.base_url.rstrip('/')}/v1/admin/resolve-preview"
    payload = {
        "channel": args.channel,
        "content_ref": args.content_ref,
        "text": args.text,
    }

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
