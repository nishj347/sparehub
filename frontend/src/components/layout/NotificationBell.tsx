import React, { useEffect, useState, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Bell } from 'lucide-react';
import { useAuth } from '../../auth/AuthContext';
import { getUnreadCount } from '../../api/notifications';

interface NotificationBellProps {
  className?: string;
}

export const NotificationBell: React.FC<NotificationBellProps> = ({ className = '' }) => {
  const { user, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const [unreadCount, setUnreadCount] = useState<number>(0);
  const isMountedRef = useRef(true);

  const fetchCount = useCallback(async () => {
    if (!isAuthenticated || user?.role !== 'STORE_ADMIN') return;
    try {
      const res = await getUnreadCount();
      if (isMountedRef.current) {
        setUnreadCount(res.unread || 0);
      }
    } catch {
      // Polling must be silent on errors
    }
  }, [isAuthenticated, user?.role]);

  useEffect(() => {
    isMountedRef.current = true;
    if (!isAuthenticated || user?.role !== 'STORE_ADMIN') {
      setUnreadCount(0);
      return;
    }

    // Initial fetch
    fetchCount();

    // 30s interval polling
    const intervalId = setInterval(() => {
      if (document.visibilityState === 'visible') {
        fetchCount();
      }
    }, 30000);

    // Refresh on tab focus
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        fetchCount();
      }
    };

    // Custom event listener so other components (e.g. NotificationsPage) can trigger a count refresh immediately
    const handleCustomRefresh = () => {
      fetchCount();
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    window.addEventListener('notification-count-update', handleCustomRefresh);

    return () => {
      isMountedRef.current = false;
      clearInterval(intervalId);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      window.removeEventListener('notification-count-update', handleCustomRefresh);
    };
  }, [fetchCount, isAuthenticated, user?.role]);

  if (!isAuthenticated || user?.role !== 'STORE_ADMIN') {
    return null;
  }

  const badgeText = unreadCount > 99 ? '99+' : unreadCount.toString();
  const ariaLabel = `Notifications, ${unreadCount} unread`;

  return (
    <button
      type="button"
      onClick={() => navigate('/admin/notifications')}
      className={`relative p-2 rounded-lg text-slate-500 hover:text-slate-800 hover:bg-slate-100 transition-colors focus:outline-none focus:ring-2 focus:ring-primary-500 ${className}`}
      aria-label={ariaLabel}
      title={ariaLabel}
    >
      <Bell className="w-5 h-5" />
      {unreadCount > 0 && (
        <span className="absolute top-1 right-1 flex items-center justify-center min-w-[1.125rem] h-4 px-1 rounded-full text-[10px] font-bold leading-none bg-rose-600 text-white shadow-sm ring-2 ring-white">
          {badgeText}
        </span>
      )}
    </button>
  );
};

