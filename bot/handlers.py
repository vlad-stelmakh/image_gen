from __future__ import annotations

import asyncio
import logging
from contextlib import suppress

from aiogram import Bot, F, Router
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import BufferedInputFile, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from openai import APIStatusError, OpenAIError

from bot.config import Settings
from bot.db import UserSettings, UserSettingsStore
from bot.defaults import MODELS
from bot.images import ImageService

logger = logging.getLogger(__name__)

router = Router()

HELP_TEXT = (
    "Я генерирую и правлю картинки через OpenAI.\n\n"
    "Сгенерировать:\n"
    "/image кот в космическом шлеме\n\n"
    "Изменить свою картинку:\n"
    "отправьте фото с подписью, что нужно изменить.\n"
    "Если подписи нет, я попрошу её следующим сообщением.\n\n"
    "Можно ответить текстом на уже отправленную картинку — "
    "я отредактирую её по этому описанию.\n\n"
    "/my_settings — показать настройки и выбрать модель\n"
    "/cancel — отменить ожидающую правку"
)

MAX_PROMPT_LENGTH = 4000


class EditFlow(StatesGroup):
    waiting_prompt = State()


@router.message(CommandStart())
@router.message(Command("help"))
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(HELP_TEXT)


@router.message(Command("my_settings"))
async def cmd_my_settings(message: Message, settings: Settings, users: UserSettingsStore) -> None:
    user = message.from_user
    if user is None:
        return
    prefs = users.get_or_create(user.id, user.username or "")
    await message.answer(
        _settings_text(prefs, user.id in settings.ADMIN_USER_IDS),
        reply_markup=_model_keyboard(prefs.model),
    )


@router.callback_query(F.data.startswith("model:"))
async def on_model_choice(query: CallbackQuery, settings: Settings, users: UserSettingsStore) -> None:
    user = query.from_user
    if not settings.can_use(user.id):
        await query.answer("Нет доступа", show_alert=True)
        return
    model = (query.data or "").split(":", 1)[1]
    if model not in MODELS:
        await query.answer("Неизвестная модель", show_alert=True)
        return
    prefs = users.set_model(user.id, user.username or "", model)
    if isinstance(query.message, Message):
        await query.message.edit_text(
            _settings_text(prefs, user.id in settings.ADMIN_USER_IDS),
            reply_markup=_model_keyboard(prefs.model),
        )
    await query.answer(f"Модель: {MODELS[model]}")


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Ожидание правки сброшено.")


@router.message(Command("image"))
async def cmd_image(
    message: Message,
    command: CommandObject,
    state: FSMContext,
    images: ImageService,
    users: UserSettingsStore,
) -> None:
    await state.clear()
    prompt = (command.args or "").strip()
    if not prompt:
        await message.answer("Напишите описание после команды: /image закат над морем")
        return
    await _generate_and_send(message, images, users, prompt)


@router.message(F.photo)
async def on_photo(message: Message, state: FSMContext, images: ImageService, users: UserSettingsStore) -> None:
    file_id = message.photo[-1].file_id
    prompt = _caption_prompt(message.caption)
    if prompt:
        await state.clear()
        await _edit_and_send(message, images, users, file_id, "photo.jpg", prompt)
        return
    await state.set_state(EditFlow.waiting_prompt)
    await state.update_data(file_id=file_id, filename="photo.jpg")
    await message.answer("Что изменить на этой картинке? Опишите правку одним сообщением.")


@router.message(F.document.mime_type.startswith("image/"))
async def on_document(
    message: Message,
    state: FSMContext,
    images: ImageService,
    users: UserSettingsStore,
) -> None:
    document = message.document
    if document is None:
        return
    filename = document.file_name or "image.jpg"
    prompt = _caption_prompt(message.caption)
    if prompt:
        await state.clear()
        await _edit_and_send(message, images, users, document.file_id, filename, prompt)
        return
    await state.set_state(EditFlow.waiting_prompt)
    await state.update_data(file_id=document.file_id, filename=filename)
    await message.answer("Что изменить на этой картинке? Опишите правку одним сообщением.")


@router.message(EditFlow.waiting_prompt, F.text)
async def on_edit_prompt(
    message: Message,
    state: FSMContext,
    images: ImageService,
    users: UserSettingsStore,
) -> None:
    prompt = (message.text or "").strip()
    if prompt.startswith("/"):
        await message.answer("Это похоже на команду. Опишите правку обычным текстом или отправьте /cancel.")
        return
    data = await state.get_data()
    await state.clear()
    file_id = data.get("file_id")
    filename = data.get("filename") or "photo.jpg"
    if not file_id:
        await message.answer("Картинка не сохранилась. Отправьте её ещё раз.")
        return
    await _edit_and_send(message, images, users, file_id, filename, prompt)


