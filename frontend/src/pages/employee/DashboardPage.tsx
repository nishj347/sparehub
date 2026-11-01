import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { CheckCircle2, XCircle, RefreshCw, Server, Database, Activity, Search } from 'lucide-react';
import { apiClient, ApiError } from '../../api/client';
import { getPartFilters } from '../../api/parts';
import { PartFilters } from '../../types/partsPublic';
import { SystemStatusState } from '../../types';
import { useAuth } from '../../auth/AuthContext';

export const DashboardPage: React.FC = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [searchInput, setSearchInput] = useState('');
  const [filters, setFilters] = useState<PartFilters | null>(null);

  // System status state (dev diagnostic; keep as is)
  const [status, setStatus] = useState<SystemStatusState>({
    apiStatus: 'loading',
    dbStatus: 'loading',
  });

  const checkHealth = useCallback(async () => {
    setStatus({ apiStatus: 'loading', dbStatus: 'loading', apiError: undefined, dbError: undefined });
    let apiEnv: string | undefined;
    try {
      const apiRes = await apiClient.getApiHealth();
      apiEnv = apiRes.environment;
      setStatus((prev) => ({ ...prev, apiStatus: 'success', environment: apiRes.environment }));
    } catch (err: unknown) {
      const msg = err instanceof ApiError ? err.message : 'Failed to reach API endpoint';
      setStatus((prev) => ({
        ...prev,
        apiStatus: 'error',
        apiError: msg,
        dbStatus: 'error',
        dbError: 'Cannot verify database connectivity while API is unreachable.',
        lastChecked: new Date(),
      }));
      return;
    }
    try {
      await apiClient.getDbHealth();
      setStatus((prev) => ({ ...prev, dbStatus: 'success', lastChecked: new Date() }));
    } catch (err: unknown) {
      const msg = err instanceof ApiError
        ? `${err.message}${err.code ? ` (${err.code})` : ''}`
        : 'Database connection failed';
      setStatus((prev) => ({ ...prev, dbStatus: 'error', dbError: msg, environment: apiEnv, lastChecked: new Date() }));
    }
  }, []);

  useEffect(() => {
    if (import.meta.env.DEV) {
      checkHealth();
    }
  }, [checkHealth]);

  useEffect(() => {
    getPartFilters().then(setFilters).catch(() => { /* silent */ });
  }, []);

  const isLoading = status.apiStatus === 'loading' || status.dbStatus === 'loading';
  const hasError = status.apiStatus === 'error' || status.dbStatus === 'error';
  const isAllHealthy = status.apiStatus === 'success' && status.dbStatus === 'success';

  function handleSearchSubmit(e: React.FormEvent) {
    e.preventDefault();
    const q = searchInput.trim();
    navigate(q ? `/parts?q=${encodeURIComponent(q)}` : '/parts');
  }

  const locationName = user?.location?.name ?? '';

  return (
    <div className="space-y-8">
      {/* Greeting */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">
          Welcome, {user?.name?.split(' ')[0] ?? 'there'}
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          {locationName ? `${locationName} — ` : ''}Spare Parts Management System
        </p>
      </div>

      {/* Big search box */}
      <form onSubmit={handleSearchSubmit} role="search" aria-label="Spare parts search">
        <div className="relative max-w-2xl">
          <span className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none text-slate-400">
            <Search className="w-5 h-5" aria-hidden="true" />
          </span>
          <input
            type="search"
            autoFocus
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder="Search by part name, part ID, category, manufacturer or machine"
            className="w-full pl-12 pr-4 py-3 text-sm bg-white border border-slate-300 rounded-xl shadow-sm placeholder-slate-400 text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
            aria-label="Search spare parts"
          />
          <button
            type="submit"
            className="absolute inset-y-0 right-0 pr-3 flex items-center text-blue-600 hover:text-blue-800 focus:outline-none"
            aria-label="Search"
          >
            <Search className="w-4 h-4" aria-hidden="true" />
          </button>
        </div>
      </form>

      {/* Browse by category */}
      {filters && filters.categories.length > 0 && (
        <div>
          <h2 className="text-sm font-semibold text-slate-700 mb-3">Browse by Category</h2>
          <div className="flex flex-wrap gap-2">
            {filters.categories.map((cat) => (
              <button
                key={cat}
                type="button"
                onClick={() => navigate(`/parts?category=${encodeURIComponent(cat)}`)}
                className="px-3 py-1.5 text-xs font-medium rounded-full border border-slate-300 bg-white text-slate-700 hover:border-blue-400 hover:text-blue-700 hover:bg-blue-50 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {cat}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* System Status Card — dev diagnostic; visible only in development mode */}
      {import.meta.env.DEV && (
      <div className="bg-white rounded-lg border border-slate-200 shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Activity className="w-5 h-5 text-slate-600" />
            <h2 className="text-base font-semibold text-slate-800">System Status &amp; Connectivity</h2>
          </div>
          <button
            type="button"
            onClick={checkHealth}
            disabled={isLoading}
            className="inline-flex items-center gap-2 px-3 py-1.5 text-xs font-medium rounded border border-slate-300 bg-white text-slate-700 hover:bg-slate-50 disabled:opacity-50 transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
            {isLoading ? 'Checking...' : 'Refresh Status'}
          </button>
        </div>

        <div className="px-6 py-3 bg-slate-50/50 border-b border-slate-100 flex items-center justify-between text-xs">
          <div className="flex items-center gap-2">
            <span className="font-medium text-slate-600">Verification Result:</span>
            {isLoading && <span className="text-slate-500 font-medium">Checking components...</span>}
            {!isLoading && isAllHealthy && (
              <span className="inline-flex items-center gap-1.5 font-medium text-emerald-700">
                <span className="w-2 h-2 rounded-full bg-emerald-500" />
                End-to-End Connectivity Verified (Frontend → API → Database)
              </span>
            )}
            {!isLoading && hasError && (
              <span className="inline-flex items-center gap-1.5 font-medium text-rose-700">
                <span className="w-2 h-2 rounded-full bg-rose-500" />
                Component Connectivity Error
              </span>
            )}
          </div>
          {status.lastChecked && (
            <span className="text-slate-400">Last checked: {status.lastChecked.toLocaleTimeString()}</span>
          )}
        </div>

        <div className="p-6 grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Backend */}
          <div className="p-4 rounded-lg border border-slate-200 bg-slate-50/30">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2.5">
                <div className="p-2 rounded bg-slate-100 text-slate-700"><Server className="w-4 h-4" /></div>
                <div>
                  <h3 className="text-sm font-semibold text-slate-800">FastAPI REST Backend</h3>
                  <p className="text-xs text-slate-500">HTTP GET /api/health</p>
                </div>
              </div>
              {status.apiStatus === 'loading' && <span className="text-xs text-slate-500 font-medium">Checking...</span>}
              {status.apiStatus === 'success' && (
                <span className="inline-flex items-center gap-1 text-xs font-medium text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                  <CheckCircle2 className="w-3.5 h-3.5" /> Online
                </span>
              )}
              {status.apiStatus === 'error' && (
                <span className="inline-flex items-center gap-1 text-xs font-medium text-rose-700 bg-rose-50 px-2 py-0.5 rounded border border-rose-200">
                  <XCircle className="w-3.5 h-3.5" /> Offline
                </span>
              )}
            </div>
            {status.apiStatus === 'success' && (
              <div className="mt-3 pt-3 border-t border-slate-200/60 text-xs space-y-1 text-slate-600">
                <div className="flex justify-between"><span className="text-slate-500">Service Status:</span><span className="font-mono text-slate-800">ok</span></div>
                <div className="flex justify-between"><span className="text-slate-500">Runtime Environment:</span><span className="font-mono text-slate-800">{status.environment || 'development'}</span></div>
              </div>
            )}
            {status.apiStatus === 'error' && (
              <div className="mt-3 p-2.5 rounded bg-rose-50 border border-rose-200 text-xs text-rose-800">
                <p className="font-medium">Connection Error</p>
                <p className="mt-1 text-rose-700">{status.apiError}</p>
              </div>
            )}
          </div>

          {/* Database */}
          <div className="p-4 rounded-lg border border-slate-200 bg-slate-50/30">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2.5">
                <div className="p-2 rounded bg-slate-100 text-slate-700"><Database className="w-4 h-4" /></div>
                <div>
                  <h3 className="text-sm font-semibold text-slate-800">PostgreSQL Database</h3>
                  <p className="text-xs text-slate-500">HTTP GET /api/health/db</p>
                </div>
              </div>
              {status.dbStatus === 'loading' && <span className="text-xs text-slate-500 font-medium">Checking...</span>}
              {status.dbStatus === 'success' && (
                <span className="inline-flex items-center gap-1 text-xs font-medium text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                  <CheckCircle2 className="w-3.5 h-3.5" /> Connected
                </span>
              )}
              {status.dbStatus === 'error' && (
                <span className="inline-flex items-center gap-1 text-xs font-medium text-rose-700 bg-rose-50 px-2 py-0.5 rounded border border-rose-200">
                  <XCircle className="w-3.5 h-3.5" /> Unreachable
                </span>
              )}
            </div>
            {status.dbStatus === 'success' && (
              <div className="mt-3 pt-3 border-t border-slate-200/60 text-xs space-y-1 text-slate-600">
                <div className="flex justify-between"><span className="text-slate-500">Connection State:</span><span className="font-mono text-slate-800">connected</span></div>
                <div className="flex justify-between"><span className="text-slate-500">Query Verification:</span><span className="font-mono text-slate-800">SELECT 1 succeeded</span></div>
              </div>
            )}
            {status.dbStatus === 'error' && (
              <div className="mt-3 p-2.5 rounded bg-rose-50 border border-rose-200 text-xs text-rose-800">
                <p className="font-medium">Connection Error</p>
                <p className="mt-1 text-rose-700">{status.dbError}</p>
              </div>
            )}
          </div>
        </div>

        {hasError && !isLoading && (
          <div className="px-6 py-4 bg-slate-50 border-t border-slate-200 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
            <p className="text-xs text-slate-600">
              One or more system services are unreachable. Ensure Docker PostgreSQL and FastAPI are running.
            </p>
            <button
              type="button"
              onClick={checkHealth}
              className="inline-flex items-center justify-center gap-2 px-4 py-2 text-xs font-medium rounded bg-blue-600 text-white hover:bg-blue-700 transition-colors shadow-sm"
            >
              <RefreshCw className="w-3.5 h-3.5" /> Retry Connection
            </button>
          </div>
        )}
      </div>
      )}
    </div>
  );
};
