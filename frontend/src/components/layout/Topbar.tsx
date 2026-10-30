import React from 'react';
import { Menu, User, ShieldCheck } from 'lucide-react';

interface TopbarProps {
  onToggleSidebar: () => void;
}

export const Topbar: React.FC<TopbarProps> = ({ onToggleSidebar }) => {
  return (
    <header className="h-16 bg-white border-b border-slate-200 sticky top-0 z-30 flex items-center justify-between px-4 sm:px-6 md:px-8">
      {/* Mobile toggle button */}
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

      {/* Right area: User menu placeholder */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-3 pl-3 border-l border-slate-200">
          <div className="w-8 h-8 rounded-full bg-slate-100 border border-slate-300 flex items-center justify-center text-slate-600">
            <User className="w-4 h-4" />
          </div>
          <div className="hidden md:flex flex-col text-left">
            <span className="text-xs font-semibold text-slate-700">Account Placeholder</span>
            <span className="text-[10px] text-slate-400">Auth enabled in Module 3</span>
          </div>
        </div>
      </div>
    </header>
  );
};
