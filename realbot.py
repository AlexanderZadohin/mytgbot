import asyncio
import os
import random

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton

# Берём токен из переменной окружения
TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise RuntimeError("Не найден BOT_TOKEN в переменных окружения")

bot = Bot(TOKEN)
dp = Dispatcher()


# /start
@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        "Привет! 👋\n"
        "Я твой учебный бот на aiogram.\n"
        "Напиши /help, чтобы посмотреть, что я умею."
    )


# /help
@dp.message(Command("help"))
async def cmd_help(message: Message):
    text = (
        "Вот, что я умею:\n"
        "/start - начать общение\n"
        "/help - показать эту справку\n"
        "/menu - открыть меню с кнопками\n\n"
        "Можешь просто писать текст — я буду повторять его."
    )
    await message.answer(text)


# /menu — покажем кнопки
@dp.message(Command("menu"))
async def cmd_menu(message: Message):
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="Случайное число"),
                KeyboardButton(text="Моя информация"),
            ]
        ],
        resize_keyboard=True,
    )

    await message.answer("Выбери действие:", reply_markup=keyboard)


# Обработка нажатий по тексту кнопки
@dp.message(F.text == "Случайное число")
async def random_number(message: Message):
    number = random.randint(1, 100)
    await message.answer(f"Твоё случайное число: {number}")


@dp.message(F.text == "Моя информация")
async def user_info(message: Message):
    user = message.from_user
    await message.answer(
        f"Твой id: {user.id}\n"
        f"Имя: {user.full_name}\n"
        f"Юзернейм: @{user.username}" if user.username else "Юзернейм не задан"
    )


# Общее эхо — на всё остальное
@dp.message(F.text)
async def echo(message: Message):
    await message.answer(f"Ты написал: {message.text}")


async def main():
    print("Бот запущен. Нажми Ctrl+C для остановки.")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
