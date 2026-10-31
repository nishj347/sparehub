import React, { useCallback, useEffect, useState } from 'react';
import { LocationOption, MachineItem } from '../../types/masterData';
import { machinesApi } from '../../api/machines';
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
import { MachineFormModal } from '../../components/admin/MachineFormModal';

export const MachinesPage: React.FC = () => {
  const { success, error: toastError } = useToast();

  // Data states
  const [machines, setMachines] = useState<MachineItem[]>([]);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [isLoading, setIsLoading] = useState(true);
  const [fetchError, setFetchError] = useState<string | null>(null);

  // Dropdown filter options
  const [locationOptions, setLocationOptions] = useState<LocationOption[]>([]);

  // Filter & pagination states
  const [search, setSearch] = useState('');
  const debouncedSearch = useDebouncedValue(search, 300);
  const [statusFilter, setStatusFilter] = useState<'all' | 'active' | 'inactive'>('all');
  const [selectedLocation, setSelectedLocation] = useState<string>('all'); // 'all' | 'unassigned' | locationId string
  const [page, setPage] = useState(1);
  const [sort, setSort] = useState<{ field: string; order: 'asc' | 'desc' }>({
    field: 'name',
    order: 'asc',
  });

  // Modal states
  const [isFormModalOpen, setIsFormModalOpen] = useState(false);
  const [editingMachine, setEditingMachine] = useState<MachineItem | null>(null);

  // Deactivation confirmation dialog
  const [deactivatingMachine, setDeactivatingMachine] = useState<MachineItem | null>(null);
  const [isDeactivating, setIsDeactivating] = useState(false);
  const [deactivateError, setDeactivateError] = useState<string | null>(null);

  // Fetch location dropdown options on mount
  useEffect(() => {
    locationsApi
      .getOptions()
      .then(setLocationOptions)
      .catch(() => {});
  }, []);

  const fetchMachines = useCallback(async () => {
    setIsLoading(true);
    setFetchError(null);
    try {
      const isUnassigned = selectedLocation === 'unassigned';
      const locId =
        selectedLocation !== 'all' && selectedLocation !== 'unassigned'
          ? Number(selectedLocation)
          : undefined;

      const res = await machinesApi.list({
        q: debouncedSearch.trim() || undefined,
        status: statusFilter,
        location_id: locId,
        unassigned: isUnassigned ? true : undefined,
        sort: sort.field,
        order: sort.order,
        page,
        page_size: 15,
      });
      setMachines(res.items);
      setTotal(res.total);
      setTotalPages(res.total_pages);
    } catch (err: unknown) {
      const msg = err instanceof ApiError ? err.message : 'Failed to load machines';
      setFetchError(msg);
    } finally {
      setIsLoading(false);
    }
  }, [debouncedSearch, statusFilter, selectedLocation, sort, page]);

  useEffect(() => {
    fetchMachines();
  }, [fetchMachines]);

  // Reset page when filters change
  useEffect(() => {
    setPage(1);
  }, [debouncedSearch, statusFilter, selectedLocation]);

  const handleSort = (field: string) => {
    setSort((prev) => ({
      field,
      order: prev.field === field && prev.order === 'asc' ? 'desc' : 'asc',
    }));
  };

  const handleOpenAdd = () => {
    setEditingMachine(null);
    setIsFormModalOpen(true);
  };

  const handleOpenEdit = (machine: MachineItem) => {
    setEditingMachine(machine);
    setIsFormModalOpen(true);
  };

  const handleConfirmDeactivate = async () => {
    if (!deactivatingMachine) return;
    setIsDeactivating(true);
    setDeactivateError(null);
    try {
      await machinesApi.deactivate(deactivatingMachine.id);
      success(`Machine "${deactivatingMachine.name}" has been deactivated.`);
      setDeactivatingMachine(null);
      fetchMachines();
    } catch (err: unknown) {
      const msg = err instanceof ApiError ? err.message : 'Failed to deactivate machine';
      setDeactivateError(msg);
    } finally {
      setIsDeactivating(false);
    }
  };

  const handleActivate = async (machine: MachineItem) => {
    try {
      await machinesApi.activate(machine.id);
      success(`Machine "${machine.name}" has been activated.`);
      fetchMachines();
    } catch (err: unknown) {
      const msg = err instanceof ApiError ? err.message : 'Failed to activate machine';
      toastError(msg);
    }
  };

  const columns: Column<MachineItem>[] = [
    {
      header: 'Code',
      sortKey: 'code',
      className: 'w-28',
      accessor: (m) => (
        <span className="font-mono text-xs font-semibold px-2 py-0.5 rounded bg-slate-100 text-slate-800 border border-slate-200">
          {m.code}
        </span>
      ),
    },
    {
      header: 'Machine Name',
      sortKey: 'name',
      accessor: (m) => <span className="font-medium text-slate-900">{m.name}</span>,
    },
    {
      header: 'Assigned Location',
      accessor: (m) =>
        m.location ? (
          <div className="flex items-center gap-2">
            <span className="text-slate-800">{m.location.name}</span>
            <span className="font-mono text-xs text-slate-500 bg-slate-100 px-1.5 py-0.5 rounded">
              {m.location.code}
            </span>
          </div>
        ) : (
          <span className="text-xs italic text-slate-400">Unassigned</span>
        ),
    },
    {
      header: 'Linked Parts',
      align: 'center',
      className: 'w-28',
      accessor: (m) => (
        <span className="inline-flex items-center justify-center px-2 py-0.5 text-xs font-medium rounded-full bg-slate-100 text-slate-700">
          {m.part_count}
        </span>
      ),
    },
    {
      header: 'Status',
      className: 'w-24',
      accessor: (m) => <StatusBadge isActive={m.is_active} />,
    },
    {
      header: 'Actions',
      align: 'right',
      className: 'w-36',
      accessor: (m) => (
        <div className="flex items-center justify-end gap-2">
          <button
            type="button"
            onClick={() => handleOpenEdit(m)}
            className="text-xs font-medium text-slate-600 hover:text-primary-600 px-2.5 py-1 rounded border border-slate-200 hover:border-primary-300 hover:bg-primary-50/50 transition-colors"
          >
            Edit
          </button>
          {m.is_active ? (
            <button
              type="button"
              onClick={() => {
                setDeactivateError(null);
                setDeactivatingMachine(m);
              }}
              className="text-xs font-medium text-rose-600 hover:text-rose-700 px-2.5 py-1 rounded border border-rose-200 hover:bg-rose-50 transition-colors"
            >
              Deactivate
            </button>
          ) : (
            <button
              type="button"
              onClick={() => handleActivate(m)}
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
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">Machines</h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Manage factory equipment, production lines, and physical machinery.
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
          Add Machine
        </button>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-4 bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
        <div className="w-full lg:w-72">
          <SearchInput
            value={search}
            onChange={setSearch}
            placeholder="Search machine name or code..."
          />
        </div>

        <div className="flex flex-wrap items-center gap-4">
          {/* Location filter */}
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              Location:
            </span>
            <select
              value={selectedLocation}
              onChange={(e) => setSelectedLocation(e.target.value)}
              className="text-xs py-1.5 px-3 bg-white border border-slate-200 rounded-lg text-slate-700 focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              <option value="all">All Locations</option>
              <option value="unassigned">Unassigned Only</option>
              {locationOptions.map((loc) => (
                <option key={loc.id} value={loc.id.toString()}>
                  {loc.name} ({loc.code})
                </option>
              ))}
            </select>
          </div>

          {/* Status filter tabs */}
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              Status:
            </span>
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
      </div>

      {/* Data Content */}
      {fetchError ? (
        <ErrorState
          title="Failed to Load Machines"
          message={fetchError}
          onRetry={fetchMachines}
        />
      ) : (
        <div className="space-y-4">
          <DataTable
            columns={columns}
            data={machines}
            keyExtractor={(m) => m.id}
            isLoading={isLoading}
            sort={sort}
            onSort={handleSort}
            emptyState={
              <EmptyState
                title="No machines found"
                description={
                  debouncedSearch || statusFilter !== 'all' || selectedLocation !== 'all'
                    ? 'Try adjusting your search or filters.'
                    : 'Get started by creating your first machine.'
                }
                action={
                  debouncedSearch || statusFilter !== 'all' || selectedLocation !== 'all'
                    ? undefined
                    : { label: 'Add Machine', onClick: handleOpenAdd }
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
      <MachineFormModal
        isOpen={isFormModalOpen}
        onClose={() => setIsFormModalOpen(false)}
        machineToEdit={editingMachine}
        onSuccess={() => fetchMachines()}
      />

      {/* Deactivate Confirmation Dialog */}
      <ConfirmDialog
        isOpen={Boolean(deactivatingMachine)}
        onClose={() => {
          setDeactivatingMachine(null);
          setDeactivateError(null);
        }}
        onConfirm={handleConfirmDeactivate}
        title="Deactivate Machine"
        message={
          <div>
            Are you sure you want to deactivate{' '}
            <strong className="text-slate-900">{deactivatingMachine?.name}</strong>?
            <p className="mt-2 text-xs text-slate-500">
              Deactivating keeps all historical records and spare part mappings intact. The machine
              will no longer appear in active dropdown selections.
            </p>
          </div>
        }
        confirmText="Deactivate Machine"
        isDestructive
        isLoading={isDeactivating}
        error={deactivateError}
      />
    </div>
  );
};

