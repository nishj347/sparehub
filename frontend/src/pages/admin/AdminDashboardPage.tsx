import React, { useEffect, useState, useRef, useCallback } from 'react';
import { Link } from 'react-router-dom';
import {
  Package,
  Layers,
  AlertTriangle,
  ArrowDownRight,
  ArrowUpRight,
  Sliders,
  RefreshCw,
  ExternalLink,
  PlusCircle,
  AlertCircle,
  Clock,
} from 'lucide-react';
import { getAdminDashboard } from '../../api/dashboard';
import {
  DashboardResponse,
  DashboardActivityItem,
  DashboardLowStockItem,
} from '../../types/dashboard';
import { useAuth } from '../../auth/AuthContext';
import { PartImage } from '../../components/parts/PartImage';
import { formatDateTime } from '../../lib/formatDateTime';
import { ErrorState } from '../../components/ui/ErrorState';
import { ApiError } from '../../api/client';

// ── Skeletons ───────────────────────────────────────────────────────────────

const DashboardSkeleton: React.FC = () => (
  <div className="space-y-8 animate-pulse">
    {/* Header Skeleton */}
    <div className="flex items-center justify-between">
      <div className="space-y-2">
        <div className="h-8 bg-slate-200 rounded w-48" />
        <div className="h-4 bg-slate-100 rounded w-64" />
      </div>
      <div className="h-9 bg-slate-200 rounded w-32" />
    </div>

    {/* Stat Cards Skeleton */}
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {[1, 2, 3, 4].map((i) => (
        <div key={i} className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-3">
          <div className="h-3 bg-slate-200 rounded w-28" />
          <div className="h-8 bg-slate-300 rounded w-16" />
          <div className="h-3 bg-slate-100 rounded w-36" />
        </div>
      ))}
    </div>

    {/* Tables Skeleton */}
    <div className="grid grid-cols-1 xl:grid-cols-2 gap-8">
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-4">
        <div className="h-5 bg-slate-200 rounded w-40" />
        <div className="space-y-3">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="h-10 bg-slate-100 rounded" />
          ))}
        </div>
      </div>
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-4">
        <div className="h-5 bg-slate-200 rounded w-40" />
        <div className="space-y-3">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="h-10 bg-slate-100 rounded" />
          ))}
        </div>
      </div>
    </div>
  </div>
);

// ── Stat Card Component ─────────────────────────────────────────────────────

interface StatCardProps {
  title: string;
  value: number | string;
  subtext?: React.ReactNode;
  icon: React.ReactNode;
  to: string;
  accent?: 'default' | 'amber' | 'blue';
}

const StatCard: React.FC<StatCardProps> = ({ title, value, subtext, icon, to, accent = 'default' }) => {
  const borderClass =
    accent === 'amber'
      ? 'border-amber-300 ring-1 ring-amber-200/50'
      : 'border-slate-200';

  const iconBgClass =
    accent === 'amber'
      ? 'bg-amber-50 text-amber-600'
      : accent === 'blue'
      ? 'bg-blue-50 text-blue-600'
      : 'bg-slate-50 text-slate-600';

  return (
    <Link
      to={to}
      className={`bg-white p-5 rounded-xl border ${borderClass} shadow-sm hover:shadow-md transition flex flex-col justify-between group`}
    >
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">{title}</p>
          <p className="text-3xl font-bold text-slate-900 mt-1 tracking-tight group-hover:text-blue-600 transition">
            {typeof value === 'number' ? value.toLocaleString() : value}
          </p>
        </div>
        <div className={`p-3 rounded-lg ${iconBgClass} border border-slate-100`}>
          {icon}
        </div>
      </div>

      {subtext && <div className="mt-3 text-xs text-slate-500 pt-2 border-t border-slate-100">{subtext}</div>}
    </Link>
  );
};

// ── Action Badge Helper ─────────────────────────────────────────────────────

const getActionBadge = (type: string) => {
  switch (type) {
    case 'ISSUED':
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-rose-50 text-rose-700 border border-rose-200">
          <ArrowDownRight className="w-3 h-3 text-rose-500" />
          ISSUED
        </span>
      );
    case 'RECEIVED':
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
          <ArrowUpRight className="w-3 h-3 text-emerald-500" />
          RECEIVED
        </span>
      );
    case 'ADJUSTED':
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-amber-50 text-amber-700 border border-amber-200">
          <Sliders className="w-3 h-3 text-amber-500" />
          ADJUSTED
        </span>
      );
    default:
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium bg-slate-100 text-slate-700 border border-slate-200">
          {type}
        </span>
      );
  }
};

