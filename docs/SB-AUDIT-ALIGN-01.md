# SB-AUDIT-ALIGN-01 — Alignment report

## Mismatches found and fixes
- **Pagination contract drift**: `/v1/admin/content-map` now matches documented defaults/limits (`is_active=true`, `limit=200`, `max=1000`) in code, plus tests for default/max boundaries.
- **Upsert response drift**: `/v1/admin/content-map/upsert` now returns `{item, result}` where `result` is `created|updated`.
- **Export filter drift**: `/v1/admin/content-map/export` now supports `channel` and `is_active` filters end-to-end.
- **Error contract drift**: manual 400/409 endpoint responses were aligned to unified error payload with `request_id` and no `detail` shape leakage.
- **Operational guardrail gap**: added `DYNAMIC_MAPPING_MAX_PER_DAY` (default `500`), with safe degradation to `fallback_catalog` when limit is reached and warning log entry.
- **Runbook drift**: deploy/manychat docs now reference real compose services (`api`, `postgres`) and include dynamic mapping retention/ops cleanup note.

## Decision notes (code vs docs)
- For pagination defaults and upsert shape, **code was changed to match docs** because behavior is explicit in API contracts and low-risk to align.
- For export filters, **code was implemented** (instead of removing from docs) because change is small and directly useful for operators.

## Validation status
- **pytest**: not executable in this environment (missing Python deps and blocked package index/proxy), see command log in delivery notes.
- **docker compose quick-start**: could not be fully validated in this environment because `docker` binary is unavailable (`command not found`). Commands in docs were aligned to actual compose service names from repository config.
