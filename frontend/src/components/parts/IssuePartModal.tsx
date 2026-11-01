import React, { useEffect, useRef, useState, useCallback } from 'react';
import {
  AlertCircle,
  AlertTriangle,
  ArrowLeft,
  CheckCircle2,
  Loader2,
  Minus,
  Plus,
  X,
} from 'lucide-react';
import { createIssue } from '../../api/issues';
import { ApiError } from '../../api/client';
import { EmployeePartDetail, LocationStockDetail } from '../../types/partDetail';
import { CurrentUser } from '../../types/auth';
import { IssueResponse } from '../../types/issues';
import { FormField } from '../ui/FormField';

interface IssuePartModalProps {
  isOpen: boolean;
  onClose: () => void;
  part: EmployeePartDetail;
  selectedLocation: LocationStockDetail;
  currentUser: CurrentUser;
  onSuccess: (response: IssueResponse) => void;
  onStockChange?: () => void;
}

type Step = 'quantity' | 'confirm' | 'success';

export const IssuePartModal: React.FC<IssuePartModalProps> = ({
  isOpen,
  onClose,
  part,
  selectedLocation,
  currentUser,
  onSuccess,
  onStockChange,
}) => {
  const [step, setStep] = useState<Step>('quantity');
  const [quantity, setQuantity] = useState<number>(1);
  const [quantityInput, setQuantityInput] = useState<string>('1');
  const [quantityError, setQuantityError] = useState<string | null>(null);
  const [notes, setNotes] = useState<string>('');
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [generalError, setGeneralError] = useState<string | null>(null);
  const [isNetworkError, setIsNetworkError] = useState<boolean>(false);
  const [successResponse, setSuccessResponse] = useState<IssueResponse | null>(null);

  // Single idempotency key per confirmation attempt
  const idempotencyKeyRef = useRef<string>('');
  const modalContainerRef = useRef<HTMLDivElement>(null);
  const initialFocusRef = useRef<HTMLInputElement | null>(null);
  const previousActiveElementRef = useRef<HTMLElement | null>(null);

  const availableStock = selectedLocation.quantity;
  const isMyLocation =
    selectedLocation.is_my_location ||
    (currentUser.location && selectedLocation.location.id === currentUser.location.id);

  // Initialize or reset state when modal opens
  useEffect(() => {
    if (isOpen) {
      previousActiveElementRef.current = document.activeElement as HTMLElement | null;
      setStep('quantity');
      setQuantity(1);
      setQuantityInput('1');
      setQuantityError(null);
      setNotes('');
      setSubmitting(false);
      setGeneralError(null);
      setIsNetworkError(false);
      setSuccessResponse(null);
      idempotencyKeyRef.current = crypto.randomUUID();

      // Lock body scroll
      document.body.style.overflow = 'hidden';

      // Autofocus first input after mount
      setTimeout(() => {
        initialFocusRef.current?.focus();
      }, 50);
    } else {
      document.body.style.overflow = 'unset';
      if (previousActiveElementRef.current) {
        previousActiveElementRef.current.focus();
      }
    }

    return () => {
      document.body.style.overflow = 'unset';
    };
  }, [isOpen]);

  // Handle ESC key to close modal (only if not submitting)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen && !submitting) {
        handleModalClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, submitting]);

  const handleModalClose = () => {
    if (submitting) return;
    if (step === 'success' && successResponse) {
      onSuccess(successResponse);
    }
    onClose();
  };

  const validateQuantity = useCallback(
    (valueStr: string): number | null => {
      if (!valueStr || valueStr.trim() === '') {
        setQuantityError('Quantity is required.');
        return null;
      }
      const num = Number(valueStr);
      if (isNaN(num) || !Number.isInteger(num)) {
        setQuantityError('Quantity must be a valid whole number.');
        return null;
      }
      if (num < 1) {
        setQuantityError('Quantity must be at least 1.');
        return null;
      }
      if (num > availableStock) {
        setQuantityError(`Cannot exceed available stock (${availableStock} units).`);
        return null;
      }
      setQuantityError(null);
      return num;
    },
    [availableStock]
  );

  const handleQuantityInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setQuantityInput(val);
    const validNum = validateQuantity(val);
    if (validNum !== null) {
      setQuantity(validNum);
    }
  };

  const handleIncrement = () => {
    const nextVal = quantity + 1;
    if (nextVal <= availableStock) {
      setQuantity(nextVal);
      setQuantityInput(String(nextVal));
      setQuantityError(null);
    } else {
      setQuantityError(`Cannot exceed available stock (${availableStock} units).`);
    }
  };

  const handleDecrement = () => {
    const nextVal = quantity - 1;
    if (nextVal >= 1) {
      setQuantity(nextVal);
      setQuantityInput(String(nextVal));
      setQuantityError(null);
    } else {
      setQuantityError('Quantity must be at least 1.');
    }
  };

  const handleProceedToConfirm = () => {
    const validNum = validateQuantity(quantityInput);
    if (validNum === null) return;
    setQuantity(validNum);
    setGeneralError(null);
    setIsNetworkError(false);
    // Ensure we have an idempotency key ready
    if (!idempotencyKeyRef.current) {
      idempotencyKeyRef.current = crypto.randomUUID();
    }
    setStep('confirm');
  };

  const handleConfirmIssue = async () => {
    if (submitting) return;

    setSubmitting(true);
    setGeneralError(null);
    setIsNetworkError(false);

    try {
      const payload = {
        inventory_id: selectedLocation.inventory_id,
        part_id: part.id,
        location_id: selectedLocation.location.id,
        quantity,
        idempotency_key: idempotencyKeyRef.current,
        notes: notes.trim() ? notes.trim() : null,
      };

      const res = await createIssue(payload);
      setSuccessResponse(res);
      setStep('success');
      // Success finished -> refresh new key for any subsequent actions
      idempotencyKeyRef.current = crypto.randomUUID();
      // Notify parent to refresh stock in background
      if (onStockChange) {
        onStockChange();
      }
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        if (err.code === 'insufficient_stock') {
          setGeneralError(err.message || 'Insufficient stock available.');
          if (onStockChange) onStockChange();
        } else if (err.code === 'part_inactive' || err.code === 'location_inactive') {
          setGeneralError(err.message || 'Part or location is no longer active.');
          if (onStockChange) onStockChange();
        } else if (err.status === 404) {
          setGeneralError('This inventory record no longer exists.');
          if (onStockChange) onStockChange();
        } else if (err.status === 422) {
          setGeneralError(err.message || 'Invalid issue parameters.');
        } else if (!err.status) {
          // Network error or server unreachable - keep the SAME idempotency key so retry is safe!
          setIsNetworkError(true);
          setGeneralError(
            'Could not confirm. Your issue may not have been recorded; check My Issue History before retrying.'
          );
        } else {
          setGeneralError(err.message || 'An unexpected error occurred.');
        }
      } else {
        setIsNetworkError(true);
        setGeneralError(
          'Could not confirm. Your issue may not have been recorded; check My Issue History before retrying.'
        );
      }
    } finally {
      setSubmitting(false);
    }
  };

  if (!isOpen) return null;

  // Build storage coordinates string
  const storageCoordinates = [
    selectedLocation.location.name,
    selectedLocation.store_name,
    selectedLocation.rack ? `R:${selectedLocation.rack}` : null,
    selectedLocation.bin ? `B:${selectedLocation.bin}` : null,
  ]
    .filter(Boolean)
    .join(' → ');

  return (
    <div
      className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4"
      onClick={(e) => {
        if (e.target === e.currentTarget && !submitting) {
          handleModalClose();
        }
      }}
      role="presentation"
    >
      <div
        ref={modalContainerRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="issue-modal-title"
        className="w-full max-w-lg bg-white rounded-xl shadow-2xl border border-slate-200 overflow-hidden transform transition-all animate-fade-in"
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 bg-slate-50/70">
          <div>
            <h2 id="issue-modal-title" className="text-base font-semibold text-slate-800">
              {step === 'success'
                ? 'Part Issued'
                : step === 'confirm'
                ? 'Confirm Issue'
                : 'Issue Part'}
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              {part.name}{' '}
              <span className="font-mono text-slate-700 font-medium">({part.part_number})</span>
            </p>
          </div>
          <button
            type="button"
            onClick={handleModalClose}
            disabled={submitting}
            className="text-slate-400 hover:text-slate-600 rounded-lg p-1.5 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-40"
            aria-label="Close dialog"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6">
          {/* General Error Banner */}
          {generalError && (
            <div
              className="mb-5 p-3.5 bg-rose-50 border border-rose-200 rounded-lg flex items-start gap-3"
              role="alert"
            >
              <AlertCircle className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
              <div className="text-xs text-rose-800 space-y-1">
                <p className="font-semibold text-rose-900">Issue Failed</p>
                <p className="leading-relaxed">{generalError}</p>
                {step === 'confirm' && !isNetworkError && (
                  <button
                    type="button"
                    onClick={() => {
                      setStep('quantity');
                      setGeneralError(null);
                    }}
                    className="mt-2 text-xs font-semibold text-rose-700 underline hover:text-rose-900 focus:outline-none"
                  >
                    Adjust quantity
                  </button>
                )}
              </div>
            </div>
          )}

          {/* STEP 1: QUANTITY */}
          {step === 'quantity' && (
            <div className="space-y-5">
              {/* Other Location Warning */}
              {!isMyLocation && (
                <div
                  className="p-3 bg-amber-50 border border-amber-200 rounded-lg flex items-start gap-2.5"
                  role="status"
                >
                  <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
                  <p className="text-xs text-amber-800 leading-relaxed">
                    You are issuing from{' '}
                    <span className="font-semibold text-amber-900">
                      {selectedLocation.location.name}
                    </span>
                    , not your own location.
                  </p>
                </div>
              )}

              {/* Location & Stock Info */}
              <div className="bg-slate-50 border border-slate-200/80 rounded-lg p-3.5 space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-slate-500 font-medium">Location:</span>
                  <span className="text-slate-800 font-semibold text-right">
                    {selectedLocation.location.name}
                  </span>
                </div>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-slate-500 font-medium">Storage Coordinates:</span>
                  <span className="text-slate-700 text-right">
                    {[
                      selectedLocation.store_name,
                      selectedLocation.rack ? `Rack ${selectedLocation.rack}` : null,
                      selectedLocation.bin ? `Bin ${selectedLocation.bin}` : null,
                    ]
                      .filter(Boolean)
                      .join(' / ') || '—'}
                  </span>
                </div>
                <div className="flex items-center justify-between text-xs pt-1.5 border-t border-slate-200/60">
                  <span className="text-slate-500 font-medium">Available at location:</span>
                  <span className="text-slate-900 font-bold">
                    {availableStock} <span className="font-normal text-slate-500">units</span>
                  </span>
                </div>
              </div>

              {/* Quantity Input */}
              <FormField
                label="Quantity to Issue"
                htmlFor="issue-quantity-input"
                error={quantityError || undefined}
                required
              >
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={handleDecrement}
                    disabled={quantity <= 1}
                    className="p-2 border border-slate-300 rounded-lg text-slate-600 hover:bg-slate-100 disabled:opacity-40 disabled:hover:bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 transition-colors"
                    aria-label="Decrease quantity"
                  >
                    <Minus className="w-4 h-4" />
                  </button>
                  <input
                    ref={initialFocusRef}
                    id="issue-quantity-input"
                    type="number"
                    min="1"
                    max={availableStock}
                    step="1"
                    value={quantityInput}
                    onChange={handleQuantityInputChange}
                    aria-describedby={quantityError ? 'issue-quantity-error' : undefined}
                    className={`w-24 text-center py-2 px-3 border rounded-lg text-sm font-semibold text-slate-800 focus:outline-none focus:ring-2 transition-colors ${
                      quantityError
                        ? 'border-rose-300 focus:ring-rose-500'
                        : 'border-slate-300 focus:ring-blue-500'
                    }`}
                  />
                  <button
                    type="button"
                    onClick={handleIncrement}
                    disabled={quantity >= availableStock}
                    className="p-2 border border-slate-300 rounded-lg text-slate-600 hover:bg-slate-100 disabled:opacity-40 disabled:hover:bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 transition-colors"
                    aria-label="Increase quantity"
                  >
                    <Plus className="w-4 h-4" />
                  </button>
                  <span className="text-xs text-slate-500 ml-2">
                    Max: {availableStock}
                  </span>
                </div>
              </FormField>

              {/* Optional Notes */}
              <FormField
                label="Notes / Job Reference (Optional)"
                htmlFor="issue-notes-input"
                hint="Max 500 characters"
              >
                <textarea
                  id="issue-notes-input"
                  rows={2}
                  maxLength={500}
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="e.g. Work order #1042, Line 3 conveyor roller repair"
                  className="w-full text-xs p-2.5 border border-slate-300 rounded-lg text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-colors"
                />
              </FormField>

              {/* Step 1 Actions */}
              <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-100">
                <button
                  type="button"
                  onClick={handleModalClose}
                  className="px-4 py-2 text-xs font-semibold text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleProceedToConfirm}
                  disabled={Boolean(quantityError) || availableStock === 0}
                  className="px-4 py-2 text-xs font-semibold text-white bg-blue-600 rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 transition-colors"
                >
                  Proceed to Confirmation
                </button>
              </div>
            </div>
          )}

          {/* STEP 2: CONFIRMATION */}
          {step === 'confirm' && (
            <div className="space-y-5">
              <div className="text-xs text-slate-600 leading-relaxed bg-slate-50 p-4 rounded-lg border border-slate-200/80 space-y-3">
                <p className="font-semibold text-slate-800 pb-2 border-b border-slate-200">
                  Please review the details below before issuing:
                </p>

                <div className="grid grid-cols-3 gap-2">
                  <span className="text-slate-500">Employee ID:</span>
                  <span className="col-span-2 font-mono font-medium text-slate-800">
                    {currentUser.employee_id}
                  </span>

                  <span className="text-slate-500">Employee Name:</span>
                  <span className="col-span-2 font-medium text-slate-800">
                    {currentUser.name}
                  </span>

                  <span className="text-slate-500">Part Name:</span>
                  <span className="col-span-2 font-medium text-slate-800">{part.name}</span>

                  <span className="text-slate-500">Part ID:</span>
                  <span className="col-span-2 font-mono font-semibold text-blue-700">
                    {part.part_number}
                  </span>

                  <span className="text-slate-500">Quantity:</span>
                  <span className="col-span-2 font-bold text-slate-900">
                    {quantity} <span className="font-normal text-slate-500">unit(s)</span>
                  </span>

                  <span className="text-slate-500">Location:</span>
                  <span className="col-span-2 text-slate-800 font-medium">
                    {storageCoordinates}
                  </span>

                  {notes.trim() && (
                    <>
                      <span className="text-slate-500">Notes:</span>
                      <span className="col-span-2 text-slate-700 italic">
                        {notes.trim()}
                      </span>
                    </>
                  )}
                </div>
              </div>

              {/* Step 2 Actions */}
              <div className="flex items-center justify-between gap-3 pt-4 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setStep('quantity')}
                  disabled={submitting}
                  className="px-3.5 py-2 text-xs font-semibold text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 transition-colors flex items-center gap-1.5"
                >
                  <ArrowLeft className="w-3.5 h-3.5" />
                  Back
                </button>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={handleModalClose}
                    disabled={submitting}
                    className="px-4 py-2 text-xs font-semibold text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    onClick={handleConfirmIssue}
                    disabled={submitting}
                    className="px-5 py-2 text-xs font-semibold text-white bg-blue-600 rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 transition-colors flex items-center gap-2"
                  >
                    {submitting ? (
                      <>
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        <span>Confirming...</span>
                      </>
                    ) : isNetworkError ? (
                      'Retry Issue'
                    ) : (
                      'Confirm Issue'
                    )}
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* STEP 3: SUCCESS STATE */}
          {step === 'success' && successResponse && (
            <div className="space-y-5 text-center py-2">
              <div className="w-12 h-12 bg-emerald-50 border border-emerald-200 text-emerald-600 rounded-full flex items-center justify-center mx-auto">
                <CheckCircle2 className="w-7 h-7" />
              </div>

              <div className="space-y-1">
                <h3 className="text-base font-bold text-slate-900">
                  {successResponse.message}
                </h3>
                <p className="text-xs text-slate-600">
                  {successResponse.idempotent_replay
                    ? 'Previously confirmed issue verified.'
                    : 'The inventory has been deducted immediately.'}
                </p>
              </div>

              <div className="bg-slate-50 border border-slate-200 rounded-lg p-3.5 text-xs text-slate-700 space-y-1.5 max-w-sm mx-auto">
                <div className="flex justify-between">
                  <span className="text-slate-500">Location:</span>
                  <span className="font-medium text-slate-800">
                    {successResponse.location.name}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Units Issued:</span>
                  <span className="font-semibold text-slate-900">
                    {successResponse.quantity_issued}
                  </span>
                </div>
                <div className="flex justify-between pt-1 border-t border-slate-200">
                  <span className="text-slate-500 font-semibold">Available Remaining:</span>
                  <span className="font-bold text-emerald-700">
                    {successResponse.quantity_remaining} units
                  </span>
                </div>
              </div>

              <div className="pt-3">
                <button
                  type="button"
                  onClick={handleModalClose}
                  className="w-full sm:w-auto min-w-[120px] px-5 py-2.5 text-xs font-semibold text-white bg-blue-600 rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-colors"
                >
                  Done
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

