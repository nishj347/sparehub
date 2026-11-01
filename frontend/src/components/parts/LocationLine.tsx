import React from 'react';
import { PrimaryLocation } from '../../types/partsPublic';
import { MapPin } from 'lucide-react';

interface LocationLineProps {
  primary: PrimaryLocation;
  /** name of the part's location (for "Most stock at …" label) */
}

export const LocationLine: React.FC<LocationLineProps> = ({ primary }) => {
  const parts: string[] = [primary.location.name];
  if (primary.store_name) parts.push(primary.store_name);
  if (primary.rack) parts.push(`Rack ${primary.rack}`);
  if (primary.bin) parts.push(`Bin ${primary.bin}`);

  return (
    <span className="inline-flex items-center gap-1 text-xs text-slate-500 truncate">
      <MapPin className="w-3 h-3 shrink-0 text-slate-400" aria-hidden="true" />
      <span className="truncate">{parts.join(' → ')}</span>
    </span>
  );
};

