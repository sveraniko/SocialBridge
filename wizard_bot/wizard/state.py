from __future__ import annotations

import json
import secrets


DEFAULT_STEP = "mode"


def session_key(chat_id: int) -> str:
    return f"wiz:chat:{chat_id}:session"


def default_session() -> dict:
    return {
        "step": DEFAULT_STEP,
        "history": [DEFAULT_STEP],
        "mode": None,
        "kind": None,
        "start_param": None,
        "slug": None,
        "slug_mode": "auto",
        "awaiting_input": None,
        "error": None,
        "created_item": None,
    }


def push_step_local(history: list[str], step: str) -> list[str]:
    if history and history[-1] == step:
        return history
    return [*history, step]


def back_step_local(history: list[str]) -> tuple[list[str], str]:
    if len(history) <= 1:
        return [DEFAULT_STEP], DEFAULT_STEP
    new_history = history[:-1]
    return new_history, new_history[-1]


def ensure_campaign_key(data: dict) -> str:
    if data.get("campaign_key"):
        return str(data["campaign_key"])
    start_param = data.get("start_param")
    if isinstance(start_param, str) and start_param:
        key = start_param.lower()
    elif isinstance(data.get("slug"), str) and data["slug"]:
        key = str(data["slug"])
    else:
        key = f"{data.get('kind', 'campaign')}-{secrets.token_hex(3)}"
    data["campaign_key"] = key
    return key


async def load_session(redis, chat_id: int) -> dict:
    raw = await redis.get(session_key(chat_id))
    if not raw:
        return default_session()
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return default_session()
    if not isinstance(parsed, dict):
        return default_session()
    base = default_session()
    base.update(parsed)
    history = base.get("history")
    if not isinstance(history, list) or not history:
        base["history"] = [DEFAULT_STEP]
    return base


async def save_session(redis, chat_id: int, data: dict) -> None:
    await redis.set(session_key(chat_id), json.dumps(data))


async def reset_session(redis, chat_id: int) -> dict:
    data = default_session()
    await save_session(redis, chat_id, data)
    return data


def apply_step(data: dict, step: str) -> dict:
    data["step"] = step
    data["history"] = push_step_local(list(data.get("history") or [DEFAULT_STEP]), step)
    data["awaiting_input"] = None
    data["error"] = None
    return data


def apply_back(data: dict) -> dict:
    new_history, step = back_step_local(list(data.get("history") or [DEFAULT_STEP]))
    data["history"] = new_history
    data["step"] = step
    data["awaiting_input"] = None
    data["error"] = None
    return data
