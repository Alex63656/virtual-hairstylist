import asyncio
import logging
import os
import aiohttp
from aiohttp import web

from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

# --- НАСТРОЙКА ПЕРЕМЕННЫХ ОКРУЖЕНИЯ ---
BOT_TOKEN = os.getenv('BOT_TOKEN')
WEB_APP_URL = os.getenv('WEB_APP_URL')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
# Bothost предоставляет порт через переменную PORT, по умолчанию 8080
PORT = os.getenv('PORT', '8080') 

# --- НАСТРОЙКА ЛОГИРОВАНИЯ ---
logging.basicConfig(level=logging.INFO)

# --- ИНИЦИАЛИЗАЦИЯ БОТА ---
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- ОБРАБОТЧИКИ ТЕЛЕГРАМ ---
@dp.message(Command("start"))
async def send_welcome(message: types.Message):
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

# --- ОБРАБОТЧИКИ ПРОКСИ-СЕРВЕРА ---
async def proxy_handler(request):
    # Добавляем заголовки CORS для разрешения запросов из браузера
    headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
    }

    # Обработка preflight-запроса OPTIONS от браузера
    if request.method == 'OPTIONS':
        return web.Response(headers=headers)

    try:
        data = await request.json()
        target_api = data.get('target_api')
        payload = data.get('payload')

        if not target_api or not payload:
            return web.Response(status=400, text="Missing target_api or payload", headers=headers)

        if target_api == 'image':
            api_url = f"[https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-image-preview:generateContent?key=](https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-image-preview:generateContent?key=){GEMINI_API_KEY}"
        elif target_api == 'text':
            api_url = f"[https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-05-20:generateContent?key=](https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-05-20:generateContent?key=){GEMINI_API_KEY}"
        else:
            return web.Response(status=400, text="Invalid target_api specified", headers=headers)

        async with aiohttp.ClientSession() as session:
            async with session.post(api_url, json=payload) as resp:
                response_text = await resp.text()
                return web.Response(status=resp.status, text=response_text, content_type='application/json', headers=headers)

    except Exception as e:
        logging.error(f"Proxy error: {e}")
        return web.Response(status=500, text=str(e), headers=headers)

# --- ФУНКЦИИ ЗАПУСКА ---
async def start_bot_polling():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

async def start_web_server():
    app = web.Application()
    app.router.add_route('*', '/api/proxy', proxy_handler) # Принимаем и POST, и OPTIONS
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', int(PORT))
    await site.start()
    logging.info(f"Web server started on port {PORT}")
    while True:
        await asyncio.sleep(3600) 

async def main():
    await asyncio.gather(
        start_bot_polling(),
        start_web_server()
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped!")
