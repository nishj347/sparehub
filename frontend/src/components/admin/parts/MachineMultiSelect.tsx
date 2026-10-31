import React, { useEffect, useState } from 'react';
import { machinesApi } from '../../../api/machines';
import { MachineOption } from '../../../types/masterData';
import { MachineBrief } from '../../../types/parts';

interface MachineMultiSelectProps {
  selectedIds: number[];
  onChange: (ids: number[]) => void;
  initialMachines?: MachineBrief[];
  error?: string;
}

export const MachineMultiSelect: React.FC<MachineMultiSelectProps> = ({
  selectedIds,
  onChange,
  initialMachines = [],
  error,
}) => {
  const [availableMachines, setAvailableMachines] = useState<MachineOption[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    machinesApi
      .getOptions()
      .then((opts) => setAvailableMachines(opts))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  // Merge in any initial machines that might be inactive and thus missing from available active options
  const activeIds = new Set(availableMachines.map((m) => m.id));
  const inactiveExistingMachines = initialMachines.filter((m) => !activeIds.has(m.id));

  const toggleMachine = (id: number) => {
    if (selectedIds.includes(id)) {
      onChange(selectedIds.filter((item) => item !== id));
    } else {
      onChange([...selectedIds, id]);
    }
  };

  const filteredMachines = availableMachines.filter(
    (m) =>
      m.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      m.code.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wider text-slate-600">
          Used In Machines ({selectedIds.length} selected)
        </span>
        <span className="text-xs text-slate-400">Attach machinery models</span>
      </div>

      {error && <p className="text-xs text-rose-600 font-medium">{error}</p>}

      {/* Inactive machines already linked shown as preserved notice */}
      {inactiveExistingMachines.length > 0 && (
        <div className="p-2.5 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-800 space-y-1">
          <p className="font-semibold">Linked Inactive Machines (Preserved):</p>
          <div className="flex flex-wrap gap-1.5">
            {inactiveExistingMachines.map((m) => (
              <span
                key={m.id}
                className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-amber-100/80 text-amber-900 border border-amber-300 font-mono text-[11px]"
              >
                {m.name} ({m.code})
                <span className="text-[10px] text-amber-700 bg-amber-200 px-1 rounded">Inactive</span>
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Machine selection box with internal search */}
      <div className="border border-slate-200 rounded-lg bg-white overflow-hidden shadow-sm">
        <div className="p-2 border-b border-slate-100 bg-slate-50/50">
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Filter machines by name or code..."
            className="w-full px-2.5 py-1.5 text-xs bg-white border border-slate-200 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
          />
        </div>

        <div className="max-h-48 overflow-y-auto p-2 divide-y divide-slate-50">
          {loading ? (
            <p className="text-xs text-slate-400 py-3 text-center">Loading machines...</p>
          ) : filteredMachines.length === 0 ? (
            <p className="text-xs text-slate-400 py-3 text-center">
              {searchTerm ? 'No matching machines found' : 'No active machines available'}
            </p>
          ) : (
            filteredMachines.map((machine) => {
              const isChecked = selectedIds.includes(machine.id);
              return (
                <label
                  key={machine.id}
                  className="flex items-center gap-2.5 py-1.5 px-2 hover:bg-slate-50 rounded cursor-pointer transition-colors text-xs text-slate-700 select-none"
                >
                  <input
                    type="checkbox"
                    checked={isChecked}
                    onChange={() => toggleMachine(machine.id)}
                    className="w-4 h-4 rounded text-primary-600 focus:ring-primary-500 border-slate-300"
                  />
                  <span className="font-mono text-slate-500 bg-slate-100 px-1.5 py-0.5 rounded text-[11px]">
                    {machine.code}
                  </span>
                  <span className="font-medium text-slate-800">{machine.name}</span>
                </label>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
};

