import React, { useEffect, useState } from "react";
import { API_BASE_URL } from "../../config";

export const GeneratorPage: React.FC = () => {
  const [html, setHtml] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>("");

  useEffect(() => {
    const fetchTemplate = async () => {
      try {
        const token = localStorage.getItem("pv_token");
        const headers: Record<string, string> = {};
        if (token) {
          headers["Authorization"] = `Bearer ${token}`;
        }
        const res = await fetch(`${API_BASE_URL}/templates/current`, { headers });
        if (!res.ok) {
          throw new Error("Failed to load current active template.");
        }
        const data = await res.json();
        if (data.success && data.data) {
          setHtml(data.data.html_content);
        } else {
          setError(data.message || "No active template available.");
        }
      } catch (e: any) {
        setError(e.message || "Error fetching template.");
      } finally {
        setLoading(false);
      }
    };
    fetchTemplate();
  }, []);

  useEffect(() => {
    if (!html) return;

    // Scope body/html styles to prevent breaking the outer dashboard layout/backgrounds
    const scopedHtml = html
      .replace(/body\s*\{/gi, ".pv-drafting-studio-wrapper {")
      .replace(/html\s*\{/gi, ".pv-drafting-studio-wrapper {");

    // Execute scripts contained in the HTML template
    const div = document.createElement("div");
    div.innerHTML = scopedHtml;
    const scripts = div.querySelectorAll("script");

    scripts.forEach((oldScript) => {
      const newScript = document.createElement("script");
      if (oldScript.src) {
        newScript.src = oldScript.src;
        newScript.async = true;
      } else {
        newScript.text = oldScript.text;
      }
      document.body.appendChild(newScript);
    });

    return () => {
      // Injected scripts are left as global declarations, standard for this setup
    };
  }, [html]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 rounded-full border-4 border-t-indigo-600 border-r-transparent border-b-transparent border-l-transparent animate-spin" />
          <span className="text-xs font-semibold text-slate-500">Loading dynamic drafting studio...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 bg-red-50 dark:bg-rose-950/20 border border-red-200 dark:border-rose-900/30 rounded-xl text-red-700 dark:text-red-400 text-sm">
        <h4 className="font-bold mb-1">Template Loader Error</h4>
        <p>{error}</p>
      </div>
    );
  }

  // Inject scoped HTML inside the wrapper class container
  return (
    <div className="pv-drafting-studio-wrapper">
      <div dangerouslySetInnerHTML={{ __html: html }} />
    </div>
  );
};

export default GeneratorPage;
