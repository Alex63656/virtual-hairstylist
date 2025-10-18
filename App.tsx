import React, { useState, useCallback, useEffect } from 'react';
import useLocalStorage from './hooks/useLocalStorage';
import type { PhotoState, ModalState } from './types';
import { generateImage, analyzeImageForText } from './services/geminiService';
import { CORRECT_PROMO_CODE, TEST_PROMO_CODE, GENERATION_SYSTEM_PROMPT, SUGGESTION_SYSTEM_PROMPT, DESCRIBE_SYSTEM_PROMPT } from './constants';
import ImageUploader from './components/ImageUploader';
import Modal from './components/Modal';
import Loader from './components/Loader';
import { ImageIcon, StyleIcon, ResultIcon, MagicIcon, DescribeIcon, DownloadIcon, AnimationIcon } from './components/icons';

const initialPhotoState: PhotoState = { file: null, preview: null, base64: null };
const initialModalState: ModalState = { visible: false, title: '', content: '', type: 'text' };

const addWatermark = (base64Image: string): Promise<string> => {
  return new Promise((resolve) => {
    const img = new Image();
    img.src = base64Image.startsWith('data:image') ? base64Image : `data:image/png;base64,${base64Image}`;
    img.onload = () => {
      const canvas = document.createElement('canvas');
      canvas.width = img.width;
      canvas.height = img.height;
      const ctx = canvas.getContext('2d');
      if (!ctx) {
        resolve(`data:image/png;base64,${base64Image}`);
        return;
      }

      ctx.drawImage(img, 0, 0);

      const watermarkText = 'MISS SLIVKI AI';
      const fontSize = Math.max(12, Math.sqrt(canvas.width * canvas.height) / 35);
      ctx.font = `bold ${fontSize}px Inter`;
      ctx.fillStyle = 'rgba(255, 255, 255, 0.1)';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      
      const angle = -25 * Math.PI / 180;
      ctx.rotate(angle);

      const textWidth = ctx.measureText(watermarkText).width;
      const stepX = textWidth * 1.5;
      const stepY = fontSize * 4;
      
      const startX = -canvas.width * 2;
      const startY = -canvas.height * 2;
      const endX = canvas.width * 3;
      const endY = canvas.height * 3;

      for (let y = startY; y < endY; y += stepY) {
        for (let x = startX; x < endX; x += stepX) {
          ctx.fillText(watermarkText, x, y);
        }
      }
      
      ctx.rotate(-angle);

      resolve(canvas.toDataURL('image/png'));
    };
    img.onerror = () => {
      resolve(`data:image/png;base64,${base64Image}`);
    };
  });
};


const downloadImage = (dataUrl: string, filename: string) => {
  const link = document.createElement('a');
  link.href = dataUrl;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
};


const fileToBase64 = (file: File): Promise<string> => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.readAsDataURL(file);
    reader.onload = () => resolve((reader.result as string).split(',')[1]);
    reader.onerror = error => reject(error);
  });
};

