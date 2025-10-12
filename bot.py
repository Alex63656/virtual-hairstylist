# Объяснение кода:
# Единственное изменение здесь - это строка 'app = web.Application(client_max_size=1024**2 * 10)'.
# Она увеличивает максимальный размер принимаемых файлов до 10 мегабайт,
# что решает проблему "Content Too Large".

import asyncio
import logging
import os
import aiohttp
from aiohttp import web
import asyncio
import logging
import os
import re
import signal
from typing import Optional
from urllib.parse import unquote

import aiohttp
from aiohttp import web

from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

# --- НАСТРОЙКА ---
BOT_TOKEN = os.getenv('BOT_TOKEN')
WEB_APP_URL = os.getenv('WEB_APP_URL')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
RAW_GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')


def _sanitize_gemini_key(raw_key: Optional[str]) -> str:
    """Возвращает аккуратный API-ключ даже если переменная заполнена неаккуратно."""
    if not raw_key:
        return ""

    raw_key = raw_key.strip()

    decoded_key = unquote(raw_key)

    candidates = []
    for value in (raw_key, decoded_key):
        if value and value not in candidates:
            candidates.append(value)

    for candidate in candidates:
        match = re.search(r"AIza[0-9A-Za-z_\-]{30,}", candidate)
        if match:
            cleaned_key = match.group(0)
            if cleaned_key != raw_key:
                logging.warning(
                    "Переменная GEMINI_API_KEY содержала лишние символы. Используем аккуратный ключ: %s...",
                    cleaned_key[:8],
                )
            return cleaned_key

    return raw_key


GEMINI_API_KEY = _sanitize_gemini_key(RAW_GEMINI_API_KEY)
PORT = os.getenv('PORT', '8080') 

logging.basicConfig(level=logging.INFO)

if not all([BOT_TOKEN, WEB_APP_URL, GEMINI_API_KEY]):
    logging.critical("!!! ОШИБКА: Одна или несколько переменных (BOT_TOKEN, WEB_APP_URL, GEMINI_API_KEY) не найдены!")
    exit()

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- ТЕЛЕГРАМ-БОТ ---
@dp.message(Command("start"))
async def send_welcome(message: types.Message):
    web_app_button = InlineKeyboardButton(text="✨ Подобрать прическу", web_app=WebAppInfo(url=WEB_APP_URL))
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[web_app_button]])
    await message.answer(f"Привет, {message.from_user.full_name}! 👋\n\nНажмите на кнопку ниже, чтобы начать!", reply_markup=keyboard)

# --- ПРОКСИ-СЕРВЕР ---
async def proxy_handler(request):
    headers = {"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Methods": "POST, OPTIONS", "Access-Control-Allow-Headers": "Content-Type"}
    if request.method == 'OPTIONS':
        return web.Response(headers=headers)
    try:
        data = await request.json()
        target_api = data.get('target_api')
        payload = data.get('payload')

        if target_api == 'image':
            api_url = f"[https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-image-preview:generateContent?key=](https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-image-preview:generateContent?key=){GEMINI_API_KEY}"
        elif target_api == 'text':
            api_url = f"[https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-05-20:generateContent?key=](https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-05-20:generateContent?key=){GEMINI_API_KEY}"
        if target_api == 'image':
            api_url = (
                "https://generativelanguage.googleapis.com/v1beta/models/"
                "gemini-2.5-flash-image-preview:generateContent"
                f"?key={GEMINI_API_KEY}"
            )
        elif target_api == 'text':
            api_url = (
                "https://generativelanguage.googleapis.com/v1beta/models/"
                "gemini-2.5-flash-preview-05-20:generateContent"
                f"?key={GEMINI_API_KEY}"
            )
        else:
            return web.json_response({"error": {"message": "Invalid target_api"}}, status=400, headers=headers)

        async with aiohttp.ClientSession() as session:
            async with session.post(api_url, json=payload) as resp:
                return web.json_response(await resp.json(), status=resp.status, headers=headers)
    except Exception as e:
        logging.error(f"Proxy error: {e}")
        return web.json_response({"error": {"message": str(e)}}, status=500, headers=headers)

# --- ФУНКЦИИ ЗАПУСКА ---
async def start_bot_polling():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

async def start_web_server():
    # Увеличиваем максимальный размер принимаемого файла до 10MB
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
async def start_bot_polling():
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    except asyncio.CancelledError:
        logging.info("Остановка Telegram-бота...")
        raise
    finally:
        await bot.session.close()

async def start_web_server(stop_event: asyncio.Event):
    # Увеличиваем максимальный размер принимаемого файла до 10MB
    app = web.Application(client_max_size=1024**2 * 10)
    app.router.add_route('*', '/api/proxy', proxy_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', int(PORT))
    await site.start()
    logging.info(f"--> Веб-сервер (прокси) запущен на порту {PORT}")
    try:
        await stop_event.wait()
    finally:
        logging.info("Остановка веб-сервера (прокси)...")
        await runner.cleanup()

async def main():
    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def _handle_shutdown(sig: signal.Signals):
        logging.warning(f"Получен сигнал {sig.name}. Инициирована корректная остановка сервиса...")
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _handle_shutdown, sig)
        except NotImplementedError:
            # На платформах без поддержки сигналов (например, Windows) просто игнорируем
            logging.debug("Регистрация обработчика сигналов не поддерживается на этой платформе")

    bot_task = asyncio.create_task(start_bot_polling())
    web_task = asyncio.create_task(start_web_server(stop_event))

    await stop_event.wait()

    for task in (bot_task, web_task):
        task.cancel()

    await asyncio.gather(bot_task, web_task, return_exceptions=True)
    logging.info("Сервис завершил работу корректно.")

if __name__ == "__main__":
    asyncio.run(main())
