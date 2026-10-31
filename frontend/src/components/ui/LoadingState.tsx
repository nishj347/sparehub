import React from 'react';

interface LoadingStateProps {
  message?: string;
}

export const LoadingState: React.FC<LoadingStateProps> = ({ message = 'Loading data...' }) => {
  return (
    <div className="flex flex-col items-center justify-center p-12 text-center">
      <div className="relative w-10 h-10 mb-3">
        <div className="w-10 h-10 border-4 border-primary-200 border-t-primary-600 rounded-full animate-spin" />
      </div>
      <p className="text-xs font-medium text-slate-500 animate-pulse">{message}</p>
    </div>
  );
};

