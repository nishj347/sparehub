import React from 'react';
import { PrimaryLocation } from '../../types/partsPublic';
import { MapPin } from 'lucide-react';

interface LocationLineProps {
  primary: PrimaryLocation;
}

/**
 * Card-level location block: labelled "LOCATION" with plant name on one line,
 * then store · rack · bin on the next. Omits missing pieces; never prints null.
 */
export const LocationLine: React.FC<LocationLineProps> = ({ primary }) => {
  const storageParts: string[] = [];
  if (primary.store_name) storageParts.push(primary.store_name);
  if (primary.rack) storageParts.push(`Rack ${primary.rack}`);
  if (primary.bin) storageParts.push(`Bin ${primary.bin}`);

  const storageLine = storageParts.length > 0
    ? storageParts.join(' · ')
    : 'Storage details not recorded';

  return (
    <div className="mt-1 space-y-0.5">
      <div className="flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wider text-slate-400">
        <MapPin className="w-3 h-3 shrink-0 text-slate-400" aria-hidden="true" />
        Location
      </div>
      <div className="text-xs font-semibold text-slate-700">{primary.location.name}</div>
      <div className="text-xs text-slate-500">{storageLine}</div>
    </div>
  );
};
