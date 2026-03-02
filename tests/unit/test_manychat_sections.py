"""Tests for ManyChat section renderers (compact UI)."""
import pytest

from wizard_bot.ui.manychat_sections import (
    ManyChatContext,
    render_pack_summary,
    render_template_a,
    render_template_b,
    render_fields,
    render_trigger,
    render_request,
    render_mapping,
    render_send,
    render_keywords,
    render_section,
    get_section_keyboard,
    build_pack_keyboard,
    is_token_placeholder,
    get_safe_token,
)


@pytest.fixture
def sample_ctx() -> ManyChatContext:
    """Sample context for testing."""
    return ManyChatContext(
        slug="dress001",
        channel="ig",
        content_ref="campaign:dress001",
        url="https://sb.example/t/dress001",
        tg_url="https://t.me/sisbot?start=DRESS001",
        mc_resolve_url="https://api.example.com/v1/mc/resolve",
        mc_token="real_production_token",
        mode="2",
        kind="product",
        start_param="DRESS001",
        keyword_product="BUY",
        keyword_look="LOOK",
        keyword_catalog="CAT",
    )


class TestPackSummary:
    """Tests for compact pack summary."""

    def test_summary_contains_mode_and_kind(self, sample_ctx: ManyChatContext) -> None:
        """Summary must show mode and kind."""
        rendered = render_pack_summary(sample_ctx)
        assert "Mode: 2" in rendered
        assert "Kind: product" in rendered

    def test_summary_contains_channel_and_ref(self, sample_ctx: ManyChatContext) -> None:
        """Summary must show channel and content_ref."""
        rendered = render_pack_summary(sample_ctx)
        assert "Channel: ig" in rendered
        assert "campaign:dress001" in rendered

    def test_summary_contains_urls(self, sample_ctx: ManyChatContext) -> None:
        """Summary must show both URLs."""
        rendered = render_pack_summary(sample_ctx)
        assert "https://sb.example/t/dress001" in rendered
        assert "https://t.me/sisbot?start=DRESS001" in rendered

    def test_summary_shows_token_configured(self, sample_ctx: ManyChatContext) -> None:
        """Summary shows token configured status."""
        rendered = render_pack_summary(sample_ctx)
        assert "✅ configured" in rendered

    def test_summary_shows_token_placeholder_warning(self) -> None:
        """Summary warns when token is placeholder."""
        ctx = ManyChatContext(
            slug="test",
            channel="ig",
            content_ref="campaign:test",
            url="https://sb.example/t/test",
            tg_url="https://t.me/bot?start=TEST",
            mc_resolve_url="https://api.example.com/v1/mc/resolve",
            mc_token="change-me-mc",
            mode="2",
            kind="product",
            start_param="TEST",
            keyword_product="BUY",
            keyword_look="LOOK",
            keyword_catalog="CAT",
        )
        rendered = render_pack_summary(ctx)
        assert "⚠️ placeholder" in rendered
        assert "MC_TOKEN" in rendered


class TestTemplateA:
    """Tests for Template A (Mode 2)."""

    def test_template_a_has_empty_text_body(self, sample_ctx: ManyChatContext) -> None:
        """Template A body must have empty text field."""
        rendered = render_template_a(sample_ctx)
        assert '"text":""' in rendered

    def test_template_a_shows_channel_and_ref(self, sample_ctx: ManyChatContext) -> None:
        """Template A shows prefill values."""
        rendered = render_template_a(sample_ctx)
        assert "sb_channel = ig" in rendered
        assert "sb_content_ref = campaign:dress001" in rendered

    def test_template_a_shows_url(self, sample_ctx: ManyChatContext) -> None:
        """Template A shows resolve URL."""
        rendered = render_template_a(sample_ctx)
        assert "https://api.example.com/v1/mc/resolve" in rendered


class TestTemplateB:
    """Tests for Template B (Mode 1)."""

    def test_template_b_has_incoming_text(self, sample_ctx: ManyChatContext) -> None:
        """Template B body must have INCOMING_TEXT placeholder."""
        rendered = render_template_b(sample_ctx)
        assert "INCOMING_TEXT" in rendered

    def test_template_b_mentions_replace_warning(self, sample_ctx: ManyChatContext) -> None:
        """Template B warns to replace INCOMING_TEXT."""
        rendered = render_template_b(sample_ctx)
        assert "Replace INCOMING_TEXT" in rendered

    def test_template_b_shows_keyword_example(self, sample_ctx: ManyChatContext) -> None:
        """Template B shows keyword example."""
        rendered = render_template_b(sample_ctx)
        # Product kind should show BUY keyword
        assert "BUY" in rendered


class TestMapping:
    """Tests for response mapping section."""

    def test_mapping_includes_plain_style(self, sample_ctx: ManyChatContext) -> None:
        """Mapping shows plain field names."""
        rendered = render_mapping(sample_ctx)
        assert "sb_last_url" in rendered
        assert "←  url" in rendered

    def test_mapping_includes_jsonpath_style(self, sample_ctx: ManyChatContext) -> None:
        """Mapping shows JSONPath style."""
        rendered = render_mapping(sample_ctx)
        assert "$.url" in rendered
        assert "$.tg_url" in rendered
        assert "$.reply_text" in rendered


