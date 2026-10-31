import React from 'react';

interface StockStatusBadgeProps {
  lowStock: boolean;
  outOfStock: boolean;
  className?: string;
}

export const StockStatusBadge: React.FC<StockStatusBadgeProps> = ({
  lowStock,
  outOfStock,
  className = '',
}) => {
  if (outOfStock) {
    return (
      <span
        className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-rose-50 text-rose-700 border border-rose-200 ${className}`}
      >
        <span className="w-1.5 h-1.5 mr-1.5 bg-rose-500 rounded-full" />
        Out of Stock
      </span>
    );
  }

  if (lowStock) {
    return (
      <span
        className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-amber-50 text-amber-700 border border-amber-200 ${className}`}
      >
        <span className="w-1.5 h-1.5 mr-1.5 bg-amber-500 rounded-full" />
        Low Stock
      </span>
    );
  }

  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200 ${className}`}
    >
      <span className="w-1.5 h-1.5 mr-1.5 bg-emerald-500 rounded-full" />
      In Stock
    </span>
  );
};

