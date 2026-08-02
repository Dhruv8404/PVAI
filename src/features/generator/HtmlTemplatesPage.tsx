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
  Trash2, 
  Clock, 
  User, 
  FileText,
  ArrowLeft,
  Edit,
  Tag
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
  const [renameOpen, setRenameOpen] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  
  const [previewContent, setPreviewContent] = useState("");
  const [previewName, setPreviewName] = useState("");

  // Upload Form state
  const [name, setName] = useState("");
  const [version, setVersion] = useState("1.0.0");
  const [description, setDescription] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);

  // Edit/Rename state
  const [selectedTemplate, setSelectedTemplate] = useState<HtmlTemplate | null>(null);
  const [editName, setEditName] = useState("");
  const [editVersion, setEditVersion] = useState("");
  const [editDescription, setEditDescription] = useState("");

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

  const handleRenameClick = (tpl: HtmlTemplate) => {
    setSelectedTemplate(tpl);
    setEditName(tpl.name);
    setRenameOpen(true);
  };

  const handleRenameSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTemplate) return;
    if (!editName.trim()) {
      toast.error("Template name cannot be empty.");
      return;
    }

    try {
      const token = localStorage.getItem("pv_token");
      const specUrl = API_BASE_URL.replace("/api/v1", "/api");
      const res = await fetch(`${specUrl}/templates/${selectedTemplate.id}/rename/`, {
        method: "PUT",
        headers: { 
          "Authorization": `Bearer ${token}`,
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ name: editName.trim() })
      });
      
      const json = await res.json();
      if (!res.ok) throw new Error(json.detail || "Failed to rename template.");

      if (json.success) {
        toast.success("Template renamed successfully.");
        setRenameOpen(false);
        fetchTemplates();
      }
    } catch (e: any) {
      toast.error(e.message || "Error renaming template.");
    }
  };

  const handleEditClick = (tpl: HtmlTemplate) => {
    setSelectedTemplate(tpl);
    setEditName(tpl.name);
    setEditVersion(tpl.version);
    setEditDescription(tpl.description || "");
    setEditOpen(true);
  };

  const handleEditSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTemplate) return;

    try {
      const token = localStorage.getItem("pv_token");
      const specUrl = API_BASE_URL.replace("/api/v1", "/api");
      const res = await fetch(`${specUrl}/templates/${selectedTemplate.id}/metadata/`, {
        method: "PUT",
        headers: { 
          "Authorization": `Bearer ${token}`,
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ 
          name: editName.trim(),
          version: editVersion.trim(),
          description: editDescription.trim()
        })
      });
      
      const json = await res.json();
      if (!res.ok) throw new Error(json.detail || "Failed to update template metadata.");

      if (json.success) {
        toast.success("Template metadata updated successfully.");
        setEditOpen(false);
        fetchTemplates();
      }
    } catch (e: any) {
      toast.error(e.message || "Error updating template metadata.");
    }
  };

  const handleDelete = async (id: string, name: string) => {
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
            Manage, version, and edit available HTML drafting studio layout templates for the generator page.
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

      {/* Template List Table */}
      <Card>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs font-medium">
              <thead>
                <tr className="border-b border-slate-100 dark:border-zinc-800 bg-slate-50/50 dark:bg-zinc-900/30 text-slate-500 uppercase tracking-wider text-[10px] font-bold">
                  <th className="px-6 py-4">Template Name</th>
                  <th className="px-6 py-4">Version</th>
                  <th className="px-6 py-4">Description</th>
                  <th className="px-6 py-4">Upload Date</th>
                  <th className="px-6 py-4">Uploaded By</th>
                  <th className="px-6 py-4">Status</th>
                  <th className="px-6 py-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-zinc-800/80 text-slate-700 dark:text-zinc-300">
                {loading ? (
                  <tr>
                    <td colSpan={7} className="px-6 py-12 text-center text-slate-400">
                      <div className="inline-flex items-center gap-2">
                        <div className="h-4 w-4 rounded-full border-2 border-t-indigo-600 border-r-transparent border-b-transparent border-l-transparent animate-spin" />
                        <span>Querying templates...</span>
                      </div>
                    </td>
                  </tr>
                ) : templates.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="px-6 py-12 text-center text-slate-400">
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
                        {tpl.name}
                      </td>
                      <td className="px-6 py-4 font-mono font-bold text-[11px] text-slate-500">{tpl.version}</td>
                      <td className="px-6 py-4 max-w-xs truncate text-slate-500 dark:text-zinc-400" title={tpl.description || ""}>
                        {tpl.description || <span className="text-slate-350 dark:text-zinc-600 italic">No description</span>}
                      </td>
                      <td className="px-6 py-4 text-slate-500">
                        {new Date(tpl.created_at).toLocaleDateString()} {new Date(tpl.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </td>
                      <td className="px-6 py-4 text-slate-650">{tpl.uploaded_by || "System"}</td>
                      <td className="px-6 py-4">
                        <Badge variant="success">
                          Available
                        </Badge>
                      </td>
                      <td className="px-6 py-4 text-right space-x-1 whitespace-nowrap">
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
                        
                        <Button 
                          variant="ghost" 
                          size="sm" 
                          onClick={() => handleEditClick(tpl)}
                          className="text-slate-600 dark:text-zinc-450 hover:text-indigo-600 dark:hover:text-indigo-400 hover:bg-indigo-50 dark:hover:bg-indigo-950/20 transition-all duration-200"
                          title="Edit Metadata"
                        >
                          <Edit className="h-3.5 w-3.5" />
                          Edit Metadata
                        </Button>

                        <Button 
                          variant="ghost" 
                          size="sm" 
                          onClick={() => handleRenameClick(tpl)}
                          className="text-slate-600 dark:text-zinc-450 hover:text-indigo-600 dark:hover:text-indigo-400 hover:bg-indigo-50 dark:hover:bg-indigo-950/20 transition-all duration-200"
                          title="Rename"
                        >
                          <Tag className="h-3.5 w-3.5" />
                          Rename
                        </Button>
                        
                        <Button 
                          variant="ghost" 
                          size="sm" 
                          onClick={() => handleDelete(tpl.id, tpl.name)}
                          className="text-rose-600 dark:text-rose-450 hover:bg-rose-50 dark:hover:bg-rose-950/20 hover:text-rose-700 dark:hover:text-rose-350 transition-all duration-200"
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
              placeholder="e.g. PV Signal Drafting Assistant"
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

      {/* Rename Modal */}
      <Modal isOpen={renameOpen} onClose={() => setRenameOpen(false)} title="Rename Template">
        <form onSubmit={handleRenameSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-bold text-slate-700 dark:text-zinc-350 uppercase tracking-wider mb-1.5">
              Template Name
            </label>
            <input 
              type="text" 
              className="w-full border border-slate-300 dark:border-zinc-700 rounded-lg px-3 py-2 bg-white dark:bg-zinc-800 text-sm text-slate-900 dark:text-zinc-50"
              value={editName}
              onChange={(e) => setEditName(e.target.value)}
              placeholder="New template name..."
              required
            />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="outline" type="button" onClick={() => setRenameOpen(false)}>
              Cancel
            </Button>
            <Button variant="primary" type="submit">
              Save Name
            </Button>
          </div>
        </form>
      </Modal>

      {/* Edit Metadata Modal */}
      <Modal isOpen={editOpen} onClose={() => setEditOpen(false)} title="Edit Template Metadata">
        <form onSubmit={handleEditSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-bold text-slate-700 dark:text-zinc-350 uppercase tracking-wider mb-1.5">
              Template Name
            </label>
            <input 
              type="text" 
              className="w-full border border-slate-300 dark:border-zinc-700 rounded-lg px-3 py-2 bg-white dark:bg-zinc-800 text-sm text-slate-900 dark:text-zinc-50"
              value={editName}
              onChange={(e) => setEditName(e.target.value)}
              placeholder="Template name..."
              required
            />
          </div>
          <div>
            <label className="block text-xs font-bold text-slate-700 dark:text-zinc-350 uppercase tracking-wider mb-1.5">
              Version
            </label>
            <input 
              type="text" 
              className="w-full border border-slate-300 dark:border-zinc-700 rounded-lg px-3 py-2 bg-white dark:bg-zinc-800 text-sm text-slate-900 dark:text-zinc-50 font-mono"
              value={editVersion}
              onChange={(e) => setEditVersion(e.target.value)}
              placeholder="1.0.0"
              required
            />
          </div>
          <div>
            <label className="block text-xs font-bold text-slate-700 dark:text-zinc-350 uppercase tracking-wider mb-1.5">
              Description
            </label>
            <textarea 
              className="w-full border border-slate-300 dark:border-zinc-700 rounded-lg px-3 py-2 bg-white dark:bg-zinc-800 text-sm text-slate-900 dark:text-zinc-50 h-24 resize-none"
              value={editDescription}
              onChange={(e) => setEditDescription(e.target.value)}
              placeholder="Summary of layout updates..."
            />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="outline" type="button" onClick={() => setEditOpen(false)}>
              Cancel
            </Button>
            <Button variant="primary" type="submit">
              Save Changes
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
