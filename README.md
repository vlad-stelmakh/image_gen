# Telegram-бот для картинок OpenAI

Бот генерирует изображения по текстовому описанию и правит присланные фото через [OpenAI Images API](https://developers.openai.com/api/docs/guides/image-generation).

## Команды

- `/start` и `/help` — краткая справка
- `/image закат над морем` — сгенерировать картинку
- фото с подписью — изменить картинку по подписи
- фото без подписи, затем текст — то же самое вторым сообщением
- ответ текстом на картинку — отредактировать её
- `/cancel` — сбросить ожидающую правку

Модель по умолчанию — `gpt-image-2`. Для правок используется высокая точность сохранения исходника (`input_fidelity=high`).

## Настройка

1. Создайте бота у [@BotFather](https://t.me/BotFather) и скопируйте токен.
2. Возьмите ключ на [platform.openai.com](https://platform.openai.com/api-keys). Для GPT Image моделей организация в OpenAI должна быть верифицирована.
3. Скопируйте пример окружения и заполните его:

```bash
cp .env.example .env
```

| Переменная | Назначение |
| --- | --- |
| `TELEGRAM_BOT_TOKEN` | токен Telegram-бота |
| `OPENAI_API_KEY` | ключ OpenAI |
| `OPENAI_IMAGE_MODEL` | `gpt-image-2`, `gpt-image-1.5`, `gpt-image-1` или `gpt-image-1-mini` |
| `OPENAI_IMAGE_SIZE` | `1024x1024`, `1024x1536`, `1536x1024` или `auto` |
| `OPENAI_IMAGE_QUALITY` | `low`, `medium` или `high` |

## Запуск

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m bot.main
```

Нужен Python 3.11+.

Docker:

```bash
docker build -t image-gen-bot .
docker run --rm --env-file .env image-gen-bot
```

Файл `.env` в репозиторий не попадает.
