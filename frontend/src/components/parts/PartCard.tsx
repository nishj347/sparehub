import React from 'react';
import { Link } from 'react-router-dom';
import { PartCard as PartCardType } from '../../types/partsPublic';
import { AvailabilityBadge } from './AvailabilityBadge';
import { LocationLine } from './LocationLine';
import { PartImage } from './PartImage';

interface HighlightProps {
  text: string;
  query: string;
}

/** Highlights matching substrings with a yellow mark – never uses dangerouslySetInnerHTML. */
const Highlight: React.FC<HighlightProps> = ({ text, query }) => {
  if (!query.trim()) return <>{text}</>;
  const terms = query
    .trim()
    .split(/\s+/)
    .slice(0, 5)
    .map((t) => t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
    .join('|');
  const regex = new RegExp(`(${terms})`, 'gi');
  const parts = text.split(regex);
  return (
    <>
      {parts.map((part, i) =>
        regex.test(part) ? (
          <mark key={i} className="bg-yellow-100 text-yellow-900 rounded-sm px-0.5">
            {part}
          </mark>
        ) : (
          <React.Fragment key={i}>{part}</React.Fragment>
        ),
      )}
    </>
  );
};

interface PartCardProps {
  part: PartCardType;
  searchQuery?: string;
}

export const PartCard: React.FC<PartCardProps> = ({ part, searchQuery = '' }) => {
  const machineLabels = part.machines
    .slice(0, 3)
    .map((m) => m.code)
    .join(', ');
  const extraMachines = part.machine_count_total - Math.min(part.machines.length, 3);

  const isMyLocation = part.primary_location?.is_my_location ?? false;
  const primaryLocationName = part.primary_location?.location.name ?? '';

  const qty = part.primary_location?.quantity ?? 0;
  const qtyLabel = `${qty} unit${qty !== 1 ? 's' : ''} available`;

  return (
    <Link
      to={`/parts/${part.id}`}
      className="group flex flex-col bg-white rounded border border-slate-200 hover:border-blue-300 hover:shadow-md transition-all focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-1"
      aria-label={`View details for ${part.name}`}
    >
      {/* Image */}
      <div className="relative overflow-hidden rounded-t">
        <PartImage
          src={part.image_url}
          alt={part.name}
          className="w-full h-36"
        />
      </div>

      {/* Body */}
      <div className="flex flex-col flex-1 p-4 gap-2">
        {/* Name + badge */}
        <div className="flex items-start justify-between gap-2">
          <h3 className="text-sm font-semibold text-slate-800 leading-snug group-hover:text-blue-700 transition-colors">
            <Highlight text={part.name} query={searchQuery} />
          </h3>
          <AvailabilityBadge status={part.availability_status} className="shrink-0 mt-0.5" />
        </div>

        {/* Part number */}
        <p className="font-mono text-[11px] text-slate-500 tracking-wide">
          <Highlight text={part.part_number} query={searchQuery} />
        </p>

        {/* Category / manufacturer */}
        <p className="text-xs text-slate-400 truncate">
          {part.category}
          {part.manufacturer ? ` · ${part.manufacturer}` : ''}
        </p>

        {/* Machines */}
        {part.machine_count_total > 0 && (
          <p className="text-xs text-slate-500 truncate">
            <span className="font-medium text-slate-600">Used in:</span>{' '}
            {machineLabels}
            {extraMachines > 0 && ` (+${extraMachines})`}
          </p>
        )}

        {/* Location + stock block */}
        <div className="mt-auto pt-3 border-t border-slate-100 flex flex-col gap-1.5">
          {part.availability_status !== 'OUT_OF_STOCK' && part.primary_location ? (
            <>
              {/* Quantity */}
              <span className="text-sm font-semibold text-slate-800">
                {isMyLocation
                  ? qtyLabel
                  : `Most stock at ${primaryLocationName}: ${qty} unit${qty !== 1 ? 's' : ''}`}
              </span>

              {/* Location block */}
              <LocationLine primary={part.primary_location} />

              {/* Other locations */}
              {part.other_locations_with_stock > 0 && (
                <span className="text-xs text-slate-400 mt-0.5">
                  Also available at {part.other_locations_with_stock} other location
                  {part.other_locations_with_stock !== 1 ? 's' : ''}
                </span>
              )}
            </>
          ) : (
            <span className="text-xs text-rose-500 font-medium">Out of stock at all locations</span>
          )}
        </div>
      </div>
    </Link>
  );
};