// ── Main Dashboard Page ─────────────────────────────────────────────────────

export const AdminDashboardPage: React.FC = () => {
  const { user, isAuthenticated } = useAuth();

  const [data, setData] = useState<DashboardResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [refreshError, setRefreshError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const reqIdRef = useRef(0);
  const isMountedRef = useRef(true);

  const fetchDashboard = useCallback(async (isBackground = false) => {
    if (!isAuthenticated || user?.role !== 'STORE_ADMIN') return;

    const currentReqId = ++reqIdRef.current;
    if (isBackground) {
      setRefreshing(true);
      setRefreshError(null);
    } else {
      setLoading(true);
      setError(null);
    }

    try {
      const res = await getAdminDashboard();
      if (currentReqId === reqIdRef.current && isMountedRef.current) {
        setData(res);
        setLastUpdated(new Date());
        setLoading(false);
        setRefreshing(false);
        setRefreshError(null);
      }
    } catch (err) {
      if (currentReqId === reqIdRef.current && isMountedRef.current) {
        const msg = err instanceof ApiError ? err.message : 'Unable to connect to dashboard service.';
        if (isBackground) {
          setRefreshError("Couldn't auto-refresh. Displaying cached data.");
          setRefreshing(false);
        } else {
          setError(msg);
          setLoading(false);
        }
      }
    }
  }, [isAuthenticated, user?.role]);

  // Initial load
  useEffect(() => {
    isMountedRef.current = true;
    fetchDashboard(false);

    // 60-second auto-refresh while tab is visible
    const interval = setInterval(() => {
      if (document.visibilityState === 'visible') {
        fetchDashboard(true);
      }
    }, 60000);

    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        fetchDashboard(true);
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);

    return () => {
      isMountedRef.current = false;
      clearInterval(interval);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [fetchDashboard]);

  if (loading) {
    return <DashboardSkeleton />;
  }

  if (error || !data) {
    return (
      <div className="py-8">
        <ErrorState
          title="Failed to load Admin Dashboard"
          message={error || 'An unexpected error occurred while loading dashboard metrics.'}
          onRetry={() => fetchDashboard(false)}
        />
      </div>
    );
  }

  const { stats, recent_activity, low_stock_items, low_stock_total } = data;
  const todayIso = new Date().toISOString().split('T')[0];

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">Dashboard</h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Operational overview of inventory levels, low-stock alerts, and recent transactions.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {refreshError && (
            <div className="flex items-center gap-1.5 text-xs text-amber-700 bg-amber-50 px-2.5 py-1.5 rounded-md border border-amber-200">
              <AlertCircle className="w-3.5 h-3.5 shrink-0" />
              <span>{refreshError}</span>
            </div>
          )}

          {lastUpdated && (
            <span className="text-xs text-slate-400 flex items-center gap-1">
              <Clock className="w-3.5 h-3.5" />
              <span>
                Updated{' '}
                {lastUpdated.toLocaleTimeString('en-GB', {
                  hour: '2-digit',
                  minute: '2-digit',
                  second: '2-digit',
                })}
              </span>
            </span>
          )}

          <button
            type="button"
            onClick={() => fetchDashboard(true)}
            disabled={refreshing}
            className="inline-flex items-center gap-2 px-3 py-1.5 text-xs font-semibold text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 shadow-sm transition disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? 'animate-spin text-blue-600' : 'text-slate-500'}`} />
            <span>{refreshing ? 'Refreshing...' : 'Refresh'}</span>
          </button>
        </div>
      </div>

      {/* 4 Key Metric Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Card 1: Total Spare Parts */}
        <StatCard
          title="Total Spare Parts"
          value={stats.total_parts}
          subtext="Active components in enterprise catalog"
          icon={<Package className="w-6 h-6" />}
          to="/admin/parts"
        />

        {/* Card 2: Total Available Units */}
        <StatCard
          title="Total Available Units"
          value={stats.total_units}
          subtext="Physical stock across all active facilities"
          icon={<Layers className="w-6 h-6" />}
          to="/admin/parts"
          accent="blue"
        />

        {/* Card 3: Low Stock Parts */}
        <StatCard
          title="Low Stock Parts"
          value={stats.low_stock_parts}
          accent={stats.low_stock_parts > 0 ? 'amber' : 'default'}
          subtext={
            <div className="flex items-center justify-between">
              <span>{stats.low_stock_parts} below reorder threshold</span>
              {stats.out_of_stock_parts > 0 && (
                <Link
                  to="/admin/parts?stock=out"
                  className="font-semibold text-rose-600 hover:text-rose-700 underline"
                  onClick={(e) => e.stopPropagation()}
                >
                  {stats.out_of_stock_parts} out of stock
                </Link>
              )}
            </div>
          }
          icon={<AlertTriangle className="w-6 h-6" />}
          to="/admin/parts?stock=low"
        />

        {/* Card 4: Today's Issues */}
        <StatCard
          title="Today's Issues"
          value={stats.todays_issues}
          subtext={
            <span>
              <strong className="text-slate-800">{stats.todays_units_issued}</strong> units issued today
            </span>
          }
          icon={<ArrowDownRight className="w-6 h-6 text-rose-600" />}
          to={`/admin/activity?type=ISSUED&date_from=${todayIso}&date_to=${todayIso}`}
        />
      </div>

      {/* Main Dual Sections: Recent Activity & Low Stock */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-8 items-start">
        {/* Left: Recent Inventory Activity */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden flex flex-col">
          <div className="p-5 border-b border-slate-200 flex items-center justify-between">
            <div>
              <h2 className="text-base font-bold text-slate-900">Recent Inventory Activity</h2>
              <p className="text-xs text-slate-500 mt-0.5">Last 10 transactions across all locations</p>
            </div>
            <Link
              to="/admin/activity"
              className="inline-flex items-center gap-1 text-xs font-semibold text-blue-600 hover:text-blue-700 hover:underline"
            >
              <span>View all activity</span>
              <ExternalLink className="w-3.5 h-3.5" />
            </Link>
          </div>

          {recent_activity.length === 0 ? (
            <div className="p-8 text-center text-slate-500 text-xs">
              No inventory activity recorded yet.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-slate-600">
                <thead className="bg-slate-50 border-b border-slate-200 uppercase font-semibold text-slate-500 tracking-wider">
                  <tr>
                    <th scope="col" className="px-4 py-3 whitespace-nowrap">
                      Time
                    </th>
                    <th scope="col" className="px-4 py-3 whitespace-nowrap">
                      Employee
                    </th>
                    <th scope="col" className="px-4 py-3">
                      Part
                    </th>
                    <th scope="col" className="px-4 py-3 whitespace-nowrap text-right">
                      Qty
                    </th>
                    <th scope="col" className="px-4 py-3 whitespace-nowrap">
                      Action
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 bg-white">
                  {recent_activity.map((tx: DashboardActivityItem) => {
                    const isPositive = tx.quantity_change > 0;
                    const isNegative = tx.quantity_change < 0;
                    const signedQty = isPositive
                      ? `+${tx.quantity_change}`
                      : `${tx.quantity_change}`;

                    return (
                      <tr key={tx.id} className="hover:bg-slate-50 transition-colors">
                        {/* Time */}
                        <td className="px-4 py-3 whitespace-nowrap font-medium text-slate-700">
                          {formatDateTime(tx.created_at)}
                        </td>

                        {/* Employee */}
                        <td className="px-4 py-3 whitespace-nowrap">
                          {tx.actor ? (
                            <div>
                              <div className="font-semibold text-slate-900">{tx.actor.name}</div>
                              <div className="text-[10px] text-slate-400 font-mono">
                                {tx.actor.employee_id}
                              </div>
                            </div>
                          ) : (
                            <span className="text-slate-400 italic">System</span>
                          )}
                        </td>

                        {/* Part */}
                        <td className="px-4 py-3">
                          <Link
                            to={`/admin/parts/${tx.part.id}`}
                            className="font-medium text-slate-900 hover:text-blue-600 transition block truncate max-w-[180px]"
                            title={tx.part.name}
                          >
                            {tx.part.name}
                          </Link>
                          <span className="text-[10px] text-slate-400 font-mono block">
                            {tx.part.part_number} · {tx.location.code}
                          </span>
                        </td>

                        {/* Signed Quantity */}
                        <td className="px-4 py-3 whitespace-nowrap text-right font-mono font-bold">
                          <span
                            className={
                              isNegative
                                ? 'text-rose-600'
                                : isPositive
                                ? 'text-emerald-600'
                                : 'text-slate-600'
                            }
                          >
                            {signedQty}
                          </span>
                        </td>

                        {/* Action Type Badge */}
                        <td className="px-4 py-3 whitespace-nowrap">
                          {getActionBadge(tx.type)}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Right: Low Stock Priority Alerts */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden flex flex-col">
          <div className="p-5 border-b border-slate-200 flex items-center justify-between">
            <div>
              <h2 className="text-base font-bold text-slate-900">Low Stock Priority Alerts</h2>
              <p className="text-xs text-slate-500 mt-0.5">Top inventory rows at or below reorder threshold</p>
            </div>
            {low_stock_total > 0 && (
              <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-50 text-amber-700 border border-amber-200">
                {low_stock_total} items
              </span>
            )}
          </div>

          {low_stock_items.length === 0 ? (
            <div className="p-8 text-center text-slate-500 text-xs">
              No low-stock parts. Inventory levels look healthy.
            </div>
          ) : (
            <>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs text-slate-600">
                  <thead className="bg-slate-50 border-b border-slate-200 uppercase font-semibold text-slate-500 tracking-wider">
                    <tr>
                      <th scope="col" className="px-4 py-3">
                        Spare Part
                      </th>
                      <th scope="col" className="px-4 py-3 whitespace-nowrap">
                        Location
                      </th>
                      <th scope="col" className="px-4 py-3 whitespace-nowrap text-right">
                        Stock / Min
                      </th>
                      <th scope="col" className="px-4 py-3 whitespace-nowrap text-right">
                        Shortfall
                      </th>
                      <th scope="col" className="px-4 py-3 text-right">
                        Action
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 bg-white">
                    {low_stock_items.map((item: DashboardLowStockItem) => (
                      <tr key={item.inventory_id} className="hover:bg-slate-50 transition-colors">
                        {/* Part */}
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-2.5">
                            <div className="w-8 h-8 rounded border border-slate-200 bg-slate-50 overflow-hidden shrink-0">
                              <PartImage
                                src={item.part.image_url}
                                alt={item.part.name}
                                className="w-full h-full object-cover"
                              />
                            </div>
                            <div className="min-w-0">
                              <Link
                                to={`/admin/parts/${item.part.id}`}
                                className="font-semibold text-slate-900 hover:text-blue-600 transition block truncate max-w-[160px]"
                                title={item.part.name}
                              >
                                {item.part.name}
                              </Link>
                              <span className="text-[10px] text-slate-400 font-mono">
                                {item.part.part_number}
                              </span>
                            </div>
                          </div>
                        </td>

                        {/* Location */}
                        <td className="px-4 py-3 whitespace-nowrap">
                          <div className="font-medium text-slate-800">{item.location.name}</div>
                          <div className="text-[10px] text-slate-400 font-mono">{item.location.code}</div>
                        </td>

                        {/* Qty vs Min */}
                        <td className="px-4 py-3 whitespace-nowrap text-right">
                          <span
                            className={`font-mono font-bold ${
                              item.quantity === 0 ? 'text-rose-600' : 'text-amber-600'
                            }`}
                          >
                            {item.quantity}
                          </span>
                          <span className="text-slate-400 font-mono"> / {item.min_stock_level}</span>
                        </td>

                        {/* Shortfall */}
                        <td className="px-4 py-3 whitespace-nowrap text-right">
                          <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[11px] font-bold font-mono bg-rose-50 text-rose-700 border border-rose-200">
                            -{item.shortfall}
                          </span>
                        </td>

                        {/* Receive Action Link */}
                        <td className="px-4 py-3 whitespace-nowrap text-right">
                          <Link
                            to={`/admin/parts/${item.part.id}`}
                            className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-semibold text-blue-700 bg-blue-50 border border-blue-200 rounded-md hover:bg-blue-100 transition shadow-sm"
                          >
                            <PlusCircle className="w-3.5 h-3.5" />
                            <span>Receive</span>
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Low Stock Footer */}
              <div className="p-3.5 bg-slate-50 border-t border-slate-200 flex items-center justify-between text-xs text-slate-500">
                <span>
                  Showing {low_stock_items.length} of {low_stock_total} low-stock inventory records
                </span>
                <Link
                  to="/admin/parts?stock=low"
                  className="font-semibold text-blue-600 hover:text-blue-700 hover:underline"
                >
                  View all low stock parts &rarr;
                </Link>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
};
