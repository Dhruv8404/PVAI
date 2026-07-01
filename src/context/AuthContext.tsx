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

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const API_BASE_URL = 'http://127.0.0.1:8000/api/v1';

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
          // Server offline - fall back to localStorage/mockDb session
          const cached = localStorage.getItem('pv_user');
          if (cached) {
            setUser(JSON.parse(cached));
          } else {
            const users = mockDb.getUsers();
            const matched = users.find(u => u.email === storedUserEmail);
            if (matched && matched.status === 'Active') {
              setUser(matched);
            } else {
              logout();
            }
          }
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
      console.warn('Backend API connection failed, falling back to mockDb:', err.message);
      
      // Fallback Mock authentication
      const users = mockDb.getUsers();
      const matched = users.find(u => u.email.toLowerCase() === email.toLowerCase());

      if (!matched) {
        setLoading(false);
        throw new Error('Invalid email or password.');
      }

      if (matched.status === 'Inactive') {
        setLoading(false);
        throw new Error('Your account has been deactivated. Please contact support.');
      }

      if (password.length < 6) {
        setLoading(false);
        throw new Error('Password must be at least 6 characters.');
      }

      localStorage.setItem('pv_token', `mock-jwt-token-${Math.random()}`);
      localStorage.setItem('pv_user_email', matched.email);
      
      matched.lastLogin = new Date().toISOString();
      mockDb.saveUser(matched);
      mockDb.addAuditLog('USER_LOGIN', `User ${matched.name} (${matched.email}) logged in successfully (Offline Mode).`, matched.id, matched.name);
      
      const fallbackUser = {
        ...matched,
        reportLimit: (matched as any).reportLimit || 5
      };
      setUser(fallbackUser);
      localStorage.setItem('pv_user', JSON.stringify(fallbackUser));
      setLoading(false);
      addNotification(`Logged in successfully as ${matched.role} (Offline Mode).`);
      return true;
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
      console.warn('Backend API registration failed, falling back to mockDb:', err.message);
      
      // Fallback Mock registration
      const users = mockDb.getUsers();
      const exists = users.some(u => u.email.toLowerCase() === email.toLowerCase());

      if (exists) {
        setLoading(false);
        throw new Error('An account with this email already exists.');
      }

      const newUser: User = {
        id: `usr-${Math.random().toString(36).substring(2, 9)}`,
        name,
        email,
        role: 'User',
        status: 'Active',
        createdDate: new Date().toISOString(),
        lastLogin: new Date().toISOString(),
        documentsGenerated: 0,
        reportLimit: 5,
        allowedTemplates: ['psur'] // Default template
      };

      const savedUser = mockDb.saveUser(newUser);
      
      localStorage.setItem('pv_token', `mock-jwt-token-${Math.random()}`);
      localStorage.setItem('pv_user_email', savedUser.email);
      
      mockDb.addAuditLog('USER_REGISTER', `New user registered: ${savedUser.name} (${savedUser.email}) (Offline Mode).`, savedUser.id, savedUser.name);

      setUser(savedUser);
      localStorage.setItem('pv_user', JSON.stringify(savedUser));
      setLoading(false);
      addNotification('Account registered successfully! Welcome aboard (Offline Mode).');
      return true;
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
