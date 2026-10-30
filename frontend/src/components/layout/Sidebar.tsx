import React from 'react';
import { NavLink } from 'react-router-dom';
import { LayoutDashboard, Wrench, ClipboardList, X } from 'lucide-react';

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

const navItems = [
  { name: 'Dashboard', path: '/', icon: LayoutDashboard },
  { name: 'Spare Parts', path: '/parts', icon: Wrench },
  { name: 'Issue History', path: '/issues', icon: ClipboardList },
];

export const Sidebar: React.FC<SidebarProps> = ({ isOpen, onClose }) => {
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
        <div className="h-16 flex items-center justify-between px-5 border-b border-slate-800">
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

        {/* Navigation list */}
        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.path}
                to={item.path}
                onClick={() => onClose()}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-blue-600 text-white shadow-sm'
                      : 'text-slate-400 hover:text-slate-100 hover:bg-slate-800'
                  }`
                }
              >
                <Icon className="w-4 h-4 shrink-0" />
                <span>{item.name}</span>
              </NavLink>
            );
          })}
        </nav>

        {/* Bottom footer metadata */}
        <div className="p-4 border-t border-slate-800 text-xs text-slate-500">
          <p className="font-medium text-slate-400">Architecture v1.0.0</p>
          <p className="mt-0.5">Core Monolith Foundation</p>
        </div>
      </aside>
    </>
  );
};
