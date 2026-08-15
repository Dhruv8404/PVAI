import React, { useState, useEffect, useRef, useMemo } from 'react';
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
  Inbox,
  MessageSquare,
  ExternalLink,
  CheckCheck,
  RotateCcw,
  Eye,
  Mail,
  Phone,
  Check

} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { useTheme } from '../../context/ThemeContext';
import { Avatar } from '../ui/Avatar';
import { Badge } from '../ui/Badge';
import { Modal } from '../ui/Modal';
import { API_BASE_URL } from '../../config';
import { mockDb } from '../../lib/mockDb';
import type { ContactQueryItem } from '../../types';

interface TopNavProps {
  sidebarCollapsed?: boolean;
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
  const [queriesOpen, setQueriesOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  // Admin Query Notification states
  const [queries, setQueries] = useState<ContactQueryItem[]>([]);
  const [queryTab, setQueryTab] = useState<'Recent' | 'Viewed'>('Recent');
  const [selectedQuery, setSelectedQuery] = useState<ContactQueryItem | null>(null);

  const profileRef = useRef<HTMLDivElement>(null);
  const notifRef = useRef<HTMLDivElement>(null);
  const queriesRef = useRef<HTMLDivElement>(null);

  // Fetch queries from API with fallback to mockDb
  const fetchQueries = async () => {
    try {
      const token = localStorage.getItem('pv_token');
      const headers: Record<string, string> = token ? { 'Authorization': `Bearer ${token}` } : {};
      const res = await fetch(`${API_BASE_URL}/queries`, { headers });
      if (res.ok) {
        const json = await res.json();
        if (json.success && Array.isArray(json.data)) {
          setQueries(json.data);
          return;
        }
      }
    } catch {
      // Ignore API errors and fallback to mockDb
    }
    setQueries(mockDb.getQueries());
  };

  // Smart polling: Only poll if Admin, and pause when tab is hidden
  useEffect(() => {
    if (user?.role !== 'Admin') return;

    fetchQueries();

    let intervalId: ReturnType<typeof setInterval> | null = null;

    const startPolling = () => {
      if (!intervalId) {
        intervalId = setInterval(fetchQueries, 15000);
      }
    };

    const stopPolling = () => {
      if (intervalId) {
        clearInterval(intervalId);
        intervalId = null;
      }
    };

    const handleVisibilityChange = () => {
      if (document.hidden) {
        stopPolling();
      } else {
        fetchQueries();
        startPolling();
      }
    };

    if (!document.hidden) {
      startPolling();
    }

    document.addEventListener('visibilitychange', handleVisibilityChange);

    return () => {
      stopPolling();
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [user?.role]);

  // Click outside to close menus
  useEffect(() => {
    const handleOutsideClick = (e: MouseEvent) => {
      if (profileRef.current && !profileRef.current.contains(e.target as Node)) {
        setProfileOpen(false);
      }
      if (notifRef.current && !notifRef.current.contains(e.target as Node)) {
        setNotifOpen(false);
      }
      if (queriesRef.current && !queriesRef.current.contains(e.target as Node)) {
        setQueriesOpen(false);
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

  // Toggle Query Status between Recent and Viewed
  const handleToggleQueryStatus = async (queryId: string, currentStatus: string) => {
    const nextStatus: 'Recent' | 'Viewed' = currentStatus === 'Recent' ? 'Viewed' : 'Recent';
    
    // Optimistic UI update
    setQueries(prev => prev.map(q => q.id === queryId ? { ...q, status: nextStatus } : q));
    if (selectedQuery && selectedQuery.id === queryId) {
      setSelectedQuery({ ...selectedQuery, status: nextStatus });
    }

    try {
      const token = localStorage.getItem('pv_token');
      const headers: Record<string, string> = { 
        'Content-Type': 'application/json',
        ...(token ? { 'Authorization': `Bearer ${token}` } : {}) 
      };
      await fetch(`${API_BASE_URL}/queries/${queryId}/status`, {
        method: 'PATCH',
        headers,
        body: JSON.stringify({ status: nextStatus })
      });
    } catch {
      // Local fallback
      mockDb.updateQueryStatus(queryId, nextStatus);
    }
  };

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
  const filteredCommands = useMemo(() => {
    const options = [
      { name: 'Dashboard overview', icon: LayoutDashboard, action: () => navigate('/dashboard') },
      { name: 'Users list (Admin)', icon: Users, action: () => navigate('/users'), adminOnly: true },
      { name: 'Generate safety report', icon: FileText, action: () => navigate('/generator') },
      { name: 'View generated history', icon: History, action: () => navigate('/history') },
      { name: 'Submit contact query', icon: MessageSquare, action: () => navigate('/contact') },
      { name: 'Toggle appearance theme', icon: Sparkles, action: () => toggleTheme() },
    ];
    return options.filter(cmd => {
      if (cmd.adminOnly && user?.role !== 'Admin') return false;
      return cmd.name.toLowerCase().includes(searchQuery.toLowerCase());
    });
  }, [user?.role, searchQuery, navigate, toggleTheme]);

  const handleCommandClick = (action: () => void) => {
    action();
    setSearchOpen(false);
    setSearchQuery('');
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const unreadNotifCount = notifications.filter(n => !n.read).length;
  
  // Queries memoized filtering
  const recentQueries = useMemo(() => queries.filter(q => q.status === 'Recent'), [queries]);
  const viewedQueries = useMemo(() => queries.filter(q => q.status === 'Viewed'), [queries]);
  const recentCount = recentQueries.length;
  const viewedCount = viewedQueries.length;

  const currentTabQueries = useMemo(() => queryTab === 'Recent' ? recentQueries : viewedQueries, [queryTab, recentQueries, viewedQueries]);


  return (
    <header className="sticky top-0 z-10 bg-white/80 dark:bg-zinc-950/80 backdrop-blur border-b border-slate-200 dark:border-zinc-900 h-16 flex items-center justify-between px-6">
      {/* Left side: Breadcrumbs and Mobile Menu Toggle */}
      <div className="flex items-center gap-4">
        <button 
          onClick={onMobileMenuToggle} 
          className="md:hidden p-1.5 rounded-lg text-slate-500 hover:bg-slate-100 dark:text-zinc-400 dark:hover:bg-zinc-900"
        >
          <Search className="h-5 w-5" />
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
          title="Toggle Dark / Light Theme"
        >
          {theme === 'light' ? <Moon className="h-4.5 w-4.5" /> : <Sun className="h-4.5 w-4.5" />}
        </button>

        {/* ADMIN QUERIES NOTIFICATION SECTION */}
        <div className="relative" ref={queriesRef}>
          <button
            onClick={() => {
              setQueriesOpen(!queriesOpen);
              setNotifOpen(false);
              setProfileOpen(false);
              fetchQueries();
            }}
            className="p-2 rounded-lg text-slate-500 hover:text-slate-600 dark:text-zinc-400 dark:hover:text-zinc-100 hover:bg-slate-50 dark:hover:bg-zinc-900 transition-colors relative"
            title="User Queries & Inquiry Notifications"
          >
            <Inbox className="h-4.5 w-4.5" />
            {recentCount > 0 && (
              <span className="absolute -top-1 -right-1 flex h-4 min-w-[1rem] items-center justify-center rounded-full bg-indigo-600 px-1 text-[9px] font-bold text-white ring-2 ring-white dark:ring-zinc-950">
                {recentCount}
              </span>
            )}
          </button>

          {queriesOpen && (
            <div className="absolute right-0 mt-2 w-88 sm:w-96 bg-white dark:bg-zinc-900 border border-slate-200 dark:border-zinc-800 rounded-xl shadow-2xl z-30 overflow-hidden">
              {/* Header */}
              <div className="px-4 py-3 border-b border-slate-100 dark:border-zinc-800 bg-slate-50/50 dark:bg-zinc-900/50 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <MessageSquare className="h-4 w-4 text-indigo-600 dark:text-indigo-400" />
                  <span className="text-xs font-bold text-slate-900 dark:text-zinc-50">User Inquiry Queries</span>
                </div>
                <Link
                  to="/contact"
                  onClick={() => setQueriesOpen(false)}
                  className="text-[10px] font-semibold text-indigo-600 dark:text-indigo-400 hover:underline flex items-center gap-1"
                >
                  <span>Form Page</span>
                  <ExternalLink className="h-3 w-3" />
                </Link>
              </div>

              {/* Filter Buttons: Recent & Viewed */}
              <div className="p-2 bg-slate-100/70 dark:bg-zinc-950/60 border-b border-slate-200/80 dark:border-zinc-800/80 grid grid-cols-2 gap-1.5">
                <button
                  type="button"
                  onClick={() => setQueryTab('Recent')}
                  className={`py-1.5 px-3 rounded-lg text-xs font-bold flex items-center justify-center gap-2 transition-all cursor-pointer ${
                    queryTab === 'Recent'
                      ? 'bg-white dark:bg-zinc-800 text-indigo-600 dark:text-indigo-400 shadow-sm border border-slate-200 dark:border-zinc-700'
                      : 'text-slate-600 dark:text-zinc-400 hover:text-slate-900 dark:hover:text-zinc-100'
                  }`}
                >
                  <span>Recent</span>
                  <span className={`text-[10px] px-1.5 py-0.2 rounded-full ${
                    queryTab === 'Recent'
                      ? 'bg-indigo-100 dark:bg-indigo-950 text-indigo-700 dark:text-indigo-300'
                      : 'bg-slate-200 dark:bg-zinc-800 text-slate-600 dark:text-zinc-400'
                  }`}>
                    {recentCount}
                  </span>
                </button>

                <button
                  type="button"
                  onClick={() => setQueryTab('Viewed')}
                  className={`py-1.5 px-3 rounded-lg text-xs font-bold flex items-center justify-center gap-2 transition-all cursor-pointer ${
                    queryTab === 'Viewed'
                      ? 'bg-white dark:bg-zinc-800 text-indigo-600 dark:text-indigo-400 shadow-sm border border-slate-200 dark:border-zinc-700'
                      : 'text-slate-600 dark:text-zinc-400 hover:text-slate-900 dark:hover:text-zinc-100'
                  }`}
                >
                  <span>Viewed</span>
                  <span className={`text-[10px] px-1.5 py-0.2 rounded-full ${
                    queryTab === 'Viewed'
                      ? 'bg-indigo-100 dark:bg-indigo-950 text-indigo-700 dark:text-indigo-300'
                      : 'bg-slate-200 dark:bg-zinc-800 text-slate-600 dark:text-zinc-400'
                  }`}>
                    {viewedCount}
                  </span>
                </button>
              </div>

              {/* Query Messages List */}
              <div className="max-h-72 overflow-y-auto divide-y divide-slate-100 dark:divide-zinc-800">
                {currentTabQueries.length === 0 ? (
                  <div className="p-6 text-center text-xs text-slate-400 dark:text-zinc-500 space-y-1">
                    <p className="font-semibold">No {queryTab.toLowerCase()} queries found.</p>
                    <p className="text-[10px]">
                      {queryTab === 'Recent' 
                        ? 'All user inquiries have been reviewed.' 
                        : 'No messages marked as viewed yet.'}
                    </p>
                  </div>
                ) : (
                  currentTabQueries.map(item => (
                    <div 
                      key={item.id} 
                      className="p-3.5 hover:bg-slate-50/70 dark:hover:bg-zinc-800/40 transition-colors space-y-2 group"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <h4 className="text-xs font-bold text-slate-900 dark:text-zinc-100 flex items-center gap-1.5">
                            <span>{item.name}</span>
                            <Badge variant={item.status === 'Recent' ? 'info' : 'neutral'}>
                              {item.status}
                            </Badge>

                          </h4>
                          <div className="flex flex-wrap items-center gap-x-3 gap-y-0.5 text-[10px] text-slate-400 dark:text-zinc-500 mt-0.5">
                            <span className="flex items-center gap-1">
                              <Mail className="h-3 w-3" />
                              {item.email}
                            </span>
                            <span className="flex items-center gap-1">
                              <Phone className="h-3 w-3" />
                              {item.phone}
                            </span>
                          </div>
                        </div>
                        <span className="text-[9px] text-slate-400 dark:text-zinc-500 shrink-0">
                          {new Date(item.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </span>
                      </div>

                      <p className="text-xs text-slate-600 dark:text-zinc-300 line-clamp-2 leading-relaxed bg-slate-50/80 dark:bg-zinc-950/40 p-2 rounded-lg border border-slate-100 dark:border-zinc-900">
                        {item.message}
                      </p>

                      {/* Action Buttons */}
                      <div className="flex items-center justify-end gap-2 pt-1">
                        <button
                          type="button"
                          onClick={() => setSelectedQuery(item)}
                          className="px-2.5 py-1 rounded-md text-[11px] font-semibold text-slate-600 dark:text-zinc-400 hover:text-slate-900 dark:hover:text-zinc-100 hover:bg-slate-100 dark:hover:bg-zinc-800 transition-colors flex items-center gap-1 cursor-pointer"
                        >
                          <Eye className="h-3 w-3" />
                          <span>View Details</span>
                        </button>

                        <button
                          type="button"
                          onClick={() => handleToggleQueryStatus(item.id, item.status)}
                          className={`px-2.5 py-1 rounded-md text-[11px] font-bold transition-all flex items-center gap-1 cursor-pointer ${
                            item.status === 'Recent'
                              ? 'bg-emerald-50 dark:bg-emerald-950/60 text-emerald-600 dark:text-emerald-400 hover:bg-emerald-100 dark:hover:bg-emerald-900/60 border border-emerald-200 dark:border-emerald-800/50'
                              : 'bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400 hover:bg-indigo-100 dark:hover:bg-indigo-900/60 border border-indigo-200 dark:border-indigo-800/50'
                          }`}
                        >
                          {item.status === 'Recent' ? (
                            <>
                              <CheckCheck className="h-3 w-3" />
                              <span>Mark as Viewed</span>
                            </>
                          ) : (
                            <>
                              <RotateCcw className="h-3 w-3" />
                              <span>Move to Recent</span>
                            </>
                          )}
                        </button>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}
        </div>

        {/* Notifications Dropdown */}
        <div className="relative" ref={notifRef}>
          <button 
            onClick={() => {
              setNotifOpen(!notifOpen);
              setQueriesOpen(false);
              setProfileOpen(false);
            }}
            className="p-2 rounded-lg text-slate-500 hover:text-slate-600 dark:text-zinc-400 dark:hover:text-zinc-100 hover:bg-slate-50 dark:hover:bg-zinc-900 transition-colors relative"
            title="System Notifications & Alerts"
          >
            <Bell className="h-4.5 w-4.5" />
            {unreadNotifCount > 0 && (
              <span className="absolute top-1 right-1 h-2 w-2 rounded-full bg-rose-500 ring-2 ring-white dark:ring-zinc-950" />
            )}
          </button>

          {notifOpen && (
            <div className="absolute right-0 mt-2 w-80 bg-white dark:bg-zinc-900 border border-slate-200 dark:border-zinc-800 rounded-xl shadow-xl z-30 overflow-hidden">
              <div className="px-4 py-3 border-b border-slate-100 dark:border-zinc-800 flex justify-between items-center bg-slate-50/50 dark:bg-zinc-900/50">
                <span className="text-xs font-bold text-slate-900 dark:text-zinc-50">Alerts & Logs</span>
                {unreadNotifCount > 0 && (
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
              setQueriesOpen(false);
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

      {/* Query Detail Modal */}
      {selectedQuery && (
        <Modal
          isOpen={!!selectedQuery}
          onClose={() => setSelectedQuery(null)}
          title="User Query Details"
          size="md"
        >
          <div className="space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-zinc-800">
              <div>
                <h3 className="text-sm font-bold text-slate-900 dark:text-zinc-50">{selectedQuery.name}</h3>
                <p className="text-xs text-slate-400 dark:text-zinc-500 mt-0.5">
                  Submitted on {new Date(selectedQuery.created_at).toLocaleString()}
                </p>
              </div>
              <Badge variant={selectedQuery.status === 'Recent' ? 'info' : 'neutral'}>
                {selectedQuery.status}
              </Badge>

            </div>

            <div className="grid grid-cols-2 gap-3 text-xs">
              <div className="p-2.5 rounded-lg bg-slate-50 dark:bg-zinc-950 border border-slate-100 dark:border-zinc-900">
                <span className="text-[10px] font-semibold text-slate-400 dark:text-zinc-500 block">Email</span>
                <a href={`mailto:${selectedQuery.email}`} className="text-indigo-600 dark:text-indigo-400 font-medium hover:underline flex items-center gap-1.5 mt-0.5">
                  <Mail className="h-3.5 w-3.5" />
                  <span className="truncate">{selectedQuery.email}</span>
                </a>
              </div>

              <div className="p-2.5 rounded-lg bg-slate-50 dark:bg-zinc-950 border border-slate-100 dark:border-zinc-900">
                <span className="text-[10px] font-semibold text-slate-400 dark:text-zinc-500 block">Phone</span>
                <a href={`tel:${selectedQuery.phone}`} className="text-indigo-600 dark:text-indigo-400 font-medium hover:underline flex items-center gap-1.5 mt-0.5">
                  <Phone className="h-3.5 w-3.5" />
                  <span>{selectedQuery.phone}</span>
                </a>
              </div>
            </div>

            <div className="space-y-1.5">
              <span className="text-xs font-semibold text-slate-700 dark:text-zinc-300">Message Content</span>
              <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-zinc-950 border border-slate-200 dark:border-zinc-800 text-xs text-slate-700 dark:text-zinc-300 leading-relaxed whitespace-pre-wrap">
                {selectedQuery.message}
              </div>
            </div>

            <div className="pt-2 flex items-center justify-between">
              <button
                type="button"
                onClick={() => setSelectedQuery(null)}
                className="px-4 py-2 rounded-lg text-xs font-semibold text-slate-600 dark:text-zinc-400 hover:bg-slate-100 dark:hover:bg-zinc-800"
              >
                Close
              </button>

              <button
                type="button"
                onClick={() => handleToggleQueryStatus(selectedQuery.id, selectedQuery.status)}
                className={`px-4 py-2 rounded-lg text-xs font-bold text-white transition-all flex items-center gap-1.5 ${
                  selectedQuery.status === 'Recent'
                    ? 'bg-emerald-600 hover:bg-emerald-700 dark:bg-emerald-500'
                    : 'bg-indigo-600 hover:bg-indigo-700 dark:bg-indigo-500'
                }`}
              >
                {selectedQuery.status === 'Recent' ? (
                  <>
                    <CheckCheck className="h-4 w-4" />
                    <span>Mark as Viewed</span>
                  </>
                ) : (
                  <>
                    <RotateCcw className="h-4 w-4" />
                    <span>Move to Recent</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </Modal>
      )}

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
