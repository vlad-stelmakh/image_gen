from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    OPENAI_API_KEY: str
    TELEGRAM_BOT_TOKEN: str
    ADMIN_USER_IDS: frozenset[int]
    ALLOWED_TELEGRAM_USER_IDS: frozenset[int]

    def can_use(self, user_id: int) -> bool:
        return user_id in self.ADMIN_USER_IDS or user_id in self.ALLOWED_TELEGRAM_USER_IDS


def load_settings() -> Settings:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    missing = [
        name
        for name, value in (
            ("OPENAI_API_KEY", api_key),
            ("TELEGRAM_BOT_TOKEN", token),
        )
        if not value
    ]
    if missing:
        joined = ", ".join(missing)
        raise RuntimeError(f"Не заданы переменные окружения: {joined}")

    return Settings(
        OPENAI_API_KEY=api_key,
        TELEGRAM_BOT_TOKEN=token,
        ADMIN_USER_IDS=_parse_user_ids("ADMIN_USER_IDS", os.getenv("ADMIN_USER_IDS", "")),
        ALLOWED_TELEGRAM_USER_IDS=_parse_user_ids(
            "ALLOWED_TELEGRAM_USER_IDS",
            os.getenv("ALLOWED_TELEGRAM_USER_IDS", ""),
        ),
    )


def _parse_user_ids(name: str, raw: str) -> frozenset[int]:
    ids: set[int] = set()
    for part in raw.replace(";", ",").split(","):
        item = part.strip()
        if not item:
            continue
        if not item.isdigit():
            raise RuntimeError(f"{name}: нужен список Telegram ID через запятую, получено {item!r}")
        ids.add(int(item))
    return frozenset(ids)
