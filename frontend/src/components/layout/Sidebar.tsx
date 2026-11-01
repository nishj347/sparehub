import React from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import {
  Activity,
  Bell,
  Building2,
  Cpu,
  LayoutDashboard,
  ClipboardList,
  LogOut,
  Package,
  Wrench,
  X,
  ChevronRight,
} from 'lucide-react';
import { useAuth } from '../../auth/AuthContext';

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

const linkBase =
  'flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium transition-colors';
const activeLink = 'bg-blue-600 text-white shadow-sm';
const inactiveLink = 'text-slate-400 hover:text-slate-100 hover:bg-slate-800';

export const Sidebar: React.FC<SidebarProps> = ({ isOpen, onClose }) => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    onClose();
    navigate('/login');
  };

  const isAdmin = user?.role === 'STORE_ADMIN';

  return (
    <>
      {/* Mobile overlay backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40 bg-slate-900/50 md:hidden"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      {/* Sidebar container */}
      <aside
        className={`fixed top-0 bottom-0 left-0 z-50 w-64 bg-slate-900 text-slate-200 flex flex-col border-r border-slate-800 transition-transform duration-200 ease-in-out md:translate-x-0 ${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {/* Brand header */}
        <div className="h-16 flex items-center justify-between px-5 border-b border-slate-800 shrink-0">
          <div className="flex flex-col">
            <span className="text-sm font-semibold tracking-wide text-white">
              Spare Parts Management
            </span>
            <span className="text-[11px] text-slate-400 tracking-wider uppercase font-medium">
              Enterprise Catalog
            </span>
          </div>
          <button
            type="button"
            className="p-1 rounded-md text-slate-400 hover:text-white md:hidden"
            onClick={onClose}
            aria-label="Close navigation"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 py-4 overflow-y-auto space-y-1">
          {isAdmin ? (
            <>
              {/* Admin navigation */}
              <p className="px-3 pt-1 pb-2 text-[10px] font-semibold uppercase tracking-widest text-slate-500">
                Admin
              </p>
              <NavLink
                to="/admin"
                end
                onClick={onClose}
                className={({ isActive }) => `${linkBase} ${isActive ? activeLink : inactiveLink}`}
              >
                <LayoutDashboard className="w-4 h-4 shrink-0" />
                <span>Admin Dashboard</span>
              </NavLink>
              <NavLink
                to="/admin/parts"
                onClick={onClose}
                className={({ isActive }) => `${linkBase} ${isActive ? activeLink : inactiveLink}`}
              >
                <Package className="w-4 h-4 shrink-0" />
                <span>Spare Parts Inventory</span>
              </NavLink>
              <NavLink
                to="/admin/activity"
                onClick={onClose}
                className={({ isActive }) => `${linkBase} ${isActive ? activeLink : inactiveLink}`}
              >
                <Activity className="w-4 h-4 shrink-0" />
                <span>Inventory Activity</span>
              </NavLink>
              <NavLink
                to="/admin/notifications"
                onClick={onClose}
                className={({ isActive }) => `${linkBase} ${isActive ? activeLink : inactiveLink}`}
              >
                <Bell className="w-4 h-4 shrink-0" />
                <span>Notifications</span>
              </NavLink>

              {/* Master Data Section */}
              <div className="pt-3 border-t border-slate-800/80 mt-3">
                <p className="px-3 pb-2 text-[10px] font-semibold uppercase tracking-widest text-slate-500">
                  Master Data
                </p>
                <NavLink
                  to="/admin/locations"
                  onClick={onClose}
                  className={({ isActive }) => `${linkBase} ${isActive ? activeLink : inactiveLink}`}
                >
                  <Building2 className="w-4 h-4 shrink-0" />
                  <span>Locations</span>
                </NavLink>
                <NavLink
                  to="/admin/machines"
                  onClick={onClose}
                  className={({ isActive }) => `${linkBase} ${isActive ? activeLink : inactiveLink}`}
                >
                  <Cpu className="w-4 h-4 shrink-0" />
                  <span>Machines</span>
                </NavLink>
              </div>

              {/* Separator + Employee View */}
              <div className="pt-4 border-t border-slate-800 mt-4">
                <p className="px-3 pb-2 text-[10px] font-semibold uppercase tracking-widest text-slate-500">
                  Employee View
                </p>
                <NavLink
                  to="/"
                  end
                  onClick={onClose}
                  className={({ isActive }) =>
                    `${linkBase} ${isActive ? activeLink : inactiveLink}`
                  }
                >
                  <ChevronRight className="w-4 h-4 shrink-0" />
                  <span>Employee Area</span>
                </NavLink>
              </div>
            </>
          ) : (
            <>
              {/* Employee navigation */}
              <NavLink
                to="/"
                end
                onClick={onClose}
                className={({ isActive }) => `${linkBase} ${isActive ? activeLink : inactiveLink}`}
              >
                <LayoutDashboard className="w-4 h-4 shrink-0" />
                <span>Dashboard</span>
              </NavLink>
              <NavLink
                to="/parts"
                onClick={onClose}
                className={({ isActive }) => `${linkBase} ${isActive ? activeLink : inactiveLink}`}
              >
                <Wrench className="w-4 h-4 shrink-0" />
                <span>Spare Parts</span>
              </NavLink>
              <NavLink
                to="/history"
                onClick={onClose}
                className={({ isActive }) => `${linkBase} ${isActive ? activeLink : inactiveLink}`}
              >
                <ClipboardList className="w-4 h-4 shrink-0" />
                <span>My Issue History</span>
              </NavLink>
            </>
          )}
        </nav>

        {/* Bottom: logout */}
        <div className="p-3 border-t border-slate-800 shrink-0">
          <button
            type="button"
            onClick={handleLogout}
            className="flex items-center gap-3 w-full px-3 py-2.5 rounded-md text-sm font-medium text-slate-400 hover:text-red-400 hover:bg-slate-800 transition-colors"
          >
            <LogOut className="w-4 h-4 shrink-0" />
            <span>Sign Out</span>
          </button>
        </div>
      </aside>
    </>
  );
};
