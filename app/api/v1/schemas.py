from pydantic import BaseModel


class ResolveResponse(BaseModel):
    reply_text: str
    url: str
    tg_url: str
    start_param: str | None
    slug: str
    tag: str | None
    result: str
