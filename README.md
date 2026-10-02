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
| `OPENAI_API_KEY` | ключ OpenAI |
| `TELEGRAM_BOT_TOKEN` | токен Telegram-бота |
| `ADMIN_USER_IDS` | Telegram ID администраторов через запятую |
| `ALLOWED_TELEGRAM_USER_IDS` | Telegram ID пользователей, которым можно пользоваться ботом |

Генерация и правка доступны администраторам и пользователям из `ALLOWED_TELEGRAM_USER_IDS`. Остальным бот отвечает отказом и присылает их Telegram ID. Списки задаются через запятую, например `123456789,987654321`.

## Запуск

Нужны Docker и Docker Compose.

```bash
cp .env.example .env
docker compose up --build -d
```

Логи: `docker compose logs -f`. Остановка: `docker compose down`.

Файл `.env` в образ и в репозиторий не попадает. Compose передаёт его переменные в контейнер при старте.
