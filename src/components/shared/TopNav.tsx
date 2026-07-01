import React, { useState, useEffect, useRef } from 'react';
import { useLocation, Link, useNavigate } from 'react-router-dom';
import { 
  Bell, 
  Search, 
  Sun, 
  Moon, 
  ChevronRight, 
  User as UserIcon,
  LogOut,
  Sparkles,
  Command,
  LayoutDashboard,
  Users,
  FileText,
  History,
  Check
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { useTheme } from '../../context/ThemeContext';
import { Avatar } from '../ui/Avatar';
import { Badge } from '../ui/Badge';
import { Modal } from '../ui/Modal';
interface TopNavProps {
  sidebarCollapsed: boolean;
  onMobileMenuToggle: () => void;
}

export const TopNav: React.FC<TopNavProps> = ({ sidebarCollapsed: _sidebarCollapsed, onMobileMenuToggle }) => {
  const { user, logout, notifications, clearNotifications } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const location = useLocation();
  const navigate = useNavigate();

  // Menu states
  const [profileOpen, setProfileOpen] = useState(false);
  const [notifOpen, setNotifOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  const profileRef = useRef<HTMLDivElement>(null);
  const notifRef = useRef<HTMLDivElement>(null);

  // Click outside to close menus
  useEffect(() => {
    const handleOutsideClick = (e: MouseEvent) => {
      if (profileRef.current && !profileRef.current.contains(e.target as Node)) {
        setProfileOpen(false);
      }
      if (notifRef.current && !notifRef.current.contains(e.target as Node)) {
        setNotifOpen(false);
      }
    };
    document.addEventListener('mousedown', handleOutsideClick);
    return () => document.removeEventListener('mousedown', handleOutsideClick);
  }, []);

  // Keyboard listener for command palette (Ctrl+K)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        setSearchOpen(true);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Breadcrumbs logic
  const getBreadcrumbs = () => {
    const pathnames = location.pathname.split('/').filter(x => x);
    return (
      <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-500 dark:text-zinc-400">
        <Link to="/dashboard" className="hover:text-slate-900 dark:hover:text-zinc-100 transition-colors">
          Portal
        </Link>
        {pathnames.map((name, index) => {
          const routeTo = `/${pathnames.slice(0, index + 1).join('/')}`;
          const isLast = index === pathnames.length - 1;
          const displayLabel = name.charAt(0).toUpperCase() + name.slice(1).replace('-', ' ');

          return (
            <React.Fragment key={name}>
              <ChevronRight className="h-3 w-3 text-slate-300 dark:text-zinc-700" />
              {isLast ? (
                <span className="text-slate-900 dark:text-zinc-50 font-bold">
                  {displayLabel}
                </span>
              ) : (
                <Link to={routeTo} className="hover:text-slate-900 dark:hover:text-zinc-100 transition-colors">
                  {displayLabel}
                </Link>
              )}
            </React.Fragment>
          );
        })}
      </div>
    );
  };

  // Command palette filter
  const commandPaletteOptions = [
    { name: 'Dashboard overview', icon: LayoutDashboard, action: () => navigate('/dashboard') },
    { name: 'Users list (Admin)', icon: Users, action: () => navigate('/users'), adminOnly: true },
    { name: 'Generate safety report', icon: FileText, action: () => navigate('/generator') },
    { name: 'View generated history', icon: History, action: () => navigate('/history') },
    { name: 'Toggle appearance theme', icon: Sparkles, action: () => toggleTheme() },
  ];

  const filteredCommands = commandPaletteOptions.filter(cmd => {
    if (cmd.adminOnly && user?.role !== 'Admin') return false;
    return cmd.name.toLowerCase().includes(searchQuery.toLowerCase());
  });

  const handleCommandClick = (action: () => void) => {
    action();
    setSearchOpen(false);
    setSearchQuery('');
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const unreadCount = notifications.filter(n => !n.read).length;

  return (
    <header className="sticky top-0 z-10 bg-white/80 dark:bg-zinc-950/80 backdrop-blur border-b border-slate-200 dark:border-zinc-900 h-16 flex items-center justify-between px-6">
      {/* Left side: Breadcrumbs and Mobile Menu Toggle */}
      <div className="flex items-center gap-4">
        <button 
          onClick={onMobileMenuToggle} 
          className="md:hidden p-1.5 rounded-lg text-slate-500 hover:bg-slate-100 dark:text-zinc-400 dark:hover:bg-zinc-900"
        >
          <Search className="h-5 w-5" /> {/* Use search or menu */}
        </button>
        <div className="hidden md:block">
          {getBreadcrumbs()}
        </div>
      </div>

      {/* Right side: Global controls */}
      <div className="flex items-center gap-3">
        {/* Search Trigger */}
        <button 
          onClick={() => setSearchOpen(true)}
          className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-slate-200 dark:border-zinc-800 text-xs text-slate-400 hover:text-slate-600 hover:border-slate-300 dark:hover:border-zinc-700 bg-slate-50/50 dark:bg-zinc-900/50 transition-all cursor-pointer"
        >
          <Search className="h-3.5 w-3.5" />
          <span>Quick search...</span>
          <kbd className="hidden sm:inline-flex items-center gap-0.5 border border-slate-200 dark:border-zinc-700 bg-white dark:bg-zinc-800 rounded px-1 text-[9px] font-mono leading-none">
            <Command className="h-2 w-2" />
            <span>K</span>
          </kbd>
        </button>

        {/* Theme Toggle */}
        <button 
          onClick={toggleTheme}
          className="p-2 rounded-lg text-slate-500 hover:text-slate-600 dark:text-zinc-400 dark:hover:text-zinc-100 hover:bg-slate-50 dark:hover:bg-zinc-900 transition-colors"
        >
          {theme === 'light' ? <Moon className="h-4.5 w-4.5" /> : <Sun className="h-4.5 w-4.5" />}
        </button>

        {/* Notifications Dropdown */}
        <div className="relative" ref={notifRef}>
          <button 
            onClick={() => {
              setNotifOpen(!notifOpen);
              setProfileOpen(false);
            }}
            className="p-2 rounded-lg text-slate-500 hover:text-slate-600 dark:text-zinc-400 dark:hover:text-zinc-100 hover:bg-slate-50 dark:hover:bg-zinc-900 transition-colors relative"
          >
            <Bell className="h-4.5 w-4.5" />
            {unreadCount > 0 && (
              <span className="absolute top-1 right-1 h-2 w-2 rounded-full bg-rose-500 ring-2 ring-white dark:ring-zinc-950" />
            )}
          </button>

          {notifOpen && (
            <div className="absolute right-0 mt-2 w-80 bg-white dark:bg-zinc-900 border border-slate-200 dark:border-zinc-800 rounded-xl shadow-xl z-30 overflow-hidden">
              <div className="px-4 py-3 border-b border-slate-100 dark:border-zinc-800 flex justify-between items-center bg-slate-50/50 dark:bg-zinc-900/50">
                <span className="text-xs font-bold text-slate-900 dark:text-zinc-50">Alerts & Logs</span>
                {unreadCount > 0 && (
                  <button 
                    onClick={clearNotifications}
                    className="text-[10px] font-semibold text-indigo-600 dark:text-indigo-400 hover:underline"
                  >
                    Clear all
                  </button>
                )}
              </div>
              <div className="max-h-60 overflow-y-auto divide-y divide-slate-100 dark:divide-zinc-800">
                {notifications.length === 0 ? (
                  <div className="p-4 text-center text-xs text-slate-400">
                    No new alerts.
                  </div>
                ) : (
                  notifications.map(n => (
                    <div key={n.id} className="p-3 hover:bg-slate-50/50 dark:hover:bg-zinc-800/40 transition-colors flex gap-2">
                      <div className="mt-0.5">
                        <div className={`h-1.5 w-1.5 rounded-full ${n.read ? 'bg-transparent' : 'bg-indigo-600 dark:bg-indigo-400'}`} />
                      </div>
                      <div className="flex-1">
                        <p className="text-xs text-slate-600 dark:text-zinc-300 leading-normal">
                          {n.message}
                        </p>
                        <span className="text-[9px] text-slate-400 dark:text-zinc-500 mt-1 block">
                          {new Date(n.timestamp).toLocaleTimeString()}
                        </span>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}
        </div>

        {/* User Profile Dropdown */}
        <div className="relative border-l border-slate-200 dark:border-zinc-800 pl-3" ref={profileRef}>
          <button 
            onClick={() => {
              setProfileOpen(!profileOpen);
              setNotifOpen(false);
            }}
            className="flex items-center gap-2 hover:opacity-90 transition-opacity"
          >
            <Avatar src={user?.avatarUrl} name={user?.name || 'User'} size="sm" />
            <div className="hidden lg:block text-left">
              <p className="text-xs font-semibold text-slate-900 dark:text-zinc-50 leading-tight">
                {user?.name}
              </p>
              <p className="text-[10px] text-slate-400 dark:text-zinc-500 font-medium">
                {user?.role}
              </p>
            </div>
          </button>

          {profileOpen && (
            <div className="absolute right-0 mt-2 w-56 bg-white dark:bg-zinc-900 border border-slate-200 dark:border-zinc-800 rounded-xl shadow-xl z-30 overflow-hidden">
              <div className="px-4 py-3 bg-slate-50/50 dark:bg-zinc-900/50 border-b border-slate-100 dark:border-zinc-800 text-left">
                <p className="text-xs font-semibold text-slate-900 dark:text-zinc-50 truncate">{user?.name}</p>
                <p className="text-[10px] text-slate-400 dark:text-zinc-500 font-medium truncate mt-0.5">{user?.email}</p>
                <div className="mt-2">
                  <Badge variant={user?.role === 'Admin' ? 'info' : 'success'}>
                    {user?.role} Account
                  </Badge>
                </div>
              </div>
              <div className="p-1.5 divide-y divide-slate-100 dark:divide-zinc-800">
                <div className="py-1">
                  <button 
                    onClick={() => { setProfileOpen(false); navigate('/dashboard'); }}
                    className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-xs font-semibold text-slate-700 dark:text-zinc-300 hover:bg-slate-50 dark:hover:bg-zinc-800 transition-colors"
                  >
                    <UserIcon className="h-4 w-4" />
                    <span>My Dashboard</span>
                  </button>
                </div>
                <div className="py-1">
                  <button 
                    onClick={handleLogout}
                    className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-xs font-semibold text-rose-600 dark:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-950/20 transition-colors"
                  >
                    <LogOut className="h-4 w-4" />
                    <span>Logout Session</span>
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Ctrl+K Command Palette Modal */}
      <Modal isOpen={searchOpen} onClose={() => setSearchOpen(false)} title="Command Palette" size="md">
        <div className="flex flex-col gap-3">
          {/* Search box input */}
          <div className="flex items-center gap-2.5 px-3 py-2 rounded-lg border border-slate-200 dark:border-zinc-800 bg-slate-50/50 dark:bg-zinc-950/50 focus-within:ring-2 focus-within:ring-indigo-500 transition-all">
            <Search className="h-4.5 w-4.5 text-slate-400" />
            <input
              type="text"
              placeholder="Search actions, pages, commands..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              className="bg-transparent text-xs text-slate-900 dark:text-zinc-50 border-none outline-none w-full placeholder-slate-400"
              autoFocus
            />
            <span className="text-[10px] font-mono text-slate-400 bg-white dark:bg-zinc-800 border border-slate-200 dark:border-zinc-700 px-1 py-0.5 rounded shadow-sm">ESC</span>
          </div>

          {/* Commands List */}
          <div className="mt-1 flex flex-col gap-1 max-h-60 overflow-y-auto">
            <span className="text-[10px] font-bold text-slate-400 dark:text-zinc-500 uppercase tracking-wider px-2 py-1">Quick Links</span>
            {filteredCommands.length === 0 ? (
              <div className="p-4 text-center text-xs text-slate-400">
                No matching actions found.
              </div>
            ) : (
              filteredCommands.map((cmd, idx) => {
                const Icon = cmd.icon;
                return (
                  <button
                    key={idx}
                    onClick={() => handleCommandClick(cmd.action)}
                    className="w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-xs font-semibold text-slate-700 dark:text-zinc-300 hover:bg-slate-50 dark:hover:bg-zinc-800/80 transition-colors text-left"
                  >
                    <div className="flex items-center gap-3">
                      <Icon className="h-4 w-4 text-slate-400" />
                      <span>{cmd.name}</span>
                    </div>
                    <Check className="h-3.5 w-3.5 text-indigo-500 opacity-0 hover:opacity-100 transition-opacity" />
                  </button>
                );
              })
            )}
          </div>
        </div>
      </Modal>
    </header>
  );
};
export default TopNav;
