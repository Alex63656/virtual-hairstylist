import os
import base64
import io
import google.generativeai as genai
import telebot
from telebot.types import WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from flask import Flask, request, jsonify
from flask_cors import CORS
from PIL import Image

# --- Инициализация Flask ---
app = Flask(__name__)
CORS(app, origins=["*"], methods=["GET", "POST", "OPTIONS"], allow_headers=["Content-Type", "Authorization"])

# --- Настройка Telegram Bot ---
BOT_TOKEN = os.environ.get('BOT_TOKEN', '7854606797:AAFKsvnC8wNC56jX7SX7-suRCs85hBMQyuY')
WEBAPP_URL = os.environ.get('WEBAPP_URL', 'https://virtual-hairstylist-production.up.railway.app')

bot = None
if BOT_TOKEN:
    try:
        bot = telebot.TeleBot(BOT_TOKEN)
        
        @bot.message_handler(commands=['start'])
        def start_handler(message):
            # Создаем обычную клавиатуру на всю ширину
            keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
            webapp_button = KeyboardButton(
                text="✨ Подобрать прическу",
                web_app=WebAppInfo(url=f"{WEBAPP_URL}/")
            )
            keyboard.add(webapp_button)
            
            bot.send_message(
                message.chat.id, 
                "Привет! Я помогу тебе подобрать новую прическу с помощью ИИ! 💇‍♀️\n\nНажми кнопку ниже, чтобы начать:",
                reply_markup=keyboard
            )
        
        print(f"✅ Telegram Bot инициализирован с токеном: {BOT_TOKEN[:10]}...")
    except Exception as e:
        print(f"❌ Ошибка инициализации Telegram Bot: {e}")
        bot = None

# --- Настройка Gemini API ---
try:
    # API ключ вписан в код согласно вашему требованию.
    api_key = "AIzaSyCX-D5d5kXJrmyMZJREykCQAbx-bXqVCIk"
    
    genai.configure(api_key=api_key)
    
    # Модель для генерации/редактирования изображений. 
    image_generation_model = genai.GenerativeModel('gemini-2.5-flash-image')
    print("✅ Gemini API инициализирован")

except Exception as e:
    # Логируем критическую ошибку при запуске, чтобы она была видна в логах сервера
    app.logger.error(f"КРИТИЧЕСКАЯ ОШИБКА при инициализации Gemini: {e}")
    print(f"❌ Ошибка Gemini API: {e}")
    image_generation_model = None


# --- Вспомогательные функции ---
def base64_to_pil(base64_string: str) -> Image.Image:
    """Конвертирует base64 строку в объект PIL.Image для обработки."""
    # Восстанавливаем padding, если он был утерян при передаче
    missing_padding = len(base64_string) % 4
    if missing_padding:
        base64_string += '=' * (4 - missing_padding)
    
    try:
        image_data = base64.b64decode(base64_string)
        image = Image.open(io.BytesIO(image_data))
        return image
    except Exception as e:
        app.logger.error(f"Ошибка декодирования base64: {e}")
        raise ValueError("Некорректный формат изображения. Попробуйте другое фото.")


