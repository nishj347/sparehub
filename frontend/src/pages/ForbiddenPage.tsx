import React from 'react';
import { useNavigate } from 'react-router-dom';
import { ShieldOff } from 'lucide-react';
import { useAuth } from '../auth/AuthContext';

export const ForbiddenPage: React.FC = () => {
  const { user } = useAuth();
  const navigate = useNavigate();

  const homeRoute = user?.role === 'STORE_ADMIN' ? '/admin' : '/';

  return (
    <div className="min-h-[60vh] flex flex-col items-center justify-center text-center px-4">
      <div className="w-14 h-14 rounded-full bg-red-50 border border-red-200 flex items-center justify-center mb-5">
        <ShieldOff className="w-7 h-7 text-red-500" />
      </div>
      <h1 className="text-xl font-bold text-slate-900 mb-2">Access Denied</h1>
      <p className="text-sm text-slate-500 max-w-sm mb-6">
        You do not have permission to view this page. This area is restricted to users with the
        required role.
      </p>
      <button
        type="button"
        onClick={() => navigate(homeRoute)}
        className="px-4 py-2 text-sm font-medium rounded-lg bg-blue-600 text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
      >
        Back to Home
      </button>
    </div>
  );
};

