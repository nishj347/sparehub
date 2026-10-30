import React from 'react';
import { Construction } from 'lucide-react';

interface PlaceholderPageProps {
  title: string;
  description: string;
  targetModule: string;
}

export const PlaceholderPage: React.FC<PlaceholderPageProps> = ({
  title,
  description,
  targetModule,
}) => {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">{title}</h1>
        <p className="mt-1 text-sm text-slate-500">{description}</p>
      </div>

      <div className="bg-white rounded-lg border border-dashed border-slate-300 p-12 text-center shadow-sm">
        <div className="w-12 h-12 rounded-full bg-slate-100 border border-slate-200 mx-auto flex items-center justify-center text-slate-500 mb-4">
          <Construction className="w-6 h-6 text-slate-600" />
        </div>
        <h2 className="text-base font-semibold text-slate-800">Module Feature In Planning</h2>
        <p className="mt-2 text-sm text-slate-500 max-w-md mx-auto">
          This section is a scheduled component of the Spare Parts Management System and will be implemented in {targetModule}.
        </p>
        <div className="mt-6 inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium bg-slate-100 text-slate-600 border border-slate-200">
          <span>Target: {targetModule}</span>
        </div>
      </div>
    </div>
  );
};
