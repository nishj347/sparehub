import React, { useEffect, useState } from 'react';
import { Modal } from '../ui/Modal';
import { FormField } from '../ui/FormField';
import { LocationOption, MachineFormData, MachineItem } from '../../types/masterData';
import { machinesApi } from '../../api/machines';
import { locationsApi } from '../../api/locations';
import { ApiError } from '../../api/client';
import { useToast } from '../ui/Toast';

interface MachineFormModalProps {
  isOpen: boolean;
  onClose: () => void;
  machineToEdit?: MachineItem | null;
  onSuccess: (machine: MachineItem) => void;
}

export const MachineFormModal: React.FC<MachineFormModalProps> = ({
  isOpen,
  onClose,
  machineToEdit,
  onSuccess,
}) => {
  const { success } = useToast();
  const [formData, setFormData] = useState<MachineFormData>({
    name: '',
    code: '',
    location_id: null,
  });
  const [locations, setLocations] = useState<LocationOption[]>([]);
  const [loadingLocations, setLoadingLocations] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [generalError, setGeneralError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const isEditing = Boolean(machineToEdit);

  useEffect(() => {
    if (isOpen) {
      setLoadingLocations(true);
      locationsApi
        .getOptions()
        .then((opts) => setLocations(opts))
        .catch(() => {
          // If locations fail to load, proceed with empty options
        })
        .finally(() => setLoadingLocations(false));

      if (machineToEdit) {
        setFormData({
          name: machineToEdit.name,
          code: machineToEdit.code,
          location_id: machineToEdit.location?.id ?? null,
        });
      } else {
        setFormData({
          name: '',
          code: '',
          location_id: null,
        });
      }
      setErrors({});
      setGeneralError(null);
    }
  }, [isOpen, machineToEdit]);

  const validate = (): boolean => {
    const newErrors: Record<string, string> = {};

    if (!formData.name.trim()) {
      newErrors.name = 'Machine name is required';
    } else if (formData.name.trim().length > 150) {
      newErrors.name = 'Name must be 150 characters or fewer';
    }

    if (!formData.code.trim()) {
      newErrors.code = 'Machine code is required';
    } else {
      const codeCleaned = formData.code.trim().toUpperCase();
      if (!/^[A-Z0-9][A-Z0-9_-]*$/.test(codeCleaned)) {
        newErrors.code = 'Code must contain only uppercase letters, numbers, hyphens, and underscores';
      } else if (codeCleaned.length > 50) {
        newErrors.code = 'Code must be 50 characters or fewer';
      }
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
      let saved: MachineItem;
      const payload: MachineFormData = {
        name: formData.name.trim(),
        code: formData.code.trim().toUpperCase(),
        location_id: formData.location_id,
      };

      if (isEditing && machineToEdit) {
        saved = await machinesApi.update(machineToEdit.id, payload);
        success(`Machine "${saved.name}" updated successfully.`);
      } else {
        saved = await machinesApi.create(payload);
        success(`Machine "${saved.name}" created successfully.`);
      }

      onSuccess(saved);
      onClose();
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        if (err.field) {
          setErrors((prev) => ({ ...prev, [err.field as string]: err.message }));
        } else {
          setGeneralError(err.message);
        }
      } else {
        setGeneralError('An unexpected error occurred. Please try again.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={isEditing ? 'Edit Machine' : 'Add New Machine'}
      maxWidth="md"
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        {generalError && (
          <div className="p-3 text-sm text-rose-700 bg-rose-50 border border-rose-200 rounded-lg">
            {generalError}
          </div>
        )}

        <FormField
          label="Machine Name"
          htmlFor="machine-name"
          required
          error={errors.name}
          hint="e.g. Conveyor Belt C-14"
        >
          <input
            id="machine-name"
            type="text"
            value={formData.name}
            onChange={(e) => {
              setFormData({ ...formData, name: e.target.value });
              if (errors.name) setErrors({ ...errors, name: '' });
            }}
            placeholder="e.g. Conveyor Belt C-14"
            className={`w-full px-3 py-2 text-sm bg-white border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 transition-all ${
              errors.name ? 'border-rose-300 bg-rose-50/20' : 'border-slate-300'
            }`}
          />
        </FormField>

        <FormField
          label="Machine Code"
          htmlFor="machine-code"
          required
          error={errors.code}
          hint="Plant identifier (e.g. C-14, CNC-02)"
        >
          <input
            id="machine-code"
            type="text"
            value={formData.code}
            onChange={(e) => {
              setFormData({ ...formData, code: e.target.value.toUpperCase() });
              if (errors.code) setErrors({ ...errors, code: '' });
            }}
            placeholder="e.g. C-14"
            className={`w-full px-3 py-2 text-sm uppercase bg-white border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 transition-all ${
              errors.code ? 'border-rose-300 bg-rose-50/20' : 'border-slate-300'
            }`}
          />
        </FormField>

        <FormField
          label="Assigned Location"
          htmlFor="machine-location"
          error={errors.location_id}
          hint="Plant facility where machine is installed"
        >
          <select
            id="machine-location"
            value={formData.location_id ?? ''}
            onChange={(e) => {
              const val = e.target.value;
              setFormData({
                ...formData,
                location_id: val === '' ? null : Number(val),
              });
              if (errors.location_id) setErrors({ ...errors, location_id: '' });
            }}
            disabled={loadingLocations}
            className={`w-full px-3 py-2 text-sm bg-white border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 transition-all ${
              errors.location_id ? 'border-rose-300 bg-rose-50/20' : 'border-slate-300'
            }`}
          >
            <option value="">-- Unassigned --</option>
            {locations.map((loc) => (
              <option key={loc.id} value={loc.id}>
                {loc.name} ({loc.code})
              </option>
            ))}
          </select>
        </FormField>

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
            {isSubmitting && (
              <svg className="animate-spin h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
              </svg>
            )}
            {isEditing ? 'Save Changes' : 'Create Machine'}
          </button>
        </div>
      </form>
    </Modal>
  );
};

