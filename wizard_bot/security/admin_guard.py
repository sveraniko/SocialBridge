from __future__ import annotations


UNAUTHORIZED_TEXT = "Access denied. Your Telegram user is not allowed to use this bot."


def is_admin(user_id: int | None, allowed_admin_ids: set[int]) -> bool:
    return user_id is not None and user_id in allowed_admin_ids


def extract_user_id(update: dict) -> int | None:
    message = update.get("message")
    if isinstance(message, dict):
        from_user = message.get("from") or {}
        return from_user.get("id")
    callback_query = update.get("callback_query")
    if isinstance(callback_query, dict):
        from_user = callback_query.get("from") or {}
        return from_user.get("id")
    return None
