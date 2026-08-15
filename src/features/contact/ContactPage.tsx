import React, { useState, useEffect, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { 
  Send, 
  User, 
  Mail, 
  Phone, 
  MessageSquare, 
  CheckCircle, 
  Sparkles, 
  Shield, 
  Clock, 
  ShieldCheck, 
  LogIn, 
  Inbox,
  Eye,
  CheckCheck,
  RotateCcw,
  Search,
  FileText
} from 'lucide-react';
import { API_BASE_URL } from '../../config';
import { mockDb } from '../../lib/mockDb';
import { useToast } from '../../components/ui/Toast';
import { useAuth } from '../../context/AuthContext';
import { Badge } from '../../components/ui/Badge';
import { Modal } from '../../components/ui/Modal';
import type { ContactQueryItem } from '../../types';

export const ContactPage: React.FC = () => {
  const { user } = useAuth();
  const { toast } = useToast();
  
  const [activeTab, setActiveTab] = useState<'submit' | 'my_queries'>('submit');
  
  const [formData, setFormData] = useState({
    name: user?.name || '',
    email: user?.email || '',
    phone: '',
    message: ''
  });

  // Sync form data if user context changes
  useEffect(() => {
    if (user) {
      setFormData(prev => ({
        ...prev,
        name: user.name || prev.name,
        email: user.email || prev.email
      }));
    }
  }, [user]);

  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [errors, setErrors] = useState<{ [key: string]: string }>({});

  // User Inquiry Queries state
  const [userQueries, setUserQueries] = useState<ContactQueryItem[]>([]);
  const [fetchingQueries, setFetchingQueries] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedQuery, setSelectedQuery] = useState<ContactQueryItem | null>(null);

  const fetchUserQueries = async () => {
    if (!user) return;
    setFetchingQueries(true);
    try {
      const token = localStorage.getItem('pv_token');
      if (token) {
        const res = await fetch(`${API_BASE_URL}/queries/my`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.ok) {
          const json = await res.json();
          if (json.success && Array.isArray(json.data)) {
            setUserQueries(json.data);
            setFetchingQueries(false);
            return;
          }
        }
      }
    } catch {
      // Ignore API errors and fallback to mockDb
    }
    setUserQueries(mockDb.getUserQueries(user.email));
    setFetchingQueries(false);
  };

  useEffect(() => {
    if (user) {
      fetchUserQueries();
    }
  }, [user]);

  const validate = () => {
    const errs: { [key: string]: string } = {};
    if (!formData.name.trim()) errs.name = 'Full name is required';
    if (!formData.email.trim()) {
      errs.email = 'Email address is required';
    } else if (!/\S+@\S+\.\S+/.test(formData.email)) {
      errs.email = 'Please enter a valid email address';
    }
    if (!formData.phone.trim()) errs.phone = 'Phone number is required';
    if (!formData.message.trim()) {
      errs.message = 'Please enter your message or query';
    } else if (formData.message.trim().length < 5) {
      errs.message = 'Message must be at least 5 characters long';
    }
    setErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate()) return;

    setLoading(true);

    try {
      const response = await fetch(`${API_BASE_URL}/queries`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      });

      if (response.ok) {
        setSubmitted(true);
        toast.success('Your inquiry query has been submitted to the Admin team.', 'Query Submitted');
      } else {
        mockDb.submitQuery(formData.name, formData.email, formData.phone, formData.message);
        setSubmitted(true);
        toast.success('Your inquiry query has been saved successfully.', 'Query Received');
      }
    } catch {
      mockDb.submitQuery(formData.name, formData.email, formData.phone, formData.message);
      setSubmitted(true);
      toast.success('Your inquiry query has been recorded.', 'Query Received');
    } finally {
      setLoading(false);
      fetchUserQueries();
    }
  };

  const handleReset = () => {
    setFormData({ 
      name: user?.name || '', 
      email: user?.email || '', 
      phone: '', 
      message: '' 
    });
    setSubmitted(false);
    setErrors({});
  };

  // Filtered queries for search
  const filteredUserQueries = useMemo(() => {
    const qStr = searchQuery.toLowerCase().trim();
    if (!qStr) return userQueries;
    return userQueries.filter(q => 
      q.message.toLowerCase().includes(qStr) ||
      q.phone.toLowerCase().includes(qStr) ||
      q.status.toLowerCase().includes(qStr)
    );
  }, [userQueries, searchQuery]);

  const recentCount = useMemo(() => userQueries.filter(q => q.status === 'Recent').length, [userQueries]);
  const viewedCount = useMemo(() => userQueries.filter(q => q.status === 'Viewed').length, [userQueries]);

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-zinc-950 transition-colors duration-300">
      {/* Standalone Header for Public Visitors */}
      {!user && (
        <header className="bg-white/80 dark:bg-zinc-900/80 backdrop-blur border-b border-slate-200 dark:border-zinc-800 py-3.5 px-6 sticky top-0 z-10 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="p-1.5 rounded-xl bg-indigo-600 dark:bg-indigo-500 text-white shadow-sm">
              <ShieldCheck className="h-5 w-5" />
            </div>
            <span className="font-bold text-sm text-slate-900 dark:text-zinc-50 tracking-tight">
              PVAI Support Portal
            </span>
          </div>

          <div className="flex items-center gap-3">
            <Link
              to="/login"
              className="flex items-center gap-2 px-3.5 py-1.5 rounded-xl text-xs font-bold text-white bg-indigo-600 hover:bg-indigo-700 dark:bg-indigo-500 dark:hover:bg-indigo-600 transition-colors shadow-sm"
            >
              <LogIn className="h-3.5 w-3.5" />
              <span>Sign In to Portal</span>
            </Link>
          </div>
        </header>
      )}

      <div className="p-4 sm:p-6 lg:p-8 flex flex-col justify-center items-center">
        <div className="max-w-5xl w-full space-y-6">
          
          {/* Header Bar for Logged-In Users */}
          {user && (
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white dark:bg-zinc-900 border border-slate-200 dark:border-zinc-800 rounded-2xl p-6 shadow-sm">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <div className="p-2 rounded-xl bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400">
                    <MessageSquare className="h-5 w-5" />
                  </div>
                  <h1 className="text-xl font-bold text-slate-900 dark:text-zinc-50">
                    User Inquiry Queries
                  </h1>
                </div>
                <p className="text-xs text-slate-500 dark:text-zinc-400">
                  Submit support inquiries directly to Administrators and track your query response statuses.
                </p>
              </div>

              {/* Tab Navigation Controls */}
              <div className="flex items-center gap-2 bg-slate-100 dark:bg-zinc-800/80 p-1 rounded-xl shrink-0">
                <button
                  type="button"
                  onClick={() => setActiveTab('submit')}
                  className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all ${
                    activeTab === 'submit'
                      ? 'bg-white dark:bg-zinc-900 text-indigo-600 dark:text-indigo-400 shadow-sm'
                      : 'text-slate-500 dark:text-zinc-400 hover:text-slate-900 dark:hover:text-zinc-100'
                  }`}
                >
                  <Send className="h-3.5 w-3.5" />
                  <span>Submit Query</span>
                </button>

                <button
                  type="button"
                  onClick={() => {
                    setActiveTab('my_queries');
                    fetchUserQueries();
                  }}
                  className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all ${
                    activeTab === 'my_queries'
                      ? 'bg-white dark:bg-zinc-900 text-indigo-600 dark:text-indigo-400 shadow-sm'
                      : 'text-slate-500 dark:text-zinc-400 hover:text-slate-900 dark:hover:text-zinc-100'
                  }`}
                >
                  <Inbox className="h-3.5 w-3.5" />
                  <span>My Submitted Queries</span>
                  {userQueries.length > 0 && (
                    <span className="ml-1 px-1.5 py-0.2 rounded-full text-[10px] bg-indigo-100 dark:bg-indigo-950 text-indigo-600 dark:text-indigo-400 font-extrabold">
                      {userQueries.length}
                    </span>
                  )}
                </button>
              </div>
            </div>
          )}

          {/* MAIN CONTENT CONTENTION */}

          {/* Tab 1: Submit Form View */}
          {activeTab === 'submit' && (
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
              {/* Left Info Panel */}
              <div className="lg:col-span-5 space-y-6">
                <div>
                  <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-indigo-50 dark:bg-indigo-950/50 text-indigo-600 dark:text-indigo-400 border border-indigo-200 dark:border-indigo-800/50 mb-4">
                    <Sparkles className="h-3.5 w-3.5" />
                    <span>PVAI Assistance Hub</span>
                  </div>
                  <h2 className="text-2xl font-extrabold text-slate-900 dark:text-zinc-50 tracking-tight leading-tight">
                    Get in Touch with Our Admin Team
                  </h2>
                  <p className="text-xs sm:text-sm text-slate-500 dark:text-zinc-400 mt-2 leading-relaxed">
                    Have questions about drug safety report templates, quota limits, custom workflow integrations, or account privileges? Submit your query below.
                  </p>
                </div>

                <div className="space-y-4 pt-2">
                  <div className="flex items-start gap-3.5 p-3.5 rounded-xl bg-white dark:bg-zinc-900 border border-slate-200/80 dark:border-zinc-800 shadow-sm">
                    <div className="p-2 rounded-lg bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400 shrink-0">
                      <Shield className="h-4 w-4" />
                    </div>
                    <div>
                      <h4 className="text-xs font-bold text-slate-900 dark:text-zinc-100">Confidential & Compliant</h4>
                      <p className="text-[11px] text-slate-500 dark:text-zinc-400 mt-0.5 leading-normal">
                        All communications are encrypted and logged with full Pharmacovigilance regulatory compliance.
                      </p>
                    </div>
                  </div>

                  <div className="flex items-start gap-3.5 p-3.5 rounded-xl bg-white dark:bg-zinc-900 border border-slate-200/80 dark:border-zinc-800 shadow-sm">
                    <div className="p-2 rounded-lg bg-emerald-50 dark:bg-emerald-950/60 text-emerald-600 dark:text-emerald-400 shrink-0">
                      <Clock className="h-4 w-4" />
                    </div>
                    <div>
                      <h4 className="text-xs font-bold text-slate-900 dark:text-zinc-100">Real-Time Admin Inbox</h4>
                      <p className="text-[11px] text-slate-500 dark:text-zinc-400 mt-0.5 leading-normal">
                        Administrators track new query submissions directly inside their management console.
                      </p>
                    </div>
                  </div>
                </div>
              </div>

              {/* Right Form Card */}
              <div className="lg:col-span-7 bg-white dark:bg-zinc-900 border border-slate-200 dark:border-zinc-800 rounded-2xl p-6 sm:p-8 shadow-xl shadow-slate-200/50 dark:shadow-none">
                {submitted ? (
                  <div className="py-8 text-center space-y-4">
                    <div className="mx-auto h-14 w-14 rounded-full bg-emerald-50 dark:bg-emerald-950/60 border border-emerald-200 dark:border-emerald-800/50 flex items-center justify-center text-emerald-600 dark:text-emerald-400 animate-bounce">
                      <CheckCircle className="h-7 w-7" />
                    </div>
                    <h3 className="text-lg font-bold text-slate-900 dark:text-zinc-50">Query Submitted Successfully!</h3>
                    <p className="text-xs text-slate-500 dark:text-zinc-400 max-w-md mx-auto leading-relaxed">
                      Thank you, <span className="font-semibold text-slate-900 dark:text-zinc-200">{formData.name}</span>. Your query has been logged and sent to the administrator review queue.
                    </p>
                    <div className="pt-4 flex justify-center gap-3">
                      {user && (
                        <button
                          type="button"
                          onClick={() => {
                            setActiveTab('my_queries');
                            fetchUserQueries();
                          }}
                          className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-xs transition-colors shadow-sm"
                        >
                          View My Queries ({userQueries.length + 1})
                        </button>
                      )}
                      <button
                        type="button"
                        onClick={handleReset}
                        className="px-4 py-2 rounded-lg bg-slate-100 dark:bg-zinc-800 hover:bg-slate-200 dark:hover:bg-zinc-700 text-slate-700 dark:text-zinc-200 font-semibold text-xs transition-colors"
                      >
                        Submit Another Query
                      </button>
                    </div>
                  </div>
                ) : (
                  <form onSubmit={handleSubmit} className="space-y-4">
                    <div>
                      <h3 className="text-lg font-bold text-slate-900 dark:text-zinc-50">Submit Inquiry Form</h3>
                      <p className="text-xs text-slate-500 dark:text-zinc-400 mt-0.5">
                        Fill in your details below to reach our Pharmacovigilance admin team.
                      </p>
                    </div>

                    {/* Name Field */}
                    <div>
                      <label className="block text-xs font-semibold text-slate-700 dark:text-zinc-300 mb-1.5">
                        Full Name <span className="text-rose-500">*</span>
                      </label>
                      <div className="relative">
                        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                          <User className="h-4 w-4" />
                        </div>
                        <input
                          type="text"
                          placeholder="e.g. Dr. Alex Mercer"
                          value={formData.name}
                          onChange={e => setFormData({ ...formData, name: e.target.value })}
                          className={`w-full pl-9 pr-3 py-2 rounded-xl text-xs border ${
                            errors.name 
                              ? 'border-rose-500 focus:ring-rose-500' 
                              : 'border-slate-200 dark:border-zinc-800 focus:border-indigo-500 dark:focus:border-indigo-500'
                          } bg-slate-50/50 dark:bg-zinc-950/50 text-slate-900 dark:text-zinc-50 outline-none transition-all`}
                        />
                      </div>
                      {errors.name && <p className="text-[11px] text-rose-500 mt-1 font-medium">{errors.name}</p>}
                    </div>

                    {/* Email & Phone grid */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      {/* Email Field */}
                      <div>
                        <label className="block text-xs font-semibold text-slate-700 dark:text-zinc-300 mb-1.5">
                          Email Address <span className="text-rose-500">*</span>
                        </label>
                        <div className="relative">
                          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                            <Mail className="h-4 w-4" />
                          </div>
                          <input
                            type="email"
                            placeholder="name@company.com"
                            value={formData.email}
                            onChange={e => setFormData({ ...formData, email: e.target.value })}
                            className={`w-full pl-9 pr-3 py-2 rounded-xl text-xs border ${
                              errors.email 
                                ? 'border-rose-500 focus:ring-rose-500' 
                                : 'border-slate-200 dark:border-zinc-800 focus:border-indigo-500 dark:focus:border-indigo-500'
                            } bg-slate-50/50 dark:bg-zinc-950/50 text-slate-900 dark:text-zinc-50 outline-none transition-all`}
                          />
                        </div>
                        {errors.email && <p className="text-[11px] text-rose-500 mt-1 font-medium">{errors.email}</p>}
                      </div>

                      {/* Phone Field */}
                      <div>
                        <label className="block text-xs font-semibold text-slate-700 dark:text-zinc-300 mb-1.5">
                          Phone Number <span className="text-rose-500">*</span>
                        </label>
                        <div className="relative">
                          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                            <Phone className="h-4 w-4" />
                          </div>
                          <input
                            type="tel"
                            placeholder="+1 (555) 000-0000"
                            value={formData.phone}
                            onChange={e => setFormData({ ...formData, phone: e.target.value })}
                            className={`w-full pl-9 pr-3 py-2 rounded-xl text-xs border ${
                              errors.phone 
                                ? 'border-rose-500 focus:ring-rose-500' 
                                : 'border-slate-200 dark:border-zinc-800 focus:border-indigo-500 dark:focus:border-indigo-500'
                            } bg-slate-50/50 dark:bg-zinc-950/50 text-slate-900 dark:text-zinc-50 outline-none transition-all`}
                          />
                        </div>
                        {errors.phone && <p className="text-[11px] text-rose-500 mt-1 font-medium">{errors.phone}</p>}
                      </div>
                    </div>

                    {/* Message Field */}
                    <div>
                      <label className="block text-xs font-semibold text-slate-700 dark:text-zinc-300 mb-1.5">
                        Message / Query <span className="text-rose-500">*</span>
                      </label>
                      <div className="relative">
                        <div className="absolute top-2.5 left-3 pointer-events-none text-slate-400">
                          <MessageSquare className="h-4 w-4" />
                        </div>
                        <textarea
                          rows={4}
                          placeholder="Enter your message or request details here..."
                          value={formData.message}
                          onChange={e => setFormData({ ...formData, message: e.target.value })}
                          className={`w-full pl-9 pr-3 py-2 rounded-xl text-xs border ${
                            errors.message 
                              ? 'border-rose-500 focus:ring-rose-500' 
                              : 'border-slate-200 dark:border-zinc-800 focus:border-indigo-500 dark:focus:border-indigo-500'
                          } bg-slate-50/50 dark:bg-zinc-950/50 text-slate-900 dark:text-zinc-50 outline-none transition-all resize-none`}
                        />
                      </div>
                      {errors.message && <p className="text-[11px] text-rose-500 mt-1 font-medium">{errors.message}</p>}
                    </div>

                    {/* Submit Button */}
                    <div className="pt-2">
                      <button
                        type="submit"
                        disabled={loading}
                        className="w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl text-xs font-bold text-white bg-indigo-600 hover:bg-indigo-700 dark:bg-indigo-500 dark:hover:bg-indigo-600 shadow-md shadow-indigo-500/20 disabled:opacity-50 transition-all cursor-pointer"
                      >
                        {loading ? (
                          <div className="h-4 w-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                        ) : (
                          <>
                            <Send className="h-4 w-4" />
                            <span>Submit Query Message</span>
                          </>
                        )}
                      </button>
                    </div>
                  </form>
                )}
              </div>
            </div>
          )}

          {/* Tab 2: My Submitted Queries List View */}
          {activeTab === 'my_queries' && user && (
            <div className="space-y-6">
              {/* Quick Metrics Bar */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div className="p-4 rounded-2xl bg-white dark:bg-zinc-900 border border-slate-200 dark:border-zinc-800 flex items-center justify-between">
                  <div>
                    <p className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Total Submitted</p>
                    <p className="text-xl font-extrabold text-slate-900 dark:text-zinc-50 mt-0.5">{userQueries.length}</p>
                  </div>
                  <div className="p-2.5 rounded-xl bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400">
                    <FileText className="h-5 w-5" />
                  </div>
                </div>

                <div className="p-4 rounded-2xl bg-white dark:bg-zinc-900 border border-slate-200 dark:border-zinc-800 flex items-center justify-between">
                  <div>
                    <p className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Recent (Awaiting Review)</p>
                    <p className="text-xl font-extrabold text-amber-600 dark:text-amber-400 mt-0.5">{recentCount}</p>
                  </div>
                  <div className="p-2.5 rounded-xl bg-amber-50 dark:bg-amber-950/60 text-amber-600 dark:text-amber-400">
                    <Clock className="h-5 w-5" />
                  </div>
                </div>

                <div className="p-4 rounded-2xl bg-white dark:bg-zinc-900 border border-slate-200 dark:border-zinc-800 flex items-center justify-between">
                  <div>
                    <p className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Reviewed by Admin</p>
                    <p className="text-xl font-extrabold text-emerald-600 dark:text-emerald-400 mt-0.5">{viewedCount}</p>
                  </div>
                  <div className="p-2.5 rounded-xl bg-emerald-50 dark:bg-emerald-950/60 text-emerald-600 dark:text-emerald-400">
                    <CheckCheck className="h-5 w-5" />
                  </div>
                </div>
              </div>

              {/* Search & Filter Bar */}
              <div className="bg-white dark:bg-zinc-900 border border-slate-200 dark:border-zinc-800 rounded-2xl p-4 flex flex-col sm:flex-row items-center justify-between gap-4">
                <div className="relative w-full sm:w-72">
                  <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
                  <input
                    type="text"
                    placeholder="Search my queries..."
                    value={searchQuery}
                    onChange={e => setSearchQuery(e.target.value)}
                    className="w-full pl-9 pr-3 py-1.5 rounded-xl text-xs border border-slate-200 dark:border-zinc-800 bg-slate-50 dark:bg-zinc-950 text-slate-900 dark:text-zinc-50 outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>

                <button
                  onClick={fetchUserQueries}
                  disabled={fetchingQueries}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold text-slate-600 dark:text-zinc-300 hover:bg-slate-100 dark:hover:bg-zinc-800 transition-colors"
                >
                  <RotateCcw className={`h-3.5 w-3.5 ${fetchingQueries ? 'animate-spin' : ''}`} />
                  <span>Refresh Queries</span>
                </button>
              </div>

              {/* Query Messages List */}
              <div className="bg-white dark:bg-zinc-900 border border-slate-200 dark:border-zinc-800 rounded-2xl overflow-hidden shadow-sm">
                {filteredUserQueries.length === 0 ? (
                  <div className="p-12 text-center space-y-3">
                    <div className="mx-auto h-12 w-12 rounded-full bg-slate-100 dark:bg-zinc-800 flex items-center justify-center text-slate-400">
                      <Inbox className="h-6 w-6" />
                    </div>
                    <h4 className="text-sm font-bold text-slate-900 dark:text-zinc-50">No inquiry queries found</h4>
                    <p className="text-xs text-slate-500 dark:text-zinc-400 max-w-sm mx-auto">
                      {searchQuery ? 'No queries match your search filter.' : 'You have not submitted any inquiry queries yet.'}
                    </p>
                    <div className="pt-2">
                      <button
                        onClick={() => setActiveTab('submit')}
                        className="px-4 py-2 rounded-xl text-xs font-bold text-white bg-indigo-600 hover:bg-indigo-700"
                      >
                        Submit Your First Query
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="divide-y divide-slate-100 dark:divide-zinc-800">
                    {filteredUserQueries.map(item => (
                      <div 
                        key={item.id}
                        className="p-5 hover:bg-slate-50/60 dark:hover:bg-zinc-850/40 transition-colors flex flex-col sm:flex-row sm:items-center justify-between gap-4 cursor-pointer"
                        onClick={() => setSelectedQuery(item)}
                      >
                        <div className="space-y-1 min-w-0 flex-1">
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-bold text-slate-900 dark:text-zinc-100 truncate">
                              Query #{item.id.substring(0, 8)}
                            </span>
                            <Badge variant={item.status === 'Recent' ? 'warning' : 'success'} className="text-[10px]">
                              {item.status === 'Recent' ? 'Recent (Pending Review)' : 'Viewed by Admin'}
                            </Badge>
                          </div>
                          <p className="text-xs text-slate-600 dark:text-zinc-300 line-clamp-2 leading-relaxed">
                            {item.message}
                          </p>
                          <div className="flex items-center gap-3 text-[10px] text-slate-400 dark:text-zinc-500 font-medium pt-1">
                            <span className="flex items-center gap-1">
                              <Phone className="h-3 w-3" />
                              {item.phone}
                            </span>
                            <span>•</span>
                            <span className="flex items-center gap-1">
                              <Clock className="h-3 w-3" />
                              {new Date(item.created_at).toLocaleString()}
                            </span>
                          </div>
                        </div>

                        <div className="flex items-center gap-2 shrink-0">
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              setSelectedQuery(item);
                            }}
                            className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-semibold text-indigo-600 dark:text-indigo-400 bg-indigo-50 dark:bg-indigo-950/60 hover:bg-indigo-100 dark:hover:bg-indigo-900 transition-colors"
                          >
                            <Eye className="h-3.5 w-3.5" />
                            <span>View Details</span>
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

        </div>
      </div>

      {/* Query Details Modal */}
      {selectedQuery && (
        <Modal
          isOpen={!!selectedQuery}
          onClose={() => setSelectedQuery(null)}
          title={`Inquiry Query Details #${selectedQuery.id.substring(0, 8)}`}
        >
          <div className="space-y-4 text-xs">
            <div className="flex items-center justify-between p-3 rounded-xl bg-slate-50 dark:bg-zinc-900 border border-slate-200 dark:border-zinc-800">
              <div>
                <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Status</p>
                <Badge variant={selectedQuery.status === 'Recent' ? 'warning' : 'success'} className="mt-1">
                  {selectedQuery.status === 'Recent' ? 'Recent (Pending Admin Review)' : 'Viewed by Admin'}
                </Badge>
              </div>
              <div className="text-right">
                <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Submitted On</p>
                <p className="font-semibold text-slate-700 dark:text-zinc-300 mt-1">
                  {new Date(selectedQuery.created_at).toLocaleString()}
                </p>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="p-3 rounded-xl bg-slate-50 dark:bg-zinc-900">
                <p className="text-[10px] font-bold text-slate-400 uppercase">Sender Name</p>
                <p className="font-semibold text-slate-800 dark:text-zinc-200 mt-0.5">{selectedQuery.name}</p>
              </div>
              <div className="p-3 rounded-xl bg-slate-50 dark:bg-zinc-900">
                <p className="text-[10px] font-bold text-slate-400 uppercase">Contact Phone</p>
                <p className="font-semibold text-slate-800 dark:text-zinc-200 mt-0.5">{selectedQuery.phone}</p>
              </div>
            </div>

            <div>
              <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1">Message Content</p>
              <div className="p-4 rounded-xl bg-slate-50 dark:bg-zinc-900 border border-slate-200 dark:border-zinc-800 text-slate-800 dark:text-zinc-200 whitespace-pre-wrap leading-relaxed">
                {selectedQuery.message}
              </div>
            </div>

            <div className="pt-2 flex justify-end">
              <button
                type="button"
                onClick={() => setSelectedQuery(null)}
                className="px-4 py-2 rounded-xl text-xs font-bold text-slate-700 dark:text-zinc-300 bg-slate-100 dark:bg-zinc-800 hover:bg-slate-200 dark:hover:bg-zinc-700"
              >
                Close
              </button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
};

export default ContactPage;
