import React, { useEffect, useState } from 'react';
import { Modal } from '../ui/Modal';
import { FormField } from '../ui/FormField';
import { UserListItem } from '../../types/user';
import { usersApi } from '../../api/users';
import { ApiError } from '../../api/client';
import { useToast } from '../ui/Toast';
import { Check, Copy, Eye, EyeOff, KeyRound, RefreshCw, Wand2 } from 'lucide-react';
import { generateStrongPassword } from './EmployeeFormModal';

interface ResetPasswordModalProps {
  isOpen: boolean;
  onClose: () => void;
  user: UserListItem | null;
  onSuccess: (updatedUser: UserListItem) => void;
}

export const ResetPasswordModal: React.FC<ResetPasswordModalProps> = ({
  isOpen,
  onClose,
  user,
  onSuccess,
}) => {
  const { success } = useToast();
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (isOpen) {
      setPassword(generateStrongPassword(16));
      setError(null);
      setShowPassword(false);
      setCopied(false);
    }
  }, [isOpen, user]);

  const handleGenerate = () => {
    setPassword(generateStrongPassword(16));
    setError(null);
  };

  const handleCopy = async () => {
    if (!password) return;
    try {
      await navigator.clipboard.writeText(password);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!user) return;

    if (!password || !password.trim()) {
      setError('Password is required.');
      return;
    }
    if (password.length < 12) {
      setError('Password must be at least 12 characters.');
      return;
    }
    if (password.length > 128) {
      setError('Password cannot exceed 128 characters.');
      return;
    }

    setIsSubmitting(true);
    setError(null);
    try {
      const updated = await usersApi.resetPassword(user.id, { password });
      success(`Password for ${user.name} (${user.employee_id}) reset successfully.`);
      onSuccess(updated);
      onClose();
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError('Failed to reset password. Please try again.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!user) return null;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Reset Employee Password"
      maxWidth="md"
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && (
          <div className="p-3 text-sm text-rose-700 bg-rose-50 border border-rose-200 rounded-lg">
            {error}
          </div>
        )}

        <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg text-sm space-y-1">
          <div className="flex justify-between">
            <span className="text-slate-500">Employee ID:</span>
            <span className="font-mono font-semibold text-slate-800">{user.employee_id}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-500">Full Name:</span>
            <span className="font-medium text-slate-800">{user.name}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-500">Role:</span>
            <span className="text-slate-700 font-medium">
              {user.role === 'STORE_ADMIN' ? 'Store Administrator' : 'Employee'}
            </span>
          </div>
        </div>

        <FormField
          label="New Password"
          htmlFor="reset-password"
          required
          hint="Minimum 12 characters. Resets login lockouts and failed attempts immediately."
        >
          <div className="flex items-center gap-2">
            <div className="relative flex-1">
              <input
                id="reset-password"
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => {
                  setPassword(e.target.value);
                  if (error) setError(null);
                }}
                placeholder="Enter or generate new password"
                className="w-full pl-3 pr-10 py-2 text-sm font-mono bg-white border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 transition-all"
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
              onClick={handleGenerate}
              className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-medium text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-primary-500 transition-colors shrink-0"
              title="Generate random password"
            >
              <Wand2 className="w-3.5 h-3.5 text-primary-600" />
              <span>Generate</span>
            </button>

            <button
              type="button"
              onClick={handleCopy}
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
          Copy this password and communicate it to the user. They will be able to log in immediately.
        </p>

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
            <KeyRound className="w-4 h-4" />
            <span>Reset Password</span>
          </button>
        </div>
      </form>
    </Modal>
  );
};

