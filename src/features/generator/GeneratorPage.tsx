import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  FileText, 
  BarChart3, 
  Activity, 
  Calendar, 
  Cpu, 
  Layers, 
  UploadCloud, 
  FileSpreadsheet, 
  CheckCircle2, 
  XCircle, 
  Loader2, 
  ArrowRight,
  Eye, 
  Copy, 
  Download, 
  Save, 
  RotateCcw,
  Info
} from 'lucide-react';
import { mockDb } from '../../lib/mockDb';
import { useAuth } from '../../context/AuthContext';
import { useToast } from '../../components/ui/Toast';
import { Card, CardHeader, CardTitle, CardContent, CardDescription, CardFooter } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Badge } from '../../components/ui/Badge';
import { Drawer } from '../../components/ui/Drawer';

interface TemplateCard {
  id: string;
  name: string;
  description: string;
  supportedFileTypes: string[];
  lastUpdated: string;
  icon: any;
  requiredColumns: string[];
}

export const GeneratorPage: React.FC = () => {
  const { user, addNotification } = useAuth();
  const { toast } = useToast();
  const navigate = useNavigate();

  const [templates, setTemplates] = useState<TemplateCard[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState<TemplateCard | null>(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  
  // Creation Stepper State: 1 = Upload, 2 = Process, 3 = Preview
  const [step, setStep] = useState(1);
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [dragActive, setDragActive] = useState(false);
  
  // Validation status
  const [validationResult, setValidationResult] = useState<{
    status: 'idle' | 'validating' | 'success' | 'error';
    message: string;
    columnsFound?: string[];
  }>({ status: 'idle', message: '' });

  const [processingLogs, setProcessingLogs] = useState<string[]>([]);
  
  // Generated output
  const [generatedHtml, setGeneratedHtml] = useState('');
  const [outputDocName, setOutputDocName] = useState('');

  const fileInputRef = useRef<HTMLInputElement>(null);

  const iconsMap: Record<string, any> = {
    FileText,
    BarChart3,
    Activity
  };

  useEffect(() => {
    const loadTemplates = async () => {
      try {
        const token = localStorage.getItem('pv_token');
        const res = await fetch('http://127.0.0.1:8000/api/v1/templates', {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        const json = await res.json();
        if (json.success && json.data) {
          const list = json.data.map((t: any) => {
            const idLower = t.name.toLowerCase();
            const localId = idLower.includes('psur') ? 'psur' : idLower.includes('quant') ? 'quant' : 'pv_auto';
            const iconStr = localId === 'psur' ? 'FileText' : localId === 'quant' ? 'BarChart3' : 'Activity';
            return {
              id: localId,
              realUuid: t.id,
              name: t.name,
              description: t.description,
              supportedFileTypes: localId === 'psur' ? ['.xlsx', '.xls'] : localId === 'quant' ? ['.xlsx', '.csv'] : ['.xlsx'],
              lastUpdated: t.updated_at,
              icon: iconsMap[iconStr] || FileText,
              requiredColumns: t.required_files
            };
          });
          setTemplates(list);
          return;
        }
      } catch (err) {
        console.warn('Backend templates offline. Using mock database.');
      }
      
      const list = mockDb.getTemplates().map(t => ({
        ...t,
        icon: iconsMap[t.icon] || FileText,
        requiredColumns: 
          t.id === 'psur' ? ['Event ID', 'Severity', 'Date'] :
          t.id === 'quant' ? ['Method ID', 'Value', 'Z-Score'] :
          ['ID', 'AutoCode', 'Priority']
      }));
      setTemplates(list);
    };

    loadTemplates();
  }, []);

  // Drag and drop handlers
  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      processSelectedFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      processSelectedFile(e.target.files[0]);
    }
  };

  const processSelectedFile = (file: File) => {
    setUploadedFile(file);
    setValidationResult({ status: 'validating', message: 'Analyzing Excel worksheet layout...' });
    
    // Simulate column checks
    setTimeout(() => {
      if (!selectedTemplate) return;
      const lowerName = file.name.toLowerCase();
      
      // Validation schema simulation logic
      // If file contains "fail" or "corrupt", we trigger a mock error
      if (lowerName.includes('fail') || lowerName.includes('corrupt') || lowerName.includes('invalid')) {
        setValidationResult({
          status: 'error',
          message: `SchemaValidationError: Required columns [${selectedTemplate.requiredColumns.join(', ')}] were missing in file "${file.name}".`,
          columnsFound: ['ID', 'RandomColumn', 'Status']
        });
        toast.error('File schema check failed.', 'Validation Error');
        return;
      }

      setValidationResult({
        status: 'success',
        message: 'Schema matches template specifications. Ready to compile report.',
        columnsFound: [...selectedTemplate.requiredColumns, 'Notes', 'CreatedBy']
      });
      toast.success('Excel workbook validated successfully.', 'Format Accepted');
    }, 1200);
  };

  const loadDemoFile = () => {
    if (!selectedTemplate) return;
    const mockFile = new File(
      ["mock"], 
      `${selectedTemplate.id.toUpperCase()}_Source_Data_Seed.xlsx`, 
      { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" }
    );
    processSelectedFile(mockFile);
  };

  // Stepper Stage 2: Processing Report Engine
  const startReportCompilation = async () => {
    setStep(2);
    setProcessingLogs(['Initializing Document generation compiler...']);

    const token = localStorage.getItem('pv_token');
    if (selectedTemplate && (selectedTemplate as any).realUuid && token && uploadedFile) {
      try {
        setProcessingLogs(prev => [...prev, 'Uploading spreadsheet file to FastAPI server...']);
        
        const formData = new FormData();
        formData.append('template_id', (selectedTemplate as any).realUuid);
        formData.append('file', uploadedFile);

        const res = await fetch('http://127.0.0.1:8000/api/v1/documents/generate', {
          method: 'POST',
          headers: { 'Authorization': `Bearer ${token}` },
          body: formData
        });
        const json = await res.json();
        
        if (json.success && json.data) {
          setProcessingLogs(prev => [
            ...prev,
            'Excel file accepted by backend.',
            'Executing strategy processing algorithm...',
            `Completed successfully in ${json.data.execution_time_ms}ms.`,
            'Rendering HTML preview layout...'
          ]);
          
          const downloadRes = await fetch(`http://127.0.0.1:8000/api/v1/downloads/${json.data.id}?format=HTML`, {
            headers: { 'Authorization': `Bearer ${token}` }
          });
          const htmlText = await downloadRes.text();
          
          setTimeout(() => {
            setGeneratedHtml(htmlText);
            setOutputDocName(json.data.name);
            setStep(3);
            toast.success('Document output rendered successfully.', 'Generation Finished');
          }, 800);
          return;
        } else {
          throw new Error(json.message || 'Generation failed.');
        }
      } catch (err: any) {
        console.warn('API document compilation failed, falling back to mock compiler:', err.message);
        setProcessingLogs(prev => [...prev, `API Error: ${err.message}. Initializing offline backup compiler...`]);
      }
    }

    // Offline mock compiler fallback
    const stages = [
      { delay: 600, log: 'Loading worksheet schemas...' },
      { delay: 1200, log: 'Extracting safety event values and headers...' },
      { delay: 1800, log: `Calculating validation checksums for [${selectedTemplate?.requiredColumns.join(', ')}]...` },
      { delay: 2400, log: 'Building quantitative metrics data frames...' },
      { delay: 3000, log: 'Mapping HTML markup templates and styling tokens...' },
      { delay: 3600, log: 'Rendering document HTML output format...' }
    ];

    stages.forEach((s, idx) => {
      setTimeout(() => {
        setProcessingLogs(prev => [...prev, s.log]);
        
        if (idx === stages.length - 1) {
          compileHtmlOutput();
        }
      }, s.delay);
    });
  };

  const compileHtmlOutput = () => {
    if (!selectedTemplate || !uploadedFile) return;
    
    const docName = `${selectedTemplate.id.toUpperCase()}_Report_${new Date().toISOString().substring(0,10)}_V1`;
    setOutputDocName(docName);

    // Build unique preview HTML depending on template
    let content = '';
    if (selectedTemplate.id === 'psur') {
      content = `
        <div style="font-family: sans-serif; padding: 24px; color: #1f2937; background: #ffffff;">
          <h1 style="color: #4f46e5; border-bottom: 2px solid #e5e7eb; padding-bottom: 12px; margin-top: 0;">Periodic Safety Update Report (PSUR)</h1>
          <p style="color: #6b7280; font-size: 13px;">Source Worksheet: ${uploadedFile.name} | Compiled on: ${new Date().toLocaleString()}</p>
          
          <div style="margin: 20px 0; padding: 16px; border: 1px solid #e5e7eb; border-radius: 8px; background-color: #f9fafb;">
            <h3 style="margin-top: 0; color: #111827;">Compliance Check Overview</h3>
            <p style="font-size: 14px;">Total Row Entries Checked: <strong>324 Adverse Events</strong></p>
            <p style="font-size: 14px;">Severe Adverse Cases Detected: <strong style="color: #ef4444;">12 (Critical)</strong></p>
            <p style="font-size: 14px;">Safety Index Variance: <strong>+1.2% (Within tolerances)</strong></p>
          </div>
          
          <div style="margin-top: 24px;">
            <h3 style="color: #111827;">Data Logs Audit</h3>
            <table style="width: 100%; border-collapse: collapse;">
              <thead>
                <tr style="background: #f3f4f6; text-align: left;">
                  <th style="padding: 10px; border: 1px solid #e5e7eb; font-size: 13px;">Event ID</th>
                  <th style="padding: 10px; border: 1px solid #e5e7eb; font-size: 13px;">Severity</th>
                  <th style="padding: 10px; border: 1px solid #e5e7eb; font-size: 13px;">Date</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td style="padding: 10px; border: 1px solid #e5e7eb; font-size: 13px;">AE-2093</td>
                  <td style="padding: 10px; border: 1px solid #e5e7eb; font-size: 13px; color: #ef4444;">HIGH</td>
                  <td style="padding: 10px; border: 1px solid #e5e7eb; font-size: 13px;">2026-06-29</td>
                </tr>
                <tr style="background: #f9fafb;">
                  <td style="padding: 10px; border: 1px solid #e5e7eb; font-size: 13px;">AE-2094</td>
                  <td style="padding: 10px; border: 1px solid #e5e7eb; font-size: 13px; color: #f59e0b;">MEDIUM</td>
                  <td style="padding: 10px; border: 1px solid #e5e7eb; font-size: 13px;">2026-06-29</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      `;
    } else if (selectedTemplate.id === 'quant') {
      content = `
        <div style="font-family: sans-serif; padding: 24px; color: #1f2937; background: #ffffff;">
          <h1 style="color: #0d9488; border-bottom: 2px solid #e5e7eb; padding-bottom: 12px; margin-top: 0;">Quantitative Method (Non-DME) Analysis</h1>
          <p style="color: #6b7280; font-size: 13px;">Source Worksheet: ${uploadedFile.name} | Compiled on: ${new Date().toLocaleString()}</p>
          
          <div style="margin: 20px 0; padding: 16px; border: 1px solid #e5e7eb; border-radius: 8px; background-color: #f0fdfa;">
            <h3 style="margin-top: 0; color: #115e59;">Z-Score Quantitative Check</h3>
            <p style="font-size: 14px;">Active Method Indices Checked: <strong>1,490 Records</strong></p>
            <p style="font-size: 14px;">Statistical Critical Z-Score Threshold: <strong>> 2.58</strong></p>
            <p style="font-size: 14px; color: #b91c1c; font-weight: bold;">Outliers Flagged: 2 Methods Detected</p>
          </div>
        </div>
      `;
    } else {
      content = `
        <div style="font-family: sans-serif; padding: 24px; color: #1f2937; background: #ffffff;">
          <h1 style="color: #7c3aed; border-bottom: 2px solid #e5e7eb; padding-bottom: 12px; margin-top: 0;">PV Auto Signal Detection Report</h1>
          <p style="color: #6b7280; font-size: 13px;">Source Worksheet: ${uploadedFile.name} | Compiled on: ${new Date().toLocaleString()}</p>
          
          <div style="margin: 20px 0; padding: 16px; border: 1px solid #e5e7eb; border-radius: 8px; background-color: #faf5ff;">
            <h3 style="margin-top: 0; color: #6b21a8;">Signal Detections Triggered</h3>
            <p style="font-size: 14px;">Total AutoCode Inputs Processed: <strong>14 AEs</strong></p>
            <p style="font-size: 14px;">PRR Ratio Alert Threshold: <strong>>= 2.0</strong></p>
          </div>
        </div>
      `;
    }

    setTimeout(() => {
      setGeneratedHtml(content);
      setStep(3);
      toast.success('Document output rendered successfully.', 'Generation Finished');
    }, 400);
  };

  // Actions on preview
  const handleSaveToVault = () => {
    if (!selectedTemplate || !uploadedFile) return;

    try {
      mockDb.addDocument({
        name: outputDocName,
        templateId: selectedTemplate.id,
        templateName: selectedTemplate.name,
        createdBy: user?.name || 'Workspace Account',
        createdById: user?.id || 'usr-1',
        status: 'Success',
        excelFileName: uploadedFile.name,
        htmlContent: generatedHtml
      });

      toast.success('Document saved to workspace Vault.', 'Saved to Vault');
      addNotification(`Saved newly generated document "${outputDocName}".`);
      setIsDrawerOpen(false);
      resetGeneratorDrawer();
      navigate('/history');
    } catch (err: any) {
      toast.error(err.message || 'Error occurred.');
    }
  };

  const handleCopyClipboard = () => {
    navigator.clipboard.writeText(generatedHtml);
    toast.success('Markup content copied to clipboard.', 'Copied');
  };

  const handleDownloadHtml = () => {
    const blob = new Blob([generatedHtml], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${outputDocName}.html`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    
    // Track download in logs if saved
    toast.success('Downloaded compiled HTML file package.', 'Downloaded HTML');
  };

  const resetGeneratorDrawer = () => {
    setStep(1);
    setUploadedFile(null);
    setValidationResult({ status: 'idle', message: '' });
    setProcessingLogs([]);
    setGeneratedHtml('');
    setOutputDocName('');
  };

  const handleCardGenerate = (tpl: TemplateCard) => {
    if (user && user.status === 'Inactive') {
      toast.error('Permissions revoked. Account suspended.');
      return;
    }
    
    // Check if user has permissions for this template
    if (!user?.allowedTemplates.includes(tpl.id)) {
      toast.warning(`You do not have access rights to run "${tpl.name}". Contact Admin.`, 'Access Restricted');
      return;
    }

    setSelectedTemplate(tpl);
    setIsDrawerOpen(true);
    resetGeneratorDrawer();
  };

  const handleCardHistory = (tplId: string) => {
    navigate(`/history?template=${tplId}`);
  };

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div>
        <h1 className="text-xl font-bold text-slate-900 dark:text-zinc-50 leading-tight">
          Document Generation Workspace
        </h1>
        <p className="text-xs text-slate-500 dark:text-zinc-400 mt-1 font-medium">
          Select document compiler templates, validate data sets, and extract HTML files.
        </p>
      </div>

      {/* Grid of Templates cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {templates.map(tpl => {
          const Icon = tpl.icon;
          const isAllowed = user?.allowedTemplates.includes(tpl.id);
          
          return (
            <Card key={tpl.id} hoverable className={`flex flex-col h-full ${!isAllowed ? 'opacity-60' : ''}`}>
              <CardHeader className="flex flex-row justify-between items-start gap-4">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <CardTitle className="text-sm font-bold">{tpl.name}</CardTitle>
                    {!isAllowed && (
                      <Badge variant="neutral" className="text-[9px]">Locked</Badge>
                    )}
                  </div>
                  <CardDescription className="text-xs line-clamp-2">{tpl.description}</CardDescription>
                </div>
                <div className="p-2.5 bg-indigo-50 dark:bg-zinc-800 text-indigo-600 dark:text-indigo-400 rounded-lg border border-indigo-100/50 dark:border-zinc-800">
                  <Icon className="h-5 w-5" />
                </div>
              </CardHeader>
              <CardContent className="flex-1 text-xs text-slate-500 dark:text-zinc-400 space-y-3 pt-0">
                <div className="flex justify-between items-center py-1 border-b border-slate-100 dark:border-zinc-850">
                  <span className="font-semibold">Supported Extension:</span>
                  <span className="font-mono font-bold text-slate-800 dark:text-zinc-300 uppercase">{tpl.supportedFileTypes.join(', ')}</span>
                </div>
                <div className="flex justify-between items-center py-1 border-b border-slate-100 dark:border-zinc-850">
                  <span className="font-semibold">Required Fields:</span>
                  <div className="flex flex-wrap gap-1 justify-end max-w-[60%]">
                    {tpl.requiredColumns.map(col => (
                      <Badge key={col} variant="neutral" className="text-[8px] tracking-wide">{col}</Badge>
                    ))}
                  </div>
                </div>
                <div className="flex justify-between items-center py-1">
                  <span className="font-semibold">Last Checked Update:</span>
                  <span className="font-medium flex items-center gap-1">
                    <Calendar className="h-3.5 w-3.5" />
                    {new Date(tpl.lastUpdated).toLocaleDateString()}
                  </span>
                </div>
              </CardContent>
              <CardFooter className="flex gap-2">
                <Button 
                  variant="outline" 
                  size="sm" 
                  onClick={() => handleCardHistory(tpl.id)}
                  className="flex-1 text-xs"
                >
                  <Layers className="h-3.5 w-3.5" />
                  <span>Vault Logs</span>
                </Button>
                <Button 
                  variant="primary" 
                  size="sm" 
                  onClick={() => handleCardGenerate(tpl)}
                  disabled={!isAllowed}
                  className="flex-1 text-xs"
                >
                  <Cpu className="h-3.5 w-3.5" />
                  <span>Generate</span>
                </Button>
              </CardFooter>
            </Card>
          );
        })}
      </div>

      {/* Generator Stepper Drawer slide out */}
      <Drawer
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        title={selectedTemplate ? `Report Generation Wizard: ${selectedTemplate.name}` : 'Document Wizard'}
        width="3xl"
      >
        {selectedTemplate && (
          <div className="space-y-6 text-left">
            {/* Visual Stepper bar */}
            <div className="flex justify-between items-center px-4 py-2 border rounded-xl bg-slate-50/50 dark:bg-zinc-950/20 text-xs font-bold text-slate-400 select-none">
              <span className={`flex items-center gap-1.5 ${step >= 1 ? 'text-indigo-650' : ''}`}>
                <Badge variant={step >= 1 ? 'info' : 'neutral'} className="h-5 w-5 items-center justify-center p-0">1</Badge>
                Worksheet Upload
              </span>
              <ArrowRight className="h-4 w-4 text-slate-300" />
              <span className={`flex items-center gap-1.5 ${step >= 2 ? 'text-indigo-650' : ''}`}>
                <Badge variant={step >= 2 ? 'info' : 'neutral'} className="h-5 w-5 items-center justify-center p-0">2</Badge>
                Compile Engine
              </span>
              <ArrowRight className="h-4 w-4 text-slate-300" />
              <span className={`flex items-center gap-1.5 ${step >= 3 ? 'text-indigo-650' : ''}`}>
                <Badge variant={step >= 3 ? 'info' : 'neutral'} className="h-5 w-5 items-center justify-center p-0">3</Badge>
                Previewer Vault
              </span>
            </div>

            {/* Stepper Content details */}
            {step === 1 && (
              <div className="space-y-5">
                <Card>
                  <CardContent className="p-6">
                    {/* Dragzone */}
                    <div 
                      onDragEnter={handleDrag}
                      onDragOver={handleDrag}
                      onDragLeave={handleDrag}
                      onDrop={handleDrop}
                      onClick={() => fileInputRef.current?.click()}
                      className={`
                        border-2 border-dashed rounded-2xl p-10 text-center cursor-pointer transition-all duration-300 flex flex-col items-center gap-3
                        ${dragActive ? 'border-indigo-500 bg-indigo-50/20' : 'border-slate-300 hover:border-indigo-400 dark:border-zinc-800'}
                      `}
                    >
                      <input 
                        type="file" 
                        ref={fileInputRef}
                        onChange={handleFileChange}
                        accept=".xlsx,.xls,.csv"
                        className="hidden"
                      />
                      <UploadCloud className="h-10 w-10 text-indigo-500 animate-pulse" />
                      <div className="space-y-1">
                        <span className="text-xs font-bold text-slate-800 dark:text-zinc-200">Drag and drop Excel spreadsheet here</span>
                        <p className="text-[10px] text-slate-500 dark:text-zinc-400">Supported formats: Excel (.xlsx, .xls) and CSV</p>
                      </div>
                      <Button variant="outline" size="sm" type="button" className="text-xs mt-2">
                        Browse Files
                      </Button>
                    </div>

                    {/* Pre-seeded demo button */}
                    <div className="mt-4 flex justify-between items-center p-3 rounded-xl bg-slate-50 dark:bg-zinc-900 border border-slate-150 dark:border-zinc-800 text-xs">
                      <span className="font-semibold text-slate-600 dark:text-zinc-400 flex items-center gap-1.5">
                        <Info className="h-4 w-4 text-indigo-500" />
                        Need sample data? Auto-load demo sheet file:
                      </span>
                      <Button variant="outline" size="sm" onClick={loadDemoFile} className="text-xs">
                        Use Seed Excel File
                      </Button>
                    </div>
                  </CardContent>
                </Card>

                {/* File validation display results */}
                {uploadedFile && (
                  <Card>
                    <CardHeader className="pb-2">
                      <div className="flex justify-between items-center">
                        <div className="flex items-center gap-2 text-xs font-bold text-slate-800 dark:text-zinc-200">
                          <FileSpreadsheet className="h-4.5 w-4.5 text-emerald-500" />
                          <span>{uploadedFile.name}</span>
                          <span className="text-[10px] text-slate-400">({(uploadedFile.size / 1024).toFixed(1)} KB)</span>
                        </div>
                        {validationResult.status === 'success' && (
                          <Badge variant="success" className="text-[9px]">Matched</Badge>
                        )}
                        {validationResult.status === 'error' && (
                          <Badge variant="danger" className="text-[9px]">Mismatch</Badge>
                        )}
                      </div>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      {validationResult.status === 'validating' && (
                        <div className="flex items-center gap-2 text-xs font-medium text-slate-500">
                          <Loader2 className="h-4 w-4 animate-spin text-indigo-650" />
                          <span>Validating worksheet columns schema...</span>
                        </div>
                      )}

                      {validationResult.status === 'success' && (
                        <div className="space-y-3">
                          <div className="flex items-start gap-2 text-xs text-slate-600 dark:text-zinc-400">
                            <CheckCircle2 className="h-4.5 w-4.5 text-emerald-500 mt-0.5 flex-shrink-0" />
                            <div className="flex-1 font-semibold leading-relaxed">
                              {validationResult.message}
                            </div>
                          </div>
                          {validationResult.columnsFound && (
                            <div className="p-3 bg-slate-50 dark:bg-zinc-900 border rounded-xl space-y-2">
                              <span className="block text-[9px] font-bold text-slate-500 uppercase tracking-wider">Identified Worksheet Headers:</span>
                              <div className="flex flex-wrap gap-1">
                                {validationResult.columnsFound.map(c => (
                                  <Badge key={c} variant="success" className="text-[8px] tracking-wide py-0.5">
                                    {c}
                                  </Badge>
                                ))}
                              </div>
                            </div>
                          )}
                          <div className="flex justify-end pt-2">
                            <Button 
                              variant="primary" 
                              size="sm" 
                              onClick={startReportCompilation}
                              className="text-xs"
                            >
                              <span>Compile HTML Report</span>
                              <ArrowRight className="h-3.5 w-3.5" />
                            </Button>
                          </div>
                        </div>
                      )}

                      {validationResult.status === 'error' && (
                        <div className="space-y-3">
                          <div className="flex items-start gap-2 text-xs text-rose-650">
                            <XCircle className="h-4.5 w-4.5 text-rose-500 mt-0.5 flex-shrink-0" />
                            <div className="flex-1 font-bold leading-relaxed">
                              {validationResult.message}
                            </div>
                          </div>
                          <div className="p-3 bg-rose-50/50 dark:bg-rose-950/10 border border-rose-200 rounded-xl space-y-2">
                            <span className="block text-[9px] font-bold text-rose-600 uppercase tracking-wider">Required Schema:</span>
                            <div className="flex flex-wrap gap-1">
                              {selectedTemplate.requiredColumns.map(c => (
                                <Badge key={c} variant="neutral" className="text-[8px] tracking-wide border-rose-300">
                                  {c}
                                </Badge>
                              ))}
                            </div>
                          </div>
                          <div className="p-2.5 bg-slate-50 dark:bg-zinc-900 border rounded-xl text-[10px] text-slate-500 font-semibold leading-relaxed flex gap-2">
                            <Info className="h-4.5 w-4.5 text-indigo-500 flex-shrink-0" />
                            <span>Hint: Avoid files containing keywords like "fail", "corrupt", or "invalid" to complete validation. Click "Use Seed Excel File" to auto-load a valid structure.</span>
                          </div>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                )}
              </div>
            )}

            {step === 2 && (
              <Card>
                <CardContent className="p-6 space-y-5">
                  <div className="flex flex-col items-center gap-4 py-8">
                    <Loader2 className="h-10 w-10 text-indigo-600 animate-spin" />
                    <div className="text-center space-y-1">
                      <span className="text-sm font-bold text-slate-900 dark:text-zinc-50">Compiling Safety Document Layouts</span>
                      <p className="text-xs text-slate-500 dark:text-zinc-400">Processing sheet indices, calculations and markup styles...</p>
                    </div>
                  </div>

                  {/* Processing Stepper Logs */}
                  <div className="bg-slate-950 dark:bg-black p-4 rounded-xl font-mono text-[10px] text-zinc-400 border border-zinc-800 space-y-2.5 max-h-40 overflow-y-auto">
                    {processingLogs.map((log, index) => (
                      <div key={index} className="flex gap-2 leading-relaxed">
                        <span className="text-indigo-500 font-bold select-none">[PV-ENGINE]</span>
                        <span>{log}</span>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}

            {step === 3 && (
              <div className="space-y-4">
                {/* Save header actions */}
                <div className="flex flex-wrap justify-between items-center gap-3 p-4 rounded-xl border border-slate-205 dark:border-zinc-800 bg-white dark:bg-zinc-900">
                  <div className="flex flex-col text-left">
                    <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Output File Label</span>
                    <input 
                      type="text"
                      value={outputDocName}
                      onChange={e => setOutputDocName(e.target.value)}
                      className="text-xs font-bold text-slate-800 dark:text-zinc-100 bg-transparent border-none outline-none focus:ring-1 focus:ring-indigo-500 px-1 py-0.5 rounded"
                    />
                  </div>

                  <div className="flex gap-2">
                    <Button variant="outline" size="sm" onClick={handleCopyClipboard}>
                      <Copy className="h-3.5 w-3.5" />
                      <span>Copy</span>
                    </Button>
                    <Button variant="outline" size="sm" onClick={handleDownloadHtml}>
                      <Download className="h-3.5 w-3.5" />
                      <span>HTML</span>
                    </Button>
                    <Button variant="primary" size="sm" onClick={handleSaveToVault}>
                      <Save className="h-3.5 w-3.5" />
                      <span>Save to Vault</span>
                    </Button>
                  </div>
                </div>

                {/* HTML Iframe Preview */}
                <Card className="overflow-hidden">
                  <CardHeader className="bg-slate-50/50 dark:bg-zinc-950/20 py-3">
                    <div className="flex items-center gap-1.5 text-xs font-bold text-slate-500 dark:text-zinc-400">
                      <Eye className="h-4.5 w-4.5" />
                      <span>Document Previewer Sandbox (Isolating Styles)</span>
                    </div>
                  </CardHeader>
                  <CardContent className="p-0 bg-white">
                    <iframe
                      title="HTML Report Preview"
                      srcDoc={generatedHtml}
                      className="w-full h-[32rem] border-none"
                      sandbox="allow-same-origin"
                    />
                  </CardContent>
                </Card>

                {/* Generate again controls */}
                <div className="flex justify-end gap-2 pt-2">
                  <Button variant="outline" size="sm" onClick={() => setStep(1)} className="text-xs">
                    <RotateCcw className="h-3.5 w-3.5" />
                    <span>Upload Again</span>
                  </Button>
                </div>
              </div>
            )}
          </div>
        )}
      </Drawer>
    </div>
  );
};
export default GeneratorPage;
