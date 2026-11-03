import React, { useEffect, useState } from 'react';
import { Modal } from '../ui/Modal';
import { FormField } from '../ui/FormField';
import { LocationOption } from '../../types/masterData';
import { UserCreatePayload, UserListItem, UserUpdatePayload } from '../../types/user';
import { UserRole } from '../../types/auth';
import { usersApi } from '../../api/users';
import { locationsApi } from '../../api/locations';
import { ApiError } from '../../api/client';
import { useToast } from '../ui/Toast';
import { Check, Copy, Eye, EyeOff, RefreshCw, Wand2 } from 'lucide-react';

interface EmployeeFormModalProps {
  isOpen: boolean;
  onClose: () => void;
  userToEdit?: UserListItem | null;
  onSuccess: (savedUser: UserListItem, temporaryPassword?: string) => void;
}

export function generateStrongPassword(length = 16): string {
  const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789!@#$%^&*()-_=+';
  const array = new Uint8Array(length);
  crypto.getRandomValues(array);
  return Array.from(array)
    .map((x) => chars[x % chars.length])
    .join('');
}

export const EmployeeFormModal: React.FC<EmployeeFormModalProps> = ({
  isOpen,
  onClose,
  userToEdit,
  onSuccess,
}) => {
  const { success } = useToast();
  const isEditing = Boolean(userToEdit);

  const [employeeId, setEmployeeId] = useState('');
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [role, setRole] = useState<UserRole>('EMPLOYEE');
  const [locationId, setLocationId] = useState<number | ''>('');
  const [password, setPassword] = useState('');

  const [showPassword, setShowPassword] = useState(false);
  const [copied, setCopied] = useState(false);
  const [locations, setLocations] = useState<LocationOption[]>([]);
  const [loadingLocations, setLoadingLocations] = useState(false);

  const [errors, setErrors] = useState<Record<string, string>>({});
  const [generalError, setGeneralError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Load active locations options
  useEffect(() => {
    if (isOpen) {
      setLoadingLocations(true);
      locationsApi
        .getOptions()
        .then((opts) => {
          setLocations(opts);
          if (!isEditing && opts.length > 0 && locationId === '') {
            setLocationId(opts[0].id);
          }
        })
        .catch(() => {
          // ignore
        })
        .finally(() => setLoadingLocations(false));
    }
  }, [isOpen, isEditing]);

  // Reset form when modal opens or userToEdit changes
  useEffect(() => {
    if (userToEdit) {
      setEmployeeId(userToEdit.employee_id);
      setName(userToEdit.name);
      setEmail(userToEdit.email);
      setRole(userToEdit.role);
      setLocationId(userToEdit.location.id);
      setPassword('');
    } else {
      setEmployeeId('');
      setName('');
      setEmail('');
      setRole('EMPLOYEE');
      setLocationId(locations.length > 0 ? locations[0].id : '');
      const initialPw = generateStrongPassword(16);
      setPassword(initialPw);
    }
    setErrors({});
    setGeneralError(null);
    setShowPassword(false);
    setCopied(false);
  }, [userToEdit, isOpen]);

  const handleGeneratePassword = () => {
    const pw = generateStrongPassword(16);
    setPassword(pw);
    if (errors.password) {
      setErrors((prev) => ({ ...prev, password: '' }));
    }
  };

  const handleCopyPassword = async () => {
    if (!password) return;
    try {
      await navigator.clipboard.writeText(password);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback
    }
  };

  const validate = (): boolean => {
    const newErrors: Record<string, string> = {};

    if (!isEditing) {
      const cleanEmpId = employeeId.trim().toUpperCase();
      if (!cleanEmpId) {
        newErrors.employee_id = 'Employee ID is required.';
      } else if (!/^[A-Z0-9][A-Z0-9_-]{2,31}$/.test(cleanEmpId)) {
        newErrors.employee_id =
          'Employee ID must be 3-32 characters, start with alphanumeric, and contain letters, numbers, _, -';
      }

      if (!password || !password.trim()) {
        newErrors.password = 'Temporary password is required.';
      } else if (password.length < 12) {
        newErrors.password = 'Password must be at least 12 characters.';
      } else if (password.length > 128) {
        newErrors.password = 'Password cannot exceed 128 characters.';
      }
    }

    const cleanName = name.trim();
    if (!cleanName) {
      newErrors.name = 'Full name is required.';
    } else if (cleanName.length < 2 || cleanName.length > 100) {
      newErrors.name = 'Name must be between 2 and 100 characters.';
    }

    const cleanEmail = email.trim().toLowerCase();
    if (!cleanEmail) {
      newErrors.email = 'Email address is required.';
    } else if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(cleanEmail)) {
      newErrors.email = 'Please enter a valid email address.';
    }

    if (!locationId) {
      newErrors.location_id = 'Please select a location.';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setGeneralError(null);

    if (!validate()) return;

    setIsSubmitting(true);
    try {
      if (isEditing && userToEdit) {
        const updatePayload: UserUpdatePayload = {
          name: name.trim(),
          email: email.trim().toLowerCase(),
          role,
          location_id: Number(locationId),
        };
        const updated = await usersApi.update(userToEdit.id, updatePayload);
        success(`Employee "${updated.name}" updated successfully.`);
        onSuccess(updated);
        onClose();
      } else {
        const createPayload: UserCreatePayload = {
          employee_id: employeeId.trim().toUpperCase(),
          name: name.trim(),
          email: email.trim().toLowerCase(),
          role,
          location_id: Number(locationId),
          password: password,
        };
        const created = await usersApi.create(createPayload);
        success(`Employee "${created.name}" created successfully.`);
        onSuccess(created, password);
        onClose();
      }
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        if (err.field) {
          setErrors((prev) => ({ ...prev, [err.field as string]: err.message }));
        } else {
          setGeneralError(err.message);
        }
      } else {
        setGeneralError('An unexpected network or server error occurred. Please try again.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={isEditing ? 'Edit Employee' : 'Add Employee'}
      maxWidth="md"
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        {generalError && (
          <div className="p-3 text-sm text-rose-700 bg-rose-50 border border-rose-200 rounded-lg">
            {generalError}
          </div>
        )}

        {/* Employee ID */}
        <FormField
          label="Employee ID"
          htmlFor="employee-id"
          required={!isEditing}
          error={errors.employee_id}
          hint={isEditing ? 'Employee ID is immutable' : 'Unique identifier (e.g. ITC10892, ADM002)'}
        >
          <input
            id="employee-id"
            type="text"
            value={employeeId}
            disabled={isEditing}
            onChange={(e) => {
              setEmployeeId(e.target.value.toUpperCase());
              if (errors.employee_id) setErrors({ ...errors, employee_id: '' });
            }}
            placeholder="e.g. ITC10892"
            className={`w-full px-3 py-2 text-sm uppercase font-mono bg-white border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 transition-all ${
              isEditing ? 'bg-slate-100 text-slate-500 cursor-not-allowed' : ''
            } ${errors.employee_id ? 'border-rose-300 bg-rose-50/20' : 'border-slate-300'}`}
          />
        </FormField>

        {/* Full Name */}
        <FormField
          label="Full Name"
          htmlFor="employee-name"
          required
          error={errors.name}
        >
          <input
            id="employee-name"
            type="text"
            value={name}
            onChange={(e) => {
              setName(e.target.value);
              if (errors.name) setErrors({ ...errors, name: '' });
            }}
            placeholder="e.g. Ramesh Kumar"
            className={`w-full px-3 py-2 text-sm bg-white border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 transition-all ${
              errors.name ? 'border-rose-300 bg-rose-50/20' : 'border-slate-300'
            }`}
          />
        </FormField>

        {/* Email */}
        <FormField
          label="Email Address"
          htmlFor="employee-email"
          required
          error={errors.email}
          hint="Used for account login and notifications"
        >
          <input
            id="employee-email"
            type="email"
            value={email}
            onChange={(e) => {
              setEmail(e.target.value);
              if (errors.email) setErrors({ ...errors, email: '' });
            }}
            placeholder="e.g. ramesh.kumar@itc.in"
            className={`w-full px-3 py-2 text-sm bg-white border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 transition-all ${
              errors.email ? 'border-rose-300 bg-rose-50/20' : 'border-slate-300'
            }`}
          />
        </FormField>

        {/* Role & Location Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <FormField
            label="Role"
            htmlFor="employee-role"
            required
            error={errors.role}
          >
            <select
              id="employee-role"
              value={role}
              onChange={(e) => setRole(e.target.value as UserRole)}
              className="w-full px-3 py-2 text-sm bg-white border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 transition-all"
            >
              <option value="EMPLOYEE">Employee</option>
              <option value="STORE_ADMIN">Store Administrator</option>
            </select>
          </FormField>

          <FormField
            label="Location"
            htmlFor="employee-location"
            required
            error={errors.location_id}
          >
            <select
              id="employee-location"
              value={locationId}
              disabled={loadingLocations}
              onChange={(e) => {
                setLocationId(e.target.value ? Number(e.target.value) : '');
                if (errors.location_id) setErrors({ ...errors, location_id: '' });
              }}
              className={`w-full px-3 py-2 text-sm bg-white border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 transition-all ${
                errors.location_id ? 'border-rose-300 bg-rose-50/20' : 'border-slate-300'
              }`}
            >
              <option value="">Select location...</option>
              {locations.map((loc) => (
                <option key={loc.id} value={loc.id}>
                  {loc.name} ({loc.code})
                </option>
              ))}
            </select>
          </FormField>
        </div>

        {/* Temporary Password (Create Mode Only) */}
        {!isEditing && (
          <div className="space-y-1.5 pt-2 border-t border-slate-100">
            <FormField
              label="Temporary Password"
              htmlFor="employee-password"
              required
              error={errors.password}
              hint="Minimum 12 characters. Share securely with the employee."
            >
              <div className="flex items-center gap-2">
                <div className="relative flex-1">
                  <input
                    id="employee-password"
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(e) => {
                      setPassword(e.target.value);
                      if (errors.password) setErrors({ ...errors, password: '' });
                    }}
                    placeholder="Enter or generate password"
                    className={`w-full pl-3 pr-10 py-2 text-sm font-mono bg-white border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 transition-all ${
                      errors.password ? 'border-rose-300 bg-rose-50/20' : 'border-slate-300'
                    }`}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 focus:outline-none"
                    title={showPassword ? 'Hide password' : 'Show password'}
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>

                <button
                  type="button"
                  onClick={handleGeneratePassword}
                  className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-medium text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-primary-500 transition-colors shrink-0"
                  title="Generate random password"
                >
                  <Wand2 className="w-3.5 h-3.5 text-primary-600" />
                  <span>Generate</span>
                </button>

                <button
                  type="button"
                  onClick={handleCopyPassword}
                  className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-medium text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-primary-500 transition-colors shrink-0"
                  title="Copy password to clipboard"
                >
                  {copied ? (
                    <>
                      <Check className="w-3.5 h-3.5 text-emerald-600" />
                      <span className="text-emerald-700">Copied</span>
                    </>
                  ) : (
                    <>
                      <Copy className="w-3.5 h-3.5 text-slate-400" />
                      <span>Copy</span>
                    </>
                  )}
                </button>
              </div>
            </FormField>
            <p className="text-xs text-slate-500 italic">
              Share this password with the employee securely. They should change it after first login.
            </p>
          </div>
        )}

        {/* Modal Actions */}
        <div className="flex justify-end gap-3 pt-4 border-t border-slate-100">
          <button
            type="button"
            onClick={onClose}
            disabled={isSubmitting}
            className="px-4 py-2 text-sm font-medium text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:opacity-50 transition-colors"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={isSubmitting}
            className="px-4 py-2 text-sm font-medium text-white bg-primary-600 rounded-lg hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:opacity-50 transition-colors flex items-center gap-2"
          >
            {isSubmitting && <RefreshCw className="animate-spin h-4 w-4 text-white" />}
            {isEditing ? 'Save Changes' : 'Create Employee'}
          </button>
        </div>
      </form>
    </Modal>
  );
};

