import React, { useState } from 'react';
import { TopHeader } from './TopHeader.jsx';
import { Sidebar } from './Sidebar.jsx';
import { Breadcrumbs } from './Breadcrumbs.jsx';
import { useAuth } from '../../context/AuthProvider.jsx';
import { X } from 'lucide-react';

export function AppShell({ children, breadcrumbs = [], noPadding = false }) {
  const { user } = useAuth();
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);

  return (
    <div className="h-screen bg-zinc-100/90 flex flex-col font-sans text-zinc-900 overflow-hidden rounded-none">
      {/* Top Header - Sharp outer container */}
      <TopHeader onToggleSidebar={() => setMobileSidebarOpen(!mobileSidebarOpen)} />

      {/* Main Container: Sidebar + Workspace */}
      <div className="flex-1 flex overflow-hidden">
        {/* Desktop Persistent Sidebar - Sharp outer edges */}
        {user && (
          <div className="hidden lg:block shrink-0 h-full overflow-y-auto">
            <Sidebar />
          </div>
        )}

        {/* Mobile Slide-Over Sidebar Drawer */}
        {user && mobileSidebarOpen && (
          <div className="fixed inset-0 z-50 lg:hidden flex">
            <div
              className="fixed inset-0 bg-zinc-950/50 backdrop-blur-xs transition-opacity animate-in fade-in"
              onClick={() => setMobileSidebarOpen(false)}
            />
            <div className="relative w-64 max-w-[80vw] bg-white h-full shadow-2xl flex flex-col z-10 animate-in slide-in-from-left duration-200">
              <div className="p-3.5 border-b border-zinc-200 flex items-center justify-between bg-zinc-50/90">
                <span className="font-bold text-xs text-zinc-900 tracking-tight">Navigation</span>
                <button
                  type="button"
                  onClick={() => setMobileSidebarOpen(false)}
                  className="p-1.5 rounded-lg text-zinc-500 hover:text-zinc-900 hover:bg-zinc-200/80 transition-colors"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
              <div className="flex-1 overflow-y-auto">
                <Sidebar onCloseMobile={() => setMobileSidebarOpen(false)} />
              </div>
            </div>
          </div>
        )}

        {/* Workspace Content Area */}
        <main className={`flex-1 overflow-y-auto ${noPadding ? 'p-0 flex flex-col' : 'p-3 sm:p-5 lg:p-6 space-y-4'}`}>
          {breadcrumbs && breadcrumbs.length > 0 && (
            <div className={noPadding ? 'p-3 pb-0' : 'pb-1'}>
              <Breadcrumbs items={breadcrumbs} />
            </div>
          )}
          {children}
        </main>
      </div>
    </div>
  );
}

export default AppShell;

