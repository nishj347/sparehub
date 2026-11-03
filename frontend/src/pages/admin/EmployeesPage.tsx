import React, { useCallback, useEffect, useState } from 'react';
import { useUrlSearchState } from '../../hooks/useUrlSearchState';
import { useDebouncedValue } from '../../hooks/useDebouncedValue';
import { usersApi } from '../../api/users';
import { locationsApi } from '../../api/locations';
import { UserListItem } from '../../types/user';
import { LocationOption } from '../../types/masterData';
import { Page } from '../../types/common';
import { formatDateTime } from '../../lib/formatDateTime';
import { useAuth } from '../../auth/AuthContext';
import { useToast } from '../../components/ui/Toast';
import { DataTable } from '../../components/ui/DataTable';
import { Pagination } from '../../components/ui/Pagination';
import { SearchInput } from '../../components/ui/SearchInput';
import { StatusBadge } from '../../components/ui/StatusBadge';
import { EmptyState } from '../../components/ui/EmptyState';
import { LoadingState } from '../../components/ui/LoadingState';
import { ErrorState } from '../../components/ui/ErrorState';
import { ConfirmDialog } from '../../components/ui/ConfirmDialog';
import { EmployeeFormModal } from '../../components/admin/EmployeeFormModal';
import { ResetPasswordModal } from '../../components/admin/ResetPasswordModal';
import { TemporaryPasswordDialog } from '../../components/admin/TemporaryPasswordDialog';
import {
  KeyRound,
  Lock,
  Pencil,
  Power,
  RotateCcw,
  UserCheck,
  UserPlus,
  Users,
} from 'lucide-react';

