import React, { useState } from 'react';
import { Package } from 'lucide-react';

interface PartImageProps {
  src: string | null | undefined;
  alt: string;
  className?: string;
}

export const PartImage: React.FC<PartImageProps> = ({ src, alt, className = '' }) => {
  const [errored, setErrored] = useState(false);

  if (!src || errored) {
    return (
      <div
        className={`flex items-center justify-center bg-slate-100 ${className}`}
        aria-label={`No image for ${alt}`}
      >
        <Package className="w-10 h-10 text-slate-300" aria-hidden="true" />
      </div>
    );
  }

  return (
    <img
      src={src}
      alt={alt}
      onError={() => setErrored(true)}
      className={`object-cover ${className}`}
      loading="lazy"
    />
  );
};

