import React, { useEffect, useState } from 'react';
import { adminPartsApi } from '../../../api/adminParts';
import { ApiError } from '../../../api/client';
import { InventoryItemDetail } from '../../../types/parts';
import { FormField } from '../../ui/FormField';
import { Modal } from '../../ui/Modal';
import { useToast } from '../../ui/Toast';

interface AdjustStockModalProps {
  isOpen: boolean;
  onClose: () => void;
  inventoryItem: InventoryItemDetail | null;
  onSuccess: () => void;
}

export const AdjustStockModal: React.FC<AdjustStockModalProps> = ({
  isOpen,
  onClose,
  inventoryItem,
  onSuccess,
}) => {
  const { success } = useToast();
  const [newQuantity, setNewQuantity] = useState<number | ''>('');
  const [notes, setNotes] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    if (isOpen && inventoryItem) {
      setNewQuantity(inventoryItem.quantity);
      setNotes('');
      setError(null);
      setFieldErrors({});
    }
  }, [isOpen, inventoryItem]);

  if (!isOpen || !inventoryItem) return null;

  const currentQty = inventoryItem.quantity;
  const countedQty = typeof newQuantity === 'number' ? newQuantity : currentQty;
  const delta = countedQty - currentQty;
  const hasChanged = delta !== 0 && newQuantity !== '';

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    const errors: Record<string, string> = {};
    if (newQuantity === '' || newQuantity < 0 || !Number.isInteger(newQuantity)) {
      errors.new_quantity = 'Counted quantity must be a non-negative integer (0 or greater)';
    } else if (newQuantity === currentQty) {
      errors.new_quantity = 'New quantity must differ from current quantity';
    }

    if (!notes.trim()) {
      errors.notes = 'Reason for stock adjustment is required for audit trail';
    }

    if (Object.keys(errors).length > 0) {
      setFieldErrors(errors);
      return;
    }

    setIsSubmitting(true);
    setError(null);
    setFieldErrors({});

    try {
      await adminPartsApi.adjustStock(inventoryItem.id, {
        new_quantity: Number(newQuantity),
        notes: notes.trim(),
      });
      success(
        `Successfully adjusted inventory at ${inventoryItem.location.name} (${delta > 0 ? `+${delta}` : delta} units)`
      );
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
        setError('Failed to adjust stock. Please try again.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={`Adjust Stock Level — ${inventoryItem.location.name}`}
      maxWidth="md"
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Global error banner */}
        {error && (
          <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg text-xs text-rose-700">
            {error}
          </div>
        )}

        {/* Location coordinates */}
        <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-600 grid grid-cols-2 gap-2">
          <div>
            <span className="font-semibold text-slate-700 block">Plant / Site:</span>
            <span>{inventoryItem.location.name} ({inventoryItem.location.code})</span>
          </div>
          <div>
            <span className="font-semibold text-slate-700 block">Shelf Coordinates:</span>
            <span>
              {inventoryItem.store_name || '—'} / Rack {inventoryItem.rack || '—'} / Bin{' '}
              {inventoryItem.bin || '—'}
            </span>
          </div>
        </div>

        {/* Live difference preview */}
        <div className="p-3 bg-slate-100/70 border border-slate-200 rounded-lg flex items-center justify-between text-xs">
          <div>
            <span className="text-slate-500 block text-[11px] font-semibold uppercase tracking-wider">
              Reconciliation
            </span>
            <span className="text-slate-700">
              System: <strong className="text-slate-900 font-mono">{currentQty}</strong>
              {' → '}
              Physical: <strong className="text-slate-900 font-mono">{newQuantity === '' ? '—' : newQuantity}</strong>
            </span>
          </div>
          <div className="text-right">
            <span className="text-slate-500 block text-[11px] font-semibold uppercase tracking-wider">
              Discrepancy (Delta)
            </span>
            <span
              className={`text-base font-bold font-mono ${
                delta > 0
                  ? 'text-emerald-600'
                  : delta < 0
                  ? 'text-rose-600'
                  : 'text-slate-400'
              }`}
            >
              {delta > 0 ? `+${delta}` : delta}
            </span>
          </div>
        </div>

        {/* Physical count input */}
        <FormField
          label="New Physical Count"
          htmlFor="adjust-quantity"
          required
          error={fieldErrors.new_quantity}
          hint="Actual verified count on the shelf"
        >
          <input
            id="adjust-quantity"
            type="number"
            min={0}
            step={1}
            value={newQuantity}
            onChange={(e) => {
              const val = e.target.value;
              setNewQuantity(val === '' ? '' : parseInt(val, 10));
              if (fieldErrors.new_quantity) {
                setFieldErrors((prev) => ({ ...prev, new_quantity: '' }));
              }
            }}
            disabled={isSubmitting}
            placeholder="0"
            className="w-full px-3 py-2 text-sm bg-white border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:bg-slate-100 disabled:cursor-not-allowed font-mono"
            autoFocus
          />
        </FormField>

        {/* Adjustment reason / notes */}
        <FormField
          label="Adjustment Reason / Audit Note"
          htmlFor="adjust-notes"
          required
          error={fieldErrors.notes}
          hint="Required for audit logging (e.g. cycle count discrepancy, damaged part written off)"
        >
          <textarea
            id="adjust-notes"
            rows={2}
            value={notes}
            onChange={(e) => {
              setNotes(e.target.value);
              if (fieldErrors.notes) {
                setFieldErrors((prev) => ({ ...prev, notes: '' }));
              }
            }}
            disabled={isSubmitting}
            placeholder="e.g. Annual physical inventory audit reconciliation; 2 units damaged during handling"
            maxLength={500}
            className="w-full px-3 py-2 text-sm bg-white border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:bg-slate-100 disabled:cursor-not-allowed"
          />
        </FormField>

        {/* Actions */}
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
            disabled={isSubmitting || !hasChanged || !notes.trim()}
            className="px-4 py-2 text-xs font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors inline-flex items-center gap-1.5"
          >
            {isSubmitting ? 'Adjusting...' : 'Record Adjustment'}
          </button>
        </div>
      </form>
    </Modal>
  );
};
