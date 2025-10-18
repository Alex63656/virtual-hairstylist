import type { GenerateImageParams, AnalyzeImageParams } from '../types';

// Эта функция будет общаться с нашим прокси-сервером в bot.py
const callProxy = async (targetApi: 'image' | 'text', payload: object) => {
  try {
    const response = await fetch('/api/proxy', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        target_api: targetApi,
        payload: payload,
      }),
    });

    if (!response.ok) {
      const errorData = await response.json();
      // Пытаемся извлечь сообщение об ошибке от Gemini
      const errorMessage = errorData?.error?.message || `HTTP error! status: ${response.status}`;
      throw new Error(errorMessage);
    }
    
    return await response.json();
  } catch (error) {
    console.error(`Error calling proxy for ${targetApi}:`, error);
    // Передаем ошибку дальше, чтобы ее можно было показать пользователю
    throw error;
  }
};


export const generateImage = async ({ clientPhotoBase64, stylePhotoBase64, prompt }: GenerateImageParams): Promise<string> => {
  const parts: any[] = [
    { text: prompt },
    {
      inlineData: {
        mimeType: "image/jpeg",
        data: clientPhotoBase64,
      },
    },
  ];

  if (stylePhotoBase64) {
    parts.push({ text: "USE THIS PHOTO AS A STYLE REFERENCE FOR THE HAIRSTYLE. Match the color, length, texture, and style as closely as possible:" });
    parts.push({
      inlineData: {
        mimeType: "image/jpeg",
        data: stylePhotoBase64,
      },
    });
  }

  const payload = {
    contents: [{ parts }],
    config: {
      responseModalities: ["IMAGE"],
    },
  };

  const response = await callProxy('image', payload);
  
  const firstPart = response.candidates?.[0]?.content?.parts?.[0];
  if (firstPart && 'inlineData' in firstPart && firstPart.inlineData) {
    return firstPart.inlineData.data;
  }
  
  throw new Error('AI не вернул изображение. Попробуйте другой запрос или фото.');
};

export const analyzeImageForText = async ({ systemPrompt, userPrompt, imageBase64 }: AnalyzeImageParams): Promise<string> => {
  const payload = {
    contents: {
        parts: [
            { text: userPrompt },
            {
                inlineData: {
                    mimeType: "image/jpeg",
                    data: imageBase64,
                },
            },
        ]
    },
    config: {
      systemInstruction: systemPrompt,
    }
  };
  
  const response = await callProxy('text', payload);
  
  // Прокси возвращает полный ответ от Gemini, нам нужно извлечь текст
  if (response.candidates?.[0]?.content?.parts?.[0]?.text) {
      return response.candidates[0].content.parts[0].text;
  }

  throw new Error('AI не смог проанализировать изображение.');
};