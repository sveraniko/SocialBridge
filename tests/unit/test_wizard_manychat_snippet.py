"""Tests for ManyChat snippet generator."""
import pytest

from wizard_bot.ui.manychat import (
    build_manychat_snippet,
    mode1_trigger_text,
    _is_token_placeholder,
)


class TestMode2Snippet:
    """Tests for Mode 2 (Post/Story/Comment triggers)."""

    def test_mode2_body_has_empty_text(self) -> None:
        """Mode 2 body must include text:'' (no text input required)."""
        rendered = build_manychat_snippet(
            channel="ig",
            content_ref="campaign:dress001",
            url="https://sb.example/t/dress001",
            tg_url="https://t.me/sisbot?start=DRESS001",
            mode="2",
            kind="product",
        )
        # Body template must have empty text for Mode 2
        assert '"text":""' in rendered
        assert "TEMPLATE A" in rendered
        assert "Post/Story/Comment" in rendered

    def test_mode2_does_not_require_incoming_text(self) -> None:
        """Mode 2 primary template should NOT mention INCOMING_TEXT."""
        rendered = build_manychat_snippet(
            channel="ig",
            content_ref="campaign:dress001",
            url="https://sb.example/t/dress001",
            tg_url="https://t.me/sisbot?start=DRESS001",
            mode="2",
            kind="product",
        )
        # The primary Template A section should have empty text
        # Template B is shown as alternative and may have INCOMING_TEXT
        first_body = rendered.split('"text":""')[0]
        assert "INCOMING_TEXT" not in first_body


class TestMode1Snippet:
    """Tests for Mode 1 (Keyword DM triggers)."""

    def test_mode1_has_incoming_text_placeholder(self) -> None:
        """Mode 1 must include INCOMING_TEXT placeholder."""
        rendered = build_manychat_snippet(
            channel="ig",
            content_ref="",
            url="https://sb.example/t/catalog",
            tg_url="https://t.me/sisbot?start=",
            mode="1",
            kind="product",
            start_param="DRESS001",
        )
        assert "INCOMING_TEXT" in rendered
        assert "TEMPLATE B" in rendered
        assert "Keyword DM" in rendered

    def test_mode1_mentions_keywords(self) -> None:
        """Mode 1 should mention configured keywords."""
        rendered = build_manychat_snippet(
            channel="ig",
            content_ref="",
            url="https://sb.example/t/catalog",
            tg_url="https://t.me/sisbot?start=",
            mode="1",
            kind="product",
            start_param="CODE123",
            keyword_product="BUY",
            keyword_look="LOOK",
            keyword_catalog="CAT",
        )
        assert "BUY" in rendered
        assert "LOOK" in rendered
        assert "CAT" in rendered

    def test_mode1_trigger_text_product(self) -> None:
        """Trigger text for product should use KEYWORD_PRODUCT."""
        trigger = mode1_trigger_text("product", "DRESS001", "BUY", "LOOK", "CAT")
        assert trigger == "BUY DRESS001"

    def test_mode1_trigger_text_look(self) -> None:
        """Trigger text for look should use KEYWORD_LOOK."""
        trigger = mode1_trigger_text("look", "LK123456", "BUY", "LOOK", "CAT")
        assert trigger == "LOOK LK123456"

    def test_mode1_trigger_text_catalog(self) -> None:
        """Trigger text for catalog should use KEYWORD_CATALOG alone."""
        trigger = mode1_trigger_text("catalog", None, "BUY", "LOOK", "CAT")
        assert trigger == "CAT"


class TestMode0Snippet:
    """Tests for Mode 0 (Direct shortlink)."""

    def test_mode0_says_manychat_not_required(self) -> None:
        """Mode 0 should indicate ManyChat is not required."""
        rendered = build_manychat_snippet(
            channel="ig",
            content_ref="campaign:dress001",
            url="https://sb.example/t/dress001",
            tg_url="https://t.me/sisbot?start=DRESS001",
            mode="0",
            kind="product",
        )
        assert "ManyChat NOT required" in rendered
        assert "shortlink" in rendered.lower()


class TestResponseMapping:
    """Tests for response mapping (plain + JSONPath)."""

    def test_snippet_includes_plain_mapping(self) -> None:
        """Snippet should include plain field mapping."""
        rendered = build_manychat_snippet(
            channel="ig",
            content_ref="campaign:dress001",
            url="https://sb.example/t/dress001",
            tg_url="https://t.me/sisbot?start=DRESS001",
            mode="2",
        )
        assert "sb_last_url" in rendered
        assert "sb_tg_url" in rendered
        assert "sb_reply_text" in rendered
        # Plain mapping style
        assert "←  url" in rendered
        assert "←  tg_url" in rendered
        assert "←  reply_text" in rendered

    def test_snippet_includes_jsonpath_mapping(self) -> None:
        """Snippet should include JSONPath mapping variant."""
        rendered = build_manychat_snippet(
            channel="ig",
            content_ref="campaign:dress001",
            url="https://sb.example/t/dress001",
            tg_url="https://t.me/sisbot?start=DRESS001",
            mode="2",
        )
        assert "$.url" in rendered
        assert "$.tg_url" in rendered
        assert "$.reply_text" in rendered
        assert "JSONPath" in rendered


class TestTokenWarning:
    """Tests for token placeholder warnings."""

    def test_placeholder_token_shows_warning(self) -> None:
        """Placeholder tokens should trigger warning."""
        rendered = build_manychat_snippet(
            channel="ig",
            content_ref="campaign:dress001",
            url="https://sb.example/t/dress001",
            tg_url="https://t.me/sisbot?start=DRESS001",
            mc_token="change-me-mc",
            mode="2",
        )
        assert "WARNING" in rendered
        assert "MC_TOKEN" in rendered

    def test_valid_token_no_warning(self) -> None:
        """Valid tokens should not trigger warning."""
        rendered = build_manychat_snippet(
            channel="ig",
            content_ref="campaign:dress001",
            url="https://sb.example/t/dress001",
            tg_url="https://t.me/sisbot?start=DRESS001",
            mc_token="real_production_token_abc123",
            mode="2",
        )
        assert "WARNING" not in rendered

    @pytest.mark.parametrize(
        "token,expected",
        [
            ("change-me-mc", True),
            ("<YOUR_MC_TOKEN>", True),
            ("<set in env>", True),
            ("placeholder_token", True),
            ("real_token_abc123", False),
            ("prod_mc_token_xyz", False),
        ],
    )
    def test_is_token_placeholder(self, token: str, expected: bool) -> None:
        """Test token placeholder detection."""
        assert _is_token_placeholder(token) == expected


class TestLegacyCompatibility:
    """Tests to ensure backward compatibility with existing assertions."""

    def test_manychat_snippet_contains_content_ref_and_urls(self) -> None:
        """Original test - ensure basic fields are present."""
        rendered = build_manychat_snippet(
            channel="ig",
            content_ref="campaign:dress001",
            url="https://public.example/t/dress001",
            tg_url="https://t.me/sisbot?start=DRESS001",
        )
        # Channel and content_ref in header
        assert "ig" in rendered
        assert "campaign:dress001" in rendered
        # Mapping fields present
        assert "sb_last_url" in rendered
        assert "sb_tg_url" in rendered
        # Preview URLs
        assert "https://public.example/t/dress001" in rendered
        assert "https://t.me/sisbot?start=DRESS001" in rendered
