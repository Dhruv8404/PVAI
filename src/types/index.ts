export interface User {
  id: string;
  avatarUrl?: string;
  name: string;
  email: string;
  role: 'Admin' | 'User';
  status: 'Active' | 'Inactive';
  createdDate: string;
  lastLogin: string;
  documentsGenerated: number;
  reportLimit?: number;
  allowedTemplates: string[]; // List of template IDs user has access to
}

export interface DocumentTemplate {
  id: string;
  name: string;
  description: string;
  supportedFileTypes: string[];
  lastUpdated: string;
  icon: string;
}

export interface GeneratedDocument {
  id: string;
  name: string;
  templateId: string;
  templateName: string;
  createdBy: string; // User Name
  createdById: string; // User ID
  generatedTime: string;
  downloaded: boolean;
  status: 'Success' | 'Failed';
  version: string;
  excelFileName: string;
  htmlContent: string; // Stored HTML output
}

export interface SystemAuditLog {
  id: string;
  timestamp: string;
  userId: string;
  userName: string;
  action: string;
  details: string;
}
