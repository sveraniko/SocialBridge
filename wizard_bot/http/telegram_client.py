from __future__ import annotations

import httpx


class TelegramClient:
    def __init__(self, token: str):
        self._token = token
        self._client = httpx.AsyncClient(base_url=f"https://api.telegram.org/bot{token}", timeout=30)

    async def close(self) -> None:
        await self._client.aclose()

    async def get_updates(self, offset: int | None, timeout: int) -> list[dict]:
        payload: dict[str, int] = {"timeout": timeout}
        if offset is not None:
            payload["offset"] = offset
        response = await self._client.post("/getUpdates", json=payload)
        response.raise_for_status()
        body = response.json()
        return body.get("result", [])

    async def send_message(
        self,
        chat_id: int,
        text: str,
        parse_mode: str | None = None,
        disable_web_page_preview: bool | None = None,
        reply_markup: dict | None = None,
    ) -> dict:
        payload: dict[str, object] = {"chat_id": chat_id, "text": text}
        if parse_mode:
            payload["parse_mode"] = parse_mode
        if disable_web_page_preview is not None:
            payload["disable_web_page_preview"] = disable_web_page_preview
        if reply_markup:
            payload["reply_markup"] = reply_markup
        response = await self._client.post("/sendMessage", json=payload)
        response.raise_for_status()
        return response.json().get("result", {})

    async def send_document(self, chat_id: int, filename: str, content: bytes, caption: str | None = None) -> dict:
        data: dict[str, str | int] = {"chat_id": chat_id}
        if caption:
            data["caption"] = caption
        files = {"document": (filename, content, "application/json")}
        response = await self._client.post("/sendDocument", data=data, files=files)
        response.raise_for_status()
        return response.json().get("result", {})

    async def get_file(self, file_id: str) -> str:
        response = await self._client.post("/getFile", json={"file_id": file_id})
        response.raise_for_status()
        result = response.json().get("result", {})
        return str(result.get("file_path") or "")

    async def download_file(self, file_path: str) -> bytes:
        if not file_path:
            return b""
        response = await self._client.get(f"https://api.telegram.org/file/bot{self._token}/{file_path}")
        response.raise_for_status()
        return response.content

    async def edit_message_text(
        self,
        chat_id: int,
        message_id: int,
        text: str,
        reply_markup: dict | None = None,
    ) -> dict:
        payload = {"chat_id": chat_id, "message_id": message_id, "text": text}
        if reply_markup:
            payload["reply_markup"] = reply_markup
        response = await self._client.post("/editMessageText", json=payload)
        response.raise_for_status()
        return response.json().get("result", {})

    async def delete_message(self, chat_id: int, message_id: int) -> None:
        response = await self._client.post("/deleteMessage", json={"chat_id": chat_id, "message_id": message_id})
        response.raise_for_status()

    async def answer_callback_query(self, callback_query_id: str, text: str | None = None) -> None:
        payload = {"callback_query_id": callback_query_id}
        if text:
            payload["text"] = text
        response = await self._client.post("/answerCallbackQuery", json=payload)
        response.raise_for_status()
