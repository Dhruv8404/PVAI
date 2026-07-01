import React from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { 
  LayoutDashboard, 
  Users, 
  FileText, 
  History, 
  LogOut, 
  ChevronLeft, 
  ChevronRight,
  ShieldCheck
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

interface SidebarProps {
  isCollapsed: boolean;
  setIsCollapsed: (collapsed: boolean) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ isCollapsed, setIsCollapsed }) => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const navItems = [
    {
      name: 'Dashboard',
      path: '/dashboard',
      icon: LayoutDashboard,
      roles: ['Admin', 'User']
    },
    {
      name: 'Users Directory',
      path: '/users',
      icon: Users,
      roles: ['Admin']
    },
    {
      name: 'Document Generator',
      path: '/generator',
      icon: FileText,
      roles: ['Admin', 'User']
    },
    {
      name: 'History Vault',
      path: '/history',
      icon: History,
      roles: ['Admin', 'User']
    }
  ];

  const filteredItems = navItems.filter(item => item.roles.includes(user?.role || ''));

  return (
    <aside 
      className={`
        fixed top-0 bottom-0 left-0 z-20
        bg-white dark:bg-zinc-950 
        border-r border-slate-200 dark:border-zinc-900
        flex flex-col justify-between
        transition-all duration-300 ease-in-out
        ${isCollapsed ? 'w-16' : 'w-64'}
      `}
    >
      {/* Upper Section */}
      <div>
        {/* Brand Logo */}
        <div className="h-16 flex items-center justify-between px-4 border-b border-slate-100 dark:border-zinc-900">
          <div className="flex items-center gap-2.5 overflow-hidden">
            <div className="flex-shrink-0 p-1.5 rounded-lg bg-indigo-600 dark:bg-indigo-500 text-white shadow-sm">
              <ShieldCheck className="h-5 w-5" />
            </div>
            {!isCollapsed && (
              <span className="font-bold text-sm text-slate-900 dark:text-zinc-50 tracking-tight whitespace-nowrap">
                PV Generation
              </span>
            )}
          </div>
          
          <button 
            onClick={() => setIsCollapsed(!isCollapsed)}
            className="hidden md:flex p-1 rounded-md text-slate-400 hover:text-slate-500 dark:hover:text-zinc-300 hover:bg-slate-50 dark:hover:bg-zinc-900 transition-colors"
          >
            {isCollapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
          </button>
        </div>

        {/* Navigation Links */}
        <nav className="p-3 space-y-1">
          {filteredItems.map(item => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.path}
                to={item.path}
                className={({ isActive }) => `
                  flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs font-semibold tracking-wide transition-all
                  ${isActive 
                    ? 'bg-indigo-50 text-indigo-700 dark:bg-indigo-600/10 dark:text-indigo-400' 
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50 dark:text-zinc-400 dark:hover:text-zinc-100 dark:hover:bg-zinc-900/60'}
                `}
              >
                <Icon className="h-4.5 w-4.5 flex-shrink-0" />
                {!isCollapsed && (
                  <span className="transition-opacity duration-200">{item.name}</span>
                )}
              </NavLink>
            );
          })}
        </nav>
      </div>

      {/* Footer Section */}
      <div className="p-3 border-t border-slate-100 dark:border-zinc-900 bg-slate-50/40 dark:bg-zinc-950/20">
        <button
          onClick={handleLogout}
          className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs font-semibold text-rose-600 dark:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-950/20 transition-all"
        >
          <LogOut className="h-4.5 w-4.5 flex-shrink-0" />
          {!isCollapsed && <span>Logout Session</span>}
        </button>
      </div>
    </aside>
  );
};
export default Sidebar;