@router.message(F.reply_to_message.photo, F.text)
async def on_reply_to_photo(message: Message, images: ImageService, users: UserSettingsStore) -> None:
    prompt = (message.text or "").strip()
    if not prompt or prompt.startswith("/"):
        return
    reply = message.reply_to_message
    if reply is None or not reply.photo:
        return
    await _edit_and_send(message, images, users, reply.photo[-1].file_id, "photo.jpg", prompt)


def _caption_prompt(caption: str | None) -> str:
    text = (caption or "").strip()
    if text.lower().startswith("/image"):
        text = text.split(maxsplit=1)[1] if " " in text else ""
    return text.strip()


async def _generate_and_send(
    message: Message,
    images: ImageService,
    users: UserSettingsStore,
    prompt: str,
) -> None:
    error = _validate_prompt(prompt)
    if error:
        await message.answer(error)
        return
    options = _user_settings(message, users)
    status = await message.answer("Генерирую картинку…")
    stop = _keep_uploading(message.bot, message.chat.id)
    try:
        image = await images.generate(prompt, options)
    except Exception as exc:
        logger.exception("image generation failed")
        await status.edit_text(_error_text(exc))
        return
    finally:
        stop.set()
    await _send_result(message, status, image, "image.jpg", prompt)


async def _edit_and_send(
    message: Message,
    images: ImageService,
    users: UserSettingsStore,
    file_id: str,
    filename: str,
    prompt: str,
) -> None:
    error = _validate_prompt(prompt)
    if error:
        await message.answer(error)
        return
    options = _user_settings(message, users)
    status = await message.answer("Редактирую картинку…")
    stop = _keep_uploading(message.bot, message.chat.id)
    try:
        source = await _download(message.bot, file_id)
        image = await images.edit(source, prompt, filename, options)
    except Exception as exc:
        logger.exception("image edit failed")
        await status.edit_text(_error_text(exc))
        return
    finally:
        stop.set()
    await _send_result(message, status, image, "edited.jpg", prompt)


async def _send_result(
    message: Message,
    status: Message,
    image: bytes,
    filename: str,
    prompt: str,
) -> None:
    try:
        await message.answer_photo(
            BufferedInputFile(image, filename=filename),
            caption=prompt[:1024],
        )
    except Exception:
        logger.exception("failed to send photo")
        await status.edit_text("Картинка готова, но Telegram её не принял. Попробуйте ещё раз.")
        return
    await status.delete()


def _settings_text(prefs: UserSettings, is_admin: bool) -> str:
    username = f"@{prefs.username}" if prefs.username else "не задано"
    role = "администратор" if is_admin else "пользователь"
    title = MODELS.get(prefs.model, prefs.model)
    return (
        "Ваши настройки\n\n"
        f"Telegram ID: {prefs.user_id}\n"
        f"Имя: {username}\n"
        f"Роль: {role}\n"
        f"Модель: {title}\n"
        f"ID модели: {prefs.model}\n"
        f"Размер: {prefs.size}\n"
        f"Качество: {prefs.quality}\n\n"
        "Модель выбирается кнопками ниже. По умолчанию — GPT Image 2."
    )


def _model_keyboard(current: str) -> InlineKeyboardMarkup:
    rows = []
    for model_id, title in MODELS.items():
        mark = "✓ " if model_id == current else ""
        rows.append([InlineKeyboardButton(text=f"{mark}{title}", callback_data=f"model:{model_id}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _user_settings(message: Message, users: UserSettingsStore) -> UserSettings:
    user = message.from_user
    if user is None:
        raise RuntimeError("Telegram не передал пользователя")
    return users.get_or_create(user.id, user.username or "")


def _validate_prompt(prompt: str) -> str | None:
    if not prompt:
        return "Нужно текстовое описание."
    if len(prompt) > MAX_PROMPT_LENGTH:
        return f"Описание слишком длинное. Максимум {MAX_PROMPT_LENGTH} символов."
    return None


async def _download(bot: Bot, file_id: str) -> bytes:
    buffer = await bot.download(file_id)
    if buffer is None:
        raise RuntimeError("Telegram не отдал файл")
    return buffer.read()


_background_tasks: set[asyncio.Task[None]] = set()


def _keep_uploading(bot: Bot, chat_id: int) -> asyncio.Event:
    stop = asyncio.Event()

    async def _loop() -> None:
        while not stop.is_set():
            with suppress(Exception):
                await bot.send_chat_action(chat_id, "upload_photo")
            try:
                await asyncio.wait_for(stop.wait(), timeout=4)
            except TimeoutError:
                continue

    task = asyncio.create_task(_loop())
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return stop


def _error_text(exc: Exception) -> str:
    if isinstance(exc, APIStatusError):
        detail = getattr(exc, "message", None) or str(exc)
        return f"OpenAI отклонил запрос: {detail[:300]}"
    if isinstance(exc, OpenAIError):
        return "Не удалось связаться с OpenAI. Попробуйте ещё раз чуть позже."
    return "Не получилось обработать картинку. Попробуйте ещё раз."
