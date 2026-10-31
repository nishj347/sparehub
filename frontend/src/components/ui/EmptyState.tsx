import React from 'react';

interface EmptyStateProps {
  title: string;
  description?: string;
  action?: {
    label: string;
    onClick: () => void;
  };
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  title,
  description,
  action,
}) => {
  return (
    <div className="flex flex-col items-center justify-center p-12 text-center">
      <div className="w-12 h-12 mb-4 rounded-full bg-slate-100 flex items-center justify-center text-slate-400">
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.5}
            d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4"
          />
        </svg>
      </div>
      <h3 className="text-sm font-semibold text-slate-800 mb-1">{title}</h3>
      {description && <p className="text-xs text-slate-500 max-w-sm mb-4">{description}</p>}
      {action && (
        <button
          type="button"
          onClick={action.onClick}
          className="px-4 py-2 text-xs font-semibold text-white bg-primary-600 rounded-lg hover:bg-primary-700 transition-colors shadow-sm"
        >
          {action.label}
        </button>
      )}
    </div>
  );
};

