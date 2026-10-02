from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import Message

from bot.config import Settings


class AccessMiddleware(BaseMiddleware):
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def __call__(
        self,
        handler: Callable[[Message, dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: dict[str, Any],
    ) -> Any:
        user = event.from_user
        if user is not None and self._settings.can_use(user.id):
            return await handler(event, data)
        if user is not None and _is_addressed(event):
            await event.answer(f"Нет доступа. Ваш Telegram ID: {user.id}")
        return None


def _is_addressed(message: Message) -> bool:
    if message.chat.type == "private":
        return True
    text = message.text or message.caption or ""
    if text.startswith("/"):
        return True
    if message.photo:
        return True
    document = message.document
    return document is not None and (document.mime_type or "").startswith("image/")
