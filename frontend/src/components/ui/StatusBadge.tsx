import React from 'react';

interface StatusBadgeProps {
  isActive: boolean;
  activeLabel?: string;
  inactiveLabel?: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({
  isActive,
  activeLabel = 'Active',
  inactiveLabel = 'Inactive',
}) => {
  if (isActive) {
    return (
      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
        <span className="w-1.5 h-1.5 mr-1.5 bg-emerald-500 rounded-full" />
        {activeLabel}
      </span>
    );
  }

  return (
    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-600 border border-slate-200">
      <span className="w-1.5 h-1.5 mr-1.5 bg-slate-400 rounded-full" />
      {inactiveLabel}
    </span>
  );
};

