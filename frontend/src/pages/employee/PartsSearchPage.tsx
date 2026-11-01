import React, { useEffect, useRef, useState, useCallback } from 'react';
import { RefreshCw, SlidersHorizontal, X } from 'lucide-react';
import { searchParts, getPartFilters } from '../../api/parts';
import { PartCard as PartCardType, PartFilters, PublicMachineBrief } from '../../types/partsPublic';
import { Page } from '../../types/common';
import { PartCard } from '../../components/parts/PartCard';
import { PartFiltersBar } from '../../components/parts/PartFilters';
import { SearchInput } from '../../components/ui/SearchInput';
import { Pagination } from '../../components/ui/Pagination';
import { useUrlSearchState } from '../../hooks/useUrlSearchState';
import { useDebouncedValue } from '../../hooks/useDebouncedValue';
import { ApiError } from '../../api/client';

// Skeleton card placeholder
const CardSkeleton: React.FC = () => (
  <div className="bg-white rounded border border-slate-200 overflow-hidden animate-pulse">
    <div className="w-full h-36 bg-slate-100" />
    <div className="p-4 space-y-3">
      <div className="h-4 bg-slate-100 rounded w-3/4" />
      <div className="h-3 bg-slate-100 rounded w-1/3" />
      <div className="h-3 bg-slate-100 rounded w-1/2" />
      <div className="h-3 bg-slate-100 rounded w-2/3" />
    </div>
  </div>
);

