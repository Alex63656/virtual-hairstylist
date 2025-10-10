# Объяснение кода:
# Этот скрипт делает две вещи:
# 1. Запускает Телеграм-бота, который отвечает на команду /start.
# 2. Запускает веб-сервер (прокси), который принимает запросы от вашего сайта,
#    добавляет к ним секретный API-ключ и перенаправляет их в Google,
#    решая проблему с геоблокировкой.

import asyncio
import logging
import os
import aiohttp
from aiohttp import web

from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

# --- НАСТРОЙКА ---
# os.getenv() - это команда, которая безопасно берет "секреты"
# (токены и ключи) из настроек Replit, не показывая их в коде.
BOT_TOKEN = os.getenv('BOT_TOKEN')
WEB_APP_URL = os.getenv('WEB_APP_URL')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
# Replit предоставляет порт для веб-сервера через переменную PORT
PORT = os.getenv('PORT', '8080') 

logging.basicConfig(level=logging.INFO)

# Проверяем, что все три секрета были найдены
if not all([BOT_TOKEN, WEB_APP_URL, GEMINI_API_KEY]):
    logging.critical("!!! ОШИБКА: Один или несколько секретов (BOT_TOKEN, WEB_APP_URL, GEMINI_API_KEY) не установлены! Зайдите в раздел 'Secrets' на Replit и добавьте их.")
    exit()

# Инициализируем бота
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- ТЕЛЕГРАМ-БОТ ---
@dp.message(Command("start"))
async def send_welcome(message: types.Message):
    # Эта функция вызывается, когда пользователь пишет /start
    web_app_button = InlineKeyboardButton(text="✨ Подобрать прическу", web_app=WebAppInfo(url=WEB_APP_URL))
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[web_app_button]])
    await message.answer(f"Привет, {message.from_user.full_name}! 👋\n\nНажмите на кнопку ниже, чтобы начать!", reply_markup=keyboard)

# --- ПРОКСИ-СЕРВЕР ---
async def proxy_handler(request):
    # Эта функция принимает запросы от вашего сайта
    headers = {"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Methods": "POST, OPTIONS", "Access-Control-Allow-Headers": "Content-Type"}
    if request.method == 'OPTIONS':
        return web.Response(headers=headers)
    try:
        data = await request.json()
        target_api = data.get('target_api')
        payload = data.get('payload')

        # В зависимости от запроса, выбираем нужный URL API Google
        if target_api == 'image':
            api_url = f"[https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-image-preview:generateContent?key=](https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-image-preview:generateContent?key=){GEMINI_API_KEY}"
        elif target_api == 'text':
            api_url = f"[https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-05-20:generateContent?key=](https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-05-20:generateContent?key=){GEMINI_API_KEY}"
        else:
            return web.json_response({"error": {"message": "Invalid target_api"}}, status=400, headers=headers)

        # Отправляем запрос в Google от имени сервера
        async with aiohttp.ClientSession() as session:
            async with session.post(api_url, json=payload) as resp:
                # Возвращаем ответ от Google обратно на сайт
                return web.json_response(await resp.json(), status=resp.status, headers=headers)
    except Exception as e:
        logging.error(f"Proxy error: {e}")
        return web.json_response({"error": {"message": str(e)}}, status=500, headers=headers)

# --- ФУНКЦИИ ЗАПУСКА ---
async def start_bot_polling():
    # Эта функция запускает самого Телеграм-бота
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

async def start_web_server():
    # Эта функция запускает веб-сервер
    app = web.Application()
    app.router.add_route('*', '/api/proxy', proxy_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', int(PORT))
    await site.start()
    logging.info(f"--> Веб-сервер (прокси) запущен на порту {PORT}")
    await asyncio.Event().wait()

async def main():
    # Эта функция запускает обе задачи (бота и сервер) одновременно
    await asyncio.gather(start_bot_polling(), start_web_server())

if __name__ == "__main__":
    asyncio.run(main())
