from app.domain.validators import parse_keyword_payload


def test_parse_keyword_product_payload():
    start_param, result = parse_keyword_payload(
        "BUY BOIZMRJS",
        keyword_product="BUY",
        keyword_look="LOOK",
        keyword_catalog="CAT",
    )
    assert start_param == "BOIZMRJS"
    assert result == "fallback_payload"


def test_parse_keyword_look_payload_prefixes_when_needed():
    # SIS uses LOOK: prefix (colon) not LOOK_ (underscore)
    start_param, result = parse_keyword_payload(
        "LOOK Look001",
        keyword_product="BUY",
        keyword_look="LOOK",
        keyword_catalog="CAT",
    )
    assert start_param == "LOOK:Look001"
    assert result == "fallback_payload"


def test_parse_keyword_catalog_payload_no_code():
    start_param, result = parse_keyword_payload(
        "CAT",
        keyword_product="BUY",
        keyword_look="LOOK",
        keyword_catalog="CAT",
    )
    assert start_param is None
    assert result == "fallback_catalog"
