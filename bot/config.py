from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str
    openai_api_key: str
    image_model: str
    image_size: str
    image_quality: str


def load_settings() -> Settings:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    missing = [
        name
        for name, value in (
            ("TELEGRAM_BOT_TOKEN", token),
            ("OPENAI_API_KEY", api_key),
        )
        if not value
    ]
    if missing:
        joined = ", ".join(missing)
        raise RuntimeError(f"Не заданы переменные окружения: {joined}")

    return Settings(
        telegram_bot_token=token,
        openai_api_key=api_key,
        image_model=os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-2").strip() or "gpt-image-2",
        image_size=os.getenv("OPENAI_IMAGE_SIZE", "1024x1024").strip() or "1024x1024",
        image_quality=os.getenv("OPENAI_IMAGE_QUALITY", "medium").strip() or "medium",
    )
