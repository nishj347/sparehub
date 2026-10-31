import React, { useCallback, useEffect, useState } from 'react';
import { LocationItem } from '../../types/masterData';
import { locationsApi } from '../../api/locations';
import { useDebouncedValue } from '../../hooks/useDebouncedValue';
import { useToast } from '../../components/ui/Toast';
import { ApiError } from '../../api/client';
import { Column, DataTable } from '../../components/ui/DataTable';
import { Pagination } from '../../components/ui/Pagination';
import { SearchInput } from '../../components/ui/SearchInput';
import { StatusBadge } from '../../components/ui/StatusBadge';
import { ConfirmDialog } from '../../components/ui/ConfirmDialog';
import { EmptyState } from '../../components/ui/EmptyState';
import { ErrorState } from '../../components/ui/ErrorState';
import { LocationFormModal } from '../../components/admin/LocationFormModal';

export const LocationsPage: React.FC = () => {
  const { success, error: toastError } = useToast();

  // Data states
  const [locations, setLocations] = useState<LocationItem[]>([]);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [isLoading, setIsLoading] = useState(true);
  const [fetchError, setFetchError] = useState<string | null>(null);

  // Filter & pagination states
  const [search, setSearch] = useState('');
  const debouncedSearch = useDebouncedValue(search, 300);
  const [statusFilter, setStatusFilter] = useState<'all' | 'active' | 'inactive'>('all');
  const [page, setPage] = useState(1);
  const [sort, setSort] = useState<{ field: string; order: 'asc' | 'desc' }>({
    field: 'name',
    order: 'asc',
  });

  // Modal states
  const [isFormModalOpen, setIsFormModalOpen] = useState(false);
  const [editingLocation, setEditingLocation] = useState<LocationItem | null>(null);

  // Deactivation confirmation dialog
  const [deactivatingLocation, setDeactivatingLocation] = useState<LocationItem | null>(null);
  const [isDeactivating, setIsDeactivating] = useState(false);
  const [deactivateError, setDeactivateError] = useState<string | null>(null);

  const fetchLocations = useCallback(async () => {
    setIsLoading(true);
    setFetchError(null);
    try {
      const res = await locationsApi.list({
        q: debouncedSearch.trim() || undefined,
        status: statusFilter,
        sort: sort.field,
        order: sort.order,
        page,
        page_size: 15,
      });
      setLocations(res.items);
      setTotal(res.total);
      setTotalPages(res.total_pages);
    } catch (err: unknown) {
      const msg = err instanceof ApiError ? err.message : 'Failed to load locations';
      setFetchError(msg);
    } finally {
      setIsLoading(false);
    }
  }, [debouncedSearch, statusFilter, sort, page]);

  useEffect(() => {
    fetchLocations();
  }, [fetchLocations]);

  // Reset page when search or status filter changes
  useEffect(() => {
    setPage(1);
  }, [debouncedSearch, statusFilter]);

  const handleSort = (field: string) => {
    setSort((prev) => ({
      field,
      order: prev.field === field && prev.order === 'asc' ? 'desc' : 'asc',
    }));
  };

  const handleOpenAdd = () => {
    setEditingLocation(null);
    setIsFormModalOpen(true);
  };

  const handleOpenEdit = (location: LocationItem) => {
    setEditingLocation(location);
    setIsFormModalOpen(true);
  };

  const handleConfirmDeactivate = async () => {
    if (!deactivatingLocation) return;
    setIsDeactivating(true);
    setDeactivateError(null);
    try {
      await locationsApi.deactivate(deactivatingLocation.id);
      success(`Location "${deactivatingLocation.name}" has been deactivated.`);
      setDeactivatingLocation(null);
      fetchLocations();
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setDeactivateError(err.message);
      } else {
        setDeactivateError('Failed to deactivate location. Please try again.');
      }
    } finally {
      setIsDeactivating(false);
    }
  };

  const handleActivate = async (location: LocationItem) => {
    try {
      await locationsApi.activate(location.id);
      success(`Location "${location.name}" has been activated.`);
      fetchLocations();
    } catch (err: unknown) {
      const msg = err instanceof ApiError ? err.message : 'Failed to activate location';
      toastError(msg);
    }
  };

  const columns: Column<LocationItem>[] = [
    {
      header: 'Code',
      sortKey: 'code',
      className: 'w-28',
      accessor: (loc) => (
        <span className="font-mono text-xs font-semibold px-2 py-0.5 rounded bg-slate-100 text-slate-800 border border-slate-200">
          {loc.code}
        </span>
      ),
    },
    {
      header: 'Name',
      sortKey: 'name',
      accessor: (loc) => (
        <div>
          <span className="font-medium text-slate-900">{loc.name}</span>
        </div>
      ),
    },
    {
      header: 'City',
      sortKey: 'city',
      accessor: (loc) => <span className="text-slate-600">{loc.city}</span>,
    },
    {
      header: 'Users',
      align: 'center',
      className: 'w-24',
      accessor: (loc) => (
        <span className="inline-flex items-center justify-center px-2 py-0.5 text-xs font-medium rounded-full bg-slate-100 text-slate-700">
          {loc.user_count}
        </span>
      ),
    },
    {
      header: 'Machines',
      align: 'center',
      className: 'w-24',
      accessor: (loc) => (
        <span className="inline-flex items-center justify-center px-2 py-0.5 text-xs font-medium rounded-full bg-slate-100 text-slate-700">
          {loc.machine_count}
        </span>
      ),
    },
    {
      header: 'Stocked Parts',
      align: 'center',
      className: 'w-28',
      accessor: (loc) => (
        <span className="inline-flex items-center justify-center px-2 py-0.5 text-xs font-medium rounded-full bg-slate-100 text-slate-700">
          {loc.stocked_part_count}
        </span>
      ),
    },
    {
      header: 'Status',
      className: 'w-24',
      accessor: (loc) => <StatusBadge isActive={loc.is_active} />,
    },
    {
      header: 'Actions',
      align: 'right',
      className: 'w-36',
      accessor: (loc) => (
        <div className="flex items-center justify-end gap-2">
          <button
            type="button"
            onClick={() => handleOpenEdit(loc)}
            className="text-xs font-medium text-slate-600 hover:text-primary-600 px-2.5 py-1 rounded border border-slate-200 hover:border-primary-300 hover:bg-primary-50/50 transition-colors"
          >
            Edit
          </button>
          {loc.is_active ? (
            <button
              type="button"
              onClick={() => {
                setDeactivateError(null);
                setDeactivatingLocation(loc);
              }}
              className="text-xs font-medium text-rose-600 hover:text-rose-700 px-2.5 py-1 rounded border border-rose-200 hover:bg-rose-50 transition-colors"
            >
              Deactivate
            </button>
          ) : (
            <button
              type="button"
              onClick={() => handleActivate(loc)}
              className="text-xs font-medium text-emerald-600 hover:text-emerald-700 px-2.5 py-1 rounded border border-emerald-200 hover:bg-emerald-50 transition-colors"
            >
              Activate
            </button>
          )}
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">Locations</h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Manage company plants, warehouses, and manufacturing facilities.
          </p>
        </div>
        <button
          type="button"
          onClick={handleOpenAdd}
          className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-primary-600 rounded-lg hover:bg-primary-700 shadow-sm transition-colors focus:outline-none focus:ring-2 focus:ring-primary-500 self-start sm:self-auto"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          Add Location
        </button>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4 bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
        <div className="w-full sm:w-80">
          <SearchInput
            value={search}
            onChange={setSearch}
            placeholder="Search by name, code, or city..."
          />
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Status:</span>
          <div className="inline-flex rounded-lg border border-slate-200 p-0.5 bg-slate-50">
            {(['all', 'active', 'inactive'] as const).map((status) => (
              <button
                key={status}
                type="button"
                onClick={() => setStatusFilter(status)}
                className={`px-3 py-1 text-xs font-medium rounded-md capitalize transition-colors ${
                  statusFilter === status
                    ? 'bg-white text-slate-900 shadow-sm'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                {status}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Data Content */}
      {fetchError ? (
        <ErrorState
          title="Failed to Load Locations"
          message={fetchError}
          onRetry={fetchLocations}
        />
      ) : (
        <div className="space-y-4">
          <DataTable
            columns={columns}
            data={locations}
            keyExtractor={(loc) => loc.id}
            isLoading={isLoading}
            sort={sort}
            onSort={handleSort}
            emptyState={
              <EmptyState
                title="No locations found"
                description={
                  debouncedSearch || statusFilter !== 'all'
                    ? 'Try adjusting your search or filters.'
                    : 'Get started by creating your first company location.'
                }
                action={
                  debouncedSearch || statusFilter !== 'all'
                    ? undefined
                    : { label: 'Add Location', onClick: handleOpenAdd }
                }
              />
            }
          />

          <Pagination
            page={page}
            pageSize={15}
            total={total}
            totalPages={totalPages}
            onPageChange={setPage}
          />
        </div>
      )}

      {/* Add / Edit Form Modal */}
      <LocationFormModal
        isOpen={isFormModalOpen}
        onClose={() => setIsFormModalOpen(false)}
        locationToEdit={editingLocation}
        onSuccess={() => fetchLocations()}
      />

      {/* Deactivate Confirmation Dialog */}
      <ConfirmDialog
        isOpen={Boolean(deactivatingLocation)}
        onClose={() => {
          setDeactivatingLocation(null);
          setDeactivateError(null);
        }}
        onConfirm={handleConfirmDeactivate}
        title="Deactivate Location"
        message={
          <div>
            Are you sure you want to deactivate{' '}
            <strong className="text-slate-900">{deactivatingLocation?.name}</strong>?
            <p className="mt-2 text-xs text-slate-500">
              Deactivated locations cannot be assigned to new machines or users. Historical records
              and transactions remain intact.
            </p>
          </div>
        }
        confirmText="Deactivate Location"
        isDestructive
        isLoading={isDeactivating}
        error={deactivateError}
      />
    </div>
  );
};

