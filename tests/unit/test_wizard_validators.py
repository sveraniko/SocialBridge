from wizard_bot.wizard.validators import validate_slug, validate_start_param


def test_validate_start_param_product_ok():
    ok, value, err = validate_start_param("product", "DRESS001")
    assert ok is True
    assert value == "DRESS001"
    assert err is None


def test_validate_start_param_look_requires_prefix():
    ok, value, err = validate_start_param("look", "SPRING26")
    assert ok is False
    assert value is None
    assert err


def test_validate_slug_lowercase_only():
    ok, value, _ = validate_slug("Dress-001")
    assert ok is True
    assert value == "dress-001"
