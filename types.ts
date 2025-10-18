export interface PhotoState {
  file: File | null;
  preview: string | null;
  base64: string | null;
}

export interface ModalState {
  visible: boolean;
  title: string;
  content: string;
  type: 'image' | 'text' | 'animation';
}

export interface GenerateImageParams {
  clientPhotoBase64: string;
  prompt: string;
  stylePhotoBase64?: string | null;
}

export interface AnalyzeImageParams {
  systemPrompt: string;
  userPrompt: string;
  imageBase64: string;
}

// This is for Telegram Web App integration
declare global {
  interface Window {
    Telegram: {
      WebApp: {
        ready: () => void;
        expand: () => void;
        // You can add other properties and methods you might use
      };
    };
  }
}