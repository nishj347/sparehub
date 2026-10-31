import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Package, Plus, RotateCcw } from 'lucide-react';
import { adminPartsApi } from '../../api/adminParts';
import { ApiError } from '../../api/client';
import { locationsApi } from '../../api/locations';
import { machinesApi } from '../../api/machines';
import { LocationOption, MachineOption } from '../../types/masterData';
import { PartListItem } from '../../types/parts';
import { useDebouncedValue } from '../../hooks/useDebouncedValue';
import { getAssetUrl } from '../../lib/assetUrl';
import { Column, DataTable } from '../../components/ui/DataTable';
import { EmptyState } from '../../components/ui/EmptyState';
import { ErrorState } from '../../components/ui/ErrorState';
import { Pagination } from '../../components/ui/Pagination';
import { SearchInput } from '../../components/ui/SearchInput';
import { StatusBadge } from '../../components/ui/StatusBadge';
import { StockStatusBadge } from '../../components/admin/parts/StockStatusBadge';

export const PartsPage: React.FC = () => {
  const navigate = useNavigate();

  // Data states
  const [parts, setParts] = useState<PartListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [isLoading, setIsLoading] = useState(true);
  const [fetchError, setFetchError] = useState<string | null>(null);

  // Filter options
  const [categories, setCategories] = useState<string[]>([]);
  const [locations, setLocations] = useState<LocationOption[]>([]);
  const [machines, setMachines] = useState<MachineOption[]>([]);

  // Filter & search states
  const [search, setSearch] = useState('');
  const debouncedSearch = useDebouncedValue(search, 300);
  const [categoryFilter, setCategoryFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState<'all' | 'active' | 'inactive'>('all');
  const [stockFilter, setStockFilter] = useState<'all' | 'in_stock' | 'low' | 'out'>('all');
  const [locationFilter, setLocationFilter] = useState<number | ''>('');
  const [machineFilter, setMachineFilter] = useState<number | ''>('');

  // Pagination & sort states
  const [page, setPage] = useState(1);
  const [sort, setSort] = useState<{
    field: 'name' | 'part_number' | 'category' | 'total_quantity' | 'updated_at';
    order: 'asc' | 'desc';
  }>({
    field: 'name',
    order: 'asc',
  });

  // Stale request protection
  const latestRequestId = useRef(0);

  // Load filter options on mount
  useEffect(() => {
    adminPartsApi
      .getCategories()
      .then((cats) => setCategories(cats))
      .catch(() => {});

    locationsApi
      .getOptions()
      .then((locs) => setLocations(locs))
      .catch(() => {});

    machinesApi
      .getOptions()
      .then((machs) => setMachines(machs))
      .catch(() => {});
  }, []);

  const fetchParts = useCallback(async () => {
    const requestId = ++latestRequestId.current;
    setIsLoading(true);
    setFetchError(null);

    try {
      const res = await adminPartsApi.list({
        q: debouncedSearch.trim() || undefined,
        category: categoryFilter || undefined,
        status: statusFilter,
        stock: stockFilter,
        location_id: locationFilter ? Number(locationFilter) : undefined,
        machine_id: machineFilter ? Number(machineFilter) : undefined,
        sort: sort.field,
        order: sort.order,
        page,
        page_size: 15,
      });

      // Ignore response if a newer search/filter request was launched
      if (requestId === latestRequestId.current) {
        setParts(res.items);
        setTotal(res.total);
        setTotalPages(res.total_pages);
      }
    } catch (err) {
      if (requestId === latestRequestId.current) {
        const msg = err instanceof ApiError ? err.message : 'Failed to load spare parts catalog.';
        setFetchError(msg);
      }
    } finally {
      if (requestId === latestRequestId.current) {
        setIsLoading(false);
      }
    }
  }, [
    debouncedSearch,
    categoryFilter,
    statusFilter,
    stockFilter,
    locationFilter,
    machineFilter,
    sort,
    page,
  ]);

  useEffect(() => {
    fetchParts();
  }, [fetchParts]);

  // Reset page when filters change
  useEffect(() => {
    setPage(1);
  }, [
    debouncedSearch,
    categoryFilter,
    statusFilter,
    stockFilter,
    locationFilter,
    machineFilter,
  ]);

  const handleSort = (field: string) => {
    setSort((prev) => ({
      field: field as 'name' | 'part_number' | 'category' | 'total_quantity' | 'updated_at',
      order: prev.field === field && prev.order === 'asc' ? 'desc' : 'asc',
    }));
  };

  const hasActiveFilters =
    Boolean(search) ||
    Boolean(categoryFilter) ||
    statusFilter !== 'all' ||
    stockFilter !== 'all' ||
    Boolean(locationFilter) ||
    Boolean(machineFilter);

  const clearFilters = () => {
    setSearch('');
    setCategoryFilter('');
    setStatusFilter('all');
    setStockFilter('all');
    setLocationFilter('');
    setMachineFilter('');
    setPage(1);
  };

  const columns: Column<PartListItem>[] = [
    {
      header: 'Part',
      className: 'w-16 px-4',
      accessor: (part) => {
        const imgUrl = getAssetUrl(part.image_url);
        return (
          <div className="w-10 h-10 rounded-lg border border-slate-200 bg-slate-100 flex items-center justify-center overflow-hidden shrink-0 shadow-sm">
            {imgUrl ? (
              <img
                src={imgUrl}
                alt={part.name}
                className="w-full h-full object-cover"
                loading="lazy"
              />
            ) : (
              <Package className="w-5 h-5 text-slate-400" />
            )}
          </div>
        );
      },
    },
    {
      header: 'Part ID',
      sortKey: 'part_number',
      accessor: (part) => (
        <span className="font-mono text-xs font-semibold text-slate-800 bg-slate-100 border border-slate-200 px-2 py-0.5 rounded">
          {part.part_number}
        </span>
      ),
    },
    {
      header: 'Name',
      sortKey: 'name',
      accessor: (part) => (
        <div className="max-w-xs">
          <p className="font-medium text-slate-900 truncate hover:text-blue-600 transition-colors">
            {part.name}
          </p>
          <p className="text-xs text-slate-400 truncate">
            {part.category} {part.manufacturer ? `· ${part.manufacturer}` : ''}
          </p>
        </div>
      ),
    },
    {
      header: 'Category',
      sortKey: 'category',
      accessor: (part) => (
        <span className="text-xs text-slate-600 bg-slate-100 px-2 py-0.5 rounded-md">
          {part.category}
        </span>
      ),
    },
    {
      header: 'Used In',
      accessor: (part) => {
        if (!part.machines || part.machines.length === 0) {
          return <span className="text-xs text-slate-400 italic">—</span>;
        }
        const visibleMachines = part.machines.slice(0, 2);
        const remainder = part.machines.length - 2;

        return (
          <div className="flex flex-wrap items-center gap-1 max-w-[200px]">
            {visibleMachines.map((m) => (
              <span
                key={m.id}
                className="inline-flex items-center text-[11px] font-mono bg-slate-100 text-slate-700 px-1.5 py-0.5 rounded border border-slate-200"
                title={`${m.name} (${m.code})`}
              >
                {m.code}
              </span>
            ))}
            {remainder > 0 && (
              <span
                className="inline-flex items-center text-[10px] font-semibold bg-slate-200 text-slate-600 px-1.5 py-0.5 rounded"
                title={`${remainder} additional machines`}
              >
                +{remainder}
              </span>
            )}
          </div>
        );
      },
    },
    {
      header: 'Total Stock',
      sortKey: 'total_quantity',
      align: 'right',
      accessor: (part) => (
        <div className="text-right">
          <span className="font-mono font-semibold text-slate-900">
            {part.total_quantity.toLocaleString()}
          </span>
          <span className="text-[11px] text-slate-400 block">
            {part.location_count} {part.location_count === 1 ? 'site' : 'sites'}
          </span>
        </div>
      ),
    },
    {
      header: 'Stock Status',
      accessor: (part) => (
        <StockStatusBadge
          lowStock={part.low_stock}
          outOfStock={part.out_of_stock}
        />
      ),
    },
    {
      header: 'Status',
      accessor: (part) => <StatusBadge isActive={part.is_active} />,
    },
    {
      header: 'Actions',
      align: 'right',
      accessor: (part) => (
        <div
          className="flex items-center justify-end gap-2"
          onClick={(e) => e.stopPropagation()}
        >
          <Link
            to={`/admin/parts/${part.id}`}
            className="px-2.5 py-1 text-xs font-medium text-slate-700 bg-white border border-slate-300 rounded-md hover:bg-slate-50 transition-colors"
          >
            View
          </Link>
          <Link
            to={`/admin/parts/${part.id}/edit`}
            className="px-2.5 py-1 text-xs font-medium text-blue-600 bg-blue-50 border border-blue-200 rounded-md hover:bg-blue-100 transition-colors"
          >
            Edit
          </Link>
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      {/* Page Title & Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">
            Spare Parts Catalog
          </h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Manage spare parts definitions, cross-plant stock levels, and machinery assignments.
          </p>
        </div>
        <Link
          to="/admin/parts/new"
          className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors shadow-sm shrink-0"
        >
          <Plus className="w-4 h-4" />
          <span>Add Spare Part</span>
        </Link>
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm space-y-3">
        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 gap-3">
          {/* Search box */}
          <div className="lg:col-span-2">
            <SearchInput
              value={search}
              onChange={setSearch}
              placeholder="Search ID, name, manufacturer, machine..."
            />
          </div>

          {/* Category Filter */}
          <div>
            <select
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              className="w-full px-3 py-2 text-xs bg-white border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              <option value="">All Categories</option>
              {categories.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </div>

          {/* Stock Status Filter */}
          <div>
            <select
              value={stockFilter}
              onChange={(e) =>
                setStockFilter(e.target.value as 'all' | 'in_stock' | 'low' | 'out')
              }
              className="w-full px-3 py-2 text-xs bg-white border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              <option value="all">All Stock Statuses</option>
              <option value="in_stock">In Stock</option>
              <option value="low">Low Stock</option>
              <option value="out">Out of Stock</option>
            </select>
          </div>

          {/* Plant Location Filter */}
          <div>
            <select
              value={locationFilter}
              onChange={(e) =>
                setLocationFilter(e.target.value ? Number(e.target.value) : '')
              }
              className="w-full px-3 py-2 text-xs bg-white border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              <option value="">All Plant Sites</option>
              {locations.map((loc) => (
                <option key={loc.id} value={loc.id}>
                  {loc.name} ({loc.code})
                </option>
              ))}
            </select>
          </div>

          {/* Active Status Filter */}
          <div>
            <select
              value={statusFilter}
              onChange={(e) =>
                setStatusFilter(e.target.value as 'all' | 'active' | 'inactive')
              }
              className="w-full px-3 py-2 text-xs bg-white border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              <option value="all">Active & Inactive</option>
              <option value="active">Active Only</option>
              <option value="inactive">Inactive Only</option>
            </select>
          </div>
        </div>

        {/* Machine filter and Reset */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-2 border-t border-slate-100">
          <div className="w-full sm:w-64">
            <select
              value={machineFilter}
              onChange={(e) =>
                setMachineFilter(e.target.value ? Number(e.target.value) : '')
              }
              className="w-full px-3 py-1.5 text-xs bg-slate-50 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              <option value="">All Machinery Assignments</option>
              {machines.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.name} ({m.code})
                </option>
              ))}
            </select>
          </div>

          {hasActiveFilters && (
            <button
              type="button"
              onClick={clearFilters}
              className="inline-flex items-center gap-1.5 text-xs font-medium text-slate-600 hover:text-slate-900 bg-slate-100 hover:bg-slate-200 px-3 py-1.5 rounded-lg transition-colors"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>Clear Filters</span>
            </button>
          )}
        </div>
      </div>

      {/* Main Table or State */}
      {fetchError ? (
        <ErrorState message={fetchError} onRetry={fetchParts} />
      ) : (
        <div className="space-y-4">
          <DataTable
            columns={columns}
            data={parts}
            keyExtractor={(part) => part.id}
            isLoading={isLoading}
            sort={sort}
            onSort={handleSort}
            onRowClick={(part) => navigate(`/admin/parts/${part.id}`)}
            emptyState={
              hasActiveFilters ? (
                <EmptyState
                  title="No matching spare parts"
                  description="Adjust your search query or reset your filters to see more results."
                  action={{
                    label: 'Clear all filters',
                    onClick: clearFilters,
                  }}
                />
              ) : (
                <EmptyState
                  title="Catalog is empty"
                  description="No spare parts have been defined in the system yet."
                  action={{
                    label: '+ Add First Spare Part',
                    onClick: () => navigate('/admin/parts/new'),
                  }}
                />
              )
            }
          />

          {/* Pagination */}
          {!isLoading && total > 0 && (
            <Pagination
              page={page}
              totalPages={totalPages}
              total={total}
              pageSize={15}
              onPageChange={setPage}
            />
          )}
        </div>
      )}
    </div>
  );
};
