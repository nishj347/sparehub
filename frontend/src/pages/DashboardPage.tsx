import React, { useEffect, useState, useCallback } from 'react';
import { CheckCircle2, XCircle, RefreshCw, Server, Database, Activity } from 'lucide-react';
import { apiClient, ApiError } from '../api/client';
import { SystemStatusState } from '../types';

export const DashboardPage: React.FC = () => {
  const [status, setStatus] = useState<SystemStatusState>({
    apiStatus: 'loading',
    dbStatus: 'loading',
  });

  const checkHealth = useCallback(async () => {
    setStatus({
      apiStatus: 'loading',
      dbStatus: 'loading',
      apiError: undefined,
      dbError: undefined,
    });

    let apiEnv: string | undefined;

    // Check API Health
    try {
      const apiRes = await apiClient.getApiHealth();
      apiEnv = apiRes.environment;
      setStatus((prev) => ({
        ...prev,
        apiStatus: 'success',
        environment: apiRes.environment,
      }));
    } catch (err: unknown) {
      const errorMsg = err instanceof ApiError ? err.message : 'Failed to reach API endpoint';
      setStatus((prev) => ({
        ...prev,
        apiStatus: 'error',
        apiError: errorMsg,
        dbStatus: 'error',
        dbError: 'Cannot verify database connectivity while API is unreachable.',
        lastChecked: new Date(),
      }));
      return;
    }

    // Check Database Health via API
    try {
      await apiClient.getDbHealth();
      setStatus((prev) => ({
        ...prev,
        dbStatus: 'success',
        lastChecked: new Date(),
      }));
    } catch (err: unknown) {
      const errorMsg =
        err instanceof ApiError
          ? `${err.message}${err.code ? ` (${err.code})` : ''}`
          : 'Database connection failed';
      setStatus((prev) => ({
        ...prev,
        dbStatus: 'error',
        dbError: errorMsg,
        environment: apiEnv,
        lastChecked: new Date(),
      }));
    }
  }, []);

  useEffect(() => {
    checkHealth();
  }, [checkHealth]);

  const isLoading = status.apiStatus === 'loading' || status.dbStatus === 'loading';
  const hasError = status.apiStatus === 'error' || status.dbStatus === 'error';
  const isAllHealthy = status.apiStatus === 'success' && status.dbStatus === 'success';

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">System Dashboard</h1>
        <p className="mt-1 text-sm text-slate-500">
          Module 1 Technical Architecture Skeleton & End-to-End Connectivity Verification
        </p>
      </div>

      {/* System Status Card */}
      <div className="bg-white rounded-lg border border-slate-200 shadow-sm overflow-hidden">
        {/* Card Header */}
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Activity className="w-5 h-5 text-slate-600" />
            <h2 className="text-base font-semibold text-slate-800">System Status & Connectivity</h2>
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

        {/* Overall Status Banner */}
        <div className="px-6 py-3 bg-slate-50/50 border-b border-slate-100 flex items-center justify-between text-xs">
          <div className="flex items-center gap-2">
            <span className="font-medium text-slate-600">Verification Result:</span>
            {isLoading && (
              <span className="text-slate-500 font-medium">Checking components...</span>
            )}
            {!isLoading && isAllHealthy && (
              <span className="inline-flex items-center gap-1.5 font-medium text-emerald-700">
                <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
                End-to-End Connectivity Verified (Frontend → API → Database)
              </span>
            )}
            {!isLoading && hasError && (
              <span className="inline-flex items-center gap-1.5 font-medium text-rose-700">
                <span className="w-2 h-2 rounded-full bg-rose-500"></span>
                Component Connectivity Error
              </span>
            )}
          </div>
          {status.lastChecked && (
            <span className="text-slate-400">
              Last checked: {status.lastChecked.toLocaleTimeString()}
            </span>
          )}
        </div>

        {/* Grid Components */}
        <div className="p-6 grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Component 1: FastAPI Backend */}
          <div className="p-4 rounded-lg border border-slate-200 bg-slate-50/30 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2.5">
                  <div className="p-2 rounded bg-slate-100 text-slate-700">
                    <Server className="w-4 h-4" />
                  </div>
                  <div>
                    <h3 className="text-sm font-semibold text-slate-800">FastAPI REST Backend</h3>
                    <p className="text-xs text-slate-500">HTTP GET /api/health</p>
                  </div>
                </div>

                {status.apiStatus === 'loading' && (
                  <span className="text-xs text-slate-500 font-medium">Checking...</span>
                )}
                {status.apiStatus === 'success' && (
                  <span className="inline-flex items-center gap-1 text-xs font-medium text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    Online
                  </span>
                )}
                {status.apiStatus === 'error' && (
                  <span className="inline-flex items-center gap-1 text-xs font-medium text-rose-700 bg-rose-50 px-2 py-0.5 rounded border border-rose-200">
                    <XCircle className="w-3.5 h-3.5" />
                    Offline
                  </span>
                )}
              </div>

              {status.apiStatus === 'success' && (
                <div className="mt-3 pt-3 border-t border-slate-200/60 text-xs space-y-1 text-slate-600">
                  <div className="flex justify-between">
                    <span className="text-slate-500">Service Status:</span>
                    <span className="font-mono text-slate-800">ok</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">Runtime Environment:</span>
                    <span className="font-mono text-slate-800">{status.environment || 'development'}</span>
                  </div>
                </div>
              )}

              {status.apiStatus === 'error' && (
                <div className="mt-3 p-2.5 rounded bg-rose-50 border border-rose-200 text-xs text-rose-800">
                  <p className="font-medium">Connection Error</p>
                  <p className="mt-1 text-rose-700">{status.apiError}</p>
                </div>
              )}
            </div>
          </div>

          {/* Component 2: PostgreSQL Database */}
          <div className="p-4 rounded-lg border border-slate-200 bg-slate-50/30 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2.5">
                  <div className="p-2 rounded bg-slate-100 text-slate-700">
                    <Database className="w-4 h-4" />
                  </div>
                  <div>
                    <h3 className="text-sm font-semibold text-slate-800">PostgreSQL Database</h3>
                    <p className="text-xs text-slate-500">HTTP GET /api/health/db</p>
                  </div>
                </div>

                {status.dbStatus === 'loading' && (
                  <span className="text-xs text-slate-500 font-medium">Checking...</span>
                )}
                {status.dbStatus === 'success' && (
                  <span className="inline-flex items-center gap-1 text-xs font-medium text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    Connected
                  </span>
                )}
                {status.dbStatus === 'error' && (
                  <span className="inline-flex items-center gap-1 text-xs font-medium text-rose-700 bg-rose-50 px-2 py-0.5 rounded border border-rose-200">
                    <XCircle className="w-3.5 h-3.5" />
                    Unreachable
                  </span>
                )}
              </div>

              {status.dbStatus === 'success' && (
                <div className="mt-3 pt-3 border-t border-slate-200/60 text-xs space-y-1 text-slate-600">
                  <div className="flex justify-between">
                    <span className="text-slate-500">Connection State:</span>
                    <span className="font-mono text-slate-800">connected</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">Query Verification:</span>
                    <span className="font-mono text-slate-800">SELECT 1 succeeded</span>
                  </div>
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
        </div>

        {/* Retry / Troubleshooting Footer when error occurs */}
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
              <RefreshCw className="w-3.5 h-3.5" />
              Retry Connection
            </button>
          </div>
        )}
      </div>

      {/* Architecture Information Box */}
      <div className="bg-white rounded-lg border border-slate-200 p-6 shadow-sm">
        <h2 className="text-sm font-semibold text-slate-900 mb-2">Module 1 Architecture Skeleton</h2>
        <p className="text-xs text-slate-600 leading-relaxed">
          This monorepo establishes the core architectural boundary for the Spare Parts Management & Discovery System.
          The backend handles relational persistence through SQLAlchemy 2.x and schema versioning via Alembic.
          Subsequent modules will layer business entities (Module 2: Data Models, Module 3: Authentication, Module 4: Parts Catalog, Module 5: Inventory, Module 6: Issues & Workflows).
        </p>
      </div>
    </div>
  );
};
