import asyncio
import os
from typing import Optional

import asyncpg
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

# Токен бота и URL базы берём из переменных окружения
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("Не найден BOT_TOKEN в переменных окружения")

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("Не найден DATABASE_URL в переменных окружения")

bot = Bot(TOKEN)
dp = Dispatcher(storage=MemoryStorage())
db_pool: Optional[asyncpg.Pool] = None


class DndSurvey(StatesGroup):
    """Состояния опроса по DnD."""
    want_play = State()
    fav_class = State()
    style = State()


async def init_db():
    """Создаём пул соединений и таблицы, если их ещё нет."""
    global db_pool
    db_pool = await asyncpg.create_pool(DATABASE_URL)

    async with db_pool.acquire() as conn:
        # Таблица пользователей
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id BIGINT PRIMARY KEY,
                full_name TEXT,
                username TEXT
            );
            """
        )
        # Таблица ответов по ДнД-опросу
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS dnd_answers (
                id SERIAL PRIMARY KEY,
                user_id BIGINT REFERENCES users(id),
                want_play BOOLEAN,
                fav_class TEXT,
                style TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
            """
        )


@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """Начинаем опрос: сохраняем юзера и спрашиваем первый вопрос."""
    global db_pool
    user = message.from_user

    if db_pool is None:
        raise RuntimeError("db_pool не инициализирован")

    # Сохраняем/обновляем пользователя в таблице users
    async with db_pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO users(id, full_name, username)
            VALUES($1, $2, $3)
            ON CONFLICT (id) DO UPDATE
            SET full_name = EXCLUDED.full_name,
                username = EXCLUDED.username;
            """,
            user.id,
            user.full_name,
            user.username,
        )

    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Да"), KeyboardButton(text="Нет")],
        ],
        resize_keyboard=True,
    )

    await state.clear()
    await state.set_state(DndSurvey.want_play)
    await message.answer(
        "Привет! 👋\n"
        "Давай небольшой опрос по DnD.\n\n"
        "Хочешь поиграть в D&D?",
        reply_markup=keyboard,
    )


@dp.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "Я бот-опросник по DnD.\n"
        "Команды:\n"
        "/start — начать опрос сначала\n"
        "/help — показать это сообщение\n\n"
        "Просто напиши /start, и я задам тебе несколько вопросов.",
    )


@dp.message(DndSurvey.want_play, F.text)
async def q_want_play(message: Message, state: FSMContext):
    """Обрабатываем ответ на 'Хочешь поиграть в DnD?'."""
    text = (message.text or "").strip().lower()

    if text not in ("да", "нет"):
        await message.answer("Пожалуйста, выбери вариант: 'Да' или 'Нет' 🙂")
        return

    want_play = text == "да"
    await state.update_data(want_play=want_play)

    await state.set_state(DndSurvey.fav_class)
    await message.answer(
        "Окей, записал 👍\n\n"
        "Вопрос 2:\n"
        "Какой твой любимый класс в DnD? (например: маг, бард, варвар)",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="Маг"), KeyboardButton(text="Воин")],
                [KeyboardButton(text="Бард"), KeyboardButton(text="Вор")],
            ],
            resize_keyboard=True,
        ),
    )


@dp.message(DndSurvey.fav_class, F.text)
async def q_fav_class(message: Message, state: FSMContext):
    """Обрабатываем любимый класс."""
    fav_class = (message.text or "").strip()
    if not fav_class:
        await message.answer("Напиши, пожалуйста, название класса 🙂")
        return

    await state.update_data(fav_class=fav_class)

    await state.set_state(DndSurvey.style)
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Драться 💥"), KeyboardButton(text="Диалоги 🗣")],
            [KeyboardButton(text="Смешанное ⚔️🗣")],
        ],
        resize_keyboard=True,
    )
    await message.answer(
        "Круто! 🎲\n\n"
        "Последний вопрос:\n"
        "Что ты больше любишь в DnD:\n"
        "— драться и кидать кости\n"
        "— диалоги и отыгрыш\n"
        "— или что-то смешанное?",
        reply_markup=keyboard,
    )


@dp.message(DndSurvey.style, F.text)
async def q_style(message: Message, state: FSMContext):
    """Финальный ответ: сохраняем всё в БД и показываем резюме."""
    global db_pool
    style = (message.text or "").strip()
    if not style:
        await message.answer("Напиши, пожалуйста, хотя бы пару слов 🙂")
        return

    data = await state.get_data()
    want_play = data.get("want_play")
    fav_class = data.get("fav_class")

    if db_pool is None:
        raise RuntimeError("db_pool не инициализирован")

    user = message.from_user

    # Сохраняем ответы в таблицу dnd_answers
    async with db_pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO dnd_answers(user_id, want_play, fav_class, style)
            VALUES($1, $2, $3, $4);
            """,
            user.id,
            want_play,
            fav_class,
            style,
        )

    await state.clear()

    answer_text = (
        "Спасибо, я всё записал! ✅\n\n"
        f"Ты: {user.full_name} (id: {user.id})\n"
        f"Хочешь играть: {'Да' if want_play else 'Нет'}\n"
        f"Любимый класс: {fav_class}\n"
        f"Стиль игры: {style}\n\n"
        "Если хочешь пройти опрос ещё раз — напиши /start."
    )

    await message.answer(answer_text)


@dp.message(F.text)
async def fallback(message: Message):
    """Обработка всего остального текста вне состояний."""
    await message.answer(
        "Я сейчас работаю как опросник по DnD 😊\n"
        "Напиши /start, чтобы пройти опрос, или /help за подсказкой.",
    )


async def main():
    await init_db()
    print("Бот запущен. Нажми Ctrl+C для остановки.")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
