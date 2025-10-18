import React from 'react';

const Loader: React.FC<{ statusText: string }> = ({ statusText }) => {
  return (
    <div className="flex flex-col items-center justify-center absolute inset-0">
      <div className="animate-spin ease-linear rounded-full border-8 border-t-8 border-[#e0d8d0]/30 border-t-[#e0d8d0] h-24 w-24 mb-4"></div>
      <p className="text-lg text-[#e0d8d0]">{statusText}</p>
    </div>
  );
};

export default Loader;