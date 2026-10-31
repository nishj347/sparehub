import React, { useEffect, useState } from 'react';
import { adminPartsApi } from '../../../api/adminParts';
import { ApiError } from '../../../api/client';
import { locationsApi } from '../../../api/locations';
import { LocationOption } from '../../../types/masterData';
import { InventoryItemDetail } from '../../../types/parts';
import { FormField } from '../../ui/FormField';
import { Modal } from '../../ui/Modal';
import { useToast } from '../../ui/Toast';

interface InventoryLocationModalProps {
  isOpen: boolean;
  onClose: () => void;
  mode: 'add' | 'edit';
  partId: number;
  inventoryItem?: InventoryItemDetail | null;
  existingLocationIds?: number[];
  onSuccess: () => void;
}

export const InventoryLocationModal: React.FC<InventoryLocationModalProps> = ({
  isOpen,
  onClose,
  mode,
  partId,
  inventoryItem,
  existingLocationIds = [],
  onSuccess,
}) => {
  const { success } = useToast();
  const [locations, setLocations] = useState<LocationOption[]>([]);
  const [loadingLocations, setLoadingLocations] = useState(false);

  // Form state
  const [locationId, setLocationId] = useState<number | ''>('');
  const [quantity, setQuantity] = useState<number>(0);
  const [storeName, setStoreName] = useState('');
  const [rack, setRack] = useState('');
  const [bin, setBin] = useState('');
  const [minStockLevel, setMinStockLevel] = useState<number>(0);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    if (!isOpen) return;

    setError(null);
    setFieldErrors({});

    if (mode === 'add') {
      setLocationId('');
      setQuantity(0);
      setStoreName('');
      setRack('');
      setBin('');
      setMinStockLevel(0);

      setLoadingLocations(true);
      locationsApi
        .getOptions()
        .then((opts) => setLocations(opts))
        .catch(() => setError('Failed to load active plant locations'))
        .finally(() => setLoadingLocations(false));
    } else if (mode === 'edit' && inventoryItem) {
      setLocationId(inventoryItem.location.id);
      setQuantity(inventoryItem.quantity);
      setStoreName(inventoryItem.store_name || '');
      setRack(inventoryItem.rack || '');
      setBin(inventoryItem.bin || '');
      setMinStockLevel(inventoryItem.min_stock_level ?? 0);
    }
  }, [isOpen, mode, inventoryItem]);

  if (!isOpen) return null;

  // Filter out locations that already exist for this part (in add mode)
  const availableLocations = locations.filter(
    (loc) => !existingLocationIds.includes(loc.id)
  );

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    const errors: Record<string, string> = {};
    if (mode === 'add') {
      if (!locationId) {
        errors.location_id = 'Please select a storage plant / location';
      }
      if (quantity < 0 || !Number.isInteger(quantity)) {
        errors.quantity = 'Initial quantity must be a non-negative integer (0 or greater)';
      }
    }

    if (minStockLevel < 0 || !Number.isInteger(minStockLevel)) {
      errors.min_stock_level = 'Min stock level must be 0 or greater';
    }

    if (Object.keys(errors).length > 0) {
      setFieldErrors(errors);
      return;
    }

    setIsSubmitting(true);
    setError(null);
    setFieldErrors({});

    try {
      if (mode === 'add') {
        await adminPartsApi.addLocation(partId, {
          location_id: Number(locationId),
          quantity: Number(quantity),
          store_name: storeName.trim() || undefined,
          rack: rack.trim() || undefined,
          bin: bin.trim() || undefined,
          min_stock_level: Number(minStockLevel),
        });
        success('Storage location attached successfully');
      } else if (mode === 'edit' && inventoryItem) {
        await adminPartsApi.updateInventory(inventoryItem.id, {
          store_name: storeName.trim() || undefined,
          rack: rack.trim() || undefined,
          bin: bin.trim() || undefined,
          min_stock_level: Number(minStockLevel),
        });
        success('Storage coordinates updated successfully');
      }

      onSuccess();
      onClose();
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.field) {
          setFieldErrors({ [err.field]: err.message });
        } else {
          setError(err.message);
        }
      } else {
        setError(
          mode === 'add'
            ? 'Failed to add location. Please try again.'
            : 'Failed to update location details. Please try again.'
        );
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={
        mode === 'add'
          ? 'Add Inventory Location'
          : `Edit Location Details — ${inventoryItem?.location.name}`
      }
      maxWidth="md"
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && (
          <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg text-xs text-rose-700">
            {error}
          </div>
        )}

        {mode === 'add' ? (
          <FormField
            label="Storage Plant / Location"
            htmlFor="add-location-id"
            required
            error={fieldErrors.location_id}
            hint="Select an active site"
          >
            {loadingLocations ? (
              <p className="text-xs text-slate-400 py-2">Loading plant locations...</p>
            ) : availableLocations.length === 0 ? (
              <p className="text-xs text-amber-600 bg-amber-50 p-2.5 rounded-lg border border-amber-200">
                All active plant locations already hold inventory for this part.
              </p>
            ) : (
              <select
                id="add-location-id"
                value={locationId}
                onChange={(e) => {
                  setLocationId(e.target.value ? Number(e.target.value) : '');
                  if (fieldErrors.location_id) {
                    setFieldErrors((prev) => ({ ...prev, location_id: '' }));
                  }
                }}
                disabled={isSubmitting}
                className="w-full px-3 py-2 text-sm bg-white border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
              >
                <option value="">— Select Location —</option>
                {availableLocations.map((loc) => (
                  <option key={loc.id} value={loc.id}>
                    {loc.name} ({loc.code})
                  </option>
                ))}
              </select>
            )}
          </FormField>
        ) : (
          <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-600">
            <span className="font-semibold text-slate-700 block">Plant / Site:</span>
            <span>
              {inventoryItem?.location.name} ({inventoryItem?.location.code})
            </span>
          </div>
        )}

        {/* Quantity */}
        {mode === 'add' ? (
          <FormField
            label="Initial On-Hand Quantity"
            htmlFor="add-quantity"
            required
            error={fieldErrors.quantity}
            hint="Initial stock to record (creates opening ledger transaction if > 0)"
          >
            <input
              id="add-quantity"
              type="number"
              min={0}
              step={1}
              value={quantity}
              onChange={(e) => {
                const val = e.target.value;
                setQuantity(val === '' ? 0 : parseInt(val, 10));
              }}
              disabled={isSubmitting}
              className="w-full px-3 py-2 text-sm bg-white border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 font-mono"
            />
          </FormField>
        ) : (
          <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-600 flex justify-between items-center">
            <div>
              <span className="font-semibold text-slate-700 block">Current Stock:</span>
              <span className="text-slate-500">
                Quantity is immutable here to guarantee audit ledger consistency.
              </span>
            </div>
            <span className="text-base font-bold font-mono text-slate-900">
              {inventoryItem?.quantity ?? 0} units
            </span>
          </div>
        )}

        {/* Shelf Coordinates */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <FormField
            label="Store / Warehouse"
            htmlFor="loc-store-name"
            error={fieldErrors.store_name}
          >
            <input
              id="loc-store-name"
              type="text"
              value={storeName}
              onChange={(e) => setStoreName(e.target.value)}
              disabled={isSubmitting}
              placeholder="e.g. Central Store"
              maxLength={100}
              className="w-full px-3 py-2 text-sm bg-white border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
          </FormField>

          <FormField label="Rack / Bay" htmlFor="loc-rack" error={fieldErrors.rack}>
            <input
              id="loc-rack"
              type="text"
              value={rack}
              onChange={(e) => setRack(e.target.value)}
              disabled={isSubmitting}
              placeholder="e.g. R-04"
              maxLength={50}
              className="w-full px-3 py-2 text-sm bg-white border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 font-mono"
            />
          </FormField>

          <FormField label="Bin / Slot" htmlFor="loc-bin" error={fieldErrors.bin}>
            <input
              id="loc-bin"
              type="text"
              value={bin}
              onChange={(e) => setBin(e.target.value)}
              disabled={isSubmitting}
              placeholder="e.g. B-12"
              maxLength={50}
              className="w-full px-3 py-2 text-sm bg-white border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 font-mono"
            />
          </FormField>
        </div>

        {/* Min Stock Level */}
        <FormField
          label="Minimum Stock Threshold"
          htmlFor="loc-min-stock"
          required
          error={fieldErrors.min_stock_level}
          hint="Triggers Low Stock warning when on-hand quantity falls below this"
        >
          <input
            id="loc-min-stock"
            type="number"
            min={0}
            step={1}
            value={minStockLevel}
            onChange={(e) => {
              const val = e.target.value;
              setMinStockLevel(val === '' ? 0 : parseInt(val, 10));
            }}
            disabled={isSubmitting}
            className="w-full px-3 py-2 text-sm bg-white border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 font-mono"
          />
        </FormField>

        {/* Modal actions */}
        <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-100">
          <button
            type="button"
            onClick={onClose}
            disabled={isSubmitting}
            className="px-4 py-2 text-xs font-medium text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:opacity-50 transition-colors"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={isSubmitting || (mode === 'add' && !locationId)}
            className="px-4 py-2 text-xs font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isSubmitting
              ? 'Saving...'
              : mode === 'add'
              ? 'Add Location'
              : 'Save Changes'}
          </button>
        </div>
      </form>
    </Modal>
  );
};
