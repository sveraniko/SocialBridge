from __future__ import annotations

import json


def stack_key(chat_id: int) -> str:
    return f"wiz:chat:{chat_id}:stack"


def push_local(stack: list[str], route: str) -> list[str]:
    if stack and stack[-1] == route:
        return stack
    return [*stack, route]


def pop_local(stack: list[str], fallback: str) -> tuple[list[str], str]:
    if not stack:
        return [fallback], fallback
    if len(stack) == 1:
        return stack, stack[-1]
    new_stack = stack[:-1]
    return new_stack, new_stack[-1]


async def load_stack(redis, chat_id: int, fallback: str) -> list[str]:
    raw = await redis.get(stack_key(chat_id))
    if not raw:
        return [fallback]
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return [fallback]
    if not isinstance(value, list) or not value:
        return [fallback]
    return [str(item) for item in value]


async def save_stack(redis, chat_id: int, stack: list[str]) -> None:
    await redis.set(stack_key(chat_id), json.dumps(stack))


async def push_route(redis, chat_id: int, route: str, fallback: str) -> str:
    stack = await load_stack(redis, chat_id, fallback)
    new_stack = push_local(stack, route)
    await save_stack(redis, chat_id, new_stack)
    return new_stack[-1]


async def pop_route(redis, chat_id: int, fallback: str) -> str:
    stack = await load_stack(redis, chat_id, fallback)
    new_stack, active = pop_local(stack, fallback)
    await save_stack(redis, chat_id, new_stack)
    return active


async def reset_stack(redis, chat_id: int, route: str) -> str:
    await save_stack(redis, chat_id, [route])
    return route


async def current_route(redis, chat_id: int, fallback: str) -> str:
    stack = await load_stack(redis, chat_id, fallback)
    return stack[-1]
