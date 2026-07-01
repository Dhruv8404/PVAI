import React, { createContext, useContext, useState, useEffect } from 'react';
import type { User } from '../types';
import { mockDb } from '../lib/mockDb';

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<boolean>;
  register: (name: string, email: string, password: string) => Promise<boolean>;
  logout: () => void;
  refreshSession: () => void;
  notifications: Notification[];
  addNotification: (message: string) => void;
  clearNotifications: () => void;
}

export interface Notification {
  id: string;
  message: string;
  read: boolean;
  timestamp: string;
}

import { API_BASE_URL } from '../config';

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [notifications, setNotifications] = useState<Notification[]>([]);

  useEffect(() => {
    const token = localStorage.getItem('pv_token');
    const storedUserEmail = localStorage.getItem('pv_user_email');
    
    const verifyAndLoadSession = async () => {
      if (token && storedUserEmail) {
        try {
          const res = await fetch(`${API_BASE_URL}/users/me`, {
            headers: {
              'Authorization': `Bearer ${token}`
            }
          });
          const json = await res.json();
          if (json.success && json.data) {
            const apiUser = json.data;
            const mappedUser: User = {
              id: apiUser.id,
              name: apiUser.name,
              email: apiUser.email,
              role: apiUser.roles[0]?.name || 'User',
              status: apiUser.status,
              createdDate: apiUser.created_at,
              lastLogin: apiUser.last_login || new Date().toISOString(),
              documentsGenerated: apiUser.documents_generated || 0,
              reportLimit: apiUser.report_limit || 5,
              allowedTemplates: apiUser.allowed_templates?.map((t: any) => {
                const nameLower = t.name.toLowerCase();
                return nameLower.includes('psur') ? 'psur' : nameLower.includes('quant') ? 'quant' : 'pv_auto';
              }) || []
            };
            setUser(mappedUser);
            localStorage.setItem('pv_user', JSON.stringify(mappedUser));
          } else {
            // Clean up session if backend rejects
            logout();
          }
        } catch (err) {
          logout();
        }
      }
      setLoading(false);
    };

    verifyAndLoadSession();

    // Initial notification
    setNotifications([
      {
        id: 'n-1',
        message: 'Welcome to the Document Generation Platform Portal.',
        read: false,
        timestamp: new Date().toISOString()
      }
    ]);
  }, []);

  const login = async (email: string, password: string): Promise<boolean> => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ email, password })
      });
      const json = await res.json();
      
      if (!json.success || !json.data) {
        throw new Error(json.message || 'Invalid email or password.');
      }
      
      const { access_token } = json.data;
      localStorage.setItem('pv_token', access_token);
      localStorage.setItem('pv_user_email', email);
      
      // Load user details
      const meRes = await fetch(`${API_BASE_URL}/users/me`, {
        headers: {
          'Authorization': `Bearer ${access_token}`
        }
      });
      const meJson = await meRes.json();
      
      if (meJson.success && meJson.data) {
        const apiUser = meJson.data;
        const mappedUser: User = {
          id: apiUser.id,
          name: apiUser.name,
          email: apiUser.email,
          role: apiUser.roles[0]?.name || 'User',
          status: apiUser.status,
          createdDate: apiUser.created_at,
          lastLogin: apiUser.last_login || new Date().toISOString(),
          documentsGenerated: apiUser.documents_generated || 0,
          reportLimit: apiUser.report_limit || 5,
          allowedTemplates: apiUser.allowed_templates?.map((t: any) => {
            const nameLower = t.name.toLowerCase();
            return nameLower.includes('psur') ? 'psur' : nameLower.includes('quant') ? 'quant' : 'pv_auto';
          }) || []
        };
        
        setUser(mappedUser);
        localStorage.setItem('pv_user', JSON.stringify(mappedUser));
        setLoading(false);
        addNotification(`Logged in successfully as ${mappedUser.role}.`);
        return true;
      }
      
      throw new Error('Authentication failed during profile resolution.');
    } catch (err: any) {
      setLoading(false);
      throw err;
    }
  };

  const register = async (name: string, email: string, password: string): Promise<boolean> => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/auth/register`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ name, email, password })
      });
      const json = await res.json();
      
      if (!json.success) {
        throw new Error(json.message || 'Registration failed.');
      }
      
      // Automatically log in after registration
      return await login(email, password);
    } catch (err: any) {
      setLoading(false);
      throw err;
    }
  };

  const logout = () => {
    if (user) {
      mockDb.addAuditLog('USER_LOGOUT', `User ${user.name} logged out.`, user.id, user.name);
    }
    localStorage.removeItem('pv_token');
    localStorage.removeItem('pv_user_email');
    localStorage.removeItem('pv_user');
    setUser(null);
  };

  const refreshSession = async () => {
    if (user) {
      const token = localStorage.getItem('pv_token');
      // If it's a real JWT token, verify it against backend
      if (token && !token.startsWith('mock-jwt-token-')) {
        try {
          const res = await fetch(`${API_BASE_URL}/users/me`, {
            headers: { 'Authorization': `Bearer ${token}` }
          });
          const json = await res.json();
          if (json.success && json.data) {
            const apiUser = json.data;
            const mappedUser: User = {
              id: apiUser.id,
              name: apiUser.name,
              email: apiUser.email,
              role: apiUser.roles[0]?.name || 'User',
              status: apiUser.status,
              createdDate: apiUser.created_at,
              lastLogin: apiUser.last_login || new Date().toISOString(),
              documentsGenerated: apiUser.documents_generated || 0,
              reportLimit: apiUser.report_limit || 5,
              allowedTemplates: apiUser.allowed_templates?.map((t: any) => {
                const nameLower = t.name.toLowerCase();
                return nameLower.includes('psur') ? 'psur' : nameLower.includes('quant') ? 'quant' : 'pv_auto';
              }) || []
            };
            setUser(mappedUser);
            localStorage.setItem('pv_user', JSON.stringify(mappedUser));
          } else {
            logout();
          }
        } catch (err) {
          // offline mode - do nothing
        }
        return;
      }

      // Mock Fallback check
      const users = mockDb.getUsers();
      const updated = users.find(u => u.id === user.id);
      if (updated) {
        if (updated.status === 'Inactive') {
          logout();
        } else {
          setUser({
            ...updated,
            reportLimit: (updated as any).reportLimit || 5
          } as any);
        }
      }
    }
  };

  const addNotification = (message: string) => {
    const newNotif: Notification = {
      id: `notif-${Math.random().toString(36).substring(2, 9)}`,
      message,
      read: false,
      timestamp: new Date().toISOString()
    };
    setNotifications(prev => [newNotif, ...prev]);
  };

  const clearNotifications = () => {
    setNotifications(prev => prev.map(n => ({ ...n, read: true })));
  };

  return (
    <AuthContext.Provider value={{ 
      user, 
      loading, 
      login, 
      register, 
      logout, 
      refreshSession,
      notifications,
      addNotification,
      clearNotifications
    }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within an AuthProvider');
  return context;
};
