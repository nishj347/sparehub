import React, { useRef, useState } from 'react';
import { getAssetUrl } from '../../../lib/assetUrl';

interface ImageUploaderProps {
  currentImageUrl?: string | null;
  onFileSelect: (file: File | null) => void;
  onRemoveCurrent?: () => void;
  disabled?: boolean;
}

const MAX_BYTES = 5 * 1024 * 1024; // 5 MB
const ALLOWED_TYPES = ['image/jpeg', 'image/png', 'image/webp'];

export const ImageUploader: React.FC<ImageUploaderProps> = ({
  currentImageUrl,
  onFileSelect,
  onRemoveCurrent,
  disabled = false,
}) => {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  const displayUrl = previewUrl || getAssetUrl(currentImageUrl);

  const handleValidateAndSelect = (file: File) => {
    setError(null);

    // Validate type
    const isValidType =
      ALLOWED_TYPES.includes(file.type) ||
      /\.(jpe?g|png|webp)$/i.test(file.name);
    if (!isValidType) {
      setError('Only JPEG, PNG, and WebP images are allowed.');
      return;
    }

    // Validate size
    if (file.size > MAX_BYTES) {
      setError('Image file size exceeds maximum limit of 5MB.');
      return;
    }

    // Generate local preview
    const objectUrl = URL.createObjectURL(file);
    setPreviewUrl(objectUrl);
    onFileSelect(file);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      handleValidateAndSelect(e.target.files[0]);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (disabled) return;
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleValidateAndSelect(e.dataTransfer.files[0]);
    }
  };

  const handleRemove = () => {
    setPreviewUrl(null);
    setError(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
    onFileSelect(null);
    if (onRemoveCurrent) {
      onRemoveCurrent();
    }
  };

  return (
    <div className="space-y-2">
      <span className="text-xs font-semibold uppercase tracking-wider text-slate-600 block">
        Part Photograph
      </span>

      {error && (
        <div className="p-2.5 bg-rose-50 border border-rose-200 rounded-lg text-xs text-rose-700">
          {error}
        </div>
      )}

      <div className="flex flex-col sm:flex-row items-center gap-4">
        {/* Image preview box */}
        <div className="w-28 h-28 rounded-xl border border-slate-200 bg-slate-50 flex items-center justify-center overflow-hidden shrink-0 shadow-sm relative group">
          {displayUrl ? (
            <img
              src={displayUrl}
              alt="Part preview"
              className="w-full h-full object-cover"
            />
          ) : (
            <div className="flex flex-col items-center justify-center text-slate-300">
              <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={1.5}
                  d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
                />
              </svg>
              <span className="text-[10px] text-slate-400 mt-1">No Image</span>
            </div>
          )}
        </div>

        {/* Drop zone / selector */}
        <div
          onDragOver={(e) => {
            e.preventDefault();
            setIsDragging(true);
          }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={handleDrop}
          onClick={() => !disabled && fileInputRef.current?.click()}
          className={`flex-1 border-2 border-dashed rounded-xl p-4 text-center cursor-pointer transition-colors ${
            isDragging
              ? 'border-primary-500 bg-primary-50/50'
              : 'border-slate-300 hover:border-slate-400 bg-slate-50/30'
          } ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept="image/jpeg,image/png,image/webp"
            onChange={handleFileChange}
            className="hidden"
            disabled={disabled}
          />
          <svg className="w-6 h-6 text-slate-400 mx-auto mb-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
            />
          </svg>
          <p className="text-xs font-medium text-slate-700">
            Click to upload or drag image here
          </p>
          <p className="text-[11px] text-slate-400 mt-0.5">
            JPEG, PNG, or WebP (max 5 MB)
          </p>
        </div>
      </div>

      {displayUrl && (
        <div className="flex justify-start">
          <button
            type="button"
            onClick={handleRemove}
            disabled={disabled}
            className="text-xs text-rose-600 hover:text-rose-700 font-medium py-1 px-2 rounded hover:bg-rose-50 transition-colors"
          >
            Remove Image
          </button>
        </div>
      )}
    </div>
  );
};