export const EmployeesPage: React.FC = () => {
  const { user: currentUser } = useAuth();
  const { success, error: toastError } = useToast();
  const { get, getInt, set, clear } = useUrlSearchState();

  // URL State
  const urlSearch = get('q');
  const roleFilter = get('role', 'all');
  const locationFilter = get('location_id', 'all');
  const statusFilter = get('status', 'all');
  const page = getInt('page', 1);

  // Local state for debounced search
  const [searchTerm, setSearchTerm] = useState(urlSearch);
  const debouncedSearch = useDebouncedValue(searchTerm, 300);

  // Synchronize debounced search to URL
  useEffect(() => {
    if (debouncedSearch !== urlSearch) {
      set({ q: debouncedSearch || null, page: 1 });
    }
  }, [debouncedSearch]); // eslint-disable-line react-hooks/exhaustive-deps

  // Synchronize URL search back to input (e.g. browser back)
  useEffect(() => {
    setSearchTerm(urlSearch);
  }, [urlSearch]);

  // Data state
  const [data, setData] = useState<Page<UserListItem> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [locations, setLocations] = useState<LocationOption[]>([]);

  // Modals state
  const [isFormModalOpen, setIsFormModalOpen] = useState(false);
  const [userToEdit, setUserToEdit] = useState<UserListItem | null>(null);

  const [deactivatingUser, setDeactivatingUser] = useState<UserListItem | null>(null);
  const [resettingUser, setResettingUser] = useState<UserListItem | null>(null);

  // Post-create temporary password display state
  const [createdInfo, setCreatedInfo] = useState<{
    employeeId: string;
    name: string;
    temporaryPassword: string;
  } | null>(null);

  // Fetch locations options for filter
  useEffect(() => {
    locationsApi.getOptions().then(setLocations).catch(() => {});
  }, []);

  // Fetch users
  const fetchUsers = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await usersApi.list({
        q: urlSearch || undefined,
        role: roleFilter !== 'all' ? roleFilter : undefined,
        location_id: locationFilter !== 'all' ? Number(locationFilter) : undefined,
        status: statusFilter as 'active' | 'inactive' | 'all',
        page,
        page_size: 15,
        sort: 'employee_id',
        order: 'asc',
      });
      setData(res);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load employees.');
    } finally {
      setLoading(false);
    }
  }, [urlSearch, roleFilter, locationFilter, statusFilter, page]);

  useEffect(() => {
    fetchUsers();
  }, [fetchUsers]);

  // Open Create Modal
  const handleOpenCreate = () => {
    setUserToEdit(null);
    setIsFormModalOpen(true);
  };

  // Open Edit Modal
  const handleOpenEdit = (user: UserListItem) => {
    setUserToEdit(user);
    setIsFormModalOpen(true);
  };

  // Handle Form Success
  const handleFormSuccess = (savedUser: UserListItem, temporaryPassword?: string) => {
    fetchUsers();
    if (temporaryPassword) {
      setCreatedInfo({
        employeeId: savedUser.employee_id,
        name: savedUser.name,
        temporaryPassword,
      });
    }
  };

  // Toggle active/inactive
  const handleConfirmToggleActive = async () => {
    if (!deactivatingUser) return;
    try {
      if (deactivatingUser.is_active) {
        await usersApi.deactivate(deactivatingUser.id);
        success(`Account for ${deactivatingUser.name} deactivated.`);
      } else {
        await usersApi.activate(deactivatingUser.id);
        success(`Account for ${deactivatingUser.name} activated.`);
      }
      fetchUsers();
    } catch (err: unknown) {
      toastError(err instanceof Error ? err.message : 'Action failed.');
    } finally {
      setDeactivatingUser(null);
    }
  };

  const hasActiveFilters =
    Boolean(urlSearch) ||
    roleFilter !== 'all' ||
    locationFilter !== 'all' ||
    statusFilter !== 'all';

  const handleClearFilters = () => {
    setSearchTerm('');
    clear();
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 flex items-center gap-2.5">
            <Users className="w-6 h-6 text-primary-600" />
            Employees
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            Manage employee access, assign locations and roles, and recover accounts.
          </p>
        </div>

        {/* Primary Action Button */}
        <button
          type="button"
          onClick={handleOpenCreate}
          className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-primary-600 rounded-lg hover:bg-primary-700 shadow-sm transition-colors focus:outline-none focus:ring-2 focus:ring-primary-500 self-start sm:self-auto"
        >
          <UserPlus className="w-4 h-4" />
          <span>Add Employee</span>
        </button>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-4 bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
        <div className="w-full lg:w-80">
          <SearchInput
            value={searchTerm}
            onChange={setSearchTerm}
            placeholder="Search by ID, name, email..."
          />
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {/* Role Filter */}
          <select
            value={roleFilter}
            onChange={(e) => set({ role: e.target.value === 'all' ? null : e.target.value, page: 1 })}
            className="text-xs border border-slate-300 rounded-lg px-2.5 py-2 bg-white text-slate-700 focus:outline-none focus:ring-2 focus:ring-primary-500 hover:border-slate-400 transition-colors"
            aria-label="Filter by role"
          >
            <option value="all">All Roles</option>
            <option value="EMPLOYEE">Employees</option>
            <option value="STORE_ADMIN">Store Administrators</option>
          </select>

          {/* Location Filter */}
          <select
            value={locationFilter}
            onChange={(e) => set({ location_id: e.target.value === 'all' ? null : e.target.value, page: 1 })}
            className="text-xs border border-slate-300 rounded-lg px-2.5 py-2 bg-white text-slate-700 focus:outline-none focus:ring-2 focus:ring-primary-500 hover:border-slate-400 transition-colors"
            aria-label="Filter by location"
          >
            <option value="all">All Locations</option>
            {locations.map((loc) => (
              <option key={loc.id} value={String(loc.id)}>
                {loc.name} ({loc.code})
              </option>
            ))}
          </select>

          {/* Status Filter */}
          <select
            value={statusFilter}
            onChange={(e) => set({ status: e.target.value === 'all' ? null : e.target.value, page: 1 })}
            className="text-xs border border-slate-300 rounded-lg px-2.5 py-2 bg-white text-slate-700 focus:outline-none focus:ring-2 focus:ring-primary-500 hover:border-slate-400 transition-colors"
            aria-label="Filter by status"
          >
            <option value="all">All Statuses</option>
            <option value="active">Active Accounts</option>
            <option value="inactive">Deactivated</option>
          </select>

          {/* Clear Filters */}
          {hasActiveFilters && (
            <button
              type="button"
              onClick={handleClearFilters}
              className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-medium text-slate-600 hover:text-slate-900 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>Clear</span>
            </button>
          )}
        </div>
      </div>

      {/* Main Content Area */}
      {loading ? (
        <LoadingState message="Loading employee directory..." />
      ) : error ? (
        <ErrorState message={error} onRetry={fetchUsers} />
      ) : !data || data.items.length === 0 ? (
        <EmptyState
          title={hasActiveFilters ? 'No employees match your filters' : 'No employees registered yet'}
          description={
            hasActiveFilters
              ? 'Try modifying your search keywords or removing selected filters.'
              : 'Add your first employee or administrator account to get started.'
          }
          action={
            hasActiveFilters
              ? { label: 'Clear Filters', onClick: handleClearFilters }
              : { label: 'Add Employee', onClick: handleOpenCreate }
          }
        />
      ) : (
        <div className="space-y-4">
          <DataTable
            data={data.items}
            keyExtractor={(user) => user.id}
            columns={[
              {
                header: 'Employee ID',
                accessor: (user) => (
                  <span className="font-mono text-xs font-semibold text-slate-800 bg-slate-100 px-2 py-0.5 rounded border border-slate-200">
                    {user.employee_id}
                  </span>
                ),
              },
              {
                header: 'Name',
                accessor: (user) => (
                  <div>
                    <div className="font-semibold text-slate-900">{user.name}</div>
                    <div className="text-xs text-slate-400 sm:hidden">{user.email}</div>
                  </div>
                ),
              },
              {
                header: 'Email',
                accessor: (user) => (
                  <span className="text-xs text-slate-600 font-normal">{user.email}</span>
                ),
                className: 'hidden sm:table-cell',
              },
              {
                header: 'Role',
                accessor: (user) => (
                  <span
                    className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold border ${
                      user.role === 'STORE_ADMIN'
                        ? 'bg-violet-50 text-violet-700 border-violet-200'
                        : 'bg-blue-50 text-blue-700 border-blue-200'
                    }`}
                  >
                    {user.role === 'STORE_ADMIN' ? 'Store Admin' : 'Employee'}
                  </span>
                ),
              },
              {
                header: 'Location',
                accessor: (user) => (
                  <span className="text-xs text-slate-700 font-medium">
                    {user.location.name}
                    <span className="text-slate-400 ml-1">({user.location.code})</span>
                  </span>
                ),
              },
              {
                header: 'Status',
                accessor: (user) => (
                  <div className="flex items-center gap-1.5 flex-wrap">
                    <StatusBadge
                      isActive={user.is_active}
                    />
                    {user.is_locked && (
                      <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-semibold bg-amber-100 text-amber-800 border border-amber-200">
                        <Lock className="w-2.5 h-2.5" />
                        Locked
                      </span>
                    )}
                  </div>
                ),
              },
              {
                header: 'Created',
                accessor: (user) => (
                  <span className="text-xs text-slate-400">{formatDateTime(user.created_at)}</span>
                ),
                className: 'hidden md:table-cell',
              },
              {
                header: 'Actions',
                accessor: (user) => {
                  const isSelf = currentUser?.id === user.id;
                  return (
                    <div className="flex items-center justify-end gap-1.5">
                      {/* Edit */}
                      <button
                        type="button"
                        onClick={() => handleOpenEdit(user)}
                        className="p-1.5 text-slate-500 hover:text-primary-600 hover:bg-slate-100 rounded transition-colors"
                        title="Edit employee"
                        aria-label={`Edit ${user.name}`}
                      >
                        <Pencil className="w-4 h-4" />
                      </button>

                      {/* Reset Password */}
                      <button
                        type="button"
                        onClick={() => setResettingUser(user)}
                        className="p-1.5 text-slate-500 hover:text-amber-600 hover:bg-slate-100 rounded transition-colors"
                        title="Reset password"
                        aria-label={`Reset password for ${user.name}`}
                      >
                        <KeyRound className="w-4 h-4" />
                      </button>

                      {/* Activate / Deactivate */}
                      <button
                        type="button"
                        onClick={() => setDeactivatingUser(user)}
                        disabled={isSelf}
                        className={`p-1.5 rounded transition-colors ${
                          isSelf
                            ? 'text-slate-300 cursor-not-allowed'
                            : user.is_active
                            ? 'text-slate-500 hover:text-rose-600 hover:bg-slate-100'
                            : 'text-slate-500 hover:text-emerald-600 hover:bg-slate-100'
                        }`}
                        title={
                          isSelf
                            ? 'Cannot deactivate your own account'
                            : user.is_active
                            ? 'Deactivate account'
                            : 'Activate account'
                        }
                        aria-label={`${user.is_active ? 'Deactivate' : 'Activate'} ${user.name}`}
                      >
                        {user.is_active ? (
                          <Power className="w-4 h-4" />
                        ) : (
                          <UserCheck className="w-4 h-4" />
                        )}
                      </button>
                    </div>
                  );
                },
                className: 'text-right',
              },
            ]}
          />

          <Pagination
            page={page}
            pageSize={15}
            total={data.total}
            totalPages={data.total_pages}
            onPageChange={(newPage) => set({ page: newPage })}
          />
        </div>
      )}

      {/* Add / Edit Modal */}
      <EmployeeFormModal
        isOpen={isFormModalOpen}
        onClose={() => setIsFormModalOpen(false)}
        userToEdit={userToEdit}
        onSuccess={handleFormSuccess}
      />

      {/* Reset Password Modal */}
      <ResetPasswordModal
        isOpen={Boolean(resettingUser)}
        onClose={() => setResettingUser(null)}
        user={resettingUser}
        onSuccess={() => fetchUsers()}
      />

      {/* Temporary Password Confirmation Modal (One-time on create) */}
      {createdInfo && (
        <TemporaryPasswordDialog
          isOpen={Boolean(createdInfo)}
          onClose={() => setCreatedInfo(null)}
          employeeId={createdInfo.employeeId}
          employeeName={createdInfo.name}
          temporaryPassword={createdInfo.temporaryPassword}
        />
      )}

      {/* Deactivate / Activate Confirm Dialog */}
      <ConfirmDialog
        isOpen={Boolean(deactivatingUser)}
        onClose={() => setDeactivatingUser(null)}
        onConfirm={handleConfirmToggleActive}
        title={deactivatingUser?.is_active ? 'Deactivate Employee Account' : 'Activate Employee Account'}
        message={
          deactivatingUser?.is_active
            ? `Are you sure you want to deactivate ${deactivatingUser?.name} (${deactivatingUser?.employee_id})? They will no longer be able to log in or issue spare parts.`
            : `Are you sure you want to re-activate ${deactivatingUser?.name} (${deactivatingUser?.employee_id})? They will be able to log in immediately.`
        }
        confirmText={deactivatingUser?.is_active ? 'Deactivate Account' : 'Activate Account'}
        isDestructive={Boolean(deactivatingUser?.is_active)}
      />
    </div>
  );
};
