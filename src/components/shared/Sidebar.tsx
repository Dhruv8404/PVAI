import React, { useEffect, useState } from 'react';
import { NavLink, useNavigate, useLocation } from 'react-router-dom';
import { 
  LayoutDashboard, 
  Users, 
  FileText, 
  History, 
  LogOut, 
  ChevronLeft, 
  ChevronRight,
  ChevronDown,
  ChevronUp,
  ShieldCheck,
  FileCode,
  MessageSquare,
  Inbox
} from 'lucide-react';


import { useAuth } from '../../context/AuthContext';
import { API_BASE_URL } from '../../config';

interface SidebarProps {
  isCollapsed: boolean;
  setIsCollapsed: (collapsed: boolean) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ isCollapsed, setIsCollapsed }) => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  
  const [templates, setTemplates] = useState<any[]>([]);
  const [generatorExpanded, setGeneratorExpanded] = useState(true);

  // Fetch templates list dynamically for the submenu
  useEffect(() => {
    const fetchTemplates = async () => {
      try {
        const token = localStorage.getItem("pv_token");
        const headers: Record<string, string> = token ? { "Authorization": `Bearer ${token}` } : {};
        const specUrl = API_BASE_URL.replace("/api/v1", "/api");
        const res = await fetch(`${specUrl}/templates/`, { headers });
        if (!res.ok) throw new Error("Failed to load templates.");
        const json = await res.json();
        if (json.success && json.data) {
          setTemplates(json.data);
        }
      } catch (e) {
        console.error("Error loading sidebar templates:", e);
      }
    };
    fetchTemplates();
  }, []);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const isGeneratorRouteActive = location.pathname.startsWith('/generator');

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
      name: 'HTML Templates',
      path: '/html-templates',
      icon: FileCode,
      roles: ['Admin']
    },
    {
      name: 'Admin Queries Inbox',
      path: '/admin/queries',
      icon: Inbox,
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
    },
    {
      name: 'Inquiry Queries',
      path: '/contact',
      icon: MessageSquare,
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
            
            // Special render for expandable Document Generator
            if (item.name === 'Document Generator') {
              return (
                <div key="generator-menu-container" className="space-y-0.5">
                  <button
                    onClick={() => {
                      if (isCollapsed) {
                        setIsCollapsed(false);
                      }
                      setGeneratorExpanded(!generatorExpanded);
                    }}
                    className={`
                      w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-xs font-semibold tracking-wide transition-all
                      ${isGeneratorRouteActive 
                        ? 'bg-indigo-50/50 text-indigo-700 dark:bg-indigo-600/10 dark:text-indigo-400 font-bold' 
                        : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50 dark:text-zinc-400 dark:hover:text-zinc-100 dark:hover:bg-zinc-900/60'}
                    `}
                  >
                    <div className="flex items-center gap-3">
                      <Icon className="h-4.5 w-4.5 flex-shrink-0" />
                      {!isCollapsed && (
                        <span className="transition-opacity duration-200">{item.name}</span>
                      )}
                    </div>
                    {!isCollapsed && (
                      generatorExpanded ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />
                    )}
                  </button>

                  {/* Submenu links */}
                  {generatorExpanded && !isCollapsed && templates.map(tpl => {
                    const isSubActive = location.pathname === `/generator/${tpl.id}`;
                    return (
                      <NavLink
                        key={tpl.id}
                        to={`/generator/${tpl.id}`}
                        className={`
                          flex items-center gap-2.5 pl-9 pr-3 py-2 rounded-lg text-xs font-medium tracking-wide transition-all
                          ${isSubActive 
                            ? 'text-indigo-700 dark:text-indigo-400 bg-indigo-50/30 dark:bg-indigo-650/5 font-semibold' 
                            : 'text-slate-500 hover:text-slate-900 hover:bg-slate-50/40 dark:text-zinc-450 dark:hover:text-zinc-100 dark:hover:bg-zinc-900/30'}
                        `}
                      >
                        <span className="text-[9px] text-slate-400 dark:text-zinc-600 font-bold">●</span>
                        <span className="truncate">{tpl.name}</span>
                      </NavLink>
                    );
                  })}
                </div>
              );
            }

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
