from wizard_bot.ui.manychat import build_manychat_snippet


def test_manychat_snippet_contains_content_ref_and_urls() -> None:
    rendered = build_manychat_snippet(
        channel="ig",
        content_ref="campaign:dress001",
        url="https://public.example/t/dress001",
        tg_url="https://t.me/sisbot?start=DRESS001",
    )

    assert "sb_content_ref=campaign:dress001" in rendered
    assert "sb_last_url <- url" in rendered
    assert "sb_tg_url <- tg_url" in rendered
    assert "Preview url: https://public.example/t/dress001" in rendered
    assert "Preview tg_url: https://t.me/sisbot?start=DRESS001" in rendered
