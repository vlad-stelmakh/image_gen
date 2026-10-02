from __future__ import annotations

import base64
from typing import Any

from openai import AsyncOpenAI

from bot.config import Settings


MODEL = "gpt-image-2"
SIZE = "1024x1024"
QUALITY = "medium"


class ImageService:
    def __init__(self, settings: Settings) -> None:
        self._client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    async def generate(self, prompt: str) -> bytes:
        result = await self._client.images.generate(
            model=MODEL,
            prompt=prompt,
            size=SIZE,
            quality=QUALITY,
            output_format="jpeg",
        )
        return _decode_image(result)

    async def edit(self, image: bytes, prompt: str, filename: str) -> bytes:
        result = await self._client.images.edit(
            model=MODEL,
            image=(filename, image, _content_type(filename)),
            prompt=prompt,
            size=SIZE,
            quality=QUALITY,
            output_format="jpeg",
            input_fidelity="high",
        )
        return _decode_image(result)


def _decode_image(result: Any) -> bytes:
    data = result.data or []
    if not data or not data[0].b64_json:
        raise RuntimeError("OpenAI не вернул изображение")
    return base64.b64decode(data[0].b64_json)


def _content_type(filename: str) -> str:
    lower = filename.lower()
    if lower.endswith(".png"):
        return "image/png"
    if lower.endswith(".webp"):
        return "image/webp"
    return "image/jpeg"