function App() {
  const [clientPhoto, setClientPhoto] = useState<PhotoState>(initialPhotoState);
  const [stylePhoto, setStylePhoto] = useState<PhotoState>(initialPhotoState);
  const [generatedImage, setGeneratedImage] = useState<{ preview: string | null }>({ preview: null });
  const [prompt, setPrompt] = useState('');
  const [loading, setLoading] = useState(false);
  const [statusText, setStatusText] = useState('Магия начинается...');
  const [modal, setModal] = useState<ModalState>(initialModalState);
  const [promoCode, setPromoCode] = useState('');

  const [generationCount, setGenerationCount] = useLocalStorage('generationCount_v2', 0);
  const [maxGenerations, setMaxGenerations] = useLocalStorage('maxGenerations_v2', 10);
  const [isPro, setIsPro] = useLocalStorage('isPro_v2', false);
  const [generationHistory, setGenerationHistory] = useLocalStorage<string[]>('generationHistory_v1', []);
  const [selectedImages, setSelectedImages] = useState<string[]>([]);

  useEffect(() => {
    // This hook is for Telegram Mini App integration
    if (window.Telegram && window.Telegram.WebApp) {
      window.Telegram.WebApp.ready();
      window.Telegram.WebApp.expand();
    }
  }, []);

  const showErrorModal = useCallback((message: string) => {
    setLoading(false);
    setModal({ visible: true, title: 'Ошибка', content: message, type: 'text' });
  }, []);

  const handleFileSelect = useCallback(async (file: File, photoType: 'client' | 'style') => {
    const preview = URL.createObjectURL(file);
    try {
      const base64 = await fileToBase64(file);
      const setter = photoType === 'client' ? setClientPhoto : setStylePhoto;
      setter({ file, preview, base64 });
    } catch (error) {
      console.error("Error converting file to base64", error);
      showErrorModal('Не удалось обработать файл.');
    }
  }, [showErrorModal]);

  const handleGenerate = useCallback(async () => {
    if (!clientPhoto.base64) {
      showErrorModal("Пожалуйста, загрузите ваше фото.");
      return;
    }
    if (!isPro && generationCount >= maxGenerations) {
      showErrorModal(`Вы исчерпали лимит бесплатных генераций (${maxGenerations}). Введите промокод, чтобы продолжить.`);
      return;
    }

    setLoading(true);
    setStatusText('Создание нового образа...');

    let userPrompt = prompt || "a new hairstyle";
    const fullPrompt = `${GENERATION_SYSTEM_PROMPT}\n\nCLIENT REQUEST: ${userPrompt}`;

    try {
      const resultBase64 = await generateImage({
        clientPhotoBase64: clientPhoto.base64,
        stylePhotoBase64: stylePhoto.base64,
        prompt: fullPrompt,
      });
      const watermarkedDataUrl = await addWatermark(resultBase64);
      setGeneratedImage({ preview: watermarkedDataUrl });

      if (!isPro) {
        setGenerationCount(c => c + 1);
      }
      setGenerationHistory(prev => [watermarkedDataUrl, ...prev].slice(0, 20));

    } catch (error) {
      console.error("Image generation error:", error);
      showErrorModal(error instanceof Error ? error.message : 'Произошла неизвестная ошибка.');
    } finally {
      setLoading(false);
    }
  }, [clientPhoto.base64, stylePhoto.base64, prompt, isPro, generationCount, maxGenerations, setGenerationCount, showErrorModal, setGenerationHistory]);

  const handleLLMCall = useCallback(async (systemPrompt: string, userPrompt: string, imageBase64: string | null) => {
    if (!imageBase64) {
      showErrorModal('Пожалуйста, сначала загрузите фото.');
      return null;
    }
    setLoading(true);
    setStatusText('Анализ...');
    try {
      const result = await analyzeImageForText({ systemPrompt, userPrompt, imageBase64 });
      return result;
    } catch (error) {
      console.error("LLM call error:", error);
      showErrorModal(error instanceof Error ? error.message : 'Не удалось получить ответ от AI.');
      return null;
    } finally {
      setLoading(false);
    }
  }, [showErrorModal]);

  const getHairstyleSuggestions = async () => {
    const result = await handleLLMCall(SUGGESTION_SYSTEM_PROMPT, "Посоветуй, какие прически мне подойдут?", clientPhoto.base64);
    if (result) {
      setModal({ visible: true, title: 'Рекомендации по прическам', content: result, type: 'text' });
    }
  };

  const describeHairstyle = async () => {
    const result = await handleLLMCall(DESCRIBE_SYSTEM_PROMPT, "Опиши эту прическу.", stylePhoto.base64);
    if (result) {
      setPrompt(result);
    }
  };

  const applyPromoCode = () => {
    const code = promoCode.trim().toUpperCase();
    if (code === CORRECT_PROMO_CODE) {
      setIsPro(true);
      setModal({ visible: true, title: 'Успех!', content: 'Промокод для PRO-доступа успешно применен! Все ограничения сняты.', type: 'text' });
    } else if (code === TEST_PROMO_CODE) {
      setMaxGenerations(g => g + 30);
      setModal({ visible: true, title: 'Успех!', content: 'Вам добавлено 30 генераций!', type: 'text' });
    } else {
      setModal({ visible: true, title: 'Ошибка', content: 'Неверный промокод.', type: 'text' });
    }
    setPromoCode('');
  };

  const resetAll = () => {
    setClientPhoto(initialPhotoState);
    setStylePhoto(initialPhotoState);
    setGeneratedImage({ preview: null });
    setPrompt('');
    setGenerationHistory([]);
    setSelectedImages([]);
  };

  const handleImageSelection = (image: string) => {
    setSelectedImages(prev => 
        prev.includes(image) 
            ? prev.filter(item => item !== image) 
            : [...prev, image]
    );
  };

  const handleDownloadSelected = () => {
    if (selectedImages.length === 0) return;
    selectedImages.forEach((image, index) => {
        downloadImage(image, `miss-slivki-ai-style-${Date.now()}-${index + 1}.png`);
    });
  };

  const viewHistoryImage = (image: string) => {
    setModal({
        visible: true,
        title: 'Сгенерированный образ',
        content: image,
        type: 'image'
    });
  };

  const canGenerate = !loading && clientPhoto.file && (!!prompt || !!stylePhoto.file) && (isPro || generationCount < maxGenerations);

  return (
    <div className="container mx-auto max-w-4xl p-4">
      <header className="text-center my-6">
        <img src="https://imagee.ru/uploads/img_68f3f8d2667e95.52862117.jpg" alt="MISS SLIVKI Logo" className="mx-auto h-24 w-auto mb-4 rounded-xl"/>
        <h1 className="text-4xl md:text-5xl font-bold tracking-tight">MISS SLIVKI <span className="text-[#f2ebe5]">AI</span></h1>
        <p className="mt-2 text-lg">Примерьте новый образ за секунды</p>
      </header>
      
      <div className="mb-8 bg-black/10 backdrop-blur-md border border-white/20 rounded-2xl p-4 text-base">
        <h4 className="font-semibold text-lg mb-2 text-center">💡 Советы для лучшего результата</h4>
        <ul className="list-disc list-inside space-y-1">
          <li><b>Фото клиента:</b> Загружайте фото анфас, с хорошим освещением, где волосы четко видны и не перекрыты руками или предметами.</li>
          <li><b>Фото-пример:</b> Используйте изображения, где прическа хорошо видна на модели, смотрящей прямо в камеру.</li>
          <li><b>Описание:</b> Описание надо писать только тогда, когда нет фото-примера! Будьте конкретны. Указывайте цвет, длину, наличие челки и тип укладки (например, 'длинные прямые платиновые волосы с челкой').</li>
        </ul>
      </div>

      {!isPro && (
        <div className="mb-6 bg-black/10 backdrop-blur-md border border-white/20 rounded-2xl p-4 text-center">
          <p className="mb-2 font-semibold">Осталось бесплатных генераций: <span className="text-[#f2ebe5] text-lg">{Math.max(0, maxGenerations - generationCount)}</span> / <span>{maxGenerations}</span></p>
          <div className="flex justify-center mt-2">
            <input type="text" value={promoCode} onChange={e => setPromoCode(e.target.value)} onKeyUp={e => e.key === 'Enter' && applyPromoCode()} className="bg-black/20 border border-white/20 text-[#e0d8d0] text-sm rounded-lg focus:ring-[#e0d8d0] focus:border-[#e0d8d0] block w-full md:w-1/2 p-2.5 placeholder:text-[#e0d8d0]/60" placeholder="Введите промокод"/>
            <button onClick={applyPromoCode} className="ml-2 bg-green-600 hover:bg-green-700 text-white font-bold py-2 px-4 rounded-lg">Применить</button>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 items-start">
        <div className="bg-black/10 backdrop-blur-md border border-white/20 rounded-2xl p-6 space-y-6">
          <div>
            <h3 className="text-lg font-semibold mb-3 border-b-2 border-[#e0d8d0]/80 pb-2">1. Загрузите ваше фото</h3>
            <div className="h-64">
                <ImageUploader onFileSelect={(file) => handleFileSelect(file, 'client')} preview={clientPhoto.preview}>
                    <ImageIcon />
                    <p className="mt-2">Нажмите или перетащите фото</p>
                </ImageUploader>
            </div>
            {clientPhoto.preview && (
              <button onClick={getHairstyleSuggestions} disabled={loading} className="w-full mt-3 bg-transparent border border-[#e0d8d0]/80 hover:bg-[#e0d8d0]/10 disabled:opacity-50 text-[#e0d8d0] font-semibold py-2 px-4 rounded-lg transition flex items-center justify-center">
                {loading ? 'Анализ...' : <><MagicIcon /> Подобрать прическу по фото</>}
              </button>
            )}
          </div>
          <div>
            <h3 className="text-lg font-semibold mb-3 border-b-2 border-[#e0d8d0]/80 pb-2">2. Опишите или покажите прическу</h3>
            <textarea value={prompt} onChange={e => setPrompt(e.target.value)} rows={3} className="w-full bg-black/20 border-2 border-white/20 rounded-lg p-3 focus:ring-2 focus:ring-[#e0d8d0] focus:border-[#e0d8d0] transition placeholder:text-[#e0d8d0]/60" placeholder="Например: длинные волнистые волосы медного цвета..."></textarea>
            <p className="text-center text-[#e0d8d0]/70 my-2">-- ИЛИ --</p>
             <div className="h-48">
                <ImageUploader onFileSelect={(file) => handleFileSelect(file, 'style')} preview={stylePhoto.preview}>
                    <StyleIcon />
                    <p className="mt-2">Загрузите фото-пример</p>
                </ImageUploader>
             </div>
            {stylePhoto.preview && (
              <button onClick={describeHairstyle} disabled={loading} className="w-full mt-3 bg-transparent border border-[#e0d8d0]/80 hover:bg-[#e0d8d0]/10 disabled:opacity-50 text-[#e0d8d0] font-semibold py-2 px-4 rounded-lg transition flex items-center justify-center">
                {loading ? 'Описание...' : <><DescribeIcon /> Описать прическу с фото</>}
              </button>
            )}
          </div>
          <button onClick={() => handleGenerate()} disabled={!canGenerate} className="w-full bg-[#e0d8d0] text-[#4f4a45] hover:bg-[#d1c8c0] disabled:bg-[#e0d8d0]/50 disabled:text-[#4f4a45]/50 disabled:cursor-not-allowed font-bold py-3 px-4 rounded-lg text-lg transition transform hover:scale-105">
            {loading ? 'Создание...' : 'Сгенерировать образ'}
          </button>
          <button onClick={resetAll} className="w-full bg-red-600 hover:bg-red-700 text-white font-bold py-2 px-4 rounded-lg transition">СБРОС</button>
        </div>

        <div className="bg-black/10 backdrop-blur-md border border-white/20 rounded-2xl p-6 space-y-6">
          <h3 className="text-lg font-semibold mb-3 border-b-2 border-[#e0d8d0]/80 pb-2">3. Результат</h3>
          <div className="relative bg-black/20 rounded-lg min-h-[256px] flex items-center justify-center border-2 border-white/20 aspect-square">
            {loading && <Loader statusText={statusText} />}
            {!loading && !generatedImage.preview && (
              <div className="text-center text-[#e0d8d0]/70">
                <ResultIcon/>
                <p className="mt-2">Здесь появится ваша новая прическа</p>
              </div>
            )}
            {!loading && generatedImage.preview && (
              <img src={generatedImage.preview} alt="Сгенерированное изображение" className="rounded-lg max-h-full w-auto max-w-full object-contain" />
            )}
          </div>
          {generatedImage.preview && (
            <div className="grid grid-cols-1 gap-4">
              <button onClick={() => setModal({ visible: true, title: 'Анимация До/После', content: '', type: 'animation' })} disabled={loading} className="w-full bg-transparent border border-[#e0d8d0]/80 hover:bg-[#e0d8d0]/10 disabled:opacity-50 text-[#e0d8d0] font-semibold py-2 px-4 rounded-lg transition flex items-center justify-center">
                <AnimationIcon /> Анимация До/После
              </button>
            </div>
          )}
        </div>
      </div>
      
      {generationHistory.length > 0 && (
        <div className="mt-8 bg-black/10 backdrop-blur-md border border-white/20 rounded-2xl p-6">
          <h3 className="text-xl font-semibold mb-4 text-center">История генераций</h3>
          <div className="flex justify-center mb-4">
            <button 
              onClick={handleDownloadSelected} 
              disabled={selectedImages.length === 0}
              className="bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 disabled:cursor-not-allowed text-white font-semibold py-2 px-6 rounded-lg transition flex items-center justify-center"
            >
              <DownloadIcon /> Скачать выбранные ({selectedImages.length})
            </button>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
            {generationHistory.map((imgSrc, index) => (
              <div key={index} className="relative group aspect-square bg-black/20 rounded-lg">
                <img 
                  src={imgSrc} 
                  alt={`Generated style ${index + 1}`} 
                  className="w-full h-full object-contain rounded-lg cursor-pointer"
                  onClick={() => viewHistoryImage(imgSrc)}
                />
                <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center cursor-pointer pointer-events-none">
                  <p className="text-white text-lg font-bold">Просмотр</p>
                </div>
                <input
                  type="checkbox"
                  checked={selectedImages.includes(imgSrc)}
                  onChange={() => handleImageSelection(imgSrc)}
                  className="absolute top-2 right-2 h-6 w-6 rounded-md text-blue-500 bg-gray-100 border-gray-300 focus:ring-blue-500 dark:focus:ring-blue-600 dark:ring-offset-gray-800 focus:ring-2 dark:bg-gray-700 dark:border-gray-600 cursor-pointer"
                />
              </div>
            ))}
          </div>
        </div>
      )}

      <Modal modal={modal} closeModal={() => setModal(initialModalState)} clientPhoto={clientPhoto} generatedImage={generatedImage}/>
    </div>
  );
}

export default App;