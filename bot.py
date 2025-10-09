import asyncio
import logging
import os

from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

# --- НАСТРОЙКА ---
BOT_TOKEN = os.getenv('BOT_TOKEN')
WEB_APP_URL = os.getenv('WEB_APP_URL')
# -----------------

logging.basicConfig(level=logging.INFO)

if not BOT_TOKEN:
    logging.critical("!!! ОШИБКА: Переменная окружения BOT_TOKEN не установлена!")
    exit()

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def send_welcome(message: types.Message):
    if not WEB_APP_URL:
        await message.answer("Ошибка: WEB_APP_URL не настроен.")
        return

    web_app_button = InlineKeyboardButton(
        text="✨ Подобрать прическу",
        web_app=WebAppInfo(url=WEB_APP_URL)
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[web_app_button]])
    welcome_text = (
        f"Привет, {message.from_user.full_name}! 👋\n\n"
        "Я — ваш персональный AI-стилист. Готов помочь вам примерить новый образ!\n\n"
        "Нажмите на кнопку ниже, чтобы начать! 👇"
    )
    await message.answer(welcome_text, reply_markup=keyboard)

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
