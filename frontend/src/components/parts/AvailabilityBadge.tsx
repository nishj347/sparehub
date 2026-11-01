import React from 'react';
import { AvailabilityStatus } from '../../types/partsPublic';

interface AvailabilityBadgeProps {
  status: AvailabilityStatus;
  className?: string;
}

const CONFIG: Record<AvailabilityStatus, { label: string; className: string }> = {
  IN_STOCK: {
    label: 'In Stock',
    className: 'bg-emerald-50 text-emerald-700 border border-emerald-200',
  },
  LOW_STOCK: {
    label: 'Low Stock',
    className: 'bg-amber-50 text-amber-700 border border-amber-200',
  },
  OUT_OF_STOCK: {
    label: 'Out of Stock',
    className: 'bg-rose-50 text-rose-700 border border-rose-200',
  },
};

export const AvailabilityBadge: React.FC<AvailabilityBadgeProps> = ({ status, className = '' }) => {
  const cfg = CONFIG[status] ?? CONFIG.OUT_OF_STOCK;
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${cfg.className} ${className}`}
    >
      {cfg.label}
    </span>
  );
};

