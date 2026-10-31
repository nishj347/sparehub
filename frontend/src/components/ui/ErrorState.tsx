import React from 'react';

interface ErrorStateProps {
  title?: string;
  message?: string;
  onRetry?: () => void;
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  title = 'Something went wrong',
  message = 'Failed to load content. Please verify your connection and try again.',
  onRetry,
}) => {
  return (
    <div className="flex flex-col items-center justify-center p-12 text-center bg-rose-50/50 rounded-xl border border-rose-100">
      <div className="w-12 h-12 mb-3 rounded-full bg-rose-100 flex items-center justify-center text-rose-600">
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
          />
        </svg>
      </div>
      <h3 className="text-sm font-semibold text-rose-900 mb-1">{title}</h3>
      <p className="text-xs text-rose-600 max-w-sm mb-4">{message}</p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="px-4 py-2 text-xs font-semibold text-rose-700 bg-white border border-rose-200 rounded-lg hover:bg-rose-50 transition-colors shadow-sm"
        >
          Try Again
        </button>
      )}
    </div>
  );
};