# --- Веб-приложение ---
@app.route('/')
def serve_webapp():
    """Раздача HTML приложения"""
    try:
        with open('virtual_hairstylist_bot_ru.html', 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return jsonify({"error": "Файл приложения не найден"}), 404

@app.route('/health')
def health_check():
    """Проверка состояния сервера"""
    return jsonify({
        "status": "ok", 
        "message": "Сервер AI Стилиста работает",
        "bot_status": "active" if bot else "inactive",
        "gemini_status": "active" if image_generation_model else "inactive"
    })

@app.route('/setup_webhook')
def setup_webhook_route():
    """Ручная настройка webhook"""
    if bot and BOT_TOKEN:
        try:
            webhook_url = f"{WEBAPP_URL}/telegram_webhook"
            result = bot.set_webhook(url=webhook_url)
            return jsonify({
                "success": result,
                "webhook_url": webhook_url,
                "message": "Webhook установлен!" if result else "Ошибка webhook"
            })
        except Exception as e:
            return jsonify({"error": str(e)})
    return jsonify({"error": "Бот не инициализирован"})

@app.route('/test_webhook_route')
def test_webhook_route():
    """Проверяем, существует ли маршрут webhook"""
    webhook_path = '/telegram_webhook'
    return jsonify({
        "webhook_path": webhook_path,
        "full_url": f"{WEBAPP_URL}{webhook_path}",
        "bot_token_exists": BOT_TOKEN is not None,
        "message": "Тест маршрута webhook"
    })

# --- Telegram Webhook ---
@app.route('/telegram_webhook', methods=['POST'])
def webhook():
    """Обработка webhook от Telegram"""
    print(f"🔥 WEBHOOK ПОЛУЧЕН! Данные: {request.get_data()}")
    
    if bot:
        try:
            json_string = request.get_data().decode('utf-8')
            print(f"📝 JSON: {json_string}")
            update = telebot.types.Update.de_json(json_string)
            bot.process_new_updates([update])
            print("✅ Обновление обработано!")
            return "OK"
        except Exception as e:
            print(f"❌ Ошибка webhook: {e}")
            app.logger.error(f"Ошибка webhook: {e}")
            return "ERROR", 500
    
    print("❌ Бот не инициализирован")
    return "Bot not initialized", 400

# --- API маршруты ---

# НОВЫЙ МАРШРУТ: /api/proxy - это то, что искал фронтенд!
@app.route('/api/proxy', methods=['POST', 'OPTIONS'], strict_slashes=False)
def handle_proxy():
    """Прокси маршрут для обработки запросов от фронтенда"""
    # Обрабатываем CORS preflight запросы
    if request.method == 'OPTIONS':
        return '', 200
    
    if not request.is_json:
        return jsonify({"error": "Неверный формат запроса. Ожидается JSON."}), 400

    data = request.get_json()
    target_api = data.get('target_api')
    payload = data.get('payload')
    
    if not target_api or not payload:
        return jsonify({"error": "Отсутствуют обязательные параметры: target_api и payload."}), 400
    
    try:
        if target_api == 'image':
            # Обрабатываем запрос на генерацию изображения
            contents = payload.get('contents', [])
            if not contents:
                return jsonify({"error": "Отсутствует содержимое для генерации."}), 400
            
            parts = contents[0].get('parts', [])
            if not parts:
                return jsonify({"error": "Отсутствуют части для генерации."}), 400
            
            # Извлекаем данные для Gemini
            prompt_text = ""
            images = []
            
            for part in parts:
                if 'text' in part:
                    prompt_text += part['text'] + " "
                elif 'inlineData' in part:
                    # Преобразуем base64 в PIL Image
                    image_b64 = part['inlineData']['data']
                    image_pil = base64_to_pil(image_b64)
                    images.append(image_pil)
            
            # ИСПРАВЛЕНИЕ: Создаем список ПРАВИЛЬНО - сначала текст, потом картинки!
            gemini_parts = []
            if prompt_text.strip():
                gemini_parts.append(prompt_text.strip())  # Добавляем текст ПЕРВЫМ!
            
            for img in images:
                gemini_parts.append(img)  # Добавляем изображения ПОСЛЕ текста!
            
            # Вызов Gemini API
            if not image_generation_model:
                return jsonify({"error": "Модель генерации изображений не инициализирована."}), 500
            
            # ИСПРАВЛЕНО: Убрал проблемные параметры!
            response = image_generation_model.generate_content(gemini_parts)
            
            # Ищем изображение в ответе
            generated_image_b64 = None
            
            # Способ 1: В response.parts
            if hasattr(response, 'parts'):
                for part in response.parts:
                    if hasattr(part, 'mime_type') and part.mime_type and part.mime_type.startswith('image/'):
                        img_bytes = part.inline_data.data
                        generated_image_b64 = base64.b64encode(img_bytes).decode('utf-8')
                        break
            
            # Способ 2: В candidates (если в способе 1 не нашли)
            if not generated_image_b64 and hasattr(response, 'candidates'):
                for candidate in response.candidates:
                    if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                        for part in candidate.content.parts:
                            if hasattr(part, 'inline_data') and part.inline_data:
                                img_bytes = part.inline_data.data
                                generated_image_b64 = base64.b64encode(img_bytes).decode('utf-8')
                                break
                        if generated_image_b64:
                            break
            
            if not generated_image_b64:
                # Дополнительная информация для отладки
                app.logger.error(f"Gemini ответ: {response}")
                raise ValueError("AI не вернул изображение в ответе. Попробуйте другое фото или описание.")
            
            # Формируем ответ в формате, который ожидает фронтенд
            return jsonify({
                "candidates": [{
                    "content": {
                        "parts": [{
                            "inlineData": {
                                "data": generated_image_b64,
                                "mimeType": "image/png"
                            }
                        }]
                    }
                }]
            })
            
        elif target_api == 'text':
            # Обрабатываем запрос на анализ текста
            contents = payload.get('contents', {})
            config = payload.get('config', {})
            
            parts = contents.get('parts', [])
            system_instruction = config.get('systemInstruction')
            
            # Извлекаем текст и изображение
            user_prompt = ""
            image_pil = None
            
            for part in parts:
                if 'text' in part:
                    user_prompt = part['text']
                elif 'inlineData' in part:
                    image_b64 = part['inlineData']['data']
                    image_pil = base64_to_pil(image_b64)
            
            if not user_prompt or not image_pil:
                return jsonify({"error": "Отсутствуют необходимые данные для анализа."}), 400
            
            # Создаем модель для анализа
            text_vision_model = genai.GenerativeModel(
                'gemini-2.5-flash',
                system_instruction=system_instruction if system_instruction else None
            )
            
            response = text_vision_model.generate_content([user_prompt, image_pil])
            
            # Формируем ответ в формате, который ожидает фронтенд
            return jsonify({
                "candidates": [{
                    "content": {
                        "parts": [{
                            "text": response.text
                        }]
                    }
                }]
            })
            
        else:
            return jsonify({"error": f"Неизвестный тип API: {target_api}"}), 400
            
    except Exception as e:
        app.logger.error(f"Ошибка в прокси: {e}")
        return jsonify({"error": f"Произошла ошибка: {str(e)}"}), 500

@app.route('/api/generate', methods=['POST'], strict_slashes=False)
def handle_generate():
    """
    Основной маршрут для изменения прически.
    strict_slashes=False делает маршрут нечувствительным к наличию / в конце URL.
    """
    if not image_generation_model:
        return jsonify({"error": "Серверная ошибка: модель генерации изображений не инициализирована."}), 500

    if not request.is_json:
        return jsonify({"error": "Неверный формат запроса. Ожидается JSON."}), 400

    data = request.get_json()
    client_photo_b64 = data.get('clientPhotoBase64')
    prompt = data.get('prompt')
    style_photo_b64 = data.get('stylePhotoBase64')

    if not client_photo_b64 or not prompt:
        return jsonify({"error": "Отсутствуют обязательные параметры: clientPhotoBase64 и prompt."}), 400

    try:
        # ИСПРАВЛЕНИЕ: Сначала текст, потом картинки!
        parts = []
        parts.append(prompt)  # Добавляем описание ПЕРВЫМ!
        
        client_photo_pil = base64_to_pil(client_photo_b64)
        parts.append(client_photo_pil)
        
        if style_photo_b64:
            style_photo_pil = base64_to_pil(style_photo_b64)
            parts.append(style_photo_pil)

        # ИСПРАВЛЕНО: Убрал проблемные параметры!
        response = image_generation_model.generate_content(parts)

        # Ищем изображение в ответе
        generated_image_b64 = None
        
        # Способ 1: В response.parts
        if hasattr(response, 'parts'):
            for part in response.parts:
                if hasattr(part, 'mime_type') and part.mime_type and part.mime_type.startswith('image/'):
                    img_bytes = part.inline_data.data
                    generated_image_b64 = base64.b64encode(img_bytes).decode('utf-8')
                    break
        
        # Способ 2: В candidates (если в способе 1 не нашли)
        if not generated_image_b64 and hasattr(response, 'candidates'):
            for candidate in response.candidates:
                if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                    for part in candidate.content.parts:
                        if hasattr(part, 'inline_data') and part.inline_data:
                            img_bytes = part.inline_data.data
                            generated_image_b64 = base64.b64encode(img_bytes).decode('utf-8')
                            break
                    if generated_image_b64:
                        break
        
        if not generated_image_b64:
            # Дополнительная информация для отладки
            app.logger.error(f"Gemini ответ: {response}")
            raise ValueError("AI не вернул изображение в ответе. Попробуйте другой запрос или фото.")

        return jsonify({"base64Image": generated_image_b64})

    except Exception as e:
        app.logger.error(f"Ошибка при генерации изображения: {e}")
        return jsonify({"error": f"Произошла ошибка на сервере при генерации: {str(e)}"}), 500


@app.route('/api/analyze', methods=['POST'], strict_slashes=False)
def handle_analyze():
    """
    Маршрут для текстового анализа фото (рекомендации, описание).
    """
    if not request.is_json:
        return jsonify({"error": "Неверный формат запроса. Ожидается JSON."}), 400

    data = request.get_json()
    system_prompt = data.get('systemPrompt')
    user_prompt = data.get('userPrompt')
    image_b64 = data.get('imageBase64')

    if not image_b64 or not user_prompt:
        return jsonify({"error": "Отсутствуют обязательные параметры: imageBase64 и userPrompt."}), 400

    try:
        image_pil = base64_to_pil(image_b64)
        
        # Модель для анализа фото и текста.
        text_vision_model = genai.GenerativeModel(
            'gemini-2.5-flash',
            system_instruction=system_prompt if system_prompt else None
        )

        response = text_vision_model.generate_content([user_prompt, image_pil])

        return jsonify({"text": response.text})

    except Exception as e:
        app.logger.error(f"Ошибка при анализе изображения: {e}")
        return jsonify({"error": f"Произошла ошибка на сервере при анализе: {str(e)}"}), 500

# --- Запуск приложения ---
if __name__ == '__main__':
    # Эта часть выполняется только при локальном запуске (python bot.py).
    # На Railway используется Gunicorn из Procfile.
    port = int(os.environ.get('PORT', 8080))
    print(f"🚀 Запуск сервера на порту {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
