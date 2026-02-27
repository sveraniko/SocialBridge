from wizard_bot.ui.manychat import mode1_trigger_text


def test_mode1_copy_generation_uses_keyword_by_kind():
    assert mode1_trigger_text("product", "BOIZMRJS", "BUY", "LOOK", "CAT") == "BUY BOIZMRJS"
    assert mode1_trigger_text("look", "SPRING26", "BUY", "LOOK", "CAT") == "LOOK SPRING26"
    assert mode1_trigger_text("catalog", None, "BUY", "LOOK", "CAT") == "CAT"
