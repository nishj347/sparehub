import React, { useEffect, useState, useRef, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { Search, X, RotateCcw, AlertCircle, ArrowUpDown, Calendar, MapPin } from 'lucide-react';
import { getMyIssues } from '../../api/history';
import { getPartFilters } from '../../api/parts';
import { MyIssuesResponse, MyIssueItem } from '../../types/activity';
import { PartFilters } from '../../types/partsPublic';
import { useUrlSearchState } from '../../hooks/useUrlSearchState';
import { useDebouncedValue } from '../../hooks/useDebouncedValue';
import { PartImage } from '../../components/parts/PartImage';
import { Pagination } from '../../components/ui/Pagination';
import { LoadingState } from '../../components/ui/LoadingState';
import { ErrorState } from '../../components/ui/ErrorState';
import { EmptyState } from '../../components/ui/EmptyState';
import { formatDateTime } from '../../lib/formatDateTime';
import { ApiError } from '../../api/client';

export const IssueHistoryPage: React.FC = () => {
  const { get, getInt, set, clear } = useUrlSearchState();

  // URL State
  const q = get('q');
  const locationId = get('location_id');
  const dateFrom = get('date_from');
  const dateTo = get('date_to');
  const sort = get('sort', 'created_at');
  const order = get('order', 'desc');
  const page = getInt('page', 1);

  // Search input with debounce
  const [searchInput, setSearchInput] = useState(q);
  const debouncedSearch = useDebouncedValue(searchInput, 300);

  // Filter options
  const [filterOptions, setFilterOptions] = useState<PartFilters | null>(null);

  // Data states
  const [data, setData] = useState<MyIssuesResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dateError, setDateError] = useState<string | null>(null);

  // Stale request guard
  const reqIdRef = useRef(0);

  // Sync debounced search to URL
  useEffect(() => {
    if (debouncedSearch !== q) {
      set({ q: debouncedSearch || null, page: null });
    }
  }, [debouncedSearch]); // eslint-disable-line react-hooks/exhaustive-deps

  // Sync URL search to local input on popstate
  useEffect(() => {
    setSearchInput(q);
  }, [q]);

  // Load filter options (locations)
  useEffect(() => {
    getPartFilters()
      .then((res) => setFilterOptions(res))
      .catch(() => {
        // Fallback gracefully if filters fail
      });
  }, []);

  // Check reversed dates
  useEffect(() => {
    if (dateFrom && dateTo && dateFrom > dateTo) {
      setDateError('"From" date cannot be after "To" date');
    } else {
      setDateError(null);
    }
  }, [dateFrom, dateTo]);

  // Fetch data
  const fetchData = useCallback(async () => {
    if (dateFrom && dateTo && dateFrom > dateTo) {
      return;
    }

    const currentReqId = ++reqIdRef.current;
    setLoading(true);
    setError(null);

    try {
      const res = await getMyIssues({
        q: q || undefined,
        location_id: locationId || undefined,
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
        sort: sort || undefined,
        order: order || undefined,
        page,
        page_size: 20,
      });

      if (currentReqId === reqIdRef.current) {
        setData(res);
        setLoading(false);
      }
    } catch (err) {
      if (currentReqId === reqIdRef.current) {
        const msg = err instanceof ApiError ? err.message : 'Failed to load your issue history.';
        setError(msg);
        setLoading(false);
      }
    }
  }, [q, locationId, dateFrom, dateTo, sort, order, page]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const hasActiveFilters = Boolean(q || locationId || dateFrom || dateTo || (sort && sort !== 'created_at') || (order && order !== 'desc'));

  const handleClearFilters = () => {
    setSearchInput('');
    clear();
  };

  const isFilteredEmpty = !loading && !error && data?.items.length === 0 && hasActiveFilters;
  const isAllEmpty = !loading && !error && data?.items.length === 0 && !hasActiveFilters;

  return (
    <div className="space-y-6">
      {/* Page Title & Breadcrumb Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">My Issue History</h1>
          <p className="text-sm text-slate-500 mt-0.5">
            View all spare parts issued to your account for maintenance operations.
          </p>
        </div>

        {data?.summary && (
          <div className="flex items-center gap-3 bg-white px-4 py-2.5 rounded-lg border border-slate-200 shadow-sm text-sm">
            <div>
              <span className="text-slate-500">Total Issues: </span>
              <span className="font-semibold text-slate-900">{data.summary.total_issues}</span>
            </div>
            <span className="text-slate-300">|</span>
            <div>
              <span className="text-slate-500">Total Units: </span>
              <span className="font-semibold text-blue-600">{data.summary.total_units}</span>
            </div>
          </div>
        )}
      </div>

      {/* Filter / Search Toolbar */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm space-y-3">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {/* Search Input */}
          <div className="relative">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              placeholder="Search part name, ID..."
              className="w-full pl-9 pr-8 py-2 text-sm bg-white border border-slate-300 rounded-lg text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition"
            />
            {searchInput && (
              <button
                type="button"
                onClick={() => setSearchInput('')}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                aria-label="Clear search"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>

          {/* Location Select */}
          <div className="relative">
            <MapPin className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
            <select
              value={locationId}
              onChange={(e) => set({ location_id: e.target.value || null, page: null })}
              className="w-full pl-9 pr-3 py-2 text-sm bg-white border border-slate-300 rounded-lg text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition appearance-none"
            >
              <option value="">All Locations</option>
              {filterOptions?.locations?.map((loc) => (
                <option key={loc.id} value={loc.id}>
                  {loc.name} ({loc.code})
                </option>
              ))}
            </select>
          </div>

          {/* Date From */}
          <div className="relative">
            <Calendar className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
            <input
              type="date"
              value={dateFrom}
              onChange={(e) => set({ date_from: e.target.value || null, page: null })}
              className="w-full pl-9 pr-3 py-2 text-sm bg-white border border-slate-300 rounded-lg text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition"
              title="From date"
            />
          </div>

          {/* Date To */}
          <div className="relative">
            <Calendar className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
            <input
              type="date"
              value={dateTo}
              onChange={(e) => set({ date_to: e.target.value || null, page: null })}
              className="w-full pl-9 pr-3 py-2 text-sm bg-white border border-slate-300 rounded-lg text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition"
              title="To date"
            />
          </div>
        </div>

        {/* Toolbar Secondary Row: Sorting & Reset */}
        <div className="flex flex-wrap items-center justify-between gap-3 pt-2 border-t border-slate-100 text-xs">
          <div className="flex items-center gap-2">
            <ArrowUpDown className="w-3.5 h-3.5 text-slate-400" />
            <span className="text-slate-500 font-medium">Sort by:</span>
            <select
              value={sort}
              onChange={(e) => set({ sort: e.target.value, page: null })}
              className="px-2 py-1 bg-white border border-slate-300 rounded text-slate-700 focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              <option value="created_at">Date / Time</option>
              <option value="part_name">Part Name</option>
              <option value="quantity">Quantity</option>
            </select>
            <select
              value={order}
              onChange={(e) => set({ order: e.target.value, page: null })}
              className="px-2 py-1 bg-white border border-slate-300 rounded text-slate-700 focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              <option value="desc">Descending (Newest / Highest)</option>
              <option value="asc">Ascending (Oldest / Lowest)</option>
            </select>
          </div>

          {hasActiveFilters && (
            <button
              type="button"
              onClick={handleClearFilters}
              className="inline-flex items-center gap-1.5 text-slate-600 hover:text-slate-900 font-medium hover:bg-slate-100 px-2.5 py-1 rounded transition"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>Reset Filters</span>
            </button>
          )}
        </div>

        {/* Date error inline message */}
        {dateError && (
          <div className="flex items-center gap-2 text-xs text-rose-600 bg-rose-50 px-3 py-2 rounded-md border border-rose-200">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{dateError}</span>
          </div>
        )}
      </div>

      {/* Main Content Area */}
      {loading ? (
        <LoadingState message="Loading issue history..." />
      ) : error ? (
        <ErrorState
          title="Could not load issue history"
          message={error}
          onRetry={fetchData}
        />
      ) : isAllEmpty ? (
        <EmptyState
          title="You haven't issued any parts yet"
          description="Browse the catalog to find spare parts needed for maintenance and log your first issue."
          action={{
            label: "Explore Spare Parts",
            onClick: () => {
              window.location.href = '/parts';
            },
          }}
        />
      ) : isFilteredEmpty ? (
        <EmptyState
          title="No issues match your criteria"
          description="Try broadening your search term, clearing date constraints, or selecting a different location."
          action={{
            label: "Clear All Filters",
            onClick: handleClearFilters,
          }}
        />
      ) : (
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-600">
              <thead className="bg-slate-50 border-b border-slate-200 text-xs font-semibold uppercase text-slate-500 tracking-wider">
                <tr>
                  <th scope="col" className="px-6 py-3.5 whitespace-nowrap">
                    Date &amp; Time
                  </th>
                  <th scope="col" className="px-6 py-3.5">
                    Spare Part
                  </th>
                  <th scope="col" className="px-6 py-3.5 whitespace-nowrap">
                    Quantity
                  </th>
                  <th scope="col" className="px-6 py-3.5 whitespace-nowrap">
                    Location
                  </th>
                  <th scope="col" className="px-6 py-3.5">
                    Notes
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 bg-white">
                {data?.items.map((item: MyIssueItem) => (
                  <tr key={item.transaction_id} className="hover:bg-slate-50 transition-colors">
                    {/* Date & Time */}
                    <td className="px-6 py-4 whitespace-nowrap text-xs font-medium text-slate-800">
                      {formatDateTime(item.created_at)}
                    </td>

                    {/* Spare Part */}
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-lg overflow-hidden border border-slate-200 bg-slate-50 shrink-0">
                          <PartImage
                            src={item.part.image_url}
                            alt={item.part.name}
                            className="w-full h-full object-cover"
                          />
                        </div>
                        <div className="min-w-0">
                          <Link
                            to={`/parts/${item.part.id}`}
                            className="font-semibold text-slate-900 hover:text-blue-600 transition truncate block"
                          >
                            {item.part.name}
                          </Link>
                          <span className="text-xs text-slate-500 font-mono">
                            {item.part.part_number}
                          </span>
                        </div>
                      </div>
                    </td>

                    {/* Quantity Issued */}
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold bg-blue-50 text-blue-700 border border-blue-200">
                        +{item.quantity} {item.quantity === 1 ? 'unit' : 'units'}
                      </span>
                    </td>

                    {/* Location */}
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-xs text-slate-800 font-medium">{item.location.name}</div>
                      <div className="text-[11px] text-slate-400 font-mono">{item.location.code}</div>
                    </td>

                    {/* Notes */}
                    <td className="px-6 py-4 text-xs text-slate-600 max-w-xs truncate" title={item.notes || ''}>
                      {item.notes ? (
                        <span>{item.notes}</span>
                      ) : (
                        <span className="text-slate-300 italic">No notes provided</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {data && data.total_pages > 1 && (
            <Pagination
              page={data.page}
              pageSize={data.page_size}
              total={data.total}
              totalPages={data.total_pages}
              onPageChange={(newPage) => set({ page: newPage > 1 ? newPage : null })}
            />
          )}
        </div>
      )}
    </div>
  );
};

