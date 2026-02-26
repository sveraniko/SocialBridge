import hashlib
import json


def canonical_json(data: dict) -> str:
    return json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def payload_hash(data: dict) -> str:
    return hashlib.sha256(canonical_json(data).encode("utf-8")).hexdigest()


def ip_hash(value: str, salt: str) -> str:
    return hashlib.sha256(f"{value}:{salt}".encode("utf-8")).hexdigest()
