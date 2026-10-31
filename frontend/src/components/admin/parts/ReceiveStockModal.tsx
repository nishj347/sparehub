import React, { useEffect, useState } from 'react';
import { adminPartsApi } from '../../../api/adminParts';
import { ApiError } from '../../../api/client';
import { InventoryItemDetail } from '../../../types/parts';
import { FormField } from '../../ui/FormField';
import { Modal } from '../../ui/Modal';
import { useToast } from '../../ui/Toast';

interface ReceiveStockModalProps {
  isOpen: boolean;
  onClose: () => void;
  inventoryItem: InventoryItemDetail | null;
  partIsActive: boolean;
  onSuccess: () => void;
}

export const ReceiveStockModal: React.FC<ReceiveStockModalProps> = ({
  isOpen,
  onClose,
  inventoryItem,
  partIsActive,
  onSuccess,
}) => {
  const { success } = useToast();
  const [quantity, setQuantity] = useState<number | ''>('');
  const [notes, setNotes] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    if (isOpen) {
      setQuantity('');
      setNotes('');
      setError(null);
      setFieldErrors({});
    }
  }, [isOpen]);

  if (!isOpen || !inventoryItem) return null;

  const currentQty = inventoryItem.quantity;
  const numQty = typeof quantity === 'number' ? quantity : 0;
  const newQty = currentQty + (numQty > 0 ? numQty : 0);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!partIsActive) return;

    const errors: Record<string, string> = {};
    if (quantity === '' || quantity <= 0 || !Number.isInteger(quantity)) {
      errors.quantity = 'Quantity must be a positive integer greater than 0';
    }

    if (Object.keys(errors).length > 0) {
      setFieldErrors(errors);
      return;
    }

    setIsSubmitting(true);
    setError(null);
    setFieldErrors({});

    try {
      await adminPartsApi.receiveStock(inventoryItem.id, {
        quantity: Number(quantity),
        notes: notes.trim() || undefined,
      });
      success(`Successfully received ${quantity} units at ${inventoryItem.location.name}`);
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
        setError('Failed to receive stock. Please try again.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={`Receive Stock — ${inventoryItem.location.name}`}
      maxWidth="md"
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Inactive part warning */}
        {!partIsActive && (
          <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg text-xs text-rose-700 flex items-center gap-2">
            <svg className="w-4 h-4 shrink-0 text-rose-600" fill="currentColor" viewBox="0 0 20 20">
              <path
                fillRule="evenodd"
                d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z"
                clipRule="evenodd"
              />
            </svg>
            <span>This part is inactive. Stock operations are prohibited on inactive items.</span>
          </div>
        )}

        {/* Global error banner */}
        {error && (
          <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg text-xs text-rose-700">
            {error}
          </div>
        )}

        {/* Storage location summary */}
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

        {/* Live quantity preview */}
        <div className="p-3 bg-blue-50/70 border border-blue-200 rounded-lg flex items-center justify-between text-xs text-blue-950">
          <div>
            <span className="text-blue-700 block text-[11px] font-semibold uppercase tracking-wider">
              Stock Calculation
            </span>
            <span className="text-slate-600">
              Current: <strong className="text-slate-900 font-mono">{currentQty}</strong>
              {' + '}
              Received: <strong className="text-primary-700 font-mono">{numQty}</strong>
            </span>
          </div>
          <div className="text-right">
            <span className="text-blue-700 block text-[11px] font-semibold uppercase tracking-wider">
              New Total
            </span>
            <span className="text-base font-bold text-primary-800 font-mono">{newQty}</span>
          </div>
        </div>

        {/* Quantity to receive */}
        <FormField
          label="Quantity Received"
          htmlFor="receive-quantity"
          required
          error={fieldErrors.quantity}
          hint="Units to add into inventory"
        >
          <input
            id="receive-quantity"
            type="number"
            min={1}
            step={1}
            value={quantity}
            onChange={(e) => {
              const val = e.target.value;
              setQuantity(val === '' ? '' : parseInt(val, 10));
              if (fieldErrors.quantity) {
                setFieldErrors((prev) => ({ ...prev, quantity: '' }));
              }
            }}
            disabled={!partIsActive || isSubmitting}
            placeholder="e.g. 10"
            className="w-full px-3 py-2 text-sm bg-white border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:bg-slate-100 disabled:cursor-not-allowed font-mono"
            autoFocus
          />
        </FormField>

        {/* Transaction notes */}
        <FormField
          label="Receiving Notes / PO Reference"
          htmlFor="receive-notes"
          error={fieldErrors.notes}
          hint="Optional PO number, supplier, or delivery reference"
        >
          <textarea
            id="receive-notes"
            rows={2}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            disabled={!partIsActive || isSubmitting}
            placeholder="e.g. Delivered under PO-88492 from Timken India"
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
            disabled={!partIsActive || isSubmitting || quantity === '' || quantity <= 0}
            className="px-4 py-2 text-xs font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors inline-flex items-center gap-1.5"
          >
            {isSubmitting ? 'Receiving...' : 'Confirm Receipt'}
          </button>
        </div>
      </form>
    </Modal>
  );
};
