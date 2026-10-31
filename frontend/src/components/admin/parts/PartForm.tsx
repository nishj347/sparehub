import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { adminPartsApi } from '../../../api/adminParts';
import { ApiError } from '../../../api/client';
import { locationsApi } from '../../../api/locations';
import { LocationOption } from '../../../types/masterData';
import {
  PartCreatePayload,
  PartDetail,
  PartUpdatePayload,
  SpecItem,
} from '../../../types/parts';
import { FormField } from '../../ui/FormField';
import { ImageUploader } from './ImageUploader';
import { MachineMultiSelect } from './MachineMultiSelect';
import { SpecificationsEditor } from './SpecificationsEditor';

interface PartFormProps {
  initialData?: PartDetail | null;
  isEdit?: boolean;
  onSubmit: (
    payload: PartCreatePayload | PartUpdatePayload,
    imageFile: File | null,
    shouldRemoveImage: boolean
  ) => Promise<void>;
  isSubmitting?: boolean;
}

export const PartForm: React.FC<PartFormProps> = ({
  initialData,
  isEdit = false,
  onSubmit,
  isSubmitting = false,
}) => {
  const navigate = useNavigate();

  // Basic fields
  const [partNumber, setPartNumber] = useState('');
  const [name, setName] = useState('');
  const [category, setCategory] = useState('');
  const [manufacturer, setManufacturer] = useState('');
  const [description, setDescription] = useState('');

  // Specifications
  const [specs, setSpecs] = useState<SpecItem[]>([]);

  // Machines
  const [machineIds, setMachineIds] = useState<number[]>([]);

  // Image handling
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [shouldRemoveImage, setShouldRemoveImage] = useState(false);

  // Initial stock accordion (create mode only)
  const [showInitialStock, setShowInitialStock] = useState(false);
  const [locations, setLocations] = useState<LocationOption[]>([]);
  const [stockLocationId, setStockLocationId] = useState<number | ''>('');
  const [stockQuantity, setStockQuantity] = useState<number>(0);
  const [stockStoreName, setStockStoreName] = useState('');
  const [stockRack, setStockRack] = useState('');
  const [stockBin, setStockBin] = useState('');
  const [stockMinLevel, setStockMinLevel] = useState<number>(0);

  // Categories suggestions
  const [categories, setCategories] = useState<string[]>([]);

  // Form errors
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  // Load categories and locations
  useEffect(() => {
    adminPartsApi
      .getCategories()
      .then((cats) => setCategories(cats))
      .catch(() => {});

    if (!isEdit) {
      locationsApi
        .getOptions()
        .then((locs) => setLocations(locs))
        .catch(() => {});
    }
  }, [isEdit]);

  // Populate data in edit mode
  useEffect(() => {
    if (initialData) {
      setPartNumber(initialData.part_number);
      setName(initialData.name);
      setCategory(initialData.category);
      setManufacturer(initialData.manufacturer || '');
      setDescription(initialData.description || '');

      // Specifications is already SpecItem[]
      if (initialData.specifications) {
        setSpecs(initialData.specifications);
      } else {
        setSpecs([]);
      }

      // Machines
      if (initialData.machines) {
        setMachineIds(initialData.machines.map((m) => m.id));
      }
    }
  }, [initialData]);

  const handleFormSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    const errors: Record<string, string> = {};

    if (!isEdit && !partNumber.trim()) {
      errors.part_number = 'Part ID is required';
    }
    if (!name.trim()) {
      errors.name = 'Part name is required';
    }
    if (!category.trim()) {
      errors.category = 'Category is required';
    }

    // Check duplicate spec keys
    const nonBlankSpecs = specs.filter((s) => s.key.trim());
    const specKeys = nonBlankSpecs.map((s) => s.key.trim().toLowerCase());
    const hasDupes = specKeys.some((k, idx) => specKeys.indexOf(k) !== idx);
    if (hasDupes) {
      errors.specifications = 'Duplicate specification keys detected';
    }

    // Validate initial stock if accordion enabled
    if (!isEdit && showInitialStock && stockLocationId) {
      if (stockQuantity < 0 || !Number.isInteger(stockQuantity)) {
        errors.stock_quantity = 'Stock quantity must be a non-negative integer';
      }
      if (stockMinLevel < 0 || !Number.isInteger(stockMinLevel)) {
        errors.stock_min_level = 'Min stock level must be 0 or greater';
      }
    }

    if (Object.keys(errors).length > 0) {
      setFieldErrors(errors);
      return;
    }

    try {
      if (isEdit) {
        const updatePayload: PartUpdatePayload = {
          name: name.trim(),
          category: category.trim(),
          manufacturer: manufacturer.trim() || undefined,
          description: description.trim() || undefined,
          specifications: nonBlankSpecs.length > 0 ? nonBlankSpecs : undefined,
          machine_ids: machineIds,
        };
        await onSubmit(updatePayload, imageFile, shouldRemoveImage);
      } else {
        const createPayload: PartCreatePayload = {
          part_number: partNumber.trim().toUpperCase(),
          name: name.trim(),
          category: category.trim(),
          manufacturer: manufacturer.trim() || undefined,
          description: description.trim() || undefined,
          specifications: nonBlankSpecs.length > 0 ? nonBlankSpecs : undefined,
          machine_ids: machineIds.length > 0 ? machineIds : undefined,
        };

        if (showInitialStock && stockLocationId) {
          createPayload.initial_stock = {
            location_id: Number(stockLocationId),
            quantity: Number(stockQuantity),
            store_name: stockStoreName.trim() || undefined,
            rack: stockRack.trim() || undefined,
            bin: stockBin.trim() || undefined,
            min_stock_level: Number(stockMinLevel),
          };
        }

        await onSubmit(createPayload, imageFile, false);
      }
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.field) {
          setFieldErrors({ [err.field]: err.message });
        } else if (err.status === 409 && err.code === 'duplicate_part_number') {
          setFieldErrors({ part_number: err.message || 'A spare part with this ID already exists.' });
        } else {
          setError(err.message);
        }
      } else {
        setError('An unexpected error occurred while saving the spare part.');
      }
    }
  };

  return (
    <form onSubmit={handleFormSubmit} className="space-y-6">
      {/* Top error banner */}
      {error && (
        <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl text-sm text-rose-700 flex items-start gap-2.5">
          <svg className="w-5 h-5 text-rose-500 shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
            <path
              fillRule="evenodd"
              d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z"
              clipRule="evenodd"
            />
          </svg>
          <div>
            <span className="font-semibold block">Failed to save part</span>
            <span>{error}</span>
          </div>
        </div>
      )}

      {/* Main card */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-6">
        <h2 className="text-base font-semibold text-slate-900 border-b border-slate-100 pb-3">
          Part Identification & Master Attributes
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Part ID / Number */}
          <FormField
            label="Part ID (Code)"
            htmlFor="part-number"
            required
            error={fieldErrors.part_number}
            hint={isEdit ? 'Immutable part identifier' : 'e.g. BRG-6205, VBLT-B48'}
          >
            {isEdit ? (
              <div>
                <input
                  id="part-number"
                  type="text"
                  value={partNumber}
                  readOnly
                  disabled
                  className="w-full px-3 py-2 text-sm bg-slate-100 border border-slate-300 rounded-lg text-slate-700 font-mono font-semibold cursor-not-allowed"
                />
                <p className="text-[11px] text-slate-400 mt-1">Part ID cannot be changed after creation.</p>
              </div>
            ) : (
              <input
                id="part-number"
                type="text"
                value={partNumber}
                onChange={(e) => {
                  setPartNumber(e.target.value.toUpperCase());
                  if (fieldErrors.part_number) {
                    setFieldErrors((prev) => ({ ...prev, part_number: '' }));
                  }
                }}
                placeholder="e.g. ELEC-RLY-024"
                maxLength={50}
                disabled={isSubmitting}
                className="w-full px-3 py-2 text-sm bg-white border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 font-mono font-semibold uppercase"
                autoFocus
              />
            )}
          </FormField>

          {/* Part Name */}
          <FormField
            label="Part Name"
            htmlFor="part-name"
            required
            error={fieldErrors.name}
            hint="Full descriptive equipment or component name"
          >
            <input
              id="part-name"
              type="text"
              value={name}
              onChange={(e) => {
                setName(e.target.value);
                if (fieldErrors.name) {
                  setFieldErrors((prev) => ({ ...prev, name: '' }));
                }
              }}
              placeholder="e.g. Deep Groove Ball Bearing 25mm"
              maxLength={200}
              disabled={isSubmitting}
              className="w-full px-3 py-2 text-sm bg-white border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
          </FormField>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Category with datalist */}
          <FormField
            label="Category"
            htmlFor="part-category"
            required
            error={fieldErrors.category}
            hint="Select existing or type a new category"
          >
            <div>
              <input
                id="part-category"
                type="text"
                list="category-options"
                value={category}
                onChange={(e) => {
                  setCategory(e.target.value);
                  if (fieldErrors.category) {
                    setFieldErrors((prev) => ({ ...prev, category: '' }));
                  }
                }}
                placeholder="e.g. Bearings, Belts, Electrical"
                maxLength={100}
                disabled={isSubmitting}
                className="w-full px-3 py-2 text-sm bg-white border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
              <datalist id="category-options">
                {categories.map((cat) => (
                  <option key={cat} value={cat} />
                ))}
              </datalist>
            </div>
          </FormField>

          {/* Manufacturer / Brand */}
          <FormField
            label="Manufacturer / Brand"
            htmlFor="part-manufacturer"
            error={fieldErrors.manufacturer}
            hint="OEM or manufacturer name (optional)"
          >
            <input
              id="part-manufacturer"
              type="text"
              value={manufacturer}
              onChange={(e) => setManufacturer(e.target.value)}
              placeholder="e.g. SKF, Siemens, Gates"
              maxLength={100}
              disabled={isSubmitting}
              className="w-full px-3 py-2 text-sm bg-white border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
          </FormField>
        </div>

        {/* Description */}
        <FormField
          label="Detailed Description"
          htmlFor="part-description"
          error={fieldErrors.description}
          hint="Operational context, material, usage instructions"
        >
          <textarea
            id="part-description"
            rows={3}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="e.g. Standard radial ball bearing suitable for high-speed continuous packaging lines."
            maxLength={1000}
            disabled={isSubmitting}
            className="w-full px-3 py-2 text-sm bg-white border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
          />
        </FormField>
      </div>

      {/* Image Uploader Card */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-4">
        <h2 className="text-base font-semibold text-slate-900 border-b border-slate-100 pb-3">
          Visual Identification
        </h2>
        <ImageUploader
          currentImageUrl={shouldRemoveImage ? null : initialData?.image_url}
          onFileSelect={(file) => {
            setImageFile(file);
            if (file) setShouldRemoveImage(false);
          }}
          onRemoveCurrent={() => {
            setImageFile(null);
            setShouldRemoveImage(true);
          }}
          disabled={isSubmitting}
        />
      </div>

      {/* Technical Specifications Card */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-4">
        <SpecificationsEditor
          specifications={specs}
          onChange={setSpecs}
          error={fieldErrors.specifications}
        />
      </div>

      {/* Linked Machinery Card */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-4">
        <MachineMultiSelect
          selectedIds={machineIds}
          onChange={setMachineIds}
          initialMachines={initialData?.machines || []}
          error={fieldErrors.machines}
        />
      </div>

      {/* Initial Inventory (Create Mode Only) */}
      {!isEdit && (
        <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm">
          <button
            type="button"
            onClick={() => setShowInitialStock(!showInitialStock)}
            className="w-full px-6 py-4 bg-slate-50/70 hover:bg-slate-100/70 text-left flex items-center justify-between transition-colors border-b border-slate-200"
          >
            <div>
              <span className="text-sm font-semibold text-slate-900 block">
                Initial Inventory Location (Optional)
              </span>
              <span className="text-xs text-slate-500">
                Optionally assign this part to a storage plant and receive opening stock right away.
              </span>
            </div>
            <span className="text-xs font-medium text-primary-600 bg-primary-50 border border-primary-200 px-2.5 py-1 rounded-md">
              {showInitialStock ? 'Hide Section' : '+ Add Opening Stock'}
            </span>
          </button>

          {showInitialStock && (
            <div className="p-6 space-y-4 bg-white">
              <FormField
                label="Storage Plant / Location"
                htmlFor="initial-location"
                error={fieldErrors.stock_location}
                hint="Select which facility holds this part initially"
              >
                <select
                  id="initial-location"
                  value={stockLocationId}
                  onChange={(e) => setStockLocationId(e.target.value ? Number(e.target.value) : '')}
                  disabled={isSubmitting}
                  className="w-full px-3 py-2 text-sm bg-white border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                >
                  <option value="">— Select Location (None) —</option>
                  {locations.map((loc) => (
                    <option key={loc.id} value={loc.id}>
                      {loc.name} ({loc.code})
                    </option>
                  ))}
                </select>
              </FormField>

              {stockLocationId && (
                <div className="space-y-4 pt-2">
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <FormField
                      label="Opening Quantity"
                      htmlFor="initial-quantity"
                      error={fieldErrors.stock_quantity}
                      hint="Units physically on hand"
                    >
                      <input
                        id="initial-quantity"
                        type="number"
                        min={0}
                        step={1}
                        value={stockQuantity}
                        onChange={(e) => {
                          const val = e.target.value;
                          setStockQuantity(val === '' ? 0 : parseInt(val, 10));
                        }}
                        disabled={isSubmitting}
                        className="w-full px-3 py-2 text-sm bg-white border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 font-mono"
                      />
                    </FormField>

                    <FormField
                      label="Min Stock Threshold"
                      htmlFor="initial-min-stock"
                      error={fieldErrors.stock_min_level}
                      hint="Alert threshold for low stock"
                    >
                      <input
                        id="initial-min-stock"
                        type="number"
                        min={0}
                        step={1}
                        value={stockMinLevel}
                        onChange={(e) => {
                          const val = e.target.value;
                          setStockMinLevel(val === '' ? 0 : parseInt(val, 10));
                        }}
                        disabled={isSubmitting}
                        className="w-full px-3 py-2 text-sm bg-white border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 font-mono"
                      />
                    </FormField>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    <FormField label="Store / Warehouse" htmlFor="initial-store">
                      <input
                        id="initial-store"
                        type="text"
                        value={stockStoreName}
                        onChange={(e) => setStockStoreName(e.target.value)}
                        placeholder="e.g. Central Store"
                        maxLength={100}
                        disabled={isSubmitting}
                        className="w-full px-3 py-2 text-sm bg-white border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                      />
                    </FormField>

                    <FormField label="Rack / Bay" htmlFor="initial-rack">
                      <input
                        id="initial-rack"
                        type="text"
                        value={stockRack}
                        onChange={(e) => setStockRack(e.target.value)}
                        placeholder="e.g. R-01"
                        maxLength={50}
                        disabled={isSubmitting}
                        className="w-full px-3 py-2 text-sm bg-white border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 font-mono"
                      />
                    </FormField>

                    <FormField label="Bin / Slot" htmlFor="initial-bin">
                      <input
                        id="initial-bin"
                        type="text"
                        value={stockBin}
                        onChange={(e) => setStockBin(e.target.value)}
                        placeholder="e.g. B-05"
                        maxLength={50}
                        disabled={isSubmitting}
                        className="w-full px-3 py-2 text-sm bg-white border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 font-mono"
                      />
                    </FormField>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Form Submission Actions */}
      <div className="flex items-center justify-between pt-4 border-t border-slate-200">
        <button
          type="button"
          onClick={() => navigate(isEdit && initialData ? `/admin/parts/${initialData.id}` : '/admin/parts')}
          disabled={isSubmitting}
          className="px-4 py-2 text-sm font-medium text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:opacity-50 transition-colors"
        >
          Cancel
        </button>

        <div className="flex items-center gap-3">
          <button
            type="submit"
            disabled={isSubmitting}
            className="px-5 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors inline-flex items-center gap-2 shadow-sm"
          >
            {isSubmitting && (
              <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                />
              </svg>
            )}
            {isSubmitting
              ? isEdit
                ? 'Saving Changes...'
                : 'Creating Part...'
              : isEdit
              ? 'Save Changes'
              : 'Create Spare Part'}
          </button>
        </div>
      </div>
    </form>
  );
};
