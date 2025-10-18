# Объяснение кода:
# Эта версия ищет переменную окружения с правильным именем 'API_KEY',
# которое совпадает с тем, что настроено на Railway.

import asyncio
import logging
import os
import aiohttp
from aiohttp import web

from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

# --- НАСТРОЙКА ---
BOT_TOKEN = os.getenv('BOT_TOKEN')
WEB_APP_URL = os.getenv('WEB_APP_URL')
# --- ВАШ КЛЮЧ УЖЕ ВСТАВЛЕН ---
GEMINI_API_KEY = "AIzaSyCX-D5d5kXJrmyMZJREykCQAbx-bXqVCIk" # <--- ВАШ КЛЮЧ ЗДЕСЬ
PORT = os.getenv('PORT', '8080')

logging.basicConfig(level=logging.INFO)

# Теперь проверка GEMINI_API_KEY снова важна!
if not all([BOT_TOKEN, WEB_APP_URL, GEMINI_API_KEY]):
    logging.critical("!!! ОШИБКА: Одна или несколько переменных (BOT_TOKEN, WEB_APP_URL, API_KEY) не найдены!")
    exit()

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def send_welcome(message: types.Message):
    web_app_button = InlineKeyboardButton(text="✨ Подобрать прическу", web_app=WebAppInfo(url=WEB_APP_URL))
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[web_app_button]])
    await message.answer(f"Привет, {message.from_user.full_name}! 👋\n\nНажмите на кнопку ниже, чтобы начать!", reply_markup=keyboard)

async def proxy_handler(request):
    headers = {"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Methods": "POST, OPTIONS", "Access-Control-Allow-Headers": "Content-Type"}
    if request.method == 'OPTIONS':
        return web.Response(headers=headers)
    try:
        data = await request.json()
        target_api = data.get('target_api')
        payload = data.get('payload')

        # Используем актуальные модели, которые ожидает фронтенд
        if target_api == 'image':
            api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-image-preview:generateContent?key={GEMINI_API_KEY}"
        elif target_api == 'text':
            # Заменил старую модель на новую
            api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
        else:
            return web.json_response({"error": {"message": "Invalid target_api"}}, status=400, headers=headers)

        async with aiohttp.ClientSession() as session:
            async with session.post(api_url, json=payload) as resp:
                response_json = await resp.json()
                # Логируем ответ от Google для отладки
                logging.info(f"Response from Gemini API (status {resp.status}): {response_json}")
                return web.json_response(response_json, status=resp.status, headers=headers)
    except Exception as e:
        logging.error(f"Proxy error: {e}")
        return web.json_response({"error": {"message": str(e)}}, status=500, headers=headers)

async def start_bot_polling():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

async def start_web_server():
    app = web.Application(client_max_size=1024**2 * 10)
    app.router.add_route('*', '/api/proxy', proxy_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', int(PORT))
    await site.start()
    logging.info(f"--> Веб-сервер (прокси) запущен на порту {PORT}")
    await asyncio.Event().wait()

async def main():
    await asyncio.gather(start_bot_polling(), start_web_server())

if __name__ == "__main__":

    asyncio.run(main())
