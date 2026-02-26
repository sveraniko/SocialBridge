def build_shortlink(base_url: str, slug: str) -> str:
    return f"{base_url.rstrip('/')}/t/{slug}"
