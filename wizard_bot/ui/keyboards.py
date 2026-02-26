from wizard_bot.nav import routes


def _button(text: str, callback_data: str) -> dict:
    return {"text": text, "callback_data": callback_data}


def main_menu_keyboard() -> dict:
    return {
        "inline_keyboard": [
            [_button("Campaigns", f"nav:{routes.CAMPAIGNS_LIST}")],
            [_button("Clean Chat", "act:clean")],
        ]
    }


def campaigns_keyboard() -> dict:
    return {
        "inline_keyboard": [
            [_button("Refresh", "act:refresh_campaigns")],
            [_button("Back", "act:back"), _button("Clean Chat", "act:clean")],
        ]
    }
