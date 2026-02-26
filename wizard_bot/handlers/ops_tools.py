from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta

import httpx


def parse_import_payload(content: bytes) -> list[dict]:
    try:
        decoded = json.loads(content.decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise ValueError("Invalid JSON document") from exc

    if isinstance(decoded, list):
        return [item for item in decoded if isinstance(item, dict)]
    if isinstance(decoded, dict) and isinstance(decoded.get("items"), list):
        return [item for item in decoded["items"] if isinstance(item, dict)]
    raise ValueError("JSON must be an array or an object with items[]")


def summarize_import_result(result: dict) -> str:
    lines = [
        "Import completed",
        f"• created: {int(result.get('created', 0))}",
        f"• updated: {int(result.get('updated', 0))}",
        f"• failed: {int(result.get('failed', 0))}",
    ]
    errors = result.get("errors") if isinstance(result.get("errors"), list) else []
    if errors:
        lines.append("")
        lines.append("Errors (first 5):")
        for err in errors[:5]:
            if not isinstance(err, dict):
                continue
            index = err.get("index", "?")
            code = str(err.get("code") or "unknown")[:40]
            message = str(err.get("message") or "-")[:120]
            field = str(err.get("field") or "-")[:40]
            lines.append(f"• #{index} {code}: {message} [field={field}]")
    return "\n".join(lines)


async def run_sb_call(call: Callable[[], Awaitable], default_message: str) -> tuple[object | None, str | None]:
    try:
        return await call(), None
    except httpx.HTTPStatusError as exc:
        message = default_message
        try:
            payload = exc.response.json()
            if isinstance(payload, dict):
                error = payload.get("error")
                if isinstance(error, dict) and error.get("message"):
                    message = str(error.get("message"))
        except Exception:  # noqa: BLE001
            pass
        return None, message


def build_status_text(
    health_ok: bool,
    ready_ok: bool,
    total_campaigns: int,
    dynamic_24h_count: int,
    dynamic_limit: str,
) -> str:
    return "\n".join(
        [
            "Status",
            "",
            f"• /health: {'200' if health_ok else '503'}",
            f"• /ready: {'200' if ready_ok else '503'}",
            f"• campaigns total: {total_campaigns}",
            f"• dyn mappings (24h): {dynamic_24h_count}",
            f"• dyn limit/day: {dynamic_limit}",
        ]
    )


def count_recent_dynamic(items: list[dict], now: datetime | None = None) -> int:
    reference = now or datetime.now(UTC)
    floor = reference - timedelta(hours=24)
    total = 0
    for item in items:
        if not isinstance(item, dict):
            continue
        content_ref = str(item.get("content_ref") or "")
        created_raw = str(item.get("created_at") or "")
        if not content_ref.startswith("dyn:"):
            continue
        try:
            created_at = datetime.fromisoformat(created_raw.replace("Z", "+00:00"))
        except ValueError:
            continue
        if created_at >= floor:
            total += 1
    return total
