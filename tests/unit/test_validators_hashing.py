from app.adapters.hashing import payload_hash
from app.domain.validators import parse_start_param_from_text


def test_payload_hash_is_stable():
    left = payload_hash({"b": 2, "a": 1})
    right = payload_hash({"a": 1, "b": 2})
    assert left == right


def test_parse_start_param_priority():
    assert parse_start_param_from_text("please LOOK_ABC") == "LOOK_ABC"
    assert parse_start_param_from_text("x prod_123") == "prod_123"
    assert parse_start_param_from_text("buy CODE99") == "CODE99"
