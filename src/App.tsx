import React, { lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { ThemeProvider } from './context/ThemeContext';
import { ToastProvider } from './components/ui/Toast';
import { ProtectedLayout } from './components/shared/ProtectedLayout';
import { PublicLayout } from './components/shared/PublicLayout';

// Lazy-loaded Auth Pages
const LoginPage = lazy(() => import('./features/auth/LoginPage'));
const RegisterPage = lazy(() => import('./features/auth/RegisterPage'));
const ForgotPasswordPage = lazy(() => import('./features/auth/ForgotPasswordPage'));
const ResetPasswordPage = lazy(() => import('./features/auth/ResetPasswordPage'));

// Lazy-loaded Workspace & Admin Pages
const DashboardPage = lazy(() => import('./features/dashboard/DashboardPage'));
const UsersPage = lazy(() => import('./features/users/UsersPage'));
const GeneratorPage = lazy(() => import('./features/generator/GeneratorPage'));
const HtmlTemplatesPage = lazy(() => import('./features/generator/HtmlTemplatesPage'));
const HistoryPage = lazy(() => import('./features/history/HistoryPage'));
const ContactPage = lazy(() => import('./features/contact/ContactPage'));
const AdminQueriesPage = lazy(() => import('./features/queries/AdminQueriesPage'));

// Lightweight, non-disruptive page loading fallback
const PageLoadingFallback: React.FC = () => (
  <div className="min-h-[50vh] flex items-center justify-center p-6">
    <div className="flex flex-col items-center gap-3">
      <div className="h-7 w-7 rounded-full border-3 border-indigo-600 border-t-transparent animate-spin" />
      <span className="text-xs font-semibold text-slate-400 dark:text-zinc-500">Loading page...</span>
    </div>
  </div>
);

// Administrative Access guard
const AdminRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user, loading } = useAuth();
  
  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 dark:bg-zinc-950 flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 rounded-full border-4 border-t-indigo-600 border-r-transparent border-b-transparent border-l-transparent animate-spin" />
          <span className="text-xs font-semibold text-slate-500 dark:text-zinc-400">Verifying privileges...</span>
        </div>
      </div>
    );
  }
  
  if (!user) return <Navigate to="/login" replace />;
  if (user.role !== 'Admin') {
    return <Navigate to="/dashboard" replace />;
  }
  
  return <>{children}</>;
};

// Not Found Page
const NotFoundPage: React.FC = () => {
  return (
    <div className="min-h-screen bg-slate-50 dark:bg-zinc-950 flex flex-col justify-center items-center p-6 text-center">
      <div className="space-y-4">
        <h1 className="text-4xl font-extrabold text-indigo-650 tracking-tight">404</h1>
        <h2 className="text-lg font-bold text-slate-900 dark:text-zinc-50">Page Not Found</h2>
        <p className="text-xs text-slate-500 dark:text-zinc-400 max-w-sm mx-auto leading-relaxed">
          The requested page catalog index does not exist or has been relocated to another audit path.
        </p>
        <div className="pt-2">
          <a href="/dashboard">
            <button className="inline-flex items-center justify-center font-medium rounded-lg text-xs px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white dark:bg-indigo-500 dark:hover:bg-indigo-600">
              Return to Dashboard
            </button>
          </a>
        </div>
      </div>
    </div>
  );
};

export const App: React.FC = () => {
  return (
    <ThemeProvider>
      <AuthProvider>
        <ToastProvider>
          <BrowserRouter>
            <Suspense fallback={<PageLoadingFallback />}>
              <Routes>
                {/* Standalone Public Contact Query Form (No login or registration required) */}
                <Route path="contact" element={<ContactPage />} />

                {/* Public/Auth Routes */}
                <Route element={<PublicLayout />}>
                  <Route path="login" element={<LoginPage />} />
                  <Route path="register" element={<RegisterPage />} />
                  <Route path="forgot-password" element={<ForgotPasswordPage />} />
                  <Route path="reset-password" element={<ResetPasswordPage />} />
                </Route>

                {/* Secure Protected Workspace Routes */}
                <Route element={<ProtectedLayout />}>
                  <Route path="dashboard" element={<DashboardPage />} />
                  <Route 
                    path="users" 
                    element={
                      <AdminRoute>
                        <UsersPage />
                      </AdminRoute>
                    } 
                  />
                  <Route 
                    path="html-templates" 
                    element={
                      <AdminRoute>
                        <HtmlTemplatesPage />
                      </AdminRoute>
                    } 
                  />
                  <Route 
                    path="admin/queries" 
                    element={
                      <AdminRoute>
                        <AdminQueriesPage />
                      </AdminRoute>
                    } 
                  />
                  <Route path="generator/:templateId" element={<GeneratorPage />} />
                  <Route path="generator" element={<GeneratorPage />} />
                  <Route path="history" element={<HistoryPage />} />
                  <Route path="" element={<Navigate to="/dashboard" replace />} />
                </Route>

                {/* Catch All */}
                <Route path="*" element={<NotFoundPage />} />
              </Routes>
            </Suspense>
          </BrowserRouter>
        </ToastProvider>
      </AuthProvider>
    </ThemeProvider>
  );
};
export default App;

