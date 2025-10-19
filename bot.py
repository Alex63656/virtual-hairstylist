import os
import google.generativeai as genai
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from PIL import Image
import io
import base64

# --- Конфигурация ---
# Настройка Flask приложения
app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app) # Включаем CORS для всех маршрутов

# Конфигурация Gemini API
# !!! ВАЖНО: Вставьте ваш API ключ сюда, вместо "AIzaSyCX-D5d5kXJrmyMZJREykCQAbx-bXqVCIk" !!!
API_KEY = "AIzaSyCX-D5d5kXJrmyMZJREykCQAbx-bXqVCIk" 

try:
    if not API_KEY or API_KEY == "AIzaSyCX-D5d5kXJrmyMZJREykCQAbx-bXqVCIk":
        raise ValueError("AIzaSyCX-D5d5kXJrmyMZJREykCQAbx-bXqVCIk")
    genai.configure(api_key=API_KEY)
except ValueError as e:
    print(f"Критическая ошибка: {e}")
    # Приложение не сможет запуститься без ключа API

# --- Вспомогательные функции ---
def base64_to_pil_image(base64_string):
    """Конвертирует строку base64 в объект изображения PIL."""
    if "base64," in base64_string:
        base64_string = base64_string.split("base64,")[1]
    image_data = base64.b64decode(base64_string)
    return Image.open(io.BytesIO(image_data))

def pil_image_to_blob(image, mime_type='image/jpeg'):
    """Конвертирует объект изображения PIL в blob для Gemini API."""
    buffered = io.BytesIO()
    if image.mode != 'RGB':
        image = image.convert('RGB')
    image.save(buffered, format=mime_type.split('/')[1].upper())
    img_byte = buffered.getvalue()
    return {'mime_type': mime_type, 'data': base64.b64encode(img_byte).decode('utf-8')}

# --- Маршруты API ---

@app.route('/api/generate', methods=['POST'])
def generate_style():
    """Эндпоинт API для генерации нового изображения прически."""
    if not request.is_json:
        return jsonify({"error": "Запрос должен быть в формате JSON"}), 400

    data = request.get_json()
    client_photo_b64 = data.get('clientPhotoBase64')
    style_photo_b64 = data.get('stylePhotoBase64')
    prompt = data.get('prompt')

    if not client_photo_b64 or not prompt:
        return jsonify({"error": "Отсутствует фото клиента или текстовый промпт"}), 400

    try:
        parts = [prompt]
        
        client_image = base64_to_pil_image(client_photo_b64)
        client_blob = pil_image_to_blob(client_image)
        parts.append(client_blob)
        
        if style_photo_b64:
            style_image = base64_to_pil_image(style_photo_b64)
            style_blob = pil_image_to_blob(style_image)
            parts.append(style_blob)

        model = genai.GenerativeModel('gemini-2.5-flash-image')
        response = model.generate_content(
            parts,
            generation_config={"response_modalities": ["IMAGE"]}
        )

        if response.candidates and response.candidates[0].content.parts:
            image_part = response.candidates[0].content.parts[0]
            if image_part.inline_data:
                generated_image_b64 = image_part.inline_data.data
                return jsonify({"base64Image": generated_image_b64})

        raise Exception("Модель AI не вернула изображение.")

    except Exception as e:
        print(f"Ошибка при генерации изображения: {e}")
        if "SAFETY" in str(e).upper():
             return jsonify({"error": "Запрос заблокирован из-за нарушения правил безопасности. Попробуйте другое фото или описание."}), 500
        return jsonify({"error": f"Внутренняя ошибка сервера: Попробуйте позже."}), 500


@app.route('/api/analyze', methods=['POST'])
def analyze_text():
    """Эндпоинт API для анализа изображения и возврата текста."""
    if not request.is_json:
        return jsonify({"error": "Запрос должен быть в формате JSON"}), 400

    data = request.get_json()
    system_prompt = data.get('systemPrompt')
    user_prompt = data.get('userPrompt')
    image_b64 = data.get('imageBase64')

    if not image_b64 or not user_prompt:
        return jsonify({"error": "Отсутствует изображение или пользовательский промпт"}), 400

    try:
        image = base64_to_pil_image(image_b64)
        image_blob = pil_image_to_blob(image)
        parts = [user_prompt, image_blob]
        
        model = genai.GenerativeModel(
            'gemini-2.5-flash',
            system_instruction=system_prompt
        )
        response = model.generate_content(parts)

        return jsonify({"text": response.text})

    except Exception as e:
        print(f"Ошибка при анализе текста: {e}")
        if "SAFETY" in str(e).upper():
             return jsonify({"error": "Запрос заблокирован из-за нарушения правил безопасности. Попробуйте другое фото."}), 500
        return jsonify({"error": f"Внутренняя ошибка сервера: Попробуйте позже."}), 500

# --- Отправка статических файлов (вашего сайта) ---

@app.route('/')
def index():
    """Отдает главный файл index.html."""
    return send_from_directory('.', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    """Отдает другие статические файлы (например, index.tsx)."""
    return send_from_directory('.', path)

# --- Запуск сервера ---

if __name__ == '__main__':
    # Gunicorn будет использовать этот 'app' объект
    # Для локального запуска будет использоваться порт 8080
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
