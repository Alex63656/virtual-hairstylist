import React, { useRef, useCallback } from 'react';

interface ImageUploaderProps {
  onFileSelect: (file: File) => void;
  preview: string | null;
  children: React.ReactNode;
}

const ImageUploader: React.FC<ImageUploaderProps> = ({ onFileSelect, preview, children }) => {
  const inputRef = useRef<HTMLInputElement>(null);

  const processFile = useCallback((file: File) => {
    if (!file.type.startsWith('image/')) {
      alert('Пожалуйста, выберите файл изображения.');
      return;
    }
    onFileSelect(file);
  }, [onFileSelect]);

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      processFile(file);
    }
  };

  const handleDrop = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    const file = event.dataTransfer.files?.[0];
    if (file) {
      processFile(file);
    }
  };

  const handleClick = () => {
    inputRef.current?.click();
  };

  return (
    <div>
      <div
        onDragOver={(e) => e.preventDefault()}
        onDrop={handleDrop}
        onClick={handleClick}
        className="image-container relative bg-black/20 rounded-lg flex items-center justify-center border-2 border-dashed border-white/20 hover:border-[#e0d8d0] transition-colors cursor-pointer"
        style={{ height: '100%', minHeight: '12rem' }}
      >
        {!preview ? (
          <div className="text-center text-[#e0d8d0]/70 placeholder">
            {children}
          </div>
        ) : (
          <img src={preview} alt="Preview" className="rounded-lg h-full w-full object-contain" />
        )}
      </div>
      <input
        type="file"
        ref={inputRef}
        onChange={handleFileSelect}
        accept="image/*"
        className="hidden"
      />
    </div>
  );
};

export default ImageUploader;