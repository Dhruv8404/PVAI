import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { API_BASE_URL } from "../../config";
import { useAuth } from "../../context/AuthContext";

// Helper to scope CSS selectors to prevent styling pollution of the React shell
const scopeCss = (css: string, prefix: string): string => {
  const cleanCss = css.replace(/\/\*[\s\S]*?\*\//g, "");
  let result = "";
  let depth = 0;
  let selectorBuffer = "";
  let inMediaQuery = false;

  for (let i = 0; i < cleanCss.length; i++) {
    const char = cleanCss[i];
    if (char === "{") {
      depth++;
      const selector = selectorBuffer.trim();
      if (depth === 1) {
        if (selector.startsWith("@")) {
          result += selector + " {";
          inMediaQuery = true;
        } else if (selector) {
          const prefixed = selector
            .split(",")
            .map(s => {
              const trimmed = s.trim();
              if (!trimmed) return "";
              if (trimmed === "html" || trimmed === "body" || trimmed === ":root") {
                return prefix;
              }
              return `${prefix} ${trimmed}`;
            })
            .join(", ");
          result += prefixed + " {";
        } else {
          result += "{";
        }
      } else if (depth === 2 && inMediaQuery) {
        if (selector) {
          const prefixed = selector
            .split(",")
            .map(s => {
              const trimmed = s.trim();
              if (!trimmed) return "";
              if (trimmed === "html" || trimmed === "body" || trimmed === ":root") {
                return prefix;
              }
              return `${prefix} ${trimmed}`;
            })
            .join(", ");
          result += prefixed + " {";
        } else {
          result += "{";
        }
      } else {
        result += "{";
      }
      selectorBuffer = "";
    } else if (char === "}") {
      depth--;
      result += "}";
      if (depth === 0) {
        inMediaQuery = false;
      }
      selectorBuffer = "";
    } else {
      if (depth === 0 || (depth === 1 && inMediaQuery)) {
        selectorBuffer += char;
      } else {
        result += char;
      }
    }
  }
  return result;
};

interface TemplateRendererProps {
  bodyContent: string;
  stylesText: string;
}

const TemplateRenderer: React.FC<TemplateRendererProps> = React.memo(({ bodyContent, stylesText }) => {
  return (
    <div className="generator-template">
      <style dangerouslySetInnerHTML={{ __html: `
        .generator-template {
          all: unset;
        }
        /* Reset standalone HTML/Body assumptions in templates */
        .generator-template html,
        .generator-template body,
        .generator-template #root,
        .generator-template main,
        .generator-template .page,
        .generator-template .container,
        .generator-template .wrapper,
        .generator-template .wrap,
        .generator-template .content,
        .generator-template .main {
          background: transparent !important;
          padding: 0 !important;
          margin: 0 !important;
          max-width: 100% !important;
          width: 100% !important;
          height: auto !important;
          min-height: auto !important;
          box-shadow: none !important;
          border: 0 !important;
        }
        ${stylesText}
        
        /* Layout overrides */
        .generator-template .wrap {
          max-width: 100% !important;
          padding: 0 !important;
        }
        .generator-template body {
          font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif !important;
          color: #1e293b !important;
        }
        .generator-template .grid {
          grid-template-columns: 360px 1fr !important;
        }
        .generator-template table {
          width: 100% !important;
          border-collapse: collapse !important;
          margin-bottom: 1rem !important;
        }
        .generator-template th,
        .generator-template td {
          border: 1px solid #e2e8f0 !important;
          padding: 8px 12px !important;
        }
        .generator-template .table-responsive,
        .generator-template .table-wrapper {
          overflow-x: auto !important;
          max-width: 100% !important;
          width: 100% !important;
          display: block !important;
        }
        
        /* Media & Form constraints */
        .generator-template img,
        .generator-template video {
          max-width: 100% !important;
          height: auto !important;
        }
        .generator-template form,
        .generator-template .form-container {
          max-width: 100% !important;
        }
        .generator-template input,
        .generator-template select,
        .generator-template textarea {
          max-width: 100% !important;
        }
        .generator-template .card,
        .generator-template .metric,
        .generator-template .settings,
        .generator-template .metric-card {
          box-shadow: 0 1px 3px rgba(0,0,0,0.05) !important;
        }
        .generator-template .btn {
          display: inline-flex !important;
          align-items: center !important;
          justify-content: center !important;
          font-size: 13px !important;
          font-weight: 600 !important;
        }
        .generator-template .btn:hover {
          filter: brightness(0.96) !important;
        }
        .generator-template .btn.primary,
        .generator-template .btn.blue {
          background-color: #0f172a !important;
          color: #ffffff !important;
          border-color: #0f172a !important;
        }
        .generator-template .btn.primary:hover,
        .generator-template .btn.blue:hover {
          background-color: #1e293b !important;
        }
      `}} />
      <div dangerouslySetInnerHTML={{ __html: bodyContent }} />
    </div>
  );
});

export const GeneratorPage: React.FC = () => {
  const { user, refreshSession } = useAuth();
  const navigate = useNavigate();
  const { templateId: routeTemplateId } = useParams<{ templateId?: string }>();
  
  // Template states
  const [templates, setTemplates] = useState<any[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState<any | null>(null);
  
  // Active loaded template content state
  const [templateId, setTemplateId] = useState<string>("");
  const [rawHtml, setRawHtml] = useState<string>("");
  const [bodyContent, setBodyContent] = useState<string>("");
  const [stylesText, setStylesText] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>("");

  const remainingTokens = user?.role === "Admin" ? 9999 : (user?.reportLimit || 5) - (user?.documentsGenerated || 0);

  // 1. Fetch available templates list
  const fetchTemplatesList = async (): Promise<any[]> => {
    try {
      const token = localStorage.getItem("pv_token");
      const headers: Record<string, string> = token ? { "Authorization": `Bearer ${token}` } : {};
      const specUrl = API_BASE_URL.replace("/api/v1", "/api");
      const res = await fetch(`${specUrl}/templates/`, { headers });
      if (!res.ok) throw new Error("Failed to load templates list.");
      const json = await res.json();
      if (json.success && json.data) {
        setTemplates(json.data);
        return json.data;
      }
      return [];
    } catch (e: any) {
      console.error(e);
      setError(e.message || "Error fetching available templates.");
      return [];
    }
  };

  // 2. Fetch specific template HTML content and parse it
  const fetchTemplateContent = async (id: string) => {
    setLoading(true);
    setError("");
    try {
      const token = localStorage.getItem("pv_token");
      const headers: Record<string, string> = token ? { "Authorization": `Bearer ${token}` } : {};
      const specUrl = API_BASE_URL.replace("/api/v1", "/api");
      const res = await fetch(`${specUrl}/templates/${id}/`, { headers });
      if (!res.ok) throw new Error("Failed to load selected template layout.");
      const json = await res.json();
      
      if (json.success && json.data) {
        const raw = json.data.html_content;
        setRawHtml(raw);
        setTemplateId(id);

        // Extract content using DOMParser
        const parser = new DOMParser();
        const doc = parser.parseFromString(raw, "text/html");

        // Extract inner body content
        const bodyHtml = doc.body ? doc.body.innerHTML : raw;
        setBodyContent(bodyHtml);

        // Extract and scope styles to .generator-template
        const styleElements = doc.querySelectorAll("style");
        const rawStyles = Array.from(styleElements)
          .map((el) => el.textContent || "")
          .join("\n");
        const scopedStyles = scopeCss(rawStyles, ".generator-template");
        setStylesText(scopedStyles);
      } else {
        setError(json.message || "Failed to load template layout.");
      }
    } catch (e: any) {
      console.error(e);
      setError(e.message || "Error loading template details.");
    } finally {
      setLoading(false);
    }
  };

  // 3. Load templates list once on mount
  useEffect(() => {
    const loadList = async () => {
      const list = await fetchTemplatesList();
      if (list.length === 0) {
        setError("No templates available. Please upload a template in the Templates Admin page first.");
        setLoading(false);
      }
    };
    loadList();
  }, []);

  // 4. Handle route updates and active template sync
  useEffect(() => {
    if (templates.length === 0) return;

    let targetId = routeTemplateId;
    
    // If opened base /generator path, redirect to last saved or first available
    if (!targetId) {
      const savedId = sessionStorage.getItem("pv_selected_template_id");
      if (savedId && templates.some((t: any) => t.id === savedId)) {
        targetId = savedId;
      } else {
        targetId = templates[0].id;
      }
      navigate(`/generator/${targetId}`, { replace: true });
      return;
    }

    const activeTpl = templates.find((t: any) => t.id === targetId);
    if (activeTpl) {
      setSelectedTemplate(activeTpl);
      sessionStorage.setItem("pv_selected_template_id", targetId);
      fetchTemplateContent(targetId);
    } else {
      // Invalid ID in path -> redirect to first template
      navigate(`/generator/${templates[0].id}`, { replace: true });
    }
  }, [routeTemplateId, templates]);

  // 5. Script Injection side-effect
  useEffect(() => {
    if (!bodyContent || !rawHtml) return;

    // Parse raw HTML again to extract and execute script blocks
    const parser = new DOMParser();
    const doc = parser.parseFromString(rawHtml, "text/html");
    const scripts = doc.querySelectorAll("script");

    scripts.forEach((oldScript) => {
      const newScript = document.createElement("script");
      newScript.setAttribute("data-injected-template-script", "true");
      if (oldScript.src) {
        newScript.src = oldScript.src;
        newScript.async = true;
      } else {
        // Convert const and let to var globally to allow re-declarations on component mount cycles
        const scriptText = (oldScript.text || "")
          .replace(/\bconst\s+/g, "var ")
          .replace(/\blet\s+/g, "var ");
        newScript.text = scriptText;
      }
      document.body.appendChild(newScript);
    });

    return () => {
      const injected = document.querySelectorAll("script[data-injected-template-script='true']");
      injected.forEach((el) => el.remove());
    };
  }, [bodyContent, rawHtml]);

  const getCompiledReportHtml = (): string => {
    const sOutput = document.getElementById("sOutput");
    const dmeOutput = document.getElementById("dmeOutput");
    const qPara = document.getElementById("qPara") as HTMLTextAreaElement;
    const qPt = document.getElementById("qPt") as HTMLTextAreaElement;
    const spOutput = document.getElementById("spOutput");
    
    const sLastHtml = (window as any).sLastHtml;
    const dmeLastHtml = (window as any).dmeLastHtml;
    const qLastHtml = (window as any).qLastHtml;
    const specialStore = (window as any).specialStore || {};

    let htmlBody = `
      <!DOCTYPE html>
      <html>
      <head>
        <meta charset="utf-8">
        <style>
          body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; padding: 30px; line-height: 1.6; color: #1e293b; background-color: #f8fafc; }
          .section-box { background: white; border: 1px solid #e2e8f0; border-radius: 12px; padding: 24px; margin-bottom: 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
          h2 { font-size: 16px; font-weight: 700; color: #4f46e5; text-transform: uppercase; margin-top: 0; border-bottom: 2px solid #f1f5f9; padding-bottom: 8px; }
          pre { white-space: pre-wrap; font-family: monospace; font-size: 12px; background: #f8fafc; padding: 12px; border: 1px solid #e2e8f0; border-radius: 6px; }
          .empty { color: #94a3b8; font-style: italic; }
        </style>
      </head>
      <body>
        <div style="max-width: 800px; margin: 0 auto;">
          <h1 style="font-size: 22px; margin-bottom: 30px; color: #0f172a; border-bottom: 3px solid #6366f1; padding-bottom: 12px;">Draft Compilation Report</h1>
      `;

    if (sLastHtml && sOutput) {
      htmlBody += `
        <div class="section-box">
          <h2>Section 01/02</h2>
          <div>${sOutput.innerHTML}</div>
        </div>
      `;
    }
    if (dmeLastHtml && dmeOutput) {
      htmlBody += `
        <div class="section-box">
          <h2>DME</h2>
          <div>${dmeOutput.innerHTML}</div>
        </div>
      `;
    }
    if (qLastHtml && qPara && qPt) {
      htmlBody += `
        <div class="section-box">
          <h2>Non-DME</h2>
          <h3 style="font-size: 14px; margin-bottom: 6px; color: #475569;">Paragraph</h3>
          <pre>${qPara.value}</pre>
          <h3 style="font-size: 14px; margin-bottom: 6px; color: #475569;">PT List</h3>
          <pre>${qPt.value}</pre>
        </div>
      `;
    }

    const spKeys = Object.keys(specialStore);
    if (spKeys.length > 0) {
      htmlBody += `<div class="section-box"><h2>Special Circumstances</h2>`;
      spKeys.forEach(k => {
        const storeItem = specialStore[k];
        if (storeItem) {
          htmlBody += `
            <div style="margin-bottom: 16px;">
              <h3 style="font-size: 13px; color: #334155; margin-bottom: 4px;">${storeItem.title || k}</h3>
              <pre>${storeItem.paragraph || ''}</pre>
            </div>
          `;
        }
      });
      htmlBody += `</div>`;
    } else if (spOutput && spOutput.innerText.trim()) {
      htmlBody += `
        <div class="section-box">
          <h2>Special Circumstances</h2>
          <div>${spOutput.innerHTML}</div>
        </div>
      `;
    }

    htmlBody += `</div></body></html>`;
    return htmlBody;
  };

  // 6. Hook button handlers inside template to log progress on completion
  useEffect(() => {
    if (!bodyContent || !rawHtml || !templateId) return;

    const logGenerationOnBackend = async (
      reportType: string,
      reportContent: string,
      status: string = "Success",
      failedReason?: string
    ): Promise<boolean> => {
      const token = localStorage.getItem("pv_token");
      if (!token) return false;

      // Extract actual Excel workbook name if present
      const fileInput = document.getElementById("fBook") as HTMLInputElement;
      const excelFileName = fileInput && fileInput.files && fileInput.files[0]
        ? fileInput.files[0].name
        : "dynamic_drafting_studio.xlsx";

      const formData = new FormData();
      formData.append("template_id", templateId);
      formData.append("excel_file_name", excelFileName);
      formData.append("report_type", reportType);
      formData.append("report_content", reportContent);
      formData.append("status", status);
      if (failedReason) {
        formData.append("failed_reason", failedReason);
      }

      const response = await fetch(`${API_BASE_URL}/documents/log-generation`, {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${token}`
        },
        body: formData
      });

      if (!response.ok) {
        const errJson = await response.json();
        throw new Error(errJson.detail || "Failed to log report generation on backend.");
      }

      // Refresh the context user session to update tokensGenerated immediately
      await refreshSession();
      return true;
    };

    // Map buttons to their template generator functions
    const runBtns = [
      { id: "sRun", func: "runSection", label: "Section 01_02" },
      { id: "dmeRun", func: "runDme", label: "DME" },
      { id: "qRun", func: "runNonDme", label: "Non-DME" },
      { id: "spRun", func: "runSpecialCircumstances", label: "Special Circumstances" },
      { id: "runAll", func: "runAllAvailable", label: "All Sections" }
    ];

    // Wait a brief moment to ensure template scripts have executed and registered on window
    const timer = setTimeout(() => {
      runBtns.forEach(({ id, func, label }) => {
        const btn = document.getElementById(id);
        const originalFunc = (window as any)[func];
        if (btn && originalFunc && !(originalFunc as any).__isWrapped) {
          
          const wrappedFunc = async (event: Event) => {
            if (user?.role !== "Admin" && remainingTokens <= 0) {
              alert("You have reached your report generation quota limit. Please contact an administrator to increase your allocation limit.");
              return;
            }

            let compileSuccess = false;
            let errorMsg = "";

            try {
              await originalFunc(event);
              compileSuccess = true;
            } catch (err: any) {
              console.error("Template generation error:", err);
              errorMsg = err.message || "Unknown client-side generation error";
            }

            try {
              if (compileSuccess) {
                const reportContent = getCompiledReportHtml();
                const success = await logGenerationOnBackend(label, reportContent, "Success");
                if (success && user?.role !== "Admin") {
                  alert("Report generated successfully! 1 token deducted from your quota.");
                }
              } else {
                await logGenerationOnBackend(label, "", "Failed", errorMsg);
                alert(`Report generation failed: ${errorMsg}`);
              }
            } catch (backendErr: any) {
              console.error("Failed to log generation to backend:", backendErr);
            }
          };

          (wrappedFunc as any).__isWrapped = true;
          (wrappedFunc as any).original = originalFunc;
          
          (window as any)[func] = wrappedFunc;
          btn.onclick = wrappedFunc;
        }
      });
    }, 150);

    return () => {
      clearTimeout(timer);
      runBtns.forEach(({ id, func }) => {
        const btn = document.getElementById(id);
        const wrapped = (window as any)[func];
        if (wrapped && wrapped.__isWrapped && wrapped.original) {
          (window as any)[func] = wrapped.original;
          if (btn) btn.onclick = wrapped.original;
        }
      });
    };
  }, [bodyContent, rawHtml, templateId, user, remainingTokens, refreshSession]);

  if (loading && !selectedTemplate) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 rounded-full border-4 border-t-indigo-600 border-r-transparent border-b-transparent border-l-transparent animate-spin" />
          <span className="text-xs font-semibold text-slate-500">Querying available templates...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Template Header Banner */}
      {selectedTemplate && (
        <div className="flex flex-col space-y-1 p-4 bg-indigo-50/20 dark:bg-indigo-950/5 border border-indigo-100 dark:border-indigo-950/20 rounded-xl shadow-2xs">
          <span className="text-[10px] font-bold text-indigo-600 dark:text-indigo-400 uppercase tracking-wider">
            Active Generation Studio
          </span>
          <h2 className="text-base font-bold text-slate-800 dark:text-zinc-150">
            {selectedTemplate.name} <span className="text-xs font-mono font-normal text-slate-400 dark:text-zinc-500">v{selectedTemplate.version}</span>
          </h2>
          {selectedTemplate.description && (
            <p className="text-xs text-slate-500 dark:text-zinc-400 mt-1">
              {selectedTemplate.description}
            </p>
          )}
        </div>
      )}

      {/* Quota Limit Banner */}
      {user?.role !== "Admin" && remainingTokens <= 0 && (
        <div className="p-4 bg-amber-50 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-900/30 rounded-xl text-amber-700 dark:text-amber-400 text-xs font-semibold leading-relaxed flex items-center gap-3 animate-fade-in">
          <span className="h-2 w-2 rounded-full bg-amber-500 animate-pulse flex-shrink-0" />
          <span>
            Quota Limit Reached: You have reached your report generation quota limit of {user?.reportLimit} reports.
            Please contact your administrator to increase your allocation limit.
          </span>
        </div>
      )}

      {user?.role !== "Admin" && remainingTokens > 0 && (
        <div className="p-3 bg-indigo-50/50 dark:bg-indigo-950/20 border border-indigo-100 dark:border-indigo-950/40 rounded-xl text-indigo-700 dark:text-indigo-400 text-xs font-semibold leading-relaxed flex items-center gap-3">
          <span className="h-2 w-2 rounded-full bg-indigo-600 animate-pulse flex-shrink-0" />
          <span>
            Available Token Balance: {remainingTokens} of {user?.reportLimit} generations remaining.
          </span>
        </div>
      )}

      {/* If loading a specific template */}
      {loading ? (
        <div className="flex items-center justify-center min-h-[300px]">
          <div className="flex flex-col items-center gap-3">
            <div className="h-6 w-6 rounded-full border-4 border-t-indigo-600 border-r-transparent border-b-transparent border-l-transparent animate-spin" />
            <span className="text-xs font-semibold text-slate-500">Loading template layout...</span>
          </div>
        </div>
      ) : error ? (
        <div className="p-6 bg-red-50 dark:bg-rose-950/20 border border-red-200 dark:border-rose-900/30 rounded-xl text-red-700 dark:text-red-400 text-sm">
          <h4 className="font-bold mb-1">Template Loader Error</h4>
          <p>{error}</p>
        </div>
      ) : (
        <TemplateRenderer bodyContent={bodyContent} stylesText={stylesText} />
      )}
    </div>
  );
};

export default GeneratorPage;
