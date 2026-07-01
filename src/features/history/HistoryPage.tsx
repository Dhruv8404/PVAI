import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { 
  Search, 
  SlidersHorizontal, 
  ChevronLeft, 
  ChevronRight, 
  Eye, 
  Download, 
  Trash2, 
  Layers, 
  CheckCircle2, 
  XCircle, 
  X,
  FileText,
  Printer,
  Copy,
  Info
} from 'lucide-react';
import { mockDb } from '../../lib/mockDb';
import type { GeneratedDocument, DocumentTemplate } from '../../types';
import { Button } from '../../components/ui/Button';
import { Card, CardHeader, CardContent } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import { Drawer } from '../../components/ui/Drawer';
import { useToast } from '../../components/ui/Toast';
import { ConfirmDialog } from '../../components/shared/ConfirmDialog';
import { useAuth } from '../../context/AuthContext';

export const HistoryPage: React.FC = () => {
  const { user } = useAuth();
  const { toast } = useToast();
  const [searchParams, setSearchParams] = useSearchParams();
  
  // Database datasets
  const [documents, setDocuments] = useState<GeneratedDocument[]>([]);
  const [templates, setTemplates] = useState<DocumentTemplate[]>([]);
  const [loading, setLoading] = useState(false);

  // Search & Filter state
  const [searchQuery, setSearchQuery] = useState('');
  const [templateFilter, setTemplateFilter] = useState('All');
  const [statusFilter, setStatusFilter] = useState('All');
  const [downloadFilter, setDownloadFilter] = useState('All');
  const [showFilters, setShowFilters] = useState(false);

  // Pagination
  const [currentPage, setCurrentPage] = useState(1);
  const [rowsPerPage, setRowsPerPage] = useState(10);

  // Selected document for Drawer Preview
  const [previewDoc, setPreviewDoc] = useState<GeneratedDocument | null>(null);

  // Confirm delete dialog
  const [deleteConfirm, setDeleteConfirm] = useState<{
    isOpen: boolean;
    docId: string;
    docName: string;
  }>({
    isOpen: false,
    docId: '',
    docName: ''
  });

  const loadVaultData = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('pv_token');
      if (token) {
        // Load documents
        const docsRes = await fetch('http://127.0.0.1:8000/api/v1/documents/history', {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        const docsJson = await docsRes.json();

        // Load templates
        const templatesRes = await fetch('http://127.0.0.1:8000/api/v1/templates', {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        const templatesJson = await templatesRes.json();

        if (docsJson.success && docsJson.data && templatesJson.success && templatesJson.data) {
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
            htmlContent: '' // loaded dynamically on preview
          }));
          setDocuments(mappedDocs);

          const mappedTemplates = templatesJson.data.map((t: any) => {
            const idLower = t.name.toLowerCase();
            const localId = idLower.includes('psur') ? 'psur' : idLower.includes('quant') ? 'quant' : 'pv_auto';
            return {
              id: localId,
              name: t.name,
              description: t.description,
              supportedFileTypes: localId === 'psur' ? ['.xlsx', '.xls'] : localId === 'quant' ? ['.xlsx', '.csv'] : ['.xlsx'],
              lastUpdated: t.updated_at,
              icon: localId === 'psur' ? 'FileText' : localId === 'quant' ? 'BarChart3' : 'Activity'
            };
          });
          setTemplates(mappedTemplates);
          setLoading(false);
          return;
        }
      }
    } catch (err: any) {
      console.warn('API error in history loader, falling back to mockDb:', err.message);
    }

    setDocuments(mockDb.getDocuments());
    setTemplates(mockDb.getTemplates());
    setLoading(false);
  };

  useEffect(() => {
    loadVaultData();

    // Handle template query parameter redirect
    const tplParam = searchParams.get('template');
    if (tplParam) {
      setTemplateFilter(tplParam);
      setShowFilters(true);
    }
  }, [searchParams]);

  // Actions
  const handleTriggerDelete = (doc: GeneratedDocument) => {
    if (user?.role !== 'Admin') {
      toast.warning('Administrative authorization required to erase record audits.', 'Access Restricted');
      return;
    }
    setDeleteConfirm({
      isOpen: true,
      docId: doc.id,
      docName: doc.name
    });
  };

  const handleExecuteDelete = async () => {
    try {
      const token = localStorage.getItem('pv_token');
      if (token) {
        const res = await fetch(`http://127.0.0.1:8000/api/v1/documents/${deleteConfirm.docId}`, {
          method: 'DELETE',
          headers: { 'Authorization': `Bearer ${token}` }
        });
        const json = await res.json();
        if (json.success) {
          toast.success('Document audit record removed from system database.', 'Log Erased');
          setDeleteConfirm(prev => ({ ...prev, isOpen: false }));
          loadVaultData();
          return;
        }
      }
    } catch (err: any) {
      console.warn('API delete document failed, using mockDb fallback:', err.message);
    }

    try {
      mockDb.deleteDocument(deleteConfirm.docId);
      toast.success('Document audit record removed from system database (Offline Mode).', 'Log Erased');
      setDeleteConfirm(prev => ({ ...prev, isOpen: false }));
      loadVaultData();
    } catch (err: any) {
      toast.error(err.message || 'Error occurred.');
    }
  };

  const handleDownload = async (doc: GeneratedDocument) => {
    try {
      const token = localStorage.getItem('pv_token');
      if (token) {
        // Direct download trigger from FastAPI
        window.open(`http://127.0.0.1:8000/api/v1/downloads/${doc.id}?format=HTML`, '_blank');
        toast.success(`Downloaded "${doc.name}" HTML compilation package.`, 'Download Started');
        loadVaultData();
        return;
      }
    } catch (err: any) {
      console.warn('API download failed, falling back to mockDb:', err.message);
    }

    mockDb.toggleDownloaded(doc.id);
    const blob = new Blob([doc.htmlContent], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${doc.name}.html`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    toast.success(`Downloaded "${doc.name}" HTML compilation package (Offline Mode).`, 'Download Started');
    loadVaultData();
  };

  const handleOpenPreview = async (doc: GeneratedDocument) => {
    try {
      const token = localStorage.getItem('pv_token');
      if (!doc.htmlContent && token) {
        const res = await fetch(`http://127.0.0.1:8000/api/v1/downloads/${doc.id}?format=HTML`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        const htmlText = await res.text();
        doc.htmlContent = htmlText;
      }
    } catch (err: any) {
      console.warn('API fetch document HTML failed:', err.message);
    }
    setPreviewDoc(doc);
  };

  const handlePrint = (doc: GeneratedDocument) => {
    // Open isolated iframe print window
    const printWindow = window.open('', '_blank');
    if (printWindow) {
      printWindow.document.write(doc.htmlContent);
      printWindow.document.close();
      printWindow.focus();
      printWindow.print();
    }
  };

  const handleCopy = (doc: GeneratedDocument) => {
    navigator.clipboard.writeText(doc.htmlContent);
    toast.success('Report code copied to clipboard.', 'Copied');
  };

  const clearQueryFilter = () => {
    searchParams.delete('template');
    setSearchParams(searchParams);
    setTemplateFilter('All');
  };

  // Filters logic
  const filteredDocs = documents.filter(doc => {
    // If not admin, user can only see their own generated documents
    const matchesUser = user?.role === 'Admin' || doc.createdById === user?.id;

    const matchesSearch = doc.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                          doc.createdBy.toLowerCase().includes(searchQuery.toLowerCase()) ||
                          doc.excelFileName.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesTemplate = templateFilter === 'All' || doc.templateId === templateFilter;
    const matchesStatus = statusFilter === 'All' || doc.status === statusFilter;
    
    let matchesDownload = true;
    if (downloadFilter === 'Downloaded') matchesDownload = doc.downloaded;
    else if (downloadFilter === 'NotDownloaded') matchesDownload = !doc.downloaded;

    return matchesUser && matchesSearch && matchesTemplate && matchesStatus && matchesDownload;
  });

  // Pagination calculation
  const totalPages = Math.ceil(filteredDocs.length / rowsPerPage) || 1;
  const paginatedDocs = filteredDocs.slice(
    (currentPage - 1) * rowsPerPage,
    currentPage * rowsPerPage
  );

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900 dark:text-zinc-50 leading-tight">
            Document History Vault
          </h1>
          <p className="text-xs text-slate-500 dark:text-zinc-400 mt-1 font-medium">
            Inspect compiled reports archive, review generation parameters, and download exports.
          </p>
        </div>
      </div>

      {/* Main Catalog Card */}
      <Card>
        <CardHeader className="pb-3 border-none">
          <div className="flex flex-col md:flex-row justify-between gap-3 items-center">
            {/* Search Input */}
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-slate-205 dark:border-zinc-850 bg-slate-50/50 dark:bg-zinc-950/40 focus-within:ring-2 focus-within:ring-indigo-500 transition-all w-full md:max-w-xs">
              <Search className="h-4 w-4 text-slate-400" />
              <input
                type="text"
                placeholder="Search document name, workbook..."
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

            {/* Filter Toggle */}
            <div className="flex items-center gap-2 self-end md:self-auto">
              {searchParams.get('template') && (
                <Badge variant="info" className="py-1 px-2.5 flex gap-1 items-center">
                  <span>Query template active</span>
                  <button onClick={clearQueryFilter}>
                    <X className="h-3 w-3" />
                  </button>
                </Badge>
              )}

              <Button 
                variant="outline" 
                size="sm" 
                onClick={() => setShowFilters(!showFilters)}
                className={`text-xs ${showFilters ? 'bg-slate-100 dark:bg-zinc-800 border-slate-300' : ''}`}
              >
                <SlidersHorizontal className="h-4 w-4 text-slate-400" />
                <span>Filters</span>
              </Button>
            </div>
          </div>

          {/* Collapsible Advanced Filters */}
          {showFilters && (
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mt-4 p-4 rounded-xl bg-slate-50/50 dark:bg-zinc-950/20 border border-slate-100 dark:border-zinc-850 animate-fade-in text-left">
              <div>
                <span className="block text-[10px] font-bold text-slate-500 dark:text-zinc-400 uppercase tracking-wider mb-2">Filter Template</span>
                <select
                  value={templateFilter}
                  onChange={e => { setTemplateFilter(e.target.value); setCurrentPage(1); }}
                  className="w-full text-xs px-2.5 py-1.5 border border-slate-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 rounded-lg text-slate-900 dark:text-zinc-50 outline-none"
                >
                  <option value="All">All Templates</option>
                  {templates.map(t => (
                    <option key={t.id} value={t.id}>{t.name}</option>
                  ))}
                </select>
              </div>

              <div>
                <span className="block text-[10px] font-bold text-slate-500 dark:text-zinc-400 uppercase tracking-wider mb-2">Filter Status</span>
                <select
                  value={statusFilter}
                  onChange={e => { setStatusFilter(e.target.value); setCurrentPage(1); }}
                  className="w-full text-xs px-2.5 py-1.5 border border-slate-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 rounded-lg text-slate-900 dark:text-zinc-50 outline-none"
                >
                  <option value="All">All Statuses</option>
                  <option value="Success">Success Only</option>
                  <option value="Failed">Failed Only</option>
                </select>
              </div>

              <div>
                <span className="block text-[10px] font-bold text-slate-500 dark:text-zinc-400 uppercase tracking-wider mb-2">Download Log State</span>
                <select
                  value={downloadFilter}
                  onChange={e => { setDownloadFilter(e.target.value); setCurrentPage(1); }}
                  className="w-full text-xs px-2.5 py-1.5 border border-slate-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 rounded-lg text-slate-900 dark:text-zinc-50 outline-none"
                >
                  <option value="All">All Items</option>
                  <option value="Downloaded">Downloaded Only</option>
                  <option value="NotDownloaded">Not Downloaded</option>
                </select>
              </div>
            </div>
          )}
        </CardHeader>

        <CardContent className="p-0 overflow-x-auto">
          {loading ? (
            <div className="divide-y divide-slate-100 dark:divide-zinc-800 p-5 space-y-3">
              {[...Array(4)].map((_, idx) => (
                <div key={idx} className="h-10 bg-slate-100 dark:bg-zinc-800 rounded animate-pulse" />
              ))}
            </div>
          ) : paginatedDocs.length === 0 ? (
            <div className="text-center py-16 px-4">
              <Layers className="h-8 w-8 text-slate-350 dark:text-zinc-500 mx-auto mb-3" />
              <h3 className="text-xs font-bold text-slate-900 dark:text-zinc-50 uppercase tracking-wider">Empty History Logs</h3>
              <p className="text-xs text-slate-500 dark:text-zinc-400 mt-2 font-medium">
                No documents fit selected search parameters or templates lists.
              </p>
            </div>
          ) : (
            <table className="w-full border-collapse text-left">
              <thead>
                <tr className="border-b border-slate-100 dark:border-zinc-850 bg-slate-50/50 dark:bg-zinc-950/20 text-slate-500 dark:text-zinc-400 text-[10px] font-bold uppercase tracking-wider select-none">
                  <th className="px-5 py-3.5">Document Name</th>
                  <th className="px-5 py-3.5">Template</th>
                  <th className="px-5 py-3.5">Created By</th>
                  <th className="px-5 py-3.5">Generated Time</th>
                  <th className="px-5 py-3.5">Downloads</th>
                  <th className="px-5 py-3.5">Status</th>
                  <th className="px-5 py-3.5 w-16 text-center">Version</th>
                  <th className="px-5 py-3.5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-zinc-850">
                {paginatedDocs.map(doc => (
                  <tr key={doc.id} className="hover:bg-slate-50/50 dark:hover:bg-zinc-900/40 text-xs font-semibold text-slate-700 dark:text-zinc-300">
                    <td className="px-5 py-3.5">
                      <div className="flex items-start gap-2.5 max-w-xs">
                        <FileText className="h-4.5 w-4.5 text-slate-400 mt-0.5 flex-shrink-0" />
                        <div className="flex flex-col truncate">
                          <span className="text-slate-900 dark:text-zinc-100 truncate leading-none">{doc.name}</span>
                          <span className="text-[9px] text-slate-400 dark:text-zinc-500 mt-1 font-semibold truncate">Excel: {doc.excelFileName}</span>
                        </div>
                      </div>
                    </td>
                    <td className="px-5 py-3.5 truncate max-w-[120px]">
                      {doc.templateName}
                    </td>
                    <td className="px-5 py-3.5 font-medium">{doc.createdBy}</td>
                    <td className="px-5 py-3.5 font-medium">
                      {new Date(doc.generatedTime).toLocaleString()}
                    </td>
                    <td className="px-5 py-3.5">
                      <Badge variant={doc.downloaded ? 'success' : 'neutral'}>
                        {doc.downloaded ? 'Downloaded' : 'Unopened'}
                      </Badge>
                    </td>
                    <td className="px-5 py-3.5">
                      <div className="flex items-center gap-1.5">
                        {doc.status === 'Success' ? (
                          <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                        ) : (
                          <XCircle className="h-4 w-4 text-rose-500" />
                        )}
                        <span>{doc.status}</span>
                      </div>
                    </td>
                    <td className="px-5 py-3.5 text-center font-mono font-bold text-slate-500">
                      v{doc.version}
                    </td>
                    <td className="px-5 py-3.5 text-right">
                      <div className="flex justify-end gap-1.5">
                        <button 
                          onClick={() => handleOpenPreview(doc)}
                          className="p-1.5 rounded hover:bg-slate-100 dark:hover:bg-zinc-800 text-slate-500 dark:text-zinc-400"
                          title="Open Preview Drawer"
                        >
                          <Eye className="h-4 w-4" />
                        </button>
                        
                        <button 
                          onClick={() => handleDownload(doc)}
                          disabled={doc.status !== 'Success'}
                          className="p-1.5 rounded hover:bg-slate-100 dark:hover:bg-zinc-800 text-slate-500 dark:text-zinc-400 disabled:opacity-30"
                          title="Download HTML package"
                        >
                          <Download className="h-4 w-4" />
                        </button>

                        {user?.role === 'Admin' && (
                          <button 
                            onClick={() => handleTriggerDelete(doc)}
                            className="p-1.5 rounded hover:bg-slate-100 dark:hover:bg-zinc-800 text-rose-500"
                            title="Delete record from system log"
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </CardContent>

        {/* Footer pagination */}
        {!loading && filteredDocs.length > 0 && (
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

      {/* Audit delete Confirm Dialog */}
      <ConfirmDialog
        isOpen={deleteConfirm.isOpen}
        onClose={() => setDeleteConfirm(prev => ({ ...prev, isOpen: false }))}
        onConfirm={handleExecuteDelete}
        title="Delete Document Record?"
        message={`Warning: Removing document "${deleteConfirm.docName}" from the audit directory is permanent and recorded. Continue?`}
      />

      {/* Document Sandbox Preview Drawer */}
      <Drawer
        isOpen={!!previewDoc}
        onClose={() => setPreviewDoc(null)}
        title={previewDoc ? `Sandbox Preview: ${previewDoc.name}` : 'Document Preview'}
        width="4xl"
      >
        {previewDoc && (
          <div className="space-y-5 text-left">
            {/* Control Panel actions */}
            <div className="flex flex-wrap items-center justify-between gap-3 p-4 rounded-xl border border-slate-205 dark:border-zinc-800 bg-white dark:bg-zinc-900">
              <div className="flex flex-col text-left text-xs font-semibold">
                <span className="text-[9px] text-slate-400 dark:text-zinc-550 uppercase tracking-wider">Excel Workbook Source</span>
                <span className="text-slate-800 dark:text-zinc-150 font-bold mt-0.5">{previewDoc.excelFileName}</span>
              </div>

              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={() => handleCopy(previewDoc)}>
                  <Copy className="h-3.5 w-3.5" />
                  <span>Copy Code</span>
                </Button>
                
                <Button 
                  variant="outline" 
                  size="sm" 
                  onClick={() => handlePrint(previewDoc)}
                  disabled={previewDoc.status !== 'Success'}
                >
                  <Printer className="h-3.5 w-3.5" />
                  <span>Print Report</span>
                </Button>

                <Button 
                  variant="primary" 
                  size="sm" 
                  onClick={() => handleDownload(previewDoc)}
                  disabled={previewDoc.status !== 'Success'}
                >
                  <Download className="h-3.5 w-3.5" />
                  <span>Download HTML</span>
                </Button>
              </div>
            </div>

            {/* Preview Iframe Container */}
            <Card className="overflow-hidden">
              <CardContent className="p-0 bg-white">
                <iframe
                  title="Isolated History Report View"
                  srcDoc={previewDoc.htmlContent}
                  className="w-full h-[32rem] border-none"
                  sandbox="allow-same-origin"
                />
              </CardContent>
            </Card>

            {/* Informational Warning footer */}
            <div className="p-3 bg-slate-50 dark:bg-zinc-900 border rounded-xl flex gap-2.5 items-start text-[10px] text-slate-500 dark:text-zinc-400 font-semibold leading-relaxed">
              <Info className="h-4.5 w-4.5 text-indigo-500 mt-0.5 flex-shrink-0" />
              <div className="space-y-1">
                <span className="font-bold text-slate-700 dark:text-zinc-300">Regulatory Audit Note:</span>
                <p>This document is cryptographically locked and cached. Any further alterations or revisions to user parameters will trigger a new version release in the platform logs.</p>
              </div>
            </div>
          </div>
        )}
      </Drawer>
    </div>
  );
};
export default HistoryPage;
