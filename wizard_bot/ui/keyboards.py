from wizard_bot.nav import routes


def _button(text: str, callback_data: str) -> dict:
    return {"text": text, "callback_data": callback_data}


def main_menu_keyboard() -> dict:
    return {
        "inline_keyboard": [
            [_button("Create Link", "nav:CREATE_LINK")],
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


def kind_keyboard() -> dict:
    return {
        "inline_keyboard": [
            [_button("Product", "wiz:kind:product")],
            [_button("Look", "wiz:kind:look")],
            [_button("Catalog", "wiz:kind:catalog")],
            [_button("Back", "act:back"), _button("Cancel", "nav:MAIN")],
        ]
    }


def step_back_cancel_keyboard(skip: bool) -> dict:
    rows = [[_button("Back", "act:back"), _button("Cancel", "nav:MAIN")]]
    if skip:
        rows.insert(0, [_button("Skip", "wiz:slug:skip")])
    return {"inline_keyboard": rows}


def slug_choice_keyboard() -> dict:
    return {
        "inline_keyboard": [
            [_button("Auto", "wiz:slug:auto"), _button("Custom", "wiz:slug:custom")],
            [_button("Skip", "wiz:slug:skip")],
            [_button("Back", "act:back"), _button("Cancel", "nav:MAIN")],
        ]
    }


def result_keyboard() -> dict:
    return {
        "inline_keyboard": [
            [_button("Disable campaign", "wiz:disable")],
            [_button("Resolve Preview", "wiz:preview")],
            [_button("Main Menu", "nav:MAIN"), _button("Clean Chat", "act:clean")],
        ]
    }
