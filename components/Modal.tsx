import React, { useEffect, useState } from 'react';
import type { ModalState, PhotoState } from '../types';

interface ModalProps {
  modal: ModalState;
  closeModal: () => void;
  clientPhoto: PhotoState;
  generatedImage: { preview: string | null };
}

const Modal: React.FC<ModalProps> = ({ modal, closeModal, clientPhoto, generatedImage }) => {
  const [currentImage, setCurrentImage] = useState<string | null>(null);

  useEffect(() => {
    let timer: ReturnType<typeof setInterval> | null = null;
    if (modal.visible && modal.type === 'animation') {
      setCurrentImage(clientPhoto.preview); // Start with the original photo
      timer = setInterval(() => {
        setCurrentImage(prev => 
          prev === clientPhoto.preview ? generatedImage.preview : clientPhoto.preview
        );
      }, 1500);
    }
    return () => {
      if (timer) {
        clearInterval(timer);
      }
    };
  }, [modal.visible, modal.type, clientPhoto.preview, generatedImage.preview]);

  if (!modal.visible) return null;

  const getImageSrcForAnimation = () => {
      if (!currentImage) return clientPhoto.preview || '';
      return currentImage.startsWith('data:image') ? currentImage : `data:image/png;base64,${currentImage}`;
  }


  const renderContent = () => {
    switch (modal.type) {
      case 'image':
        return (
          <img src={modal.content} className="max-w-full max-h-[70vh] rounded-lg mx-auto object-contain" alt="Modal content" />
        );
      case 'animation':
        return (
          <div className="relative w-full" style={{ paddingBottom: '100%' }}>
              <img 
                  src={getImageSrcForAnimation()}
                  className="absolute top-0 left-0 w-full h-full object-contain rounded-lg"
                  alt="Animation frame"
              />
          </div>
        );
      case 'text':
        return (
          <div 
            className="text-left text-[#c7bfb8] whitespace-pre-wrap max-h-[60vh] overflow-y-auto"
            dangerouslySetInnerHTML={{ __html: modal.content.replace(/\*/g, '•') }} 
          />
        );
      default:
        return null;
    }
  };

  return (
    <div 
      className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center p-4 z-50" 
      onClick={closeModal}
    >
      <div 
        className="bg-[#4a413c] border border-white/20 rounded-2xl shadow-lg max-w-lg w-full p-6 text-center modal-image-animation" 
        onClick={(e) => e.stopPropagation()}
      >
        <h3 className="text-2xl font-bold mb-4">{modal.title}</h3>
        <div className="mb-4">{renderContent()}</div>
        <button 
          onClick={closeModal} 
          className="bg-[#e0d8d0] hover:bg-[#d1c8c0] text-[#4f4a45] font-bold py-2 px-6 rounded-lg transition"
        >
          Закрыть
        </button>
      </div>
    </div>
  );
};

export default Modal;