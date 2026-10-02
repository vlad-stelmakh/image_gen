from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from bot.access import AccessMiddleware
from bot.config import load_settings
from bot.db import UserSettingsStore
from bot.handlers import router
from bot.images import ImageService

DATA_DIR = Path("data")
BOT_UID = 1000
BOT_GID = 1000


def prepare_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if os.geteuid() != 0:
        return
    for root, dirs, files in os.walk(DATA_DIR):
        os.chown(root, BOT_UID, BOT_GID)
        for name in dirs + files:
            os.chown(Path(root) / name, BOT_UID, BOT_GID)
    os.setgid(BOT_GID)
    os.setuid(BOT_UID)


async def main() -> None:
    prepare_data_dir()
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
    users = UserSettingsStore(DATA_DIR / "bot.sqlite3")
    bot = Bot(settings.TELEGRAM_BOT_TOKEN)
    dispatcher = Dispatcher(
        storage=MemoryStorage(),
        images=ImageService(settings),
        settings=settings,
        users=users,
    )
    dispatcher.message.middleware(AccessMiddleware(settings))
    dispatcher.include_router(router)
    await dispatcher.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
