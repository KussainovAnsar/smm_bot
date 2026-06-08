import asyncio
import logging
from pathlib import Path
from uuid import uuid4

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from dotenv import load_dotenv
from openai import APIConnectionError, APIError, RateLimitError

from .config import settings
from .openai_service import OpenAIService
from .storage import Storage, UserProfile

load_dotenv()

storage = Storage(settings.database_path)
ai_service: OpenAIService | None = None
logger = logging.getLogger(__name__)


def chunk_text(text: str, limit: int = 3900) -> list[str]:
    chunks: list[str] = []
    current = text.strip()
    while len(current) > limit:
        split_at = current.rfind("\n", 0, limit)
        if split_at < 500:
            split_at = limit
        chunks.append(current[:split_at].strip())
        current = current[split_at:].strip()
    if current:
        chunks.append(current)
    return chunks


async def send_long(message: Message, text: str) -> None:
    for part in chunk_text(text):
        await message.answer(part)


async def send_ai_error(message: Message, error: Exception) -> None:
    logger.exception("AI request failed")
    if isinstance(error, ValueError):
        await message.answer(str(error))
        return

    if isinstance(error, RateLimitError):
        await message.answer(
            "OpenAI сейчас не дает сгенерировать ответ: на API-ключе закончилась квота "
            "или не подключен billing. Проверь баланс/оплату в OpenAI Platform и повтори запрос."
        )
        return

    if isinstance(error, APIConnectionError):
        await message.answer(
            "Не получилось подключиться к OpenAI. Проверь интернет и попробуй еще раз."
        )
        return

    if isinstance(error, APIError):
        await message.answer(
            "OpenAI вернул ошибку при генерации. Попробуй еще раз или проверь настройки API."
        )
        return

    await message.answer("Что-то пошло не так при генерации. Я записал ошибку в лог.")


def get_ai_service() -> OpenAIService:
    global ai_service
    if ai_service is None:
        ai_service = OpenAIService(settings)
    return ai_service


async def download_telegram_file(bot: Bot, file_id: str, suffix: str) -> Path:
    settings.ensure_dirs()
    file = await bot.get_file(file_id)
    target = settings.temp_dir / f"{uuid4().hex}{suffix}"
    await bot.download_file(file.file_path, destination=target)
    return target


async def start(message: Message) -> None:
    await message.answer(
        "Привет! Я SMM-ассистент.\n\n"
        "Отправь voice, текст или фото - я подготовлю 2-3 варианта поста с hook, текстом, CTA, хэштегами и визуалом.\n\n"
        "Профиль: /setprofile ниша | tone | стиль\n"
        "Контент-план: /plan week или /plan month"
    )


async def profile(message: Message) -> None:
    current = storage.get_profile(message.from_user.id)
    await message.answer(
        "Текущий профиль:\n"
        f"Ниша: {current.niche}\n"
        f"Tone: {current.tone}\n"
        f"Стиль: {current.style}"
    )


async def set_profile(message: Message, command: CommandObject) -> None:
    if not command.args:
        await message.answer("Формат: /setprofile ниша | tone | стиль")
        return

    parts = [part.strip() for part in command.args.split("|")]
    current = storage.get_profile(message.from_user.id)
    profile_data = UserProfile(
        user_id=message.from_user.id,
        niche=parts[0] if len(parts) > 0 and parts[0] else current.niche,
        tone=parts[1] if len(parts) > 1 and parts[1] else current.tone,
        style=parts[2] if len(parts) > 2 and parts[2] else current.style,
    )
    storage.set_profile(profile_data)
    await message.answer("Профиль сохранен. Теперь генерация будет точнее.")


async def plan(message: Message, command: CommandObject) -> None:
    period = (command.args or "week").strip().lower()
    readable_period = "месяц" if period in {"month", "месяц"} else "неделя"
    profile_data = storage.get_profile(message.from_user.id)
    session = storage.get_session(message.from_user.id)
    await message.answer("Собираю контент-план...")
    try:
        result = await get_ai_service().generate_plan(
            profile_data,
            readable_period,
            context=session.get("last_source_text") or session.get("last_result"),
        )
    except Exception as error:
        await send_ai_error(message, error)
        return
    storage.append_history(message.from_user.id, "plan", result)
    await send_long(message, result)


async def handle_voice(message: Message, bot: Bot) -> None:
    await message.answer("Расшифровываю voice и собираю варианты поста...")
    audio_path = await download_telegram_file(bot, message.voice.file_id, ".ogg")
    try:
        transcript = await get_ai_service().transcribe(audio_path)
        await message.answer(f"Расшифровка:\n{transcript}")
        await generate_from_source(message, transcript)
    except Exception as error:
        await send_ai_error(message, error)
    finally:
        audio_path.unlink(missing_ok=True)


async def handle_photo(message: Message, bot: Bot) -> None:
    await message.answer("Анализирую фото: качество, композицию и пригодность для поста...")
    largest_photo = message.photo[-1]
    image_path = await download_telegram_file(bot, largest_photo.file_id, ".jpg")
    try:
        analysis = await get_ai_service().analyze_photo(image_path)
        session = storage.get_session(message.from_user.id)
        merged_context = "\n\n".join(
            item for item in [session.get("photo_context"), analysis] if item
        )
        storage.save_session(message.from_user.id, photo_context=merged_context)
        storage.append_history(message.from_user.id, "photo_analysis", analysis)
        await send_long(message, f"Фото добавлено в контекст:\n{analysis}\n\nТеперь отправь текст/voice с идеей поста.")
    except Exception as error:
        await send_ai_error(message, error)
    finally:
        image_path.unlink(missing_ok=True)


async def handle_text(message: Message) -> None:
    text = message.text.strip()
    session = storage.get_session(message.from_user.id)
    last_result = session.get("last_result")

    revision_words = ("сделай", "перепиши", "добавь", "убери", "сократи", "короче", "дерзко")
    if last_result and text.lower().startswith(revision_words):
        await message.answer("Дорабатываю предыдущий результат...")
        profile_data = storage.get_profile(message.from_user.id)
        try:
            revised = await get_ai_service().revise_content(profile_data, last_result, text)
        except Exception as error:
            await send_ai_error(message, error)
            return
        storage.save_session(message.from_user.id, last_result=revised)
        storage.append_history(message.from_user.id, "revision", revised)
        await send_long(message, revised)
        return

    await message.answer("Генерирую варианты контента...")
    await generate_from_source(message, text)


async def generate_from_source(message: Message, source_text: str) -> None:
    profile_data = storage.get_profile(message.from_user.id)
    session = storage.get_session(message.from_user.id)
    try:
        result = await get_ai_service().generate_content(
            profile_data,
            source_text,
            photo_context=session.get("photo_context"),
        )
    except Exception as error:
        await send_ai_error(message, error)
        return
    storage.save_session(
        message.from_user.id,
        last_source_text=source_text,
        last_result=result,
    )
    storage.append_history(message.from_user.id, "content", result)
    await send_long(message, result)


def build_dispatcher() -> Dispatcher:
    dp = Dispatcher()
    dp.message.register(start, Command("start"))
    dp.message.register(profile, Command("profile"))
    dp.message.register(set_profile, Command("setprofile"))
    dp.message.register(plan, Command("plan"))
    dp.message.register(handle_voice, F.voice)
    dp.message.register(handle_photo, F.photo)
    dp.message.register(handle_text, F.text)
    return dp


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    settings.ensure_dirs()
    bot = Bot(token=settings.telegram_bot_token)
    dp = build_dispatcher()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
