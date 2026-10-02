from __future__ import annotations

import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from bot.defaults import MODEL, QUALITY, SIZE


@dataclass(frozen=True)
class UserSettings:
    user_id: int
    username: str
    model: str
    size: str
    quality: str


class UserSettingsStore:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user_settings (
                user_id INTEGER PRIMARY KEY,
                username TEXT NOT NULL DEFAULT '',
                model TEXT NOT NULL,
                size TEXT NOT NULL,
                quality TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        self._conn.commit()

    def get_or_create(self, user_id: int, username: str) -> UserSettings:
        now = datetime.now(timezone.utc).isoformat()
        with self._lock:
            row = self._conn.execute(
                """
                SELECT user_id, username, model, size, quality
                FROM user_settings
                WHERE user_id = ?
                """,
                (user_id,),
            ).fetchone()
            if row is None:
                self._conn.execute(
                    """
                    INSERT INTO user_settings
                        (user_id, username, model, size, quality, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (user_id, username, MODEL, SIZE, QUALITY, now),
                )
                self._conn.commit()
                return UserSettings(user_id, username, MODEL, SIZE, QUALITY)
            if username and row["username"] != username:
                self._conn.execute(
                    """
                    UPDATE user_settings
                    SET username = ?, updated_at = ?
                    WHERE user_id = ?
                    """,
                    (username, now, user_id),
                )
                self._conn.commit()
            return UserSettings(
                user_id=row["user_id"],
                username=username or row["username"],
                model=row["model"],
                size=row["size"],
                quality=row["quality"],
            )

    def set_model(self, user_id: int, username: str, model: str) -> UserSettings:
        now = datetime.now(timezone.utc).isoformat()
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO user_settings
                    (user_id, username, model, size, quality, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    username = CASE
                        WHEN excluded.username != '' THEN excluded.username
                        ELSE user_settings.username
                    END,
                    model = excluded.model,
                    updated_at = excluded.updated_at
                """,
                (user_id, username, model, SIZE, QUALITY, now),
            )
            self._conn.commit()
            row = self._conn.execute(
                """
                SELECT user_id, username, model, size, quality
                FROM user_settings
                WHERE user_id = ?
                """,
                (user_id,),
            ).fetchone()
        return UserSettings(
            user_id=row["user_id"],
            username=row["username"],
            model=row["model"],
            size=row["size"],
            quality=row["quality"],
        )
