#!/usr/bin/env python3
"""Convert campaign registry CSV to content-map import JSON."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

ALLOWED_KINDS = {"product", "look", "catalog"}
SLUG_RE = re.compile(r"^[a-z0-9_-]{1,64}$")
START_PARAM_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
CAMPAIGN_KEY_RE = re.compile(r"^campaign:[a-z0-9_\-]+$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert campaign registry CSV to content-map JSON array")
    parser.add_argument("--in", dest="in_path", required=True, help="Input campaign registry CSV")
    parser.add_argument("--out", dest="out_path", required=True, help="Output JSON path")
    return parser.parse_args()


def _clean(row: dict[str, str], key: str) -> str:
    return (row.get(key) or "").strip()


def validate_row(row: dict[str, str], line_no: int) -> list[str]:
    errors: list[str] = []

    campaign_key = _clean(row, "campaign_key")
    start_param = _clean(row, "start_param")
    slug = _clean(row, "slug")
    kind = _clean(row, "kind")

    if not campaign_key:
        errors.append(f"line {line_no}: campaign_key is required")
    elif not CAMPAIGN_KEY_RE.match(campaign_key):
        errors.append(f"line {line_no}: campaign_key must start with 'campaign:' and use [a-z0-9_-]")

    if not slug:
        errors.append(f"line {line_no}: slug is required")
    elif not SLUG_RE.match(slug):
        errors.append(f"line {line_no}: slug must match [a-z0-9_-], lowercase, len<=64")
    elif len(slug) > 32:
        errors.append(f"line {line_no}: slug len>32 is discouraged; keep <=32")

    if start_param:
        if not START_PARAM_RE.match(start_param):
            errors.append(f"line {line_no}: start_param must match [A-Za-z0-9_-], len<=64")
    elif kind != "catalog":
        errors.append(f"line {line_no}: start_param required for non-catalog kind")

    if kind not in ALLOWED_KINDS:
        errors.append(f"line {line_no}: kind must be one of product|look|catalog")

    return errors


def row_to_item(row: dict[str, str]) -> dict[str, object]:
    campaign_key = _clean(row, "campaign_key")
    start_param = _clean(row, "start_param")
    slug = _clean(row, "slug")
    kind = _clean(row, "kind")
    notes = _clean(row, "notes")
    post_url = _clean(row, "post_url")
    flow_name = _clean(row, "flow_name")

    item: dict[str, object] = {
        "channel": "ig",
        "content_ref": campaign_key,
        "slug": slug,
        "start_param": start_param or None,
        "meta": {
            "kind": kind,
            "notes": notes or None,
            "post_url": post_url or None,
            "flow_name": flow_name or None,
        },
    }
    return item


def convert_csv(path: Path) -> list[dict[str, object]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        required_columns = {
            "campaign_key",
            "start_param",
            "slug",
            "kind",
            "notes",
            "post_url",
            "flow_name",
        }
        missing = required_columns.difference(reader.fieldnames or [])
        if missing:
            missing_cols = ", ".join(sorted(missing))
            raise ValueError(f"CSV missing required columns: {missing_cols}")

        items: list[dict[str, object]] = []
        errors: list[str] = []
        for idx, row in enumerate(reader, start=2):
            if not any((v or "").strip() for v in row.values()):
                continue
            row_errors = validate_row(row, idx)
            if row_errors:
                errors.extend(row_errors)
                continue
            items.append(row_to_item(row))

    if errors:
        raise ValueError("\n".join(errors))

    return items


def main() -> int:
    args = parse_args()
    in_path = Path(args.in_path)
    out_path = Path(args.out_path)

    try:
        items = convert_csv(in_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
            f.write("\n")
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(f"written {len(items)} items to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
