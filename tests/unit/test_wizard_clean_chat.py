from wizard_bot.ui.clean_chat import normalize_message_ids


def test_normalize_message_ids_filters_invalid_values():
    values = ["10", "x", "11", "", "10"]
    assert normalize_message_ids(values) == [10, 11]
