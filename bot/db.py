from __future__ import annotations

import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from bot.defaults import MODEL, QUALITY, SIZE, qualities_for


@dataclass(frozen=True)
class UserSettings:
    user_id: int
    username: str
    model: str
    size: str
    quality: str
    input_tokens: int
    output_tokens: int
    total_tokens: int


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
                input_tokens INTEGER NOT NULL DEFAULT 0,
                output_tokens INTEGER NOT NULL DEFAULT 0,
                total_tokens INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL
            )
            """
        )
        self._ensure_token_columns()
        self._conn.commit()

    def get_or_create(self, user_id: int, username: str) -> UserSettings:
        with self._lock:
            row = self._touch(user_id, username)
            self._conn.commit()
            return _from_row(row, username)

    def set_model(self, user_id: int, username: str, model: str) -> UserSettings:
        with self._lock:
            row = self._touch(user_id, username)
            quality = row["quality"]
            if quality not in qualities_for(model):
                quality = QUALITY
            self._conn.execute(
                """
                UPDATE user_settings
                SET model = ?, quality = ?, updated_at = ?
                WHERE user_id = ?
                """,
                (model, quality, _now(), user_id),
            )
            self._conn.commit()
            return _from_row(self._fetch(user_id), username)

    def set_size(self, user_id: int, username: str, size: str) -> UserSettings:
        return self._set_field(user_id, username, "size", size)

    def set_quality(self, user_id: int, username: str, quality: str) -> UserSettings:
        return self._set_field(user_id, username, "quality", quality)

    def add_usage(self, user_id: int, input_tokens: int, output_tokens: int, total_tokens: int) -> None:
        with self._lock:
            self._conn.execute(
                """
                UPDATE user_settings
                SET input_tokens = input_tokens + ?,
                    output_tokens = output_tokens + ?,
                    total_tokens = total_tokens + ?,
                    updated_at = ?
                WHERE user_id = ?
                """,
                (input_tokens, output_tokens, total_tokens, _now(), user_id),
            )
            self._conn.commit()

    def _set_field(self, user_id: int, username: str, field: str, value: str) -> UserSettings:
        if field not in {"size", "quality"}:
            raise ValueError(field)
        with self._lock:
            self._touch(user_id, username)
            self._conn.execute(
                f"UPDATE user_settings SET {field} = ?, updated_at = ? WHERE user_id = ?",
                (value, _now(), user_id),
            )
            self._conn.commit()
            return _from_row(self._fetch(user_id), username)

    def _touch(self, user_id: int, username: str) -> sqlite3.Row:
        row = self._fetch(user_id)
        now = _now()
        if row is None:
            self._conn.execute(
                """
                INSERT INTO user_settings
                    (user_id, username, model, size, quality, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (user_id, username, MODEL, SIZE, QUALITY, now),
            )
            return self._fetch(user_id)
        if username and row["username"] != username:
            self._conn.execute(
                "UPDATE user_settings SET username = ?, updated_at = ? WHERE user_id = ?",
                (username, now, user_id),
            )
            return self._fetch(user_id)
        return row

    def _fetch(self, user_id: int) -> sqlite3.Row | None:
        return self._conn.execute(
            """
            SELECT user_id, username, model, size, quality,
                   input_tokens, output_tokens, total_tokens
            FROM user_settings
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()

    def _ensure_token_columns(self) -> None:
        existing = {row["name"] for row in self._conn.execute("PRAGMA table_info(user_settings)")}
        for column in ("input_tokens", "output_tokens", "total_tokens"):
            if column not in existing:
                self._conn.execute(
                    f"ALTER TABLE user_settings ADD COLUMN {column} INTEGER NOT NULL DEFAULT 0"
                )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _from_row(row: sqlite3.Row, username: str) -> UserSettings:
    return UserSettings(
        user_id=row["user_id"],
        username=username or row["username"],
        model=row["model"],
        size=row["size"],
        quality=row["quality"],
        input_tokens=row["input_tokens"],
        output_tokens=row["output_tokens"],
        total_tokens=row["total_tokens"],
    )
