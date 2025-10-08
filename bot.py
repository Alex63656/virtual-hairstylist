import asyncio
import logging
import os  # Импортируем модуль os для работы с переменными окружения

from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

# --- НАСТРОЙКА ---
# Теперь мы берем токен и URL из переменных окружения, а не пишем их прямо в коде.
# Railway автоматически подставит сюда значения, которые вы укажете в настройках проекта.
BOT_TOKEN = os.getenv('BOT_TOKEN')
WEB_APP_URL = os.getenv('WEB_APP_URL')
# -----------------

# Включаем логирование, чтобы видеть информацию о работе бота в консоли Railway
logging.basicConfig(level=logging.INFO)

# Добавляем проверку, чтобы убедиться, что токен был найден
if not BOT_TOKEN:
    logging.critical("!!! ОШИБКА: Переменная окружения BOT_TOKEN не установлена! Пожалуйста, добавьте ее во вкладке 'Variables' на Railway и убедитесь, что имя написано правильно.")
    exit() # Завершаем работу, если токена нет

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Обработчик команды /start
@dp.message(Command("start"))
async def send_welcome(message: types.Message):
    """
    Этот обработчик будет вызван, когда пользователь отправит команду /start.
    Он отправляет приветственное сообщение и кнопку для открытия веб-приложения.
    """
    # Создаем кнопку, которая открывает Web App
    # web_app - это специальный объект, в который передается URL нашего приложения
    web_app_button = InlineKeyboardButton(
        text="✨ Подобрать прическу",
        web_app=WebAppInfo(url=WEB_APP_URL)
    )
    # Создаем клавиатуру с одной кнопкой
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[web_app_button]])

    # Формируем текст приветствия
    welcome_text = (
        f"Привет, {message.from_user.full_name}! 👋\n\n"
        "Я — ваш персональный AI-стилист. Готов помочь вам примерить новый образ!\n\n"
        "Нажмите на кнопку ниже, чтобы начать! 👇"
    )

    # Отправляем сообщение пользователю
    await message.answer(welcome_text, reply_markup=keyboard)

# Основная функция для запуска бота
async def main():
    # Удаляем вебхуки, которые могли остаться от предыдущих запусков
    await bot.delete_webhook(drop_pending_updates=True)
    # Запускаем опрос сервера Телеграм на наличие новых сообщений
    await dp.start_polling(bot)

# Запускаем асинхронную функцию main
if __name__ == "__main__":
    asyncio.run(main())
