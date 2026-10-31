import React from 'react';
import { Link, useParams } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';

export const PartDetailPlaceholder: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  return (
    <div className="flex flex-col items-center justify-center py-24 text-center gap-4">
      <p className="text-lg font-semibold text-slate-700">
        Part details are coming in the next module.
      </p>
      <p className="text-sm text-slate-500">Part ID: {id}</p>
      <Link
        to="/parts"
        className="inline-flex items-center gap-2 text-sm text-blue-600 hover:text-blue-800 focus:outline-none focus:ring-2 focus:ring-blue-500 rounded"
      >
        <ArrowLeft className="w-4 h-4" aria-hidden="true" />
        Back to Spare Parts
      </Link>
    </div>
  );
};

