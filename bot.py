import asyncio
import logging
import os
import sys
import pprint # Добавлен для красивого вывода

from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

# --- НАСТРОЙКА ---
BOT_TOKEN = os.getenv('BOT_TOKEN')
WEB_APP_URL = os.getenv('WEB_APP_URL')
# -----------------

logging.basicConfig(level=logging.INFO)

# --- БЛОК ДЛЯ ОТЛАДКИ ---
# Выводим все переменные окружения, которые видит бот
logging.info("--- ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ, КОТОРЫЕ ВИДИТ БОТ ---")
logging.info(pprint.pformat(dict(os.environ)))
logging.info("---------------------------------------------")
# -------------------------

# Проверяем все необходимые переменные окружения
if not BOT_TOKEN:
    logging.critical("!!! ОШИБКА: Переменная окружения BOT_TOKEN не установлена!")
    sys.exit(1)

if not WEB_APP_URL:
    logging.critical("!!! ОШИБКА: Переменная окружения WEB_APP_URL не установлена!")
    sys.exit(1)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def send_welcome(message: types.Message):
    try:
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
    except Exception as e:
        logging.error(f"Ошибка при отправке приветственного сообщения: {e}")
        await message.answer("Произошла ошибка. Попробуйте позже.")

async def main():
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        logging.info("Бот запущен и готов к работе!")
        await dp.start_polling(bot)
    except Exception as e:
        logging.critical(f"Критическая ошибка при запуске бота: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
