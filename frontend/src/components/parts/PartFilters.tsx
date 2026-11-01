import React from 'react';
import { PartFilters } from '../../types/partsPublic';

interface PartFiltersProps {
  filters: PartFilters | null;
  category: string;
  machineId: string;
  locationId: string;
  availability: string;
  sort: string;
  order: string;
  hasQ: boolean;
  onCategory: (v: string) => void;
  onMachine: (v: string) => void;
  onLocation: (v: string) => void;
  onAvailability: (v: string) => void;
  onSort: (v: string) => void;
  onOrder: (v: string) => void;
  onClear: () => void;
}

const SELECT_CLS =
  'text-xs border border-slate-300 rounded-md px-2.5 py-1.5 bg-white text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500 hover:border-slate-400 transition-colors';

export const PartFiltersBar: React.FC<PartFiltersProps> = ({
  filters,
  category,
  machineId,
  locationId,
  availability,
  sort,
  order,
  hasQ,
  onCategory,
  onMachine,
  onLocation,
  onAvailability,
  onSort,
  onOrder,
  onClear,
}) => {
  const isFiltered =
    !!category || !!machineId || !!locationId || (!!availability && availability !== 'all');

  return (
    <div className="flex flex-wrap items-center gap-2">
      {/* Category */}
      <select
        value={category}
        onChange={(e) => onCategory(e.target.value)}
        className={SELECT_CLS}
        aria-label="Filter by category"
      >
        <option value="">All categories</option>
        {filters?.categories.map((c) => (
          <option key={c} value={c}>{c}</option>
        ))}
      </select>

      {/* Machine */}
      <select
        value={machineId}
        onChange={(e) => onMachine(e.target.value)}
        className={SELECT_CLS}
        aria-label="Filter by machine"
      >
        <option value="">All machines</option>
        {filters?.machines.map((m) => (
          <option key={m.id} value={String(m.id)}>{m.name} ({m.code})</option>
        ))}
      </select>

      {/* Location */}
      <select
        value={locationId}
        onChange={(e) => onLocation(e.target.value)}
        className={SELECT_CLS}
        aria-label="Filter by location"
      >
        <option value="">All locations</option>
        {filters?.locations.map((l) => (
          <option key={l.id} value={String(l.id)}>{l.name}</option>
        ))}
      </select>

      {/* Availability */}
      <select
        value={availability || 'all'}
        onChange={(e) => onAvailability(e.target.value)}
        className={SELECT_CLS}
        aria-label="Filter by availability"
      >
        <option value="all">Any availability</option>
        <option value="available">Available now</option>
        <option value="my_location">At my location</option>
        {locationId && <option value="location">At selected location</option>}
      </select>

      {/* Sort */}
      <select
        value={sort || (hasQ ? 'relevance' : 'name')}
        onChange={(e) => onSort(e.target.value)}
        className={SELECT_CLS}
        aria-label="Sort by"
      >
        {hasQ && <option value="relevance">Relevance</option>}
        <option value="name">Name</option>
        <option value="part_number">Part ID</option>
        <option value="availability">Availability</option>
      </select>

      {/* Order */}
      <select
        value={order || 'asc'}
        onChange={(e) => onOrder(e.target.value)}
        className={SELECT_CLS}
        aria-label="Sort order"
      >
        <option value="asc">↑ Asc</option>
        <option value="desc">↓ Desc</option>
      </select>

      {/* Clear filters */}
      {isFiltered && (
        <button
          type="button"
          onClick={onClear}
          className="text-xs text-blue-600 hover:text-blue-800 underline focus:outline-none focus:ring-2 focus:ring-blue-500 rounded"
        >
          Clear filters
        </button>
      )}
    </div>
  );
};