export const PartsSearchPage: React.FC = () => {
  const { get, getInt, set, clear } = useUrlSearchState();

  // URL-driven state
  const q = get('q');
  const category = get('category');
  const machineId = get('machine_id');
  const locationId = get('location_id');
  const availability = get('availability', 'all');
  const sort = get('sort', q ? 'relevance' : 'name');
  const order = get('order', 'asc');
  const page = getInt('page', 1);

  // Local search input (debounced before hitting URL)
  const [inputValue, setInputValue] = useState(q);
  const debouncedQ = useDebouncedValue(inputValue, 300);

  // Sync debounced search to URL
  useEffect(() => {
    if (debouncedQ !== q) {
      set({ q: debouncedQ || null, page: null });
    }
  }, [debouncedQ]); // eslint-disable-line react-hooks/exhaustive-deps

  // Sync URL q back to input when navigating (e.g. browser back)
  useEffect(() => {
    setInputValue(q);
  }, [q]);

  // Data state
  const [result, setResult] = useState<Page<PartCardType> | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<PartFilters | null>(null);

  // Stale-response guard: only apply the latest request
  const reqRef = useRef(0);

  const fetchParts = useCallback(async () => {
    const id = ++reqRef.current;
    setLoading(true);
    setError(null);
    try {
      const params: Record<string, string | number | undefined> = {
        q: q || undefined,
        category: category || undefined,
        machine_id: machineId ? Number(machineId) : undefined,
        location_id: locationId ? Number(locationId) : undefined,
        availability: availability !== 'all' ? availability : undefined,
        sort: sort || undefined,
        order: order || undefined,
        page,
        page_size: 12,
      };
      const res = await searchParts(params as Parameters<typeof searchParts>[0]);
      if (id !== reqRef.current) return; // stale
      setResult(res);
    } catch (err: unknown) {
      if (id !== reqRef.current) return;
      const msg = err instanceof ApiError ? err.message : 'Failed to load parts. Please try again.';
      setError(msg);
      // On 422, clear unknown URL params
      if (err instanceof ApiError && err.status === 422) {
        clear();
      }
    } finally {
      if (id === reqRef.current) setLoading(false);
    }
  }, [q, category, machineId, locationId, availability, sort, order, page]);

  useEffect(() => { fetchParts(); }, [fetchParts]);

  // Load filters once
  useEffect(() => {
    getPartFilters().then(setFilters).catch(() => { /* silent */ });
  }, []);

  // Scroll to top on page change
  useEffect(() => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }, [page]);

  const totalPages = result ? Math.ceil(result.total / result.page_size) : 0;
  const hasFilters = !!(category || machineId || locationId || (availability && availability !== 'all'));

  // Resolve selected machine name for banner
  const selectedMachine: PublicMachineBrief | undefined = machineId && filters
    ? filters.machines.find((m) => String(m.id) === machineId)
    : undefined;

  return (
    <div className="space-y-5">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">Spare Parts</h1>
        <p className="mt-1 text-sm text-slate-500">Search and browse the parts catalogue</p>
      </div>

      {/* Search */}
      <SearchInput
        value={inputValue}
        onChange={setInputValue}
        placeholder="Search by part name, part ID, category, manufacturer or machine"
        className="max-w-2xl"
      />

      {/* Filters row */}
      <div className="flex items-center gap-2 flex-wrap">
        <SlidersHorizontal className="w-4 h-4 text-slate-400 shrink-0" aria-hidden="true" />
        <PartFiltersBar
          filters={filters}
          category={category}
          machineId={machineId}
          locationId={locationId}
          availability={availability}
          sort={sort}
          order={order}
          hasQ={!!q}
          onCategory={(v) => set({ category: v || null })}
          onMachine={(v) => set({ machine_id: v || null })}
          onLocation={(v) => set({ location_id: v || null })}
          onAvailability={(v) => set({ availability: v === 'all' ? null : v })}
          onSort={(v) => set({ sort: v }, false)}
          onOrder={(v) => set({ order: v }, false)}
          onClear={() => {
            set({ category: null, machine_id: null, location_id: null, availability: null });
          }}
        />
      </div>

      {/* Machine filter banner */}
      {selectedMachine && (
        <div className="flex items-center justify-between gap-3 px-4 py-3 bg-blue-50 border border-blue-200 rounded">
          <div className="min-w-0">
            <p className="text-sm font-semibold text-blue-900 leading-snug">
              Spare parts used in {selectedMachine.name}{' '}
              <span className="font-mono font-normal text-blue-700">({selectedMachine.code})</span>
            </p>
            {result && !loading && (
              <p className="text-xs text-blue-700 mt-0.5">
                {result.total} part{result.total !== 1 ? 's' : ''} found
              </p>
            )}
          </div>
          <button
            type="button"
            onClick={() => set({ machine_id: null })}
            className="shrink-0 inline-flex items-center gap-1 text-xs font-medium text-blue-700 hover:text-blue-900 border border-blue-200 hover:border-blue-400 bg-white px-2.5 py-1 rounded transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <X className="w-3 h-3" />
            Clear
          </button>
        </div>
      )}

      {/* Result summary (only when no machine banner) */}
      {result && !loading && !selectedMachine && (
        <p
          className="text-sm text-slate-500"
          aria-live="polite"
          aria-atomic="true"
        >
          {result.total === 0
            ? q
              ? `No parts found for "${q}"`
              : 'No parts found'
            : `${result.total} part${result.total !== 1 ? 's' : ''} found${q ? ` for "${q}"` : ''}`}
        </p>
      )}

      {/* Error */}
      {error && !loading && (
        <div className="flex flex-col items-center justify-center py-16 text-center gap-4">
          <p className="text-sm text-rose-600 font-medium">{error}</p>
          <button
            type="button"
            onClick={fetchParts}
            className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium rounded bg-blue-600 text-white hover:bg-blue-700 transition-colors"
          >
            <RefreshCw className="w-4 h-4" /> Retry
          </button>
        </div>
      )}

      {/* Loading skeletons */}
      {loading && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4" aria-busy="true" aria-label="Loading parts">
          {Array.from({ length: 6 }).map((_, i) => <CardSkeleton key={i} />)}
        </div>
      )}

      {/* Results grid */}
      {!loading && !error && result && result.items.length > 0 && (
        <div
          className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4"
          role="region"
          aria-label="Parts search results"
        >
          {result.items.map((part) => (
            <PartCard key={part.id} part={part} searchQuery={q} />
          ))}
        </div>
      )}

      {/* Empty state */}
      {!loading && !error && result && result.items.length === 0 && (
        <div className="flex flex-col items-center justify-center py-16 text-center gap-3">
          <p className="text-base font-semibold text-slate-700">
            {selectedMachine
              ? `No parts mapped to ${selectedMachine.name}`
              : q
              ? `No parts match "${q}"`
              : 'No parts in the catalogue'}
          </p>
          {(q || hasFilters) && (
            <ul className="text-sm text-slate-500 list-disc list-inside text-left">
              {q && <li>Check spelling or try a broader term</li>}
              {hasFilters && <li>Try removing some filters</li>}
            </ul>
          )}
          {hasFilters && (
            <button
              type="button"
              onClick={() => set({ category: null, machine_id: null, location_id: null, availability: null })}
              className="mt-1 text-sm text-blue-600 underline hover:text-blue-800 focus:outline-none focus:ring-2 focus:ring-blue-500 rounded"
            >
              Clear filters
            </button>
          )}
        </div>
      )}

      {/* Pagination */}
      {!loading && !error && result && result.total > result.page_size && (
        <Pagination
          page={page}
          pageSize={result.page_size}
          total={result.total}
          totalPages={totalPages}
          onPageChange={(p) => set({ page: p }, false)}
        />
      )}
    </div>
  );
};
