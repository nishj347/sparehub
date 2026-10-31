import React from 'react';

interface FormFieldProps {
  label: string;
  htmlFor?: string;
  error?: string;
  hint?: string;
  required?: boolean;
  children: React.ReactNode;
}

export const FormField: React.FC<FormFieldProps> = ({
  label,
  htmlFor,
  error,
  hint,
  required = false,
  children,
}) => {
  return (
    <div className="space-y-1.5">
      <div className="flex justify-between items-baseline">
        <label
          htmlFor={htmlFor}
          className="block text-xs font-semibold uppercase tracking-wider text-slate-600"
        >
          {label}
          {required && <span className="text-rose-500 ml-1">*</span>}
        </label>
        {hint && !error && <span className="text-xs text-slate-400">{hint}</span>}
      </div>
      {children}
      {error && (
        <p className="text-xs text-rose-600 font-medium animate-fade-in flex items-center gap-1">
          <svg className="w-3.5 h-3.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
            <path
              fillRule="evenodd"
              d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z"
              clipRule="evenodd"
            />
          </svg>
          {error}
        </p>
      )}
    </div>
  );
};

