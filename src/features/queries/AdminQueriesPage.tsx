import React, { useState, useEffect, useMemo } from 'react';

import { 
  Inbox, 
  MessageSquare, 
  Mail, 
  Phone, 
  CheckCheck, 
  RotateCcw, 
  Eye, 
  Search, 
  Clock, 
  RefreshCw
} from 'lucide-react';

import { API_BASE_URL } from '../../config';
import { mockDb } from '../../lib/mockDb';
import { useToast } from '../../components/ui/Toast';
import { Badge } from '../../components/ui/Badge';
import { Modal } from '../../components/ui/Modal';
import type { ContactQueryItem } from '../../types';

export const AdminQueriesPage: React.FC = () => {
  const { toast } = useToast();
  
  const [queries, setQueries] = useState<ContactQueryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'Recent' | 'Viewed' | 'All'>('Recent');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedQuery, setSelectedQuery] = useState<ContactQueryItem | null>(null);

  const fetchQueries = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('pv_token');
      const headers: Record<string, string> = token ? { 'Authorization': `Bearer ${token}` } : {};
      const res = await fetch(`${API_BASE_URL}/queries`, { headers });
      if (res.ok) {
        const json = await res.json();
        if (json.success && Array.isArray(json.data)) {
          setQueries(json.data);
          setLoading(false);
          return;
        }
      }
    } catch (e) {
      console.error('API Error loading admin queries:', e);
    }
    // Fallback to local mock db
    setQueries(mockDb.getQueries());
    setLoading(false);
  };

  useEffect(() => {
    fetchQueries();
  }, []);

  const handleToggleStatus = async (queryId: string, currentStatus: string) => {
    const nextStatus: 'Recent' | 'Viewed' = currentStatus === 'Recent' ? 'Viewed' : 'Recent';
    
    // Optimistic state update
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
      toast.success(`Query status updated to "${nextStatus}"`, 'Status Updated');
    } catch {
      mockDb.updateQueryStatus(queryId, nextStatus);
      toast.success(`Query status updated to "${nextStatus}"`, 'Status Updated');
    }
  };

  const recentQueries = useMemo(() => queries.filter(q => q.status === 'Recent'), [queries]);
  const viewedQueries = useMemo(() => queries.filter(q => q.status === 'Viewed'), [queries]);

  const filteredQueries = useMemo(() => {
    const qStr = searchQuery.toLowerCase().trim();
    return queries.filter(q => {
      if (activeTab === 'Recent' && q.status !== 'Recent') return false;
      if (activeTab === 'Viewed' && q.status !== 'Viewed') return false;
      if (qStr) {
        return (
          q.name.toLowerCase().includes(qStr) ||
          q.email.toLowerCase().includes(qStr) ||
          q.phone.toLowerCase().includes(qStr) ||
          q.message.toLowerCase().includes(qStr)
        );
      }
      return true;
    });
  }, [queries, activeTab, searchQuery]);


  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white dark:bg-zinc-900 border border-slate-200 dark:border-zinc-800 rounded-2xl p-6 shadow-sm">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <div className="p-2 rounded-xl bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400">
              <Inbox className="h-5 w-5" />
            </div>
            <h1 className="text-xl font-bold text-slate-900 dark:text-zinc-50">
              Contact Queries Management
            </h1>
          </div>
          <p className="text-xs text-slate-500 dark:text-zinc-400 max-w-xl leading-relaxed">
            Review user-submitted inquiry messages, filter by Recent (Unread) vs. Viewed status, and respond to user requests.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={fetchQueries}
            className="flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-semibold text-slate-700 dark:text-zinc-300 bg-slate-100 dark:bg-zinc-800 hover:bg-slate-200 dark:hover:bg-zinc-700 transition-colors cursor-pointer"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Tabs & Search Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        {/* Tab Filters */}
        <div className="flex items-center gap-1.5 p-1.5 bg-slate-200/60 dark:bg-zinc-900/60 rounded-xl border border-slate-200 dark:border-zinc-800/80">
          <button
            onClick={() => setActiveTab('Recent')}
            className={`px-4 py-2 rounded-lg text-xs font-bold transition-all flex items-center gap-2 cursor-pointer ${
              activeTab === 'Recent'
                ? 'bg-white dark:bg-zinc-800 text-indigo-600 dark:text-indigo-400 shadow-sm'
                : 'text-slate-600 dark:text-zinc-400 hover:text-slate-900 dark:hover:text-zinc-100'
            }`}
          >
            <span>Recent</span>
            <span className={`text-[10px] px-2 py-0.5 rounded-full ${
              activeTab === 'Recent'
                ? 'bg-indigo-100 dark:bg-indigo-950 text-indigo-700 dark:text-indigo-300'
                : 'bg-slate-300 dark:bg-zinc-700 text-slate-700 dark:text-zinc-300'
            }`}>
              {recentQueries.length}
            </span>
          </button>

          <button
            onClick={() => setActiveTab('Viewed')}
            className={`px-4 py-2 rounded-lg text-xs font-bold transition-all flex items-center gap-2 cursor-pointer ${
              activeTab === 'Viewed'
                ? 'bg-white dark:bg-zinc-800 text-indigo-600 dark:text-indigo-400 shadow-sm'
                : 'text-slate-600 dark:text-zinc-400 hover:text-slate-900 dark:hover:text-zinc-100'
            }`}
          >
            <span>Viewed</span>
            <span className={`text-[10px] px-2 py-0.5 rounded-full ${
              activeTab === 'Viewed'
                ? 'bg-indigo-100 dark:bg-indigo-950 text-indigo-700 dark:text-indigo-300'
                : 'bg-slate-300 dark:bg-zinc-700 text-slate-700 dark:text-zinc-300'
            }`}>
              {viewedQueries.length}
            </span>
          </button>

          <button
            onClick={() => setActiveTab('All')}
            className={`px-4 py-2 rounded-lg text-xs font-bold transition-all flex items-center gap-2 cursor-pointer ${
              activeTab === 'All'
                ? 'bg-white dark:bg-zinc-800 text-indigo-600 dark:text-indigo-400 shadow-sm'
                : 'text-slate-600 dark:text-zinc-400 hover:text-slate-900 dark:hover:text-zinc-100'
            }`}
          >
            <span>All Messages</span>
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-300 dark:bg-zinc-700 text-slate-700 dark:text-zinc-300">
              {queries.length}
            </span>
          </button>
        </div>

        {/* Search input */}
        <div className="relative min-w-[240px]">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
            <Search className="h-4 w-4" />
          </div>
          <input
            type="text"
            placeholder="Search by name, email, phone..."
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-3 py-2 rounded-xl text-xs border border-slate-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 text-slate-900 dark:text-zinc-50 outline-none focus:ring-2 focus:ring-indigo-500 transition-all"
          />
        </div>
      </div>

      {/* Queries List / Cards Grid */}
      {loading ? (
        <div className="py-12 flex flex-col items-center justify-center gap-3">
          <div className="h-8 w-8 rounded-full border-4 border-t-indigo-600 border-r-transparent border-b-transparent border-l-transparent animate-spin" />
          <span className="text-xs font-semibold text-slate-500 dark:text-zinc-400">Loading inquiry queries...</span>
        </div>
      ) : filteredQueries.length === 0 ? (
        <div className="p-12 text-center bg-white dark:bg-zinc-900 border border-slate-200 dark:border-zinc-800 rounded-2xl space-y-3">
          <div className="mx-auto h-12 w-12 rounded-full bg-slate-100 dark:bg-zinc-800 flex items-center justify-center text-slate-400">
            <MessageSquare className="h-6 w-6" />
          </div>
          <h3 className="text-sm font-bold text-slate-900 dark:text-zinc-50">No Queries Found</h3>
          <p className="text-xs text-slate-500 dark:text-zinc-400 max-w-sm mx-auto">
            {searchQuery 
              ? `No messages matched "${searchQuery}".` 
              : activeTab === 'Recent' 
                ? 'Great job! There are no unread recent query messages.' 
                : 'No messages under this filter.'}
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {filteredQueries.map(q => (
            <div
              key={q.id}
              className="bg-white dark:bg-zinc-900 border border-slate-200 dark:border-zinc-800 rounded-2xl p-5 shadow-sm hover:shadow-md transition-all flex flex-col justify-between gap-4"
            >
              <div className="space-y-3">
                {/* Header info */}
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2.5">
                    <div className="h-9 w-9 rounded-full bg-indigo-50 dark:bg-indigo-950/60 border border-indigo-200 dark:border-indigo-800/50 flex items-center justify-center text-indigo-600 dark:text-indigo-400 font-bold text-xs">
                      {q.name.charAt(0).toUpperCase()}
                    </div>
                    <div>
                      <h3 className="text-sm font-bold text-slate-900 dark:text-zinc-50">{q.name}</h3>
                      <div className="flex items-center gap-3 text-[11px] text-slate-500 dark:text-zinc-400 mt-0.5">
                        <span className="flex items-center gap-1">
                          <Mail className="h-3 w-3 text-slate-400" />
                          {q.email}
                        </span>
                        <span className="flex items-center gap-1">
                          <Phone className="h-3 w-3 text-slate-400" />
                          {q.phone}
                        </span>
                      </div>
                    </div>
                  </div>

                  <Badge variant={q.status === 'Recent' ? 'info' : 'neutral'}>
                    {q.status}
                  </Badge>
                </div>

                {/* Message preview */}
                <div className="p-3.5 rounded-xl bg-slate-50/80 dark:bg-zinc-950/50 border border-slate-100 dark:border-zinc-900">
                  <p className="text-xs text-slate-700 dark:text-zinc-300 leading-relaxed whitespace-pre-wrap">
                    {q.message}
                  </p>
                </div>
              </div>

              {/* Footer action bar */}
              <div className="pt-3 border-t border-slate-100 dark:border-zinc-800/80 flex items-center justify-between">
                <span className="text-[10px] font-medium text-slate-400 dark:text-zinc-500 flex items-center gap-1">
                  <Clock className="h-3 w-3" />
                  {new Date(q.created_at).toLocaleString()}
                </span>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setSelectedQuery(q)}
                    className="px-3 py-1.5 rounded-lg text-xs font-semibold text-slate-700 dark:text-zinc-300 hover:bg-slate-100 dark:hover:bg-zinc-800 transition-colors flex items-center gap-1.5 cursor-pointer"
                  >
                    <Eye className="h-3.5 w-3.5" />
                    <span>View Details</span>
                  </button>

                  <button
                    onClick={() => handleToggleStatus(q.id, q.status)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all flex items-center gap-1.5 cursor-pointer ${
                      q.status === 'Recent'
                        ? 'bg-emerald-600 hover:bg-emerald-700 text-white shadow-sm'
                        : 'bg-indigo-600 hover:bg-indigo-700 text-white shadow-sm'
                    }`}
                  >
                    {q.status === 'Recent' ? (
                      <>
                        <CheckCheck className="h-3.5 w-3.5" />
                        <span>Mark as Viewed</span>
                      </>
                    ) : (
                      <>
                        <RotateCcw className="h-3.5 w-3.5" />
                        <span>Move to Recent</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Query Detail Modal */}
      {selectedQuery && (
        <Modal
          isOpen={!!selectedQuery}
          onClose={() => setSelectedQuery(null)}
          title="Contact Query Full Details"
          size="md"
        >
          <div className="space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-zinc-800">
              <div>
                <h3 className="text-base font-bold text-slate-900 dark:text-zinc-50">{selectedQuery.name}</h3>
                <p className="text-xs text-slate-400 dark:text-zinc-500 mt-0.5">
                  Submitted on {new Date(selectedQuery.created_at).toLocaleString()}
                </p>
              </div>
              <Badge variant={selectedQuery.status === 'Recent' ? 'info' : 'neutral'}>
                {selectedQuery.status}
              </Badge>
            </div>

            <div className="grid grid-cols-2 gap-3 text-xs">
              <div className="p-3 rounded-xl bg-slate-50 dark:bg-zinc-950 border border-slate-200 dark:border-zinc-800">
                <span className="text-[10px] font-semibold text-slate-400 dark:text-zinc-500 block">Email Address</span>
                <a href={`mailto:${selectedQuery.email}`} className="text-indigo-600 dark:text-indigo-400 font-bold hover:underline flex items-center gap-1.5 mt-1">
                  <Mail className="h-3.5 w-3.5" />
                  <span className="truncate">{selectedQuery.email}</span>
                </a>
              </div>

              <div className="p-3 rounded-xl bg-slate-50 dark:bg-zinc-950 border border-slate-200 dark:border-zinc-800">
                <span className="text-[10px] font-semibold text-slate-400 dark:text-zinc-500 block">Phone Number</span>
                <a href={`tel:${selectedQuery.phone}`} className="text-indigo-600 dark:text-indigo-400 font-bold hover:underline flex items-center gap-1.5 mt-1">
                  <Phone className="h-3.5 w-3.5" />
                  <span>{selectedQuery.phone}</span>
                </a>
              </div>
            </div>

            <div className="space-y-1.5">
              <span className="text-xs font-semibold text-slate-700 dark:text-zinc-300">Message / Query Body</span>
              <div className="p-4 rounded-xl bg-slate-50 dark:bg-zinc-950 border border-slate-200 dark:border-zinc-800 text-xs text-slate-800 dark:text-zinc-200 leading-relaxed whitespace-pre-wrap">
                {selectedQuery.message}
              </div>
            </div>

            <div className="pt-3 flex items-center justify-between">
              <button
                type="button"
                onClick={() => setSelectedQuery(null)}
                className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-600 dark:text-zinc-400 hover:bg-slate-100 dark:hover:bg-zinc-800 transition-colors"
              >
                Close Window
              </button>

              <button
                type="button"
                onClick={() => handleToggleStatus(selectedQuery.id, selectedQuery.status)}
                className={`px-4 py-2 rounded-xl text-xs font-bold text-white transition-all flex items-center gap-1.5 ${
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
    </div>
  );
};

export default AdminQueriesPage;
