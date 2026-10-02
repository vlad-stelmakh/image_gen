from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import Any

from openai import AsyncOpenAI

from bot.config import Settings
from bot.db import UserSettings


@dataclass(frozen=True)
class GeneratedImage:
    data: bytes
    input_tokens: int
    output_tokens: int
    total_tokens: int


class ImageService:
    def __init__(self, settings: Settings) -> None:
        self._client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    async def generate(self, prompt: str, options: UserSettings) -> GeneratedImage:
        result = await self._client.images.generate(
            model=options.model,
            prompt=prompt,
            size=options.size,
            quality=options.quality,
            output_format="jpeg",
        )
        return _generated_image(result)

    async def edit(self, image: bytes, prompt: str, filename: str, options: UserSettings) -> GeneratedImage:
        result = await self._client.images.edit(
            model=options.model,
            image=(filename, image, _content_type(filename)),
            prompt=prompt,
            size=options.size,
            quality=options.quality,
            output_format="jpeg",
        )
        return _generated_image(result)


def _generated_image(result: Any) -> GeneratedImage:
    data = result.data or []
    if not data or not data[0].b64_json:
        raise RuntimeError("OpenAI не вернул изображение")
    usage = getattr(result, "usage", None)
    input_tokens = int(getattr(usage, "input_tokens", 0) or 0)
    output_tokens = int(getattr(usage, "output_tokens", 0) or 0)
    total = getattr(usage, "total_tokens", None)
    total_tokens = int(total) if total is not None else input_tokens + output_tokens
    return GeneratedImage(
        data=base64.b64decode(data[0].b64_json),
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
    )


def _content_type(filename: str) -> str:
    lower = filename.lower()
    if lower.endswith(".png"):
        return "image/png"
    if lower.endswith(".webp"):
        return "image/webp"
    return "image/jpeg"