class TestTokenHandling:
    """Tests for token placeholder handling."""

    @pytest.mark.parametrize(
        "token,expected",
        [
            ("change-me-mc", True),
            ("<YOUR_MC_TOKEN>", True),
            ("<set in env>", True),
            ("placeholder_token", True),
            ("", True),
            ("real_token_abc123", False),
            ("prod_mc_token_xyz", False),
        ],
    )
    def test_is_token_placeholder(self, token: str, expected: bool) -> None:
        """Test token placeholder detection."""
        assert is_token_placeholder(token) == expected

    def test_get_safe_token_hides_placeholder(self) -> None:
        """Placeholder tokens should be replaced with <SET_ME>."""
        assert get_safe_token("change-me") == "<SET_ME>"
        assert get_safe_token("") == "<SET_ME>"

    def test_get_safe_token_shows_real_token(self) -> None:
        """Real tokens should be shown as-is."""
        assert get_safe_token("real_token_abc") == "real_token_abc"

    def test_request_section_shows_set_me_for_placeholder(self) -> None:
        """External request section shows <SET_ME> for placeholder token."""
        ctx = ManyChatContext(
            slug="test",
            channel="ig",
            content_ref="campaign:test",
            url="https://sb.example/t/test",
            tg_url="https://t.me/bot?start=TEST",
            mc_resolve_url="https://api.example.com/v1/mc/resolve",
            mc_token="change-me-mc",
            mode="2",
            kind="product",
            start_param="TEST",
            keyword_product="BUY",
            keyword_look="LOOK",
            keyword_catalog="CAT",
        )
        rendered = render_request(ctx)
        assert "<SET_ME>" in rendered
        assert "change-me-mc" not in rendered


class TestKeyboards:
    """Tests for keyboard builders."""

    def test_pack_keyboard_has_section_buttons(self, sample_ctx: ManyChatContext) -> None:
        """Pack keyboard has all section buttons."""
        kb = build_pack_keyboard(sample_ctx, "dress001")
        buttons = [btn["text"] for row in kb["inline_keyboard"] for btn in row]
        assert any("Template A" in btn for btn in buttons)
        assert any("Template B" in btn for btn in buttons)
        assert any("Fields" in btn for btn in buttons)
        assert any("Request" in btn for btn in buttons)
        assert any("Trigger" in btn for btn in buttons)
        assert any("Mapping" in btn for btn in buttons)
        assert any("Back" in btn for btn in buttons)
        assert any("Home" in btn for btn in buttons)

    def test_pack_keyboard_marks_optional_template(self) -> None:
        """Pack keyboard marks non-primary template as optional."""
        # Mode 2: Template B should be marked optional
        ctx = ManyChatContext(
            slug="test", channel="ig", content_ref="campaign:test",
            url="https://sb.example/t/test", tg_url="https://t.me/bot?start=TEST",
            mc_resolve_url="https://api.example.com/v1/mc/resolve",
            mc_token="token", mode="2", kind="product", start_param="TEST",
            keyword_product="BUY", keyword_look="LOOK", keyword_catalog="CAT",
        )
        kb = build_pack_keyboard(ctx, "test")
        buttons = [btn["text"] for row in kb["inline_keyboard"] for btn in row]
        assert any("Template B (opt)" in btn for btn in buttons)

        # Mode 1: Template A should be marked optional
        ctx.mode = "1"
        kb = build_pack_keyboard(ctx, "test")
        buttons = [btn["text"] for row in kb["inline_keyboard"] for btn in row]
        assert any("Template A (opt)" in btn for btn in buttons)


class TestSectionDispatcher:
    """Tests for section rendering dispatcher."""

    def test_render_section_pack(self, sample_ctx: ManyChatContext) -> None:
        """render_section('pack') returns summary."""
        rendered = render_section(sample_ctx, "pack")
        assert "ManyChat Integration Pack" in rendered

    def test_render_section_tpl_a(self, sample_ctx: ManyChatContext) -> None:
        """render_section('tpl_a') returns Template A."""
        rendered = render_section(sample_ctx, "tpl_a")
        assert "TEMPLATE A" in rendered
        assert '"text":""' in rendered

    def test_render_section_tpl_b(self, sample_ctx: ManyChatContext) -> None:
        """render_section('tpl_b') returns Template B."""
        rendered = render_section(sample_ctx, "tpl_b")
        assert "TEMPLATE B" in rendered
        assert "INCOMING_TEXT" in rendered

    def test_render_section_unknown_falls_back_to_pack(self, sample_ctx: ManyChatContext) -> None:
        """Unknown section falls back to pack summary."""
        rendered = render_section(sample_ctx, "unknown")  # type: ignore
        assert "ManyChat Integration Pack" in rendered
