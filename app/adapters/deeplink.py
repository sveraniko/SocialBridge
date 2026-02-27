def build_tg_deeplink(bot_username: str, start_param: str | None) -> str:
    base = f"https://t.me/{bot_username}"
    return base if not start_param else f"{base}?start={start_param}"
