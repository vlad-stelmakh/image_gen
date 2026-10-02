from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from bot.access import AccessMiddleware
from bot.config import load_settings
from bot.handlers import router
from bot.images import ImageService


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    settings = load_settings()
    logging.info(
        "admins=%s allowed=%s",
        len(settings.ADMIN_USER_IDS),
        len(settings.ALLOWED_TELEGRAM_USER_IDS),
    )
    bot = Bot(settings.TELEGRAM_BOT_TOKEN)
    dispatcher = Dispatcher(storage=MemoryStorage(), images=ImageService(settings))
    dispatcher.message.middleware(AccessMiddleware(settings))
    dispatcher.include_router(router)
    await dispatcher.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
