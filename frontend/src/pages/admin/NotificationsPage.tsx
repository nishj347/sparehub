import React, { useEffect, useState, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  CheckCheck,
  Clock,
  ExternalLink,
  Package,
  User,
} from 'lucide-react';
import { getNotifications, markRead, markAllRead } from '../../api/notifications';
import { NotificationItem, NotificationsResponse } from '../../types/notification';
import { useUrlSearchState } from '../../hooks/useUrlSearchState';
import { Pagination } from '../../components/ui/Pagination';
import { LoadingState } from '../../components/ui/LoadingState';
import { ErrorState } from '../../components/ui/ErrorState';
import { EmptyState } from '../../components/ui/EmptyState';
import { useToast } from '../../components/ui/Toast';
import { formatDateTime, formatRelativeTime } from '../../lib/formatDateTime';
import { ApiError } from '../../api/client';

export const NotificationsPage: React.FC = () => {
  const { get, getInt, set } = useUrlSearchState();
  const navigate = useNavigate();
  const { success, error: toastError } = useToast();

  const tab = get('tab', 'all') as 'all' | 'unread';
  const page = getInt('page', 1);

  const [data, setData] = useState<NotificationsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [markingAll, setMarkingAll] = useState(false);

  // Stale request guard
  const reqIdRef = useRef(0);

  const fetchNotifications = useCallback(async () => {
    const currentReqId = ++reqIdRef.current;
    setLoading(true);
    setError(null);

    try {
      const res = await getNotifications({
        status: tab === 'unread' ? 'unread' : 'all',
        page,
        page_size: 20,
      });

      if (currentReqId === reqIdRef.current) {
        setData(res);
        setLoading(false);
      }
    } catch (err) {
      if (currentReqId === reqIdRef.current) {
        const msg = err instanceof ApiError ? err.message : 'Failed to load notifications.';
        setError(msg);
        setLoading(false);
      }
    }
  }, [tab, page]);

  useEffect(() => {
    fetchNotifications();
  }, [fetchNotifications]);

  // Handle clicking an item: mark read, refresh bell, navigate if part_id exists
  const handleItemClick = async (item: NotificationItem) => {
    if (!item.is_read) {
      try {
        await markRead(item.id);
        // Optimistically update local state
        setData((prev) => {
          if (!prev) return null;
          return {
            ...prev,
            items: prev.items.map((it) => (it.id === item.id ? { ...it, is_read: true } : it)),
          };
        });
        // Notify NotificationBell
        window.dispatchEvent(new CustomEvent('notification-count-update'));
      } catch {
        // Silently proceed with navigation
      }
    }

    if (item.part_id) {
      navigate(`/admin/parts/${item.part_id}`);
    }
  };

  const handleMarkAllRead = async () => {
    setMarkingAll(true);
    try {
      const res = await markAllRead();
      success(`Marked ${res.updated} notification${res.updated === 1 ? '' : 's'} as read.`);
      // Update local state
      setData((prev) => {
        if (!prev) return null;
        return {
          ...prev,
          items: prev.items.map((it) => ({ ...it, is_read: true })),
        };
      });
      // Notify NotificationBell
      window.dispatchEvent(new CustomEvent('notification-count-update'));
      // If we are on unread tab, re-fetch to update view
      if (tab === 'unread') {
        fetchNotifications();
      }
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : 'Failed to mark all as read.';
      toastError(msg);
    } finally {
      setMarkingAll(false);
    }
  };

  // Count unread items on current page or in loaded data
  const hasUnread = data?.items.some((it) => !it.is_read) ?? false;

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">Notifications</h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Audit alerts for parts issued and low stock notifications requiring administrator attention.
          </p>
        </div>

        <button
          type="button"
          onClick={handleMarkAllRead}
          disabled={markingAll || !hasUnread}
          className="inline-flex items-center gap-2 px-3.5 py-2 text-xs font-semibold text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed shadow-sm transition"
        >
          <CheckCheck className="w-4 h-4 text-slate-500" />
          <span>{markingAll ? 'Marking...' : 'Mark all as read'}</span>
        </button>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-2 border-b border-slate-200">
        <button
          type="button"
          onClick={() => set({ tab: 'all', page: null })}
          className={`pb-3 text-sm font-semibold border-b-2 transition-colors px-1 ${
            tab === 'all'
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          All Notifications
        </button>
        <button
          type="button"
          onClick={() => set({ tab: 'unread', page: null })}
          className={`pb-3 text-sm font-semibold border-b-2 transition-colors px-1 ${
            tab === 'unread'
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          Unread Only
        </button>
      </div>

      {/* Notifications List */}
      {loading ? (
        <LoadingState message="Loading notifications..." />
      ) : error ? (
        <ErrorState
          title="Could not load notifications"
          message={error}
          onRetry={fetchNotifications}
        />
      ) : data?.items.length === 0 ? (
        <EmptyState
          title={tab === 'unread' ? 'No unread notifications' : 'No notifications yet'}
          description={
            tab === 'unread'
              ? 'All notifications have been reviewed and marked as read.'
              : 'You will receive notifications when spare parts are issued or low stock thresholds are reached.'
          }
        />
      ) : (
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          <ul className="divide-y divide-slate-100">
            {data?.items.map((item) => (
              <li
                key={item.id}
                onClick={() => handleItemClick(item)}
                className={`p-4 sm:p-5 flex items-start gap-4 transition-colors cursor-pointer ${
                  !item.is_read
                    ? 'bg-blue-50/40 hover:bg-blue-50/70'
                    : 'hover:bg-slate-50'
                }`}
              >
                {/* Status Dot / Icon */}
                <div className="pt-0.5 shrink-0">
                  {!item.is_read ? (
                    <span
                      className="inline-block w-2.5 h-2.5 rounded-full bg-blue-600 ring-4 ring-blue-100"
                      title="Unread"
                    />
                  ) : (
                    <span
                      className="inline-block w-2.5 h-2.5 rounded-full bg-slate-300"
                      title="Read"
                    />
                  )}
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-start justify-between gap-2">
                    <p
                      className={`text-sm leading-relaxed ${
                        !item.is_read ? 'font-semibold text-slate-900' : 'text-slate-700'
                      }`}
                    >
                      {item.message}
                    </p>

                    {item.part_id && (
                      <span className="text-slate-400 hover:text-blue-600 shrink-0">
                        <ExternalLink className="w-4 h-4" />
                      </span>
                    )}
                  </div>

                  {/* Metadata Chips */}
                  <div className="flex flex-wrap items-center gap-3 mt-2 text-xs text-slate-500">
                    <span
                      className="flex items-center gap-1 text-slate-500 cursor-default"
                      title={formatDateTime(item.created_at)}
                    >
                      <Clock className="w-3.5 h-3.5 text-slate-400" />
                      <span>{formatRelativeTime(item.created_at)}</span>
                    </span>

                    {item.part_name && (
                      <span className="flex items-center gap-1 text-slate-600">
                        <Package className="w-3.5 h-3.5 text-slate-400" />
                        <span>{item.part_name}</span>
                      </span>
                    )}

                    {item.actor_employee_id && (
                      <span className="flex items-center gap-1 text-slate-600 font-mono">
                        <User className="w-3.5 h-3.5 text-slate-400" />
                        <span>{item.actor_employee_id}</span>
                      </span>
                    )}

                    {item.quantity != null && (
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold bg-rose-50 text-rose-700 border border-rose-200">
                        -{item.quantity} units
                      </span>
                    )}
                  </div>
                </div>
              </li>
            ))}
          </ul>

          {/* Pagination */}
          {data && data.total_pages > 1 && (
            <Pagination
              page={data.page}
              pageSize={data.page_size}
              total={data.total}
              totalPages={data.total_pages}
              onPageChange={(newPage) => set({ page: newPage > 1 ? newPage : null })}
            />
          )}
        </div>
      )}
    </div>
  );
};
