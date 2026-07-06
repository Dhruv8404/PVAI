import React, { useState, useEffect } from 'react';
import { Outlet, Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { Sidebar } from './Sidebar';
import { TopNav } from './TopNav';

export const ProtectedLayout: React.FC = () => {
  const { user, loading, refreshSession } = useAuth();
  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => {
    const saved = localStorage.getItem('pv_sidebar_collapsed');
    return saved === 'true';
  });
  const [mobileOpen, setMobileOpen] = useState(false);
  const location = useLocation();

  useEffect(() => {
    localStorage.setItem('pv_sidebar_collapsed', sidebarCollapsed.toString());
  }, [sidebarCollapsed]);

  // Check user state periodically when switching routes
  useEffect(() => {
    refreshSession();
    setMobileOpen(false); // Close mobile drawer on route change
  }, [location.pathname]);

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 dark:bg-zinc-950 flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 rounded-full border-4 border-t-indigo-600 border-r-transparent border-b-transparent border-l-transparent animate-spin" />
          <span className="text-xs font-semibold text-slate-500 dark:text-zinc-400">Restoring session...</span>
        </div>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-zinc-950 transition-colors duration-300">
      {/* Sidebar - Desktop */}
      <div className="hidden md:block">
        <Sidebar 
          isCollapsed={sidebarCollapsed} 
          setIsCollapsed={setSidebarCollapsed} 
        />
      </div>

      {/* Sidebar - Mobile Overlay */}
      {mobileOpen && (
        <div className="fixed inset-0 z-40 md:hidden">
          {/* Backdrop */}
          <div 
            onClick={() => setMobileOpen(false)}
            className="fixed inset-0 bg-slate-900/60 dark:bg-black/80 backdrop-blur-xs"
          />
          <div className="relative w-64 h-full bg-white dark:bg-zinc-950">
            <Sidebar 
              isCollapsed={false} 
              setIsCollapsed={() => {}} 
            />
          </div>
        </div>
      )}

      {/* Main Content Area */}
      <div 
        className={`
          flex flex-col min-h-screen
          transition-all duration-300 ease-in-out
          ${sidebarCollapsed ? 'md:pl-16' : 'md:pl-64'}
        `}
      >
        {/* Top Navbar */}
        <TopNav 
          sidebarCollapsed={sidebarCollapsed} 
          onMobileMenuToggle={() => setMobileOpen(true)}
        />

        {/* Dynamic Page Router Outlet */}
        <main className="flex-1 p-6 overflow-x-hidden">
          <div className="w-full max-w-7xl xl:max-w-[1440px] 2xl:max-w-[1600px] mx-auto space-y-6 animate-fade-in">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
};
export default ProtectedLayout;
