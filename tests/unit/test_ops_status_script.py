from datetime import UTC, datetime, timedelta
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import SimpleNamespace
import sys


SCRIPT_PATH = Path("scripts/ops_status.py")


def _load_module():
    spec = spec_from_file_location("ops_status", SCRIPT_PATH)
    module = module_from_spec(spec)
    assert spec and spec.loader
    sys.modules.setdefault("httpx", SimpleNamespace(HTTPError=Exception, Client=object))
    spec.loader.exec_module(module)
    return module


def test_parse_iso8601_supports_z_suffix():
    module = _load_module()
    value = module._parse_iso8601("2026-01-01T10:00:00Z")
    assert value == datetime(2026, 1, 1, 10, 0, tzinfo=UTC)


def test_count_dynamic_last_24h_filters_meta_and_time():
    module = _load_module()
    now = datetime(2026, 1, 2, 12, 0, tzinfo=UTC)
    items = [
        {"meta": {"dynamic": True}, "created_at": (now - timedelta(hours=2)).isoformat()},
        {"meta": {"dynamic": True}, "created_at": (now - timedelta(hours=30)).isoformat()},
        {"meta": {"dynamic": False}, "created_at": (now - timedelta(hours=1)).isoformat()},
    ]

    assert module._count_dynamic_last_24h(items, now=now) == 1
