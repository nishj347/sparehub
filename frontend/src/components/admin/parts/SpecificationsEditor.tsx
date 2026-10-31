import React from 'react';
import { SpecItem } from '../../../types/parts';

interface SpecificationsEditorProps {
  specifications: SpecItem[];
  onChange: (specs: SpecItem[]) => void;
  error?: string;
}

export const SpecificationsEditor: React.FC<SpecificationsEditorProps> = ({
  specifications,
  onChange,
  error,
}) => {
  const handleAdd = () => {
    if (specifications.length >= 20) return;
    onChange([...specifications, { key: '', value: '' }]);
  };

  const handleRemove = (index: number) => {
    const updated = specifications.filter((_, i) => i !== index);
    onChange(updated);
  };

  const handleChange = (index: number, field: 'key' | 'value', val: string) => {
    const updated = specifications.map((item, i) => {
      if (i === index) {
        return { ...item, [field]: val };
      }
      return item;
    });
    onChange(updated);
  };

  // Check for duplicate keys client-side
  const keys = specifications.map((s) => s.key.trim().toLowerCase()).filter(Boolean);
  const duplicateKeys = keys.filter((k, idx) => keys.indexOf(k) !== idx);

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-600">
            Technical Specifications ({specifications.length}/20)
          </span>
          <p className="text-xs text-slate-400 mt-0.5">
            Add key-value properties (e.g. Voltage, Power, Bore Diameter)
          </p>
        </div>
        <button
          type="button"
          onClick={handleAdd}
          disabled={specifications.length >= 20}
          className="text-xs font-medium text-primary-600 hover:text-primary-700 bg-primary-50 hover:bg-primary-100 px-2.5 py-1.5 rounded-lg border border-primary-200 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
        >
          + Add Attribute
        </button>
      </div>

      {error && <p className="text-xs text-rose-600 font-medium">{error}</p>}
      {duplicateKeys.length > 0 && (
        <p className="text-xs text-rose-600 font-medium">
          Duplicate specification keys detected. Each attribute key must be unique.
        </p>
      )}

      {specifications.length === 0 ? (
        <div className="text-xs text-slate-400 italic py-3 px-4 bg-slate-50 border border-dashed border-slate-200 rounded-lg text-center">
          No technical specifications added yet. Click &quot;+ Add Attribute&quot; to define custom parameters.
        </div>
      ) : (
        <div className="space-y-2">
          {specifications.map((spec, index) => {
            const isDuplicate =
              spec.key.trim() &&
              duplicateKeys.includes(spec.key.trim().toLowerCase());

            return (
              <div key={index} className="flex items-center gap-2">
                <input
                  type="text"
                  value={spec.key}
                  onChange={(e) => handleChange(index, 'key', e.target.value)}
                  placeholder="Attribute (e.g. Voltage)"
                  maxLength={50}
                  className={`w-1/3 px-3 py-1.5 text-xs bg-white border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 transition-all ${
                    isDuplicate ? 'border-rose-400 bg-rose-50/30' : 'border-slate-300'
                  }`}
                />
                <input
                  type="text"
                  value={spec.value}
                  onChange={(e) => handleChange(index, 'value', e.target.value)}
                  placeholder="Value (e.g. 240V AC)"
                  maxLength={200}
                  className="flex-1 px-3 py-1.5 text-xs bg-white border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 transition-all"
                />
                <button
                  type="button"
                  onClick={() => handleRemove(index)}
                  className="text-slate-400 hover:text-rose-600 p-1.5 rounded-lg hover:bg-rose-50 transition-colors focus:outline-none"
                  aria-label="Remove attribute"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

