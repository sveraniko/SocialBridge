from wizard_bot.nav import routes


def _button(text: str, callback_data: str) -> dict:
    return {"text": text, "callback_data": callback_data}


def main_menu_keyboard() -> dict:
    return {
        "inline_keyboard": [
            [_button("Create Link", "nav:CREATE_LINK")],
            [_button("Campaigns", f"nav:{routes.CAMPAIGNS_LIST}")],
            [_button("Backup / Export", "ops:export")],
            [_button("Restore / Import", "ops:import")],
            [_button("Status", "ops:status")],
            [_button("Home", "act:clean")],
        ]
    }


def campaigns_keyboard(items: list[dict], offset: int, limit: int, total: int) -> dict:
    rows: list[list[dict]] = []
    for item in items:
        slug = str(item.get("slug") or "")
        ref = str(item.get("content_ref") or "-")
        label = slug or ref
        rows.append([_button(f"• {label[:45]}", f"camp:view:{slug or ref}")])

    nav_row: list[dict] = []
    if offset > 0:
        nav_row.append(_button("Prev", f"camp:page:{max(0, offset - limit)}"))
    if offset + len(items) < total:
        nav_row.append(_button("Next", f"camp:page:{offset + limit}"))
    if nav_row:
        rows.append(nav_row)

    rows.append([_button("Refresh", f"camp:page:{offset}")])
    rows.append([_button("Back", "act:back"), _button("Home", "act:clean")])
    return {"inline_keyboard": rows}


def campaign_view_keyboard(is_active: bool) -> dict:
    toggle_text = "Disable" if is_active else "Enable"
    toggle_action = "camp:disable" if is_active else "camp:enable"
    return {
        "inline_keyboard": [
            [_button(toggle_text, toggle_action), _button("Delete", "camp:delete")],
            [_button("Resolve Preview", "camp:preview")],
            [_button("Back to list", "act:back")],
            [_button("Main Menu", "nav:MAIN"), _button("Home", "act:clean")],
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


def result_keyboard(is_active: bool) -> dict:
    toggle_row = [_button("Disable campaign", "wiz:disable")] if is_active else [_button("Enable campaign", "wiz:enable")]
    secondary_row = [_button("Enable campaign", "wiz:enable")] if is_active else [_button("Disable campaign", "wiz:disable")]
    return {
        "inline_keyboard": [
            toggle_row,
            secondary_row,
            [_button("Resolve Preview", "wiz:preview")],
            [_button("Main Menu", "nav:MAIN"), _button("Home", "act:clean")],
        ]
    }
