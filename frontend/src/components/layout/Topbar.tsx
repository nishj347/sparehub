import React, { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { LogOut, Menu, ShieldCheck, User, ChevronDown } from 'lucide-react';
import { useAuth } from '../../auth/AuthContext';
import { NotificationBell } from './NotificationBell';

interface TopbarProps {
  onToggleSidebar: () => void;
}

export const Topbar: React.FC<TopbarProps> = ({ onToggleSidebar }) => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // Close dropdown when user clicks outside the menu
  useEffect(() => {
    if (!menuOpen) return;
    const handler = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [menuOpen]);

  const handleLogout = () => {
    setMenuOpen(false);
    logout();
    navigate('/login');
  };


  const roleLabel = user?.role === 'STORE_ADMIN' ? 'Store Admin' : 'Employee';
  const roleBadgeClass =
    user?.role === 'STORE_ADMIN'
      ? 'bg-violet-100 text-violet-700 border-violet-200'
      : 'bg-blue-50 text-blue-700 border-blue-200';

  return (
    <header className="h-16 bg-white border-b border-slate-200 sticky top-0 z-30 flex items-center justify-between px-4 sm:px-6 md:px-8">
      {/* Left: mobile toggle + platform badge */}
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={onToggleSidebar}
          className="p-2 rounded-md text-slate-600 hover:text-slate-900 hover:bg-slate-100 md:hidden"
          aria-label="Toggle navigation"
        >
          <Menu className="w-5 h-5" />
        </button>
        <div className="hidden sm:flex items-center gap-2 text-xs font-medium text-slate-500 bg-slate-100 px-2.5 py-1 rounded-full border border-slate-200">
          <ShieldCheck className="w-3.5 h-3.5 text-blue-600" />
          <span>Internal Enterprise Platform</span>
        </div>
      </div>

      {/* Right: user menu & notifications */}
      <div className="flex items-center gap-3">
        {user?.role === 'STORE_ADMIN' && <NotificationBell />}

        <div className="relative" ref={menuRef}>
          {user ? (
          <>
            <button
              type="button"
              onClick={() => setMenuOpen((v) => !v)}
              aria-expanded={menuOpen}
              aria-haspopup="true"
              className="flex items-center gap-2.5 pl-3 pr-2 py-1.5 rounded-lg hover:bg-slate-50 border border-transparent hover:border-slate-200 transition-colors"
            >
              <div className="w-7 h-7 rounded-full bg-slate-700 text-white text-xs font-semibold flex items-center justify-center shrink-0">
                {user.name.charAt(0).toUpperCase()}
              </div>
              <div className="hidden md:flex flex-col text-left min-w-0">
                <span className="text-xs font-semibold text-slate-700 leading-tight truncate max-w-[120px]">
                  {user.name}
                </span>
                <span className="text-[10px] text-slate-400 leading-tight truncate">
                  {user.employee_id}
                </span>
              </div>
              <ChevronDown className="w-3.5 h-3.5 text-slate-400 shrink-0" />
            </button>

            {/* Dropdown */}
            {menuOpen && (
              <div
                className="absolute right-0 mt-2 w-60 bg-white rounded-xl border border-slate-200 shadow-lg py-1 z-50"
                role="menu"
              >
                {/* User info panel */}
                <div className="px-4 py-3 border-b border-slate-100">
                  <div className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-full bg-slate-700 text-white text-sm font-semibold flex items-center justify-center shrink-0">
                      {user.name.charAt(0).toUpperCase()}
                    </div>
                    <div className="min-w-0">
                      <p className="text-sm font-semibold text-slate-800 truncate">{user.name}</p>
                      <p className="text-xs text-slate-500 truncate">{user.employee_id}</p>
                    </div>
                  </div>
                  <div className="mt-2.5 flex flex-wrap items-center gap-1.5">
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold border ${roleBadgeClass}`}
                    >
                      {roleLabel}
                    </span>
                    <span className="text-[11px] text-slate-400 truncate">
                      {user.location.name}
                    </span>
                  </div>
                </div>

                {/* Actions */}
                <div className="py-1">
                  <button
                    type="button"
                    role="menuitem"
                    onClick={handleLogout}
                    className="flex items-center gap-2.5 w-full px-4 py-2 text-sm text-red-600 hover:bg-red-50 transition-colors"
                  >
                    <LogOut className="w-4 h-4" />
                    <span>Sign Out</span>
                  </button>
                </div>
              </div>
            )}
          </>
        ) : (
          /* Unauthenticated placeholder — only shown on public pages using AppShell (edge case) */
          <div className="flex items-center gap-3 pl-3 border-l border-slate-200">
            <div className="w-8 h-8 rounded-full bg-slate-100 border border-slate-300 flex items-center justify-center text-slate-600">
              <User className="w-4 h-4" />
            </div>
          </div>
        )}
        </div>
      </div>
    </header>
  );
};
