import React, { useState } from 'react';
import { Modal } from '../ui/Modal';
import { Check, Copy, KeyRound, ShieldAlert } from 'lucide-react';

interface TemporaryPasswordDialogProps {
  isOpen: boolean;
  onClose: () => void;
  employeeId: string;
  employeeName: string;
  temporaryPassword: string;
}

export const TemporaryPasswordDialog: React.FC<TemporaryPasswordDialogProps> = ({
  isOpen,
  onClose,
  employeeId,
  employeeName,
  temporaryPassword,
}) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(temporaryPassword);
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    } catch {
      // Fallback
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Employee Account Created"
      maxWidth="md"
    >
      <div className="space-y-4">
        <div className="flex items-start gap-3 p-3 text-sm text-amber-800 bg-amber-50 border border-amber-200 rounded-lg">
          <ShieldAlert className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <p className="font-semibold text-amber-900">One-Time Temporary Password</p>
            <p className="text-xs text-amber-700">
              Share this password with the employee securely. It will not be shown again once you close this window.
            </p>
          </div>
        </div>

        <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg text-sm space-y-1">
          <div className="flex justify-between">
            <span className="text-slate-500">Employee ID:</span>
            <span className="font-mono font-semibold text-slate-800">{employeeId}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-500">Full Name:</span>
            <span className="font-medium text-slate-800">{employeeName}</span>
          </div>
        </div>

        <div className="space-y-1.5">
          <label className="text-xs font-semibold text-slate-600 uppercase tracking-wider flex items-center gap-1.5">
            <KeyRound className="w-3.5 h-3.5 text-slate-400" />
            Temporary Password
          </label>
          <div className="flex items-center gap-2">
            <div className="flex-1 px-3 py-2.5 font-mono text-sm font-semibold tracking-wider bg-slate-900 text-emerald-400 rounded-lg select-all border border-slate-800">
              {temporaryPassword}
            </div>
            <button
              type="button"
              onClick={handleCopy}
              className="inline-flex items-center gap-1.5 px-3 py-2.5 text-xs font-medium text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-primary-500 transition-colors shrink-0"
              title="Copy temporary password"
            >
              {copied ? (
                <>
                  <Check className="w-4 h-4 text-emerald-600" />
                  <span className="text-emerald-700">Copied!</span>
                </>
              ) : (
                <>
                  <Copy className="w-4 h-4 text-slate-500" />
                  <span>Copy</span>
                </>
              )}
            </button>
          </div>
        </div>

        <div className="flex justify-end pt-3 border-t border-slate-100">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-white bg-primary-600 rounded-lg hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 transition-colors"
          >
            Done
          </button>
        </div>
      </div>
    </Modal>
  );
};

