import React, { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '../../lib/resolver';
import * as z from 'zod';
import { 
  Plus, 
  Search, 
  SlidersHorizontal, 
  ChevronLeft, 
  ChevronRight, 
  Edit2, 
  Trash2, 
  UserMinus, 
  UserCheck, 
  Key, 
  Eye, 
  FileDown, 
  CheckSquare, 
  Square,
  AlertTriangle,
  X,
  FileText,
  Users
} from 'lucide-react';
import type { User, DocumentTemplate, GeneratedDocument } from '../../types';
import { Button } from '../../components/ui/Button';
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import { Avatar } from '../../components/ui/Avatar';
import { Modal } from '../../components/ui/Modal';
import { Drawer } from '../../components/ui/Drawer';
import { useToast } from '../../components/ui/Toast';
import { API_BASE_URL } from '../../config';
import { ConfirmDialog } from '../../components/shared/ConfirmDialog';

const userSchema = z.object({
  name: z.string().min(2, 'Name must be at least 2 characters'),
  email: z.string().min(1, 'Email is required').email('Must be a valid email'),
  role: z.enum(['Admin', 'User']),
  status: z.enum(['Active', 'Inactive']),
  reportLimit: z.coerce.number().min(1, 'Limit must be at least 1').default(5),
  allowedTemplates: z.array(z.string()).default([])
});

type UserFormData = z.infer<typeof userSchema>;

export const UsersPage: React.FC = () => {
  const { toast } = useToast();
  const [users, setUsers] = useState<User[]>([]);
  const [templates, setTemplates] = useState<DocumentTemplate[]>([]);
  const [documents, setDocuments] = useState<GeneratedDocument[]>([]);
  const [loading, setLoading] = useState(false);

  // Search & Filter state
  const [searchQuery, setSearchQuery] = useState('');
  const [roleFilter, setRoleFilter] = useState<'All' | 'Admin' | 'User'>('All');
  const [statusFilter, setStatusFilter] = useState<'All' | 'Active' | 'Inactive'>('All');
  const [showFilters, setShowFilters] = useState(false);

  // Sorting
  const [sortBy, setSortBy] = useState<'name' | 'email' | 'created' | 'docs'>('name');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc');

  // Pagination
  const [currentPage, setCurrentPage] = useState(1);
  const [rowsPerPage, setRowsPerPage] = useState(5);

  // Selection
  const [selectedUserIds, setSelectedUserIds] = useState<string[]>([]);

  // Modals & Drawers
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [profileUser, setProfileUser] = useState<User | null>(null);
  
  // Confirms
  const [confirmAction, setConfirmAction] = useState<{
    isOpen: boolean;
    type: 'delete' | 'deactivate' | 'activate' | 'bulk-delete' | 'bulk-deactivate';
    userIds: string[];
    title: string;
    message: string;
  }>({
    isOpen: false,
    type: 'deactivate',
    userIds: [],
    title: '',
    message: ''
  });

  // Password reset success modal
  const [resetSuccess, setResetSuccess] = useState<{
    isOpen: boolean;
    pwdStr: string;
    userName: string;
  }>({
    isOpen: false,
    pwdStr: '',
    userName: ''
  });

  const { register, handleSubmit, reset, formState: { errors } } = useForm<UserFormData>({
    resolver: zodResolver(userSchema),
    defaultValues: {
      name: '',
      email: '',
      role: 'User',
      status: 'Active',
      reportLimit: 5,
      allowedTemplates: ['psur']
    }
  });

  const loadData = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('pv_token');
      if (!token) throw new Error('No auth session token found');

      // Fetch Users
      const usersRes = await fetch(`${API_BASE_URL}/users?limit=100`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const usersJson = await usersRes.json();

      // Fetch Templates
      const templatesRes = await fetch(`${API_BASE_URL}/templates`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const templatesJson = await templatesRes.json();

      // Fetch Documents
      const docsRes = await fetch(`${API_BASE_URL}/documents/history`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const docsJson = await docsRes.json();

      if (usersJson.success && usersJson.data && templatesJson.success && templatesJson.data) {
        // Build template lookup list
        const rawTemplates = templatesJson.data;
        const mappedTemplates = rawTemplates.map((t: any) => {
          const idLower = t.name.toLowerCase();
          const localId = idLower.includes('psur') ? 'psur' : idLower.includes('quant') ? 'quant' : 'pv_auto';
          return {
            id: localId,
            realUuid: t.id,
            name: t.name,
            description: t.description,
            supportedFileTypes: localId === 'psur' ? ['.xlsx', '.xls'] : localId === 'quant' ? ['.xlsx', '.csv'] : ['.xlsx'],
            lastUpdated: t.updated_at,
            icon: localId === 'psur' ? 'FileText' : localId === 'quant' ? 'BarChart3' : 'Activity',
            requiredColumns: t.required_files
          };
        });
        setTemplates(mappedTemplates);

        // Map users
        const mappedUsers = usersJson.data.map((u: any) => ({
          id: u.id,
          name: u.name,
          email: u.email,
          role: u.roles[0]?.name || 'User',
          status: u.status,
          createdDate: u.created_at,
          lastLogin: u.last_login || 'Never',
          documentsGenerated: u.documents_generated,
          reportLimit: u.report_limit || 5,
          allowedTemplates: u.allowed_templates?.map((at: any) => {
            const nameLower = at.name.toLowerCase();
            return nameLower.includes('psur') ? 'psur' : nameLower.includes('quant') ? 'quant' : 'pv_auto';
          }) || []
        }));
        setUsers(mappedUsers);

        if (docsJson.success && docsJson.data) {
          const mappedDocs = docsJson.data.map((d: any) => ({
            id: d.id,
            name: d.name,
            templateId: d.template_id,
            templateName: d.template_name || 'Report template',
            createdBy: d.created_by_name || 'System User',
            createdById: d.user_id,
            generatedTime: d.created_at,
            downloaded: false,
            status: d.status,
            version: '1.0.0',
            excelFileName: d.excel_file_name,
            htmlContent: ''
          }));
          setDocuments(mappedDocs);
        }

        setLoading(false);
        return;
      }
    } catch (err: any) {
      console.error('API error in user directory loader:', err.message);
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  // Form Submit (Create or Edit User)
  const onSubmit = async (data: UserFormData) => {
    try {
      const token = localStorage.getItem('pv_token');
      if (token) {
        // Map templates ID keys ('psur', etc.) back to database templates UUIDs
        const allowedUuids: string[] = [];
        data.allowedTemplates.forEach(localId => {
          const matched = templates.find(t => t.id === localId);
          if (matched && (matched as any).realUuid) {
            allowedUuids.push((matched as any).realUuid);
          }
        });

        const bodyPayload = {
          email: data.email,
          name: data.name,
          role: data.role,
          status: data.status,
          report_limit: data.reportLimit,
          allowed_templates: allowedUuids
        };

        if (editingUser) {
          const res = await fetch(`${API_BASE_URL}/users/${editingUser.id}`, {
            method: 'PUT',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify(bodyPayload)
          });
          const json = await res.json();
          if (json.success) {
            toast.success(`User settings for ${data.name} saved.`, 'User Settings Saved');
            setIsFormOpen(false);
            setEditingUser(null);
            reset();
            loadData();
            return;
          }
        } else {
          // Send creation POST request (Default pwd: Password123!)
          const res = await fetch(`${API_BASE_URL}/users`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
              ...bodyPayload,
              password: 'Password123!'
            })
          });
          const json = await res.json();
          if (json.success) {
            toast.success(`Platform account initialized for ${data.name}. Default Password: Password123!`, 'Account Generated');
            setIsFormOpen(false);
            setEditingUser(null);
            reset();
            loadData();
            return;
          }
        }
      }
    } catch (err: any) {
      toast.error(err.message || 'Failed to save user settings in database');
    }
  };

  // Sorting handlers
  const handleSort = (field: 'name' | 'email' | 'created' | 'docs') => {
    if (sortBy === field) {
      setSortOrder(prev => (prev === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortBy(field);
      setSortOrder('asc');
    }
  };

  // Selection toggle
  const toggleSelectAll = () => {
    if (selectedUserIds.length === filteredUsers.length) {
      setSelectedUserIds([]);
    } else {
      setSelectedUserIds(filteredUsers.map(u => u.id));
    }
  };

  const toggleSelectUser = (id: string) => {
    setSelectedUserIds(prev =>
      prev.includes(id) ? prev.filter(uid => uid !== id) : [...prev, id]
    );
  };

  // Confirmation Trigger
  const triggerConfirm = (
    type: 'delete' | 'deactivate' | 'activate' | 'bulk-delete' | 'bulk-deactivate',
    userIds: string[],
    title: string,
    message: string
  ) => {
    setConfirmAction({
      isOpen: true,
      type,
      userIds,
      title,
      message
    });
  };

  // Execute Confirmed Operations
  const handleExecuteAction = async () => {
    const { type, userIds } = confirmAction;
    try {
      const token = localStorage.getItem('pv_token');
      if (token) {
        if (type === 'delete') {
          const res = await fetch(`${API_BASE_URL}/users/${userIds[0]}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` }
          });
          const json = await res.json();
          if (json.success) {
            toast.success('User account erased from system directory.', 'Account Deleted');
            setConfirmAction(prev => ({ ...prev, isOpen: false }));
            loadData();
            return;
          }
        } else if (type === 'deactivate') {
          const res = await fetch(`${API_BASE_URL}/users/${userIds[0]}/deactivate`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` }
          });
          const json = await res.json();
          if (json.success) {
            toast.success(`Deactivated user account.`, 'User Suspended');
            setConfirmAction(prev => ({ ...prev, isOpen: false }));
            loadData();
            return;
          }
        } else if (type === 'activate') {
          const res = await fetch(`${API_BASE_URL}/users/${userIds[0]}/activate`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` }
          });
          const json = await res.json();
          if (json.success) {
            toast.success(`Re-activated user account.`, 'User Activated');
            setConfirmAction(prev => ({ ...prev, isOpen: false }));
            loadData();
            return;
          }
        }
      }
    } catch (err: any) {
      toast.error(err.message || 'Failed to execute user directory operation');
    }
  };

  // Trigger password reset
  const handlePasswordReset = async (user: User) => {
    try {
      const token = localStorage.getItem('pv_token');
      if (token) {
        const res = await fetch(`${API_BASE_URL}/users/${user.id}/reset-password`, {
          method: 'POST',
          headers: { 'Authorization': `Bearer ${token}` }
        });
        const json = await res.json();
        if (json.success && json.data) {
          setResetSuccess({
            isOpen: true,
            pwdStr: json.data.temp_password,
            userName: user.name
          });
          return;
        }
      }
    } catch (err: any) {
      toast.error(err.message || 'Failed to reset password');
    }
  };

  // Handle template checks in Drawer
  const handleToggleTemplateAccess = async (userId: string, templateId: string) => {
    try {
      const token = localStorage.getItem('pv_token');
      if (!token) throw new Error('No session token');

      const targetUser = users.find(u => u.id === userId);
      if (!targetUser) return;

      const currentTemplates = targetUser.allowedTemplates || [];
      const updatedTemplates = currentTemplates.includes(templateId)
        ? currentTemplates.filter(t => t !== templateId)
        : [...currentTemplates, templateId];

      const allowedUuids = updatedTemplates.map(tId => {
        const match = templates.find(t => {
          const nameLower = t.name.toLowerCase();
          const localId = nameLower.includes('psur') ? 'psur' : nameLower.includes('quant') ? 'quant' : 'pv_auto';
          return localId === tId;
        });
        return match?.id;
      }).filter(Boolean);

      const res = await fetch(`${API_BASE_URL}/users/${userId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          allowed_templates: allowedUuids
        })
      });
      const json = await res.json();
      if (json.success) {
        toast.success('Document template access revised.', 'Access Modified');
        loadData();
        if (profileUser && profileUser.id === userId) {
          setProfileUser({
            ...profileUser,
            allowedTemplates: updatedTemplates
          });
        }
      }
    } catch (err: any) {
      toast.error(err.message || 'Failed to update template access in database');
    }
  };

  // Export CSV
  const handleExportCSV = () => {
    if (users.length === 0) return;
    const headers = ['Name', 'Email', 'Role', 'Status', 'Created Date', 'Last Login', 'Generated Docs'];
    const rows = users.map(u => [
      u.name,
      u.email,
      u.role,
      u.status,
      u.createdDate,
      u.lastLogin,
      u.documentsGenerated
    ]);

    const csvContent = "data:text/csv;charset=utf-8," 
      + [headers.join(','), ...rows.map(e => e.join(','))].join('\n');
    
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `PV_User_Directory_${new Date().toISOString().substring(0,10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    toast.info('Export file package initiated.', 'CSV Exported');
  };

  // Filtered and Sorted list
  const filteredUsers = users.filter(u => {
    const matchesSearch = u.name.toLowerCase().includes(searchQuery.toLowerCase()) || 
                          u.email.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesRole = roleFilter === 'All' || u.role === roleFilter;
    const matchesStatus = statusFilter === 'All' || u.status === statusFilter;
    return matchesSearch && matchesRole && matchesStatus;
  });

  const sortedUsers = [...filteredUsers].sort((a, b) => {
    let comparison = 0;
    if (sortBy === 'name') comparison = a.name.localeCompare(b.name);
    else if (sortBy === 'email') comparison = a.email.localeCompare(b.email);
    else if (sortBy === 'created') comparison = a.createdDate.localeCompare(b.createdDate);
    else if (sortBy === 'docs') comparison = a.documentsGenerated - b.documentsGenerated;

    return sortOrder === 'asc' ? comparison : -comparison;
  });

  // Pagination calculation
  const totalPages = Math.ceil(sortedUsers.length / rowsPerPage) || 1;
  const paginatedUsers = sortedUsers.slice(
    (currentPage - 1) * rowsPerPage,
    currentPage * rowsPerPage
  );

  return (
    <div className="space-y-6">
      {/* Top Banner section */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900 dark:text-zinc-50 leading-tight">
            User Workspace Directory
          </h1>
          <p className="text-xs text-slate-500 dark:text-zinc-400 mt-1 font-medium">
            Configure roles, allocate document access filters, and inspect profile histories.
          </p>
        </div>

        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={handleExportCSV}>
            <FileDown className="h-4 w-4 text-slate-400" />
            <span>Export CSV</span>
          </Button>

          <Button 
            variant="primary" 
            size="sm" 
            onClick={() => {
              setEditingUser(null);
              reset({
                name: '',
                email: '',
                role: 'User',
                status: 'Active',
                reportLimit: 5,
                allowedTemplates: ['psur']
              });
              setIsFormOpen(true);
            }}
          >
            <Plus className="h-4 w-4" />
            <span>Create User</span>
          </Button>
        </div>
      </div>

      {/* Quick Stats Row */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Card className="p-4 flex items-center justify-between">
          <div className="text-left">
            <span className="text-[10px] font-bold text-slate-500 dark:text-zinc-400 uppercase tracking-wider">Total Users</span>
            <h3 className="text-xl font-black text-slate-900 dark:text-zinc-50 mt-1">{users.length}</h3>
          </div>
          <div className="p-2 rounded-lg bg-indigo-50 dark:bg-indigo-500/10 text-indigo-600 dark:text-indigo-400">
            <Users className="h-5 w-5" />
          </div>
        </Card>
        <Card className="p-4 flex items-center justify-between">
          <div className="text-left">
            <span className="text-[10px] font-bold text-slate-500 dark:text-zinc-400 uppercase tracking-wider">Active Users</span>
            <h3 className="text-xl font-black text-emerald-600 dark:text-emerald-450 mt-1">
              {users.filter(u => u.status === 'Active').length}
            </h3>
          </div>
          <div className="p-2 rounded-lg bg-emerald-50 dark:bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
            <UserCheck className="h-5 w-5" />
          </div>
        </Card>
        <Card className="p-4 flex items-center justify-between">
          <div className="text-left">
            <span className="text-[10px] font-bold text-slate-500 dark:text-zinc-400 uppercase tracking-wider">Suspended Users</span>
            <h3 className="text-xl font-black text-rose-650 dark:text-rose-450 mt-1">
              {users.filter(u => u.status === 'Inactive').length}
            </h3>
          </div>
          <div className="p-2 rounded-lg bg-rose-50 dark:bg-rose-500/10 text-rose-650 dark:text-rose-400">
            <UserMinus className="h-5 w-5" />
          </div>
        </Card>
      </div>

      {/* Main Table Card wrapper */}
      <Card>
        <CardHeader className="pb-3 border-none">
          <div className="flex flex-col md:flex-row justify-between gap-3 items-center">
            {/* Search Input */}
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-slate-205 dark:border-zinc-800 bg-slate-50/50 dark:bg-zinc-950/40 focus-within:ring-2 focus-within:ring-indigo-500 transition-all w-full md:max-w-xs">
              <Search className="h-4 w-4 text-slate-400" />
              <input
                type="text"
                placeholder="Search name, email address..."
                value={searchQuery}
                onChange={e => { setSearchQuery(e.target.value); setCurrentPage(1); }}
                className="bg-transparent text-xs text-slate-900 dark:text-zinc-50 border-none outline-none w-full placeholder-slate-400"
              />
              {searchQuery && (
                <button onClick={() => setSearchQuery('')} className="text-slate-400 hover:text-slate-650">
                  <X className="h-3.5 w-3.5" />
                </button>
              )}
            </div>

            {/* Filter Toggle Buttons */}
            <div className="flex items-center gap-2 self-end md:self-auto">
              <Button 
                variant="outline" 
                size="sm" 
                onClick={() => setShowFilters(!showFilters)}
                className={`text-xs ${showFilters ? 'bg-slate-100 dark:bg-zinc-800 border-slate-300' : ''}`}
              >
                <SlidersHorizontal className="h-4 w-4 text-slate-400" />
                <span>Filters</span>
              </Button>

              {selectedUserIds.length > 0 && (
                <div className="flex items-center gap-1.5 border-l border-slate-200 dark:border-zinc-850 pl-3">
                  <span className="text-xs text-slate-500 dark:text-zinc-400 font-semibold">{selectedUserIds.length} chosen</span>
                  <Button 
                    variant="outline" 
                    size="sm" 
                    onClick={() => triggerConfirm(
                      'bulk-deactivate', 
                      selectedUserIds, 
                      'Deactivate Selected Seats?', 
                      `Are you sure you want to deactivate the ${selectedUserIds.length} selected user accounts?`
                    )}
                    className="text-xs text-rose-500 border-rose-200"
                  >
                    <UserMinus className="h-3.5 w-3.5" />
                  </Button>
                  <Button 
                    variant="outline" 
                    size="sm" 
                    onClick={() => triggerConfirm(
                      'bulk-delete', 
                      selectedUserIds, 
                      'Delete Selected?', 
                      `Warning: Erasing ${selectedUserIds.length} accounts is permanent. Do you wish to continue?`
                    )}
                    className="text-xs text-rose-500 border-rose-200"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                </div>
              )}
            </div>
          </div>

          {/* Advanced Filter drawer inputs */}
          {showFilters && (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-4 p-4 rounded-xl bg-slate-50/50 dark:bg-zinc-950/20 border border-slate-100 dark:border-zinc-850 animate-fade-in text-left">
              <div>
                <span className="block text-[10px] font-bold text-slate-500 dark:text-zinc-400 uppercase tracking-wider mb-2">Filter Role</span>
                <div className="flex gap-2">
                  {['All', 'Admin', 'User'].map(role => (
                    <button
                      key={role}
                      onClick={() => { setRoleFilter(role as any); setCurrentPage(1); }}
                      className={`px-3 py-1.5 rounded-lg text-xs font-semibold border transition-all ${
                        roleFilter === role 
                          ? 'bg-indigo-600 border-indigo-600 text-white dark:bg-indigo-500 dark:border-indigo-500' 
                          : 'bg-white border-slate-200 text-slate-700 dark:bg-zinc-900 dark:border-zinc-800 dark:text-zinc-300'
                      }`}
                    >
                      {role}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <span className="block text-[10px] font-bold text-slate-500 dark:text-zinc-400 uppercase tracking-wider mb-2">Filter Status</span>
                <div className="flex gap-2">
                  {['All', 'Active', 'Inactive'].map(status => (
                    <button
                      key={status}
                      onClick={() => { setStatusFilter(status as any); setCurrentPage(1); }}
                      className={`px-3 py-1.5 rounded-lg text-xs font-semibold border transition-all ${
                        statusFilter === status 
                          ? 'bg-indigo-600 border-indigo-600 text-white dark:bg-indigo-500 dark:border-indigo-500' 
                          : 'bg-white border-slate-200 text-slate-700 dark:bg-zinc-900 dark:border-zinc-800 dark:text-zinc-300'
                      }`}
                    >
                      {status}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}
        </CardHeader>

        <CardContent className="p-0 overflow-x-auto">
          {loading ? (
            // Table Skeleton Loader
            <div className="divide-y divide-slate-100 dark:divide-zinc-800 p-5 space-y-3">
              {[...Array(3)].map((_, idx) => (
                <div key={idx} className="h-10 bg-slate-100 dark:bg-zinc-800 rounded animate-pulse" />
              ))}
            </div>
          ) : paginatedUsers.length === 0 ? (
            // Empty State
            <div className="text-center py-16 px-4">
              <AlertTriangle className="h-8 w-8 text-slate-350 dark:text-zinc-500 mx-auto mb-3" />
              <h3 className="text-xs font-bold text-slate-900 dark:text-zinc-50 uppercase tracking-wider">No User Matches</h3>
              <p className="text-xs text-slate-500 dark:text-zinc-400 mt-2 font-medium">
                Try refining your filters or editing the search query.
              </p>
            </div>
          ) : (
            // Main data table
            <table className="w-full border-collapse text-left">
              <thead>
                <tr className="border-b border-slate-100 dark:border-zinc-850 bg-slate-50/50 dark:bg-zinc-950/20 text-slate-500 dark:text-zinc-400 text-[10px] font-bold uppercase tracking-wider select-none">
                  <th className="px-5 py-3.5 w-10">
                    <button onClick={toggleSelectAll}>
                      {selectedUserIds.length === filteredUsers.length ? (
                        <CheckSquare className="h-4.5 w-4.5 text-indigo-650" />
                      ) : (
                        <Square className="h-4.5 w-4.5" />
                      )}
                    </button>
                  </th>
                  <th className="px-5 py-3.5 cursor-pointer hover:text-slate-900 dark:hover:text-zinc-150" onClick={() => handleSort('name')}>
                    User Name {sortBy === 'name' && (sortOrder === 'asc' ? '↑' : '↓')}
                  </th>
                  <th className="px-5 py-3.5 cursor-pointer hover:text-slate-900 dark:hover:text-zinc-150" onClick={() => handleSort('email')}>
                    Email Address {sortBy === 'email' && (sortOrder === 'asc' ? '↑' : '↓')}
                  </th>
                  <th className="px-5 py-3.5">Role</th>
                  <th className="px-5 py-3.5">Status</th>
                  <th className="px-5 py-3.5 cursor-pointer hover:text-slate-900 dark:hover:text-zinc-150" onClick={() => handleSort('created')}>
                    Created {sortBy === 'created' && (sortOrder === 'asc' ? '↑' : '↓')}
                  </th>
                  <th className="px-5 py-3.5 cursor-pointer hover:text-slate-900 dark:hover:text-zinc-150" onClick={() => handleSort('docs')}>
                    Docs Generated {sortBy === 'docs' && (sortOrder === 'asc' ? '↑' : '↓')}
                  </th>
                  <th className="px-5 py-3.5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-zinc-850">
                {paginatedUsers.map(u => (
                  <tr key={u.id} className="hover:bg-slate-50/50 dark:hover:bg-zinc-900/40 text-xs font-semibold text-slate-700 dark:text-zinc-300">
                    <td className="px-5 py-3.5">
                      <button onClick={() => toggleSelectUser(u.id)}>
                        {selectedUserIds.includes(u.id) ? (
                          <CheckSquare className="h-4.5 w-4.5 text-indigo-650" />
                        ) : (
                          <Square className="h-4.5 w-4.5" />
                        )}
                      </button>
                    </td>
                    <td className="px-5 py-3.5">
                      <div className="flex items-center gap-2.5">
                        <Avatar src={u.avatarUrl} name={u.name} size="sm" />
                        <span className="text-slate-900 dark:text-zinc-100 leading-none">{u.name}</span>
                      </div>
                    </td>
                    <td className="px-5 py-3.5 font-medium">{u.email}</td>
                    <td className="px-5 py-3.5">
                      <Badge variant={u.role === 'Admin' ? 'info' : 'neutral'}>
                        {u.role}
                      </Badge>
                    </td>
                    <td className="px-5 py-3.5">
                      <Badge variant={u.status === 'Active' ? 'success' : 'danger'}>
                        {u.status}
                      </Badge>
                    </td>
                    <td className="px-5 py-3.5 font-medium">
                      {new Date(u.createdDate).toLocaleDateString()}
                    </td>
                    <td className="px-5 py-3.5 text-center font-bold">
                      {u.documentsGenerated}
                    </td>
                    <td className="px-5 py-3.5 text-right">
                      <div className="flex justify-end gap-1.5">
                        <button 
                          onClick={() => setProfileUser(u)}
                          className="p-1 rounded hover:bg-slate-100 dark:hover:bg-zinc-800 text-slate-500 dark:text-zinc-400"
                          title="View Profile History"
                        >
                          <Eye className="h-4 w-4" />
                        </button>
                        
                        <button 
                          onClick={() => {
                            setEditingUser(u);
                            reset({
                              name: u.name,
                              email: u.email,
                              role: u.role,
                              status: u.status,
                              reportLimit: (u as any).reportLimit || 5,
                              allowedTemplates: u.allowedTemplates
                            });
                            setIsFormOpen(true);
                          }}
                          className="p-1 rounded hover:bg-slate-100 dark:hover:bg-zinc-800 text-slate-500 dark:text-zinc-400"
                          title="Edit Settings"
                        >
                          <Edit2 className="h-4 w-4" />
                        </button>

                        <button 
                          onClick={() => handlePasswordReset(u)}
                          className="p-1 rounded hover:bg-slate-100 dark:hover:bg-zinc-800 text-slate-500 dark:text-zinc-400"
                          title="Reset Password"
                        >
                          <Key className="h-4 w-4" />
                        </button>

                        {u.status === 'Active' ? (
                          <button 
                            onClick={() => triggerConfirm(
                              'deactivate',
                              [u.id],
                              'Suspend Account?',
                              `Are you sure you want to suspend access permissions for ${u.name}?`
                            )}
                            className="p-1 rounded hover:bg-slate-100 dark:hover:bg-zinc-800 text-rose-500"
                            title="Deactivate Account"
                          >
                            <UserMinus className="h-4 w-4" />
                          </button>
                        ) : (
                          <button 
                            onClick={() => triggerConfirm(
                              'activate',
                              [u.id],
                              'Restore Account?',
                              `Restore account login access for ${u.name}?`
                            )}
                            className="p-1 rounded hover:bg-slate-100 dark:hover:bg-zinc-800 text-emerald-500"
                            title="Activate Account"
                          >
                            <UserCheck className="h-4 w-4" />
                          </button>
                        )}

                        <button 
                          onClick={() => triggerConfirm(
                            'delete',
                            [u.id],
                            'Permanently Delete Account?',
                            `Erase account catalog files and access records for ${u.name}? This cannot be undone.`
                          )}
                          className="p-1 rounded hover:bg-slate-100 dark:hover:bg-zinc-800 text-rose-500"
                          title="Delete Account"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </CardContent>

        {/* Footer pagination */}
        {!loading && sortedUsers.length > 0 && (
          <div className="px-5 py-4 border-t border-slate-100 dark:border-zinc-850 flex items-center justify-between text-xs font-semibold text-slate-500 dark:text-zinc-400 select-none bg-slate-50/50 dark:bg-zinc-950/20 rounded-b-xl">
            <div className="flex items-center gap-2">
              <span>Rows per page:</span>
              <select
                value={rowsPerPage}
                onChange={e => { setRowsPerPage(Number(e.target.value)); setCurrentPage(1); }}
                className="bg-white dark:bg-zinc-900 border border-slate-205 dark:border-zinc-800 rounded px-1.5 py-0.5 outline-none font-bold"
              >
                {[5, 10, 20].map(v => (
                  <option key={v} value={v}>{v}</option>
                ))}
              </select>
            </div>

            <div>
              <span>Page {currentPage} of {totalPages}</span>
            </div>

            <div className="flex gap-1.5">
              <Button 
                variant="outline" 
                size="sm" 
                onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
                disabled={currentPage === 1}
                className="px-2"
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <Button 
                variant="outline" 
                size="sm" 
                onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
                disabled={currentPage === totalPages}
                className="px-2"
              >
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        )}
      </Card>

      {/* Create / Edit User Modal */}
      <Modal 
        isOpen={isFormOpen} 
        onClose={() => { setIsFormOpen(false); setEditingUser(null); }} 
        title={editingUser ? 'Modify User Profile Settings' : 'Enroll New Workspace Account'}
      >
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 text-left">
          <div>
            <label className="block text-xs font-bold text-slate-700 dark:text-zinc-300 uppercase tracking-wider mb-1">
              Full Name
            </label>
            <input
              type="text"
              {...register('name')}
              placeholder="e.g. Sarah Connor"
              className={`w-full text-xs px-3 py-2.5 border rounded-lg bg-slate-50/50 dark:bg-zinc-950/50 text-slate-900 dark:text-zinc-50 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all ${
                errors.name ? 'border-rose-300' : 'border-slate-200 dark:border-zinc-800'
              }`}
            />
            {errors.name && <p className="text-[10px] text-rose-500 font-bold mt-1">{errors.name.message}</p>}
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-700 dark:text-zinc-300 uppercase tracking-wider mb-1">
              Corporate Email Address
            </label>
            <input
              type="email"
              {...register('email')}
              placeholder="sarah.c@company.com"
              className={`w-full text-xs px-3 py-2.5 border rounded-lg bg-slate-50/50 dark:bg-zinc-950/50 text-slate-900 dark:text-zinc-50 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all ${
                errors.email ? 'border-rose-300' : 'border-slate-200 dark:border-zinc-800'
              }`}
            />
            {errors.email && <p className="text-[10px] text-rose-500 font-bold mt-1">{errors.email.message}</p>}
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-bold text-slate-700 dark:text-zinc-300 uppercase tracking-wider mb-1">
                Access Role
              </label>
              <select
                {...register('role')}
                className="w-full text-xs px-3 py-2.5 border border-slate-200 dark:border-zinc-800 bg-slate-50/50 dark:bg-zinc-950/50 rounded-lg text-slate-900 dark:text-zinc-50 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all"
              >
                <option value="User">Standard User</option>
                <option value="Admin">Administrator</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 dark:text-zinc-300 uppercase tracking-wider mb-1">
                Account Status
              </label>
              <select
                {...register('status')}
                className="w-full text-xs px-3 py-2.5 border border-slate-200 dark:border-zinc-800 bg-slate-50/50 dark:bg-zinc-950/50 rounded-lg text-slate-900 dark:text-zinc-50 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all"
              >
                <option value="Active">Active</option>
                <option value="Inactive">Suspended (Inactive)</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-700 dark:text-zinc-300 uppercase tracking-wider mb-1">
              Report Generation Limit (Quota)
            </label>
            <input
              type="number"
              {...register('reportLimit')}
              placeholder="e.g. 5"
              className={`w-full text-xs px-3 py-2.5 border rounded-lg bg-slate-50/50 dark:bg-zinc-950/50 text-slate-900 dark:text-zinc-50 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all ${
                errors.reportLimit ? 'border-rose-300' : 'border-slate-200 dark:border-zinc-800'
              }`}
            />
            {errors.reportLimit && <p className="text-[10px] text-rose-500 font-bold mt-1">{errors.reportLimit.message}</p>}
          </div>

          <div className="flex justify-end gap-2 pt-3">
            <Button variant="outline" size="sm" type="button" onClick={() => { setIsFormOpen(false); setEditingUser(null); }}>
              Cancel
            </Button>
            <Button variant="primary" size="sm" type="submit">
              Save Profile
            </Button>
          </div>
        </form>
      </Modal>

      {/* User Profile Detail History Drawer */}
      <Drawer 
        isOpen={!!profileUser} 
        onClose={() => setProfileUser(null)} 
        title="Workspace Profile Audit"
        width="2xl"
      >
        {profileUser && (
          <div className="space-y-6 text-left">
            {/* Header info */}
            <div className="flex items-center gap-4 bg-white dark:bg-zinc-900 border border-slate-200 dark:border-zinc-800 p-5 rounded-2xl">
              <Avatar src={profileUser.avatarUrl} name={profileUser.name} size="xl" />
              <div className="space-y-1 flex-1">
                <div className="flex justify-between items-center">
                  <h3 className="text-base font-bold text-slate-900 dark:text-zinc-50">{profileUser.name}</h3>
                  <Badge variant={profileUser.status === 'Active' ? 'success' : 'danger'}>
                    {profileUser.status}
                  </Badge>
                </div>
                <p className="text-xs text-slate-500 dark:text-zinc-400 font-semibold">{profileUser.email}</p>
                <p className="text-[10px] text-slate-400 dark:text-zinc-500 font-medium">Joined {new Date(profileUser.createdDate).toLocaleDateString()} | Role: {profileUser.role}</p>
              </div>
            </div>

            {/* Template Permissions Config section */}
            <Card>
              <CardHeader className="pb-3">
                <CardTitle>Template Access Permissions</CardTitle>
                <CardDescription>Allocate which generators this user is permitted to launch.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                {templates.map(tpl => {
                  const isAllowed = profileUser.allowedTemplates.includes(tpl.id);
                  return (
                    <div 
                      key={tpl.id}
                      onClick={() => handleToggleTemplateAccess(profileUser.id, tpl.id)}
                      className={`flex justify-between items-center p-3 border rounded-xl cursor-pointer hover:border-slate-350 dark:hover:border-zinc-700 transition-all ${
                        isAllowed 
                          ? 'border-indigo-600 bg-indigo-50/10 dark:border-indigo-500' 
                          : 'border-slate-200 bg-white dark:bg-zinc-900'
                      }`}
                    >
                      <div className="flex flex-col text-left">
                        <span className="text-xs font-bold text-slate-900 dark:text-zinc-50">{tpl.name}</span>
                        <span className="text-[10px] text-slate-500 dark:text-zinc-400 font-medium mt-0.5">{tpl.supportedFileTypes.join(', ')}</span>
                      </div>
                      <div>
                        {isAllowed ? (
                          <span className="text-xs font-bold text-indigo-650">Enabled</span>
                        ) : (
                          <span className="text-xs font-semibold text-slate-400">Disabled</span>
                        )}
                      </div>
                    </div>
                  );
                })}
              </CardContent>
            </Card>

            {/* User Document History list */}
            <Card>
              <CardHeader className="pb-3">
                <CardTitle>Generated Document Catalog</CardTitle>
                <CardDescription>History of files compiled by this user profile.</CardDescription>
              </CardHeader>
              <CardContent className="p-0">
                {documents.filter(d => d.createdById === profileUser.id).length === 0 ? (
                  <div className="p-5 text-center text-xs text-slate-400 font-medium">
                    No documents compiled by this user yet.
                  </div>
                ) : (
                  <div className="divide-y divide-slate-100 dark:divide-zinc-800">
                    {documents
                      .filter(d => d.createdById === profileUser.id)
                      .map(doc => (
                        <div key={doc.id} className="p-4 flex justify-between items-center hover:bg-slate-50/50 dark:hover:bg-zinc-805 transition-colors">
                          <div className="flex items-start gap-3">
                            <FileText className="h-4.5 w-4.5 text-slate-400 mt-0.5" />
                            <div className="flex flex-col">
                              <span className="text-xs font-bold text-slate-800 dark:text-zinc-350">{doc.name}</span>
                              <span className="text-[9px] text-slate-400 dark:text-zinc-550 font-semibold mt-0.5">{new Date(doc.generatedTime).toLocaleDateString()} | Version {doc.version}</span>
                            </div>
                          </div>
                          <div>
                            <Badge variant={doc.status === 'Success' ? 'success' : 'danger'}>
                              {doc.status}
                            </Badge>
                          </div>
                        </div>
                      ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        )}
      </Drawer>

      {/* Confirmation dialogues wrapper */}
      <ConfirmDialog
        isOpen={confirmAction.isOpen}
        onClose={() => setConfirmAction(prev => ({ ...prev, isOpen: false }))}
        onConfirm={handleExecuteAction}
        title={confirmAction.title}
        message={confirmAction.message}
      />

      {/* Reset Password Printout modal */}
      <Modal 
        isOpen={resetSuccess.isOpen} 
        onClose={() => setResetSuccess(prev => ({ ...prev, isOpen: false }))} 
        title="Account Credentials Restored"
        size="sm"
      >
        <div className="space-y-4 text-center">
          <div className="p-3 bg-emerald-50 dark:bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 rounded-full inline-flex">
            <Key className="h-6 w-6" />
          </div>
          
          <div className="text-xs font-semibold text-slate-700 dark:text-zinc-300">
            Temp password generated for <span className="font-bold text-slate-900 dark:text-zinc-50">{resetSuccess.userName}</span>:
          </div>

          <div className="bg-slate-100 dark:bg-zinc-950 p-3 rounded-lg border border-slate-205 dark:border-zinc-800 font-mono text-sm font-bold text-slate-900 dark:text-zinc-100 select-all cursor-pointer">
            {resetSuccess.pwdStr}
          </div>

          <p className="text-[10px] text-slate-400 dark:text-zinc-500 font-medium">
            Copy this token string. The user will be requested to replace this temporary credential during their subsequent platform validation cycle.
          </p>

          <div className="pt-2">
            <Button variant="primary" size="sm" className="w-full text-xs" onClick={() => setResetSuccess(prev => ({ ...prev, isOpen: false }))}>
              Close Dialog
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
};
export default UsersPage;
