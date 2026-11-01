import React, { useEffect, useState, useRef, useCallback } from 'react';
import { Link } from 'react-router-dom';
import {
  Search,
  X,
  RotateCcw,
  AlertCircle,
  ArrowUpDown,
  Calendar,
  MapPin,
  User,
  Filter,
  ArrowDownRight,
  ArrowUpRight,
  Sliders,
} from 'lucide-react';
import { getAdminActivity } from '../../api/history';
import { getPartFilters } from '../../api/parts';
import { AdminActivityResponse, AdminActivityItem } from '../../types/activity';
import { PartFilters } from '../../types/partsPublic';
import { useUrlSearchState } from '../../hooks/useUrlSearchState';
import { useDebouncedValue } from '../../hooks/useDebouncedValue';
import { Pagination } from '../../components/ui/Pagination';
import { LoadingState } from '../../components/ui/LoadingState';
import { ErrorState } from '../../components/ui/ErrorState';
import { EmptyState } from '../../components/ui/EmptyState';
import { formatDateTime } from '../../lib/formatDateTime';
import { ApiError } from '../../api/client';

export const ActivityPage: React.FC = () => {
  const { get, getInt, set, clear } = useUrlSearchState();

  // URL State
  const q = get('q');
  const employee = get('employee');
  const txType = get('type', 'all');
  const locationId = get('location_id');
  const dateFrom = get('date_from');
  const dateTo = get('date_to');
  const sort = get('sort', 'created_at');
  const order = get('order', 'desc');
  const page = getInt('page', 1);

  // Local inputs for debounce
  const [searchInput, setSearchInput] = useState(q);
  const debouncedSearch = useDebouncedValue(searchInput, 300);

  const [employeeInput, setEmployeeInput] = useState(employee);
  const debouncedEmployee = useDebouncedValue(employeeInput, 300);

  // Options
  const [filterOptions, setFilterOptions] = useState<PartFilters | null>(null);

  // Data states
  const [data, setData] = useState<AdminActivityResponse | null>(null);
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

  useEffect(() => {
    if (debouncedEmployee !== employee) {
      set({ employee: debouncedEmployee || null, page: null });
    }
  }, [debouncedEmployee]); // eslint-disable-line react-hooks/exhaustive-deps

  // Sync back to local inputs on back/forward
  useEffect(() => {
    setSearchInput(q);
  }, [q]);

  useEffect(() => {
    setEmployeeInput(employee);
  }, [employee]);

  // Load filter options (locations)
  useEffect(() => {
    getPartFilters()
      .then((res) => setFilterOptions(res))
      .catch(() => {
        // Fallback gracefully
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
      const res = await getAdminActivity({
        q: q || undefined,
        employee: employee || undefined,
        type: txType !== 'all' ? txType : undefined,
        location_id: locationId || undefined,
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
        sort: sort || undefined,
        order: order || undefined,
        page,
        page_size: 25,
      });

      if (currentReqId === reqIdRef.current) {
        setData(res);
        setLoading(false);
      }
    } catch (err) {
      if (currentReqId === reqIdRef.current) {
        const msg = err instanceof ApiError ? err.message : 'Failed to load inventory activity.';
        setError(msg);
        setLoading(false);
      }
    }
  }, [q, employee, txType, locationId, dateFrom, dateTo, sort, order, page]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const hasActiveFilters = Boolean(
    q ||
      employee ||
      (txType && txType !== 'all') ||
      locationId ||
      dateFrom ||
      dateTo ||
      (sort && sort !== 'created_at') ||
      (order && order !== 'desc'),
  );

  const handleClearFilters = () => {
    setSearchInput('');
    setEmployeeInput('');
    clear();
  };

  const isFilteredEmpty = !loading && !error && data?.items.length === 0 && hasActiveFilters;
  const isAllEmpty = !loading && !error && data?.items.length === 0 && !hasActiveFilters;

  const getTypeBadge = (type: string) => {
    switch (type) {
      case 'ISSUED':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-50 text-rose-700 border border-rose-200">
            <ArrowDownRight className="w-3 h-3 text-rose-500" />
            ISSUED
          </span>
        );
      case 'RECEIVED':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
            <ArrowUpRight className="w-3 h-3 text-emerald-500" />
            RECEIVED
          </span>
        );
      case 'ADJUSTED':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-50 text-amber-700 border border-amber-200">
            <Sliders className="w-3 h-3 text-amber-500" />
            ADJUSTED
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-700 border border-slate-200">
            {type}
          </span>
        );
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">Inventory Activity</h1>
        <p className="text-sm text-slate-500 mt-0.5">
          Auditable transaction ledger of all spare parts received, issued, and adjusted across locations.
        </p>
      </div>

      {/* Summary Strip */}
      {data?.summary && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex items-center justify-between">
            <div>
              <p className="text-xs font-medium uppercase tracking-wider text-slate-500">Total Transactions</p>
              <p className="text-2xl font-bold text-slate-900 mt-1">{data.summary.total_rows.toLocaleString()}</p>
            </div>
            <div className="p-2.5 rounded-lg bg-slate-50 text-slate-600 border border-slate-100">
              <Filter className="w-5 h-5" />
            </div>
          </div>

          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex items-center justify-between">
            <div>
              <p className="text-xs font-medium uppercase tracking-wider text-slate-500">Units Issued</p>
              <p className="text-2xl font-bold text-rose-600 mt-1">
                {data.summary.units_issued > 0 ? `-${data.summary.units_issued.toLocaleString()}` : '0'}
              </p>
            </div>
            <div className="p-2.5 rounded-lg bg-rose-50 text-rose-600 border border-rose-100">
              <ArrowDownRight className="w-5 h-5" />
            </div>
          </div>

          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex items-center justify-between">
            <div>
              <p className="text-xs font-medium uppercase tracking-wider text-slate-500">Units Received</p>
              <p className="text-2xl font-bold text-emerald-600 mt-1">
                {data.summary.units_received > 0 ? `+${data.summary.units_received.toLocaleString()}` : '0'}
              </p>
            </div>
            <div className="p-2.5 rounded-lg bg-emerald-50 text-emerald-600 border border-emerald-100">
              <ArrowUpRight className="w-5 h-5" />
            </div>
          </div>
        </div>
      )}

      {/* Filter / Search Toolbar */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm space-y-3">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-3">
          {/* Part Search */}
          <div className="relative">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              placeholder="Part name or ID..."
              className="w-full pl-9 pr-7 py-2 text-sm bg-white border border-slate-300 rounded-lg text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition"
            />
            {searchInput && (
              <button
                type="button"
                onClick={() => setSearchInput('')}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                aria-label="Clear part search"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </div>

          {/* Employee Search */}
          <div className="relative">
            <User className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              value={employeeInput}
              onChange={(e) => setEmployeeInput(e.target.value)}
              placeholder="Employee ID / Name..."
              className="w-full pl-9 pr-7 py-2 text-sm bg-white border border-slate-300 rounded-lg text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition"
            />
            {employeeInput && (
              <button
                type="button"
                onClick={() => setEmployeeInput('')}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                aria-label="Clear employee search"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </div>

          {/* Type Select */}
          <div className="relative">
            <select
              value={txType}
              onChange={(e) => set({ type: e.target.value !== 'all' ? e.target.value : null, page: null })}
              className="w-full px-3 py-2 text-sm bg-white border border-slate-300 rounded-lg text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition appearance-none"
            >
              <option value="all">All Types</option>
              <option value="ISSUED">Issued</option>
              <option value="RECEIVED">Received</option>
              <option value="ADJUSTED">Adjusted</option>
            </select>
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

        {/* Secondary Row: Sorting & Reset */}
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
              <option value="type">Type</option>
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

      {/* Main Table Area */}
      {loading ? (
        <LoadingState message="Loading inventory activity..." />
      ) : error ? (
        <ErrorState
          title="Could not load inventory activity"
          message={error}
          onRetry={fetchData}
        />
      ) : isAllEmpty ? (
        <EmptyState
          title="No inventory activity found"
          description="Transactions will appear here as parts are received, issued, or adjusted."
        />
      ) : isFilteredEmpty ? (
        <EmptyState
          title="No transactions match your filters"
          description="Try loosening search filters, choosing a different location, or resetting the date range."
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
                  <th scope="col" className="px-5 py-3.5 whitespace-nowrap">
                    Date &amp; Time
                  </th>
                  <th scope="col" className="px-5 py-3.5 whitespace-nowrap">
                    Type
                  </th>
                  <th scope="col" className="px-5 py-3.5 whitespace-nowrap">
                    Employee
                  </th>
                  <th scope="col" className="px-5 py-3.5">
                    Spare Part
                  </th>
                  <th scope="col" className="px-5 py-3.5 whitespace-nowrap text-right">
                    Quantity
                  </th>
                  <th scope="col" className="px-5 py-3.5 whitespace-nowrap text-right">
                    Stock After
                  </th>
                  <th scope="col" className="px-5 py-3.5 whitespace-nowrap">
                    Location
                  </th>
                  <th scope="col" className="px-5 py-3.5">
                    Notes
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 bg-white">
                {data?.items.map((item: AdminActivityItem) => {
                  const isNegative = item.quantity_change < 0;
                  const isPositive = item.quantity_change > 0;
                  const signedQty = isPositive
                    ? `+${item.quantity_change}`
                    : `${item.quantity_change}`;

                  return (
                    <tr key={item.id} className="hover:bg-slate-50 transition-colors">
                      {/* Date & Time */}
                      <td className="px-5 py-4 whitespace-nowrap text-xs font-medium text-slate-800">
                        {formatDateTime(item.created_at)}
                      </td>

                      {/* Type Badge */}
                      <td className="px-5 py-4 whitespace-nowrap">
                        {getTypeBadge(item.type)}
                      </td>

                      {/* Actor (Employee) */}
                      <td className="px-5 py-4 whitespace-nowrap">
                        {item.actor ? (
                          <div>
                            <div className="text-xs font-medium text-slate-900">{item.actor.name}</div>
                            <div className="text-[11px] text-slate-400 font-mono">
                              {item.actor.employee_id}
                            </div>
                          </div>
                        ) : (
                          <span className="text-xs text-slate-400 italic">System</span>
                        )}
                      </td>

                      {/* Part */}
                      <td className="px-5 py-4">
                        <div className="min-w-0">
                          <Link
                            to={`/admin/parts/${item.part.id}`}
                            className="font-semibold text-slate-900 hover:text-blue-600 transition truncate block max-w-xs"
                          >
                            {item.part.name}
                          </Link>
                          <span className="text-xs text-slate-500 font-mono">
                            {item.part.part_number}
                          </span>
                        </div>
                      </td>

                      {/* Quantity Change (signed & colored) */}
                      <td className="px-5 py-4 whitespace-nowrap text-right font-mono font-bold text-xs">
                        <span
                          className={
                            isNegative
                              ? 'text-rose-600'
                              : isPositive
                              ? 'text-emerald-600'
                              : 'text-slate-600'
                          }
                        >
                          {signedQty}
                        </span>
                      </td>

                      {/* Resulting Qty */}
                      <td className="px-5 py-4 whitespace-nowrap text-right font-mono text-xs text-slate-700">
                        {item.quantity_after}
                      </td>

                      {/* Location */}
                      <td className="px-5 py-4 whitespace-nowrap">
                        <div className="text-xs text-slate-800 font-medium">{item.location.name}</div>
                        <div className="text-[11px] text-slate-400 font-mono">{item.location.code}</div>
                      </td>

                      {/* Notes */}
                      <td className="px-5 py-4 text-xs text-slate-600 max-w-xs truncate" title={item.notes || ''}>
                        {item.notes ? (
                          <span>{item.notes}</span>
                        ) : (
                          <span className="text-slate-300 italic">—</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
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

