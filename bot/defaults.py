from __future__ import annotations

MODEL = "gpt-image-2"
SIZE = "1024x1024"
QUALITY = "medium"

MODELS: dict[str, str] = {
    "gpt-image-2": "GPT Image 2",
    "gpt-image-2.5-flare": "GPT Image 2.5 Flare",
    "gpt-image-2.5-sunburst": "GPT Image 2.5 Sunburst",
}

SIZES: dict[str, str] = {
    "1024x1024": "1024×1024",
    "1536x1024": "1536×1024",
    "1024x1536": "1024×1536",
    "auto": "авто",
}

QUALITIES: dict[str, str] = {
    "low": "низкое",
    "medium": "среднее",
    "high": "высокое",
    "auto": "авто",
}

QUALITIES_25: dict[str, str] = {
    **QUALITIES,
    "xhigh": "очень высокое",
    "max": "максимум",
}


def qualities_for(model: str) -> dict[str, str]:
    if model.startswith("gpt-image-2.5"):
        return QUALITIES_25
    return QUALITIES
