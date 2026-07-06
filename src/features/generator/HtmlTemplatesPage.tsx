import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { API_BASE_URL } from "../../config";
import { useToast } from "../../components/ui/Toast";
import { Modal } from "../../components/ui/Modal";
import { Button } from "../../components/ui/Button";
import { Badge } from "../../components/ui/Badge";
import { Card, CardContent } from "../../components/ui/Card";
import { 
  FileCode, 
  UploadCloud, 
  Eye, 
  CheckCircle, 
  XCircle, 
  Trash2, 
  Clock, 
  User, 
  FileText,
  AlertTriangle,
  ArrowLeft
} from "lucide-react";


interface HtmlTemplate {
  id: string;
  name: string;
  version: string;
  description: string | null;
  html_file: string;
  is_active: boolean;
  uploaded_by: string | null;
  created_at: string;
  updated_at: string;
}

export const HtmlTemplatesPage: React.FC = () => {
  const navigate = useNavigate();
  const { toast } = useToast();
  const [templates, setTemplates] = useState<HtmlTemplate[]>([]);
  const [loading, setLoading] = useState(false);

  // Modals state
  const [uploadOpen, setUploadOpen] = useState(false);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewContent, setPreviewContent] = useState("");
  const [previewName, setPreviewName] = useState("");

  // Upload Form state
  const [name, setName] = useState("");
  const [version, setVersion] = useState("1.0.0");
  const [description, setDescription] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);

  const fetchTemplates = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem("pv_token");
      const specUrl = API_BASE_URL.replace("/api/v1", "/api");
      const res = await fetch(`${specUrl}/templates/`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (!res.ok) throw new Error("Failed to fetch templates.");
      const json = await res.json();
      if (json.success) {
        setTemplates(json.data);
      }
    } catch (e: any) {
      toast.error(e.message || "Error loading HTML templates.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTemplates();
  }, []);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0] || null;
    if (selected) {
      if (!selected.name.toLowerCase().endsWith(".html")) {
        toast.error("Only HTML files (.html) are allowed.");
        setFile(null);
        return;
      }
      const max_size = 5 * 1024 * 1024; // 5MB
      if (selected.size > max_size) {
        toast.error("File size exceeds 5MB limit.");
        setFile(null);
        return;
      }
      setFile(selected);
      // Auto-populate template name from file name if empty
      if (!name) {
        const cleanName = selected.name.replace(/\.[^/.]+$/, "").replace(/[-_]+/g, " ");
        setName(cleanName.charAt(0).toUpperCase() + cleanName.slice(1));
      }
    }
  };

  const handleUploadSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) {
      toast.error("Please select an HTML file to upload.");
      return;
    }
    if (!name.trim()) {
      toast.error("Please specify a template name.");
      return;
    }

    setUploading(true);
    try {
      const token = localStorage.getItem("pv_token");
      const formData = new FormData();
      formData.append("file", file);
      formData.append("name", name.trim());
      formData.append("version", version.trim());
      formData.append("description", description.trim());

      const specUrl = API_BASE_URL.replace("/api/v1", "/api");
      const res = await fetch(`${specUrl}/templates/upload/`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: formData
      });

      const json = await res.json();
      if (!res.ok) throw new Error(json.detail || "Failed to upload template.");

      if (json.success) {
        toast.success(`Template '${name}' uploaded successfully.`);
        setUploadOpen(false);
        // Reset form
        setName("");
        setVersion("1.0.0");
        setDescription("");
        setFile(null);
        fetchTemplates();
      }
    } catch (e: any) {
      toast.error(e.message || "Error uploading HTML template.");
    } finally {
      setUploading(false);
    }
  };

  const handleActivate = async (id: string, name: string) => {
    try {
      const token = localStorage.getItem("pv_token");
      const specUrl = API_BASE_URL.replace("/api/v1", "/api");
      const res = await fetch(`${specUrl}/templates/${id}/activate/`, {
        method: "PUT",
        headers: { Authorization: `Bearer ${token}` }
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json.detail || "Failed to activate template.");

      if (json.success) {
        toast.success(`Template '${name}' activated successfully.`);
        fetchTemplates();
      }
    } catch (e: any) {
      toast.error(e.message || "Error activating template.");
    }
  };

  const handleDeactivate = async (id: string, name: string) => {
    try {
      const token = localStorage.getItem("pv_token");
      const specUrl = API_BASE_URL.replace("/api/v1", "/api");
      const res = await fetch(`${specUrl}/templates/${id}/deactivate/`, {
        method: "PUT",
        headers: { Authorization: `Bearer ${token}` }
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json.detail || "Failed to deactivate template.");

      if (json.success) {
        toast.success(`Template '${name}' deactivated successfully.`);
        fetchTemplates();
      }
    } catch (e: any) {
      toast.error(e.message || "Error deactivating template.");
    }
  };

  const handleDelete = async (id: string, isActive: boolean, name: string) => {
    if (isActive) {
      toast.error("Cannot delete an active template. Please activate another template first.");
      return;
    }
    if (!window.confirm(`Are you sure you want to delete '${name}'?`)) return;

    try {
      const token = localStorage.getItem("pv_token");
      const specUrl = API_BASE_URL.replace("/api/v1", "/api");
      const res = await fetch(`${specUrl}/templates/${id}/`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` }
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json.detail || "Failed to delete template.");

      if (json.success) {
        toast.success(`Template '${name}' deleted successfully.`);
        fetchTemplates();
      }
    } catch (e: any) {
      toast.error(e.message || "Error deleting template.");
    }
  };

  const handlePreview = async (id: string, name: string) => {
    try {
      const token = localStorage.getItem("pv_token");
      const specUrl = API_BASE_URL.replace("/api/v1", "/api");
      const res = await fetch(`${specUrl}/templates/${id}/`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json.detail || "Failed to retrieve template details.");

      if (json.success && json.data) {
        setPreviewContent(json.data.html_content);
        setPreviewName(name);
        setPreviewOpen(true);
      }
    } catch (e: any) {
      toast.error(e.message || "Error loading preview.");
    }
  };

  const activeTemplate = templates.find((t) => t.is_active);

  // Generate blob URL for safe sandbox iframe preview
  const previewBlobUrl = React.useMemo(() => {
    if (!previewContent) return "";
    const blob = new Blob([previewContent], { type: "text/html" });
    return URL.createObjectURL(blob);
  }, [previewContent]);

  // Clean up blob URL to prevent memory leaks
  useEffect(() => {
    return () => {
      if (previewBlobUrl) URL.revokeObjectURL(previewBlobUrl);
    };
  }, [previewBlobUrl]);

  return (
    <div className="w-full space-y-6">
      {/* Back Button */}
      <div className="flex items-center">
        <Button 
          variant="ghost" 
          onClick={() => navigate("/dashboard")}
          className="inline-flex items-center gap-1.5 -ml-3 text-slate-500 hover:text-slate-900 dark:text-zinc-400 dark:hover:text-zinc-200 hover:bg-slate-100 dark:hover:bg-zinc-900 px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Dashboard
        </Button>
      </div>

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900 dark:text-zinc-50 leading-tight">
            HTML Template Management
          </h1>
          <p className="text-xs text-slate-500 dark:text-zinc-400 mt-1 font-medium">
            Manage, version, and activate dynamic HTML drafting studio layouts for the Generator page.
          </p>
        </div>
        <Button 
          variant="primary" 
          onClick={() => setUploadOpen(true)}
          className="shadow-sm inline-flex items-center gap-2"
        >
          <UploadCloud className="h-4 w-4" />
          Upload New Template
        </Button>
      </div>

      {/* Active Template card */}
      <Card className="border-indigo-100 dark:border-indigo-950 bg-indigo-50/30 dark:bg-indigo-950/10 overflow-hidden">
        <CardContent className="p-6">
          <div className="flex items-start gap-4">
            <div className="p-3 bg-indigo-100 dark:bg-indigo-950 rounded-xl text-indigo-600 dark:text-indigo-400 shadow-xs">
              <FileCode className="h-6 w-6" />
            </div>
            <div className="flex-1 space-y-2">
              <div className="flex items-center gap-2 flex-wrap">
                <h2 className="text-base font-bold text-slate-900 dark:text-zinc-100">
                  Current Active Template
                </h2>
                <Badge variant={activeTemplate ? "success" : "warning"}>
                  {activeTemplate ? "Active" : "No Active Template"}
                </Badge>
              </div>
              
              {activeTemplate ? (
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-1 text-xs font-semibold text-slate-600 dark:text-zinc-400">
                  <div className="flex items-center gap-1.5">
                    <FileText className="h-4 w-4 text-slate-400" />
                    <span>Name: <strong className="text-slate-900 dark:text-zinc-200">{activeTemplate.name}</strong></span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <Clock className="h-4 w-4 text-slate-400" />
                    <span>Version: <strong className="text-slate-900 dark:text-zinc-200">{activeTemplate.version}</strong></span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <User className="h-4 w-4 text-slate-400" />
                    <span>Uploaded By: <strong className="text-slate-900 dark:text-zinc-200">{activeTemplate.uploaded_by || "System"}</strong></span>
                  </div>
                  <div className="flex items-center gap-1.5 sm:col-span-3">
                    <Clock className="h-4 w-4 text-slate-400" />
                    <span>Upload Date: <strong className="text-slate-900 dark:text-zinc-200">{new Date(activeTemplate.created_at).toLocaleString()}</strong></span>
                  </div>
                </div>
              ) : (
                <div className="flex items-start gap-2 text-xs text-amber-800 dark:text-amber-400 font-medium pt-1">
                  <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
                  <p>
                    No template is currently active. The Document Generator will fall back to using the latest uploaded template. Please activate a template below.
                  </p>
                </div>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Template List Table */}
      <Card>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs font-medium">
              <thead>
                <tr className="border-b border-slate-100 dark:border-zinc-800 bg-slate-50/50 dark:bg-zinc-900/30 text-slate-500 uppercase tracking-wider text-[10px] font-bold">
                  <th className="px-6 py-4">Template Name</th>
                  <th className="px-6 py-4">Version</th>
                  <th className="px-6 py-4">Status</th>
                  <th className="px-6 py-4">Uploaded By</th>
                  <th className="px-6 py-4">Upload Date</th>
                  <th className="px-6 py-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-zinc-800/80 text-slate-700 dark:text-zinc-300">
                {loading ? (
                  <tr>
                    <td colSpan={6} className="px-6 py-12 text-center text-slate-400">
                      <div className="inline-flex items-center gap-2">
                        <div className="h-4 w-4 rounded-full border-2 border-t-indigo-600 border-r-transparent border-b-transparent border-l-transparent animate-spin" />
                        <span>Querying templates...</span>
                      </div>
                    </td>
                  </tr>
                ) : templates.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-6 py-12 text-center text-slate-400">
                      No HTML templates have been uploaded yet.
                    </td>
                  </tr>
                ) : (
                  templates.map((tpl) => (
                    <tr 
                      key={tpl.id} 
                      className="hover:bg-indigo-50/15 dark:hover:bg-indigo-950/5 border-l-2 border-l-transparent hover:border-l-indigo-650 transition-all duration-200 group"
                    >
                      <td className="px-6 py-4 font-bold text-slate-900 dark:text-zinc-100">
                        <div>
                          <div>{tpl.name}</div>
                          {tpl.description && (
                            <div className="text-[10px] font-normal text-slate-400 dark:text-zinc-500 mt-0.5 line-clamp-1">
                              {tpl.description}
                            </div>
                          )}
                        </div>
                      </td>
                      <td className="px-6 py-4 font-mono font-bold text-[11px] text-slate-500">{tpl.version}</td>
                      <td className="px-6 py-4">
                        <Badge variant={tpl.is_active ? "success" : "neutral"}>
                          {tpl.is_active ? "Active" : "Inactive"}
                        </Badge>
                      </td>
                      <td className="px-6 py-4 text-slate-650">{tpl.uploaded_by || "System"}</td>
                      <td className="px-6 py-4 text-slate-500">
                        {new Date(tpl.created_at).toLocaleDateString()} {new Date(tpl.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </td>
                      <td className="px-6 py-4 text-right space-x-1.5 whitespace-nowrap">
                        <Button 
                          variant="ghost" 
                          size="sm" 
                          onClick={() => handlePreview(tpl.id, tpl.name)}
                          className="text-slate-600 dark:text-zinc-450 hover:text-indigo-600 dark:hover:text-indigo-400 hover:bg-indigo-50 dark:hover:bg-indigo-950/20 transition-all duration-200"
                          title="Preview HTML Template"
                        >
                          <Eye className="h-3.5 w-3.5" />
                          View
                        </Button>
                        
                        {tpl.is_active ? (
                          <Button 
                            variant="outline" 
                            size="sm" 
                            onClick={() => handleDeactivate(tpl.id, tpl.name)}
                            className="border-slate-200 dark:border-zinc-800 text-slate-700 dark:text-zinc-300 hover:border-rose-350 hover:bg-rose-50 hover:text-rose-600 dark:hover:border-rose-900/40 dark:hover:bg-rose-950/20 dark:hover:text-rose-400 transition-all duration-200"
                            title="Deactivate Template"
                          >
                            <XCircle className="h-3.5 w-3.5" />
                            Deactivate
                          </Button>
                        ) : (
                          <Button 
                            variant="outline" 
                            size="sm" 
                            onClick={() => handleActivate(tpl.id, tpl.name)}
                            className="border-slate-200 dark:border-zinc-800 text-slate-700 dark:text-zinc-300 hover:border-emerald-350 hover:bg-emerald-50 hover:text-emerald-600 dark:hover:border-emerald-900/40 dark:hover:bg-emerald-950/20 dark:hover:text-emerald-400 transition-all duration-200"
                            title="Activate Template"
                          >
                            <CheckCircle className="h-3.5 w-3.5" />
                            Activate
                          </Button>
                        )}
                        
                        <Button 
                          variant="ghost" 
                          size="sm" 
                          onClick={() => handleDelete(tpl.id, tpl.is_active, tpl.name)}
                          className="text-rose-600 dark:text-rose-450 hover:bg-rose-50 dark:hover:bg-rose-950/20 hover:text-rose-700 dark:hover:text-rose-350 transition-all duration-200"
                          disabled={tpl.is_active}
                          title="Delete Template"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </Button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* Upload Template Modal */}
      <Modal isOpen={uploadOpen} onClose={() => setUploadOpen(false)} title="Upload HTML Template">
        <form onSubmit={handleUploadSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-bold text-slate-700 dark:text-zinc-350 uppercase tracking-wider mb-1.5">
              Template Name
            </label>
            <input 
              type="text" 
              className="w-full border border-slate-300 dark:border-zinc-700 rounded-lg px-3 py-2 bg-white dark:bg-zinc-800 text-sm text-slate-900 dark:text-zinc-50"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Drafting Studio v2"
              required
            />
          </div>

          <div className="grid grid-cols-3 gap-3">
            <div className="col-span-1">
              <label className="block text-xs font-bold text-slate-700 dark:text-zinc-350 uppercase tracking-wider mb-1.5">
                Version
              </label>
              <input 
                type="text" 
                className="w-full border border-slate-300 dark:border-zinc-700 rounded-lg px-3 py-2 bg-white dark:bg-zinc-800 text-sm text-slate-900 dark:text-zinc-50 font-mono"
                value={version}
                onChange={(e) => setVersion(e.target.value)}
                placeholder="1.0.0"
                required
              />
            </div>
            <div className="col-span-2">
              <label className="block text-xs font-bold text-slate-700 dark:text-zinc-350 uppercase tracking-wider mb-1.5">
                HTML File (.html only)
              </label>
              <input 
                type="file" 
                accept=".html"
                onChange={handleFileChange}
                className="w-full text-xs text-slate-500 border border-slate-300 dark:border-zinc-700 rounded-lg px-3 py-1.5 bg-white dark:bg-zinc-800 file:mr-3 file:py-1 file:px-2 file:rounded-md file:border-0 file:bg-slate-900 file:text-white file:text-[10px] file:font-semibold"
                required
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-700 dark:text-zinc-350 uppercase tracking-wider mb-1.5">
              Description (Optional)
            </label>
            <textarea 
              className="w-full border border-slate-300 dark:border-zinc-700 rounded-lg px-3 py-2 bg-white dark:bg-zinc-800 text-sm text-slate-900 dark:text-zinc-50 h-20 resize-none"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Summary of layout updates or medical safety modifications..."
            />
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button variant="outline" type="button" onClick={() => setUploadOpen(false)}>
              Cancel
            </Button>
            <Button variant="primary" type="submit" isLoading={uploading}>
              Upload
            </Button>
          </div>
        </form>
      </Modal>

      {/* Preview Modal */}
      <Modal isOpen={previewOpen} onClose={() => setPreviewOpen(false)} title={`Preview: ${previewName}`} size="full">
        <div className="space-y-4">
          <p className="text-xs text-slate-500 leading-snug">
            This preview renders the uploaded HTML template layout inside a full-width viewport container.
          </p>
          <div className="border border-slate-200 dark:border-zinc-800 rounded-xl overflow-hidden bg-slate-50">
            {previewBlobUrl ? (
              <iframe 
                src={previewBlobUrl} 
                className="w-full h-[75vh] bg-white" 
                title="HTML Template Preview viewport"
              />
            ) : (
              <div className="p-10 text-center text-xs text-slate-400">Loading viewport content...</div>
            )}
          </div>
          <div className="flex justify-end">
            <Button variant="secondary" onClick={() => setPreviewOpen(false)}>
              Close Preview
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
};

export default HtmlTemplatesPage;
