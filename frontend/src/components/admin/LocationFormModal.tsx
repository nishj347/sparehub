import React, { useEffect, useState } from 'react';
import { Modal } from '../ui/Modal';
import { FormField } from '../ui/FormField';
import { LocationFormData, LocationItem } from '../../types/masterData';
import { locationsApi } from '../../api/locations';
import { ApiError } from '../../api/client';
import { useToast } from '../ui/Toast';

interface LocationFormModalProps {
  isOpen: boolean;
  onClose: () => void;
  locationToEdit?: LocationItem | null;
  onSuccess: (location: LocationItem) => void;
}

export const LocationFormModal: React.FC<LocationFormModalProps> = ({
  isOpen,
  onClose,
  locationToEdit,
  onSuccess,
}) => {
  const { success } = useToast();
  const [formData, setFormData] = useState<LocationFormData>({
    name: '',
    code: '',
    city: '',
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [generalError, setGeneralError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const isEditing = Boolean(locationToEdit);

  useEffect(() => {
    if (locationToEdit) {
      setFormData({
        name: locationToEdit.name,
        code: locationToEdit.code,
        city: locationToEdit.city,
      });
    } else {
      setFormData({
        name: '',
        code: '',
        city: '',
      });
    }
    setErrors({});
    setGeneralError(null);
  }, [locationToEdit, isOpen]);

  const validate = (): boolean => {
    const newErrors: Record<string, string> = {};

    if (!formData.name.trim()) {
      newErrors.name = 'Location name is required';
    } else if (formData.name.trim().length > 100) {
      newErrors.name = 'Name must be 100 characters or fewer';
    }

    if (!formData.code.trim()) {
      newErrors.code = 'Location code is required';
    } else {
      const codeCleaned = formData.code.trim().toUpperCase();
      if (!/^[A-Z0-9][A-Z0-9_-]*$/.test(codeCleaned)) {
        newErrors.code = 'Code must contain only uppercase letters, numbers, hyphens, and underscores';
      } else if (codeCleaned.length > 20) {
        newErrors.code = 'Code must be 20 characters or fewer';
      }
    }

    if (!formData.city.trim()) {
      newErrors.city = 'City is required';
    } else if (formData.city.trim().length > 100) {
      newErrors.city = 'City must be 100 characters or fewer';
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
      let saved: LocationItem;
      const payload: LocationFormData = {
        name: formData.name.trim(),
        code: formData.code.trim().toUpperCase(),
        city: formData.city.trim(),
      };

      if (isEditing && locationToEdit) {
        saved = await locationsApi.update(locationToEdit.id, payload);
        success(`Location "${saved.name}" updated successfully.`);
      } else {
        saved = await locationsApi.create(payload);
        success(`Location "${saved.name}" created successfully.`);
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
      title={isEditing ? 'Edit Location' : 'Add New Location'}
      maxWidth="md"
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        {generalError && (
          <div className="p-3 text-sm text-rose-700 bg-rose-50 border border-rose-200 rounded-lg">
            {generalError}
          </div>
        )}

        <FormField
          label="Location Name"
          htmlFor="location-name"
          required
          error={errors.name}
          hint="e.g. ITC Bengaluru Plant"
        >
          <input
            id="location-name"
            type="text"
            value={formData.name}
            onChange={(e) => {
              setFormData({ ...formData, name: e.target.value });
              if (errors.name) setErrors({ ...errors, name: '' });
            }}
            placeholder="e.g. ITC Bengaluru"
            className={`w-full px-3 py-2 text-sm bg-white border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 transition-all ${
              errors.name ? 'border-rose-300 bg-rose-50/20' : 'border-slate-300'
            }`}
          />
        </FormField>

        <FormField
          label="Location Code"
          htmlFor="location-code"
          required
          error={errors.code}
          hint="Uppercase identifier (e.g. BLR, PNQ-01)"
        >
          <input
            id="location-code"
            type="text"
            value={formData.code}
            onChange={(e) => {
              setFormData({ ...formData, code: e.target.value.toUpperCase() });
              if (errors.code) setErrors({ ...errors, code: '' });
            }}
            placeholder="e.g. BLR"
            className={`w-full px-3 py-2 text-sm uppercase bg-white border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 transition-all ${
              errors.code ? 'border-rose-300 bg-rose-50/20' : 'border-slate-300'
            }`}
          />
        </FormField>

        <FormField
          label="City"
          htmlFor="location-city"
          required
          error={errors.city}
        >
          <input
            id="location-city"
            type="text"
            value={formData.city}
            onChange={(e) => {
              setFormData({ ...formData, city: e.target.value });
              if (errors.city) setErrors({ ...errors, city: '' });
            }}
            placeholder="e.g. Bengaluru"
            className={`w-full px-3 py-2 text-sm bg-white border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 transition-all ${
              errors.city ? 'border-rose-300 bg-rose-50/20' : 'border-slate-300'
            }`}
          />
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
            {isEditing ? 'Save Changes' : 'Create Location'}
          </button>
        </div>
      </form>
    </Modal>
  );
};

