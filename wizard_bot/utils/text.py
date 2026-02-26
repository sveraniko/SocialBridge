
def truncate(value: str, limit: int = 64) -> str:
    if len(value) <= limit:
        return value
    return f"{value[: limit - 1]}…"
