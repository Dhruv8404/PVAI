import React, { createContext, useContext, useState, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { X, CheckCircle2, AlertTriangle, Info, AlertCircle } from 'lucide-react';
import { AnimatePresence, motion } from 'framer-motion';

type ToastType = 'success' | 'error' | 'warning' | 'info';

interface Toast {
  id: string;
  message: string;
  type: ToastType;
  title?: string;
}

interface ToastContextType {
  toast: {
    success: (message: string, title?: string) => void;
    error: (message: string, title?: string) => void;
    warning: (message: string, title?: string) => void;
    info: (message: string, title?: string) => void;
  };
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

export const ToastProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const addToast = useCallback((type: ToastType, message: string, title?: string) => {
    const id = Math.random().toString(36).substring(2, 9);
    setToasts(prev => [...prev, { id, message, type, title }]);
    
    // Auto-remove after 4 seconds
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id));
    }, 4000);
  }, []);

  const removeToast = useCallback((id: string) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  }, []);

  const toastHandlers = {
    success: (message: string, title?: string) => addToast('success', message, title),
    error: (message: string, title?: string) => addToast('error', message, title),
    warning: (message: string, title?: string) => addToast('warning', message, title),
    info: (message: string, title?: string) => addToast('info', message, title),
  };

  const getIcon = (type: ToastType) => {
    switch (type) {
      case 'success':
        return <CheckCircle2 className="h-5 w-5 text-emerald-500" />;
      case 'error':
        return <AlertCircle className="h-5 w-5 text-rose-500" />;
      case 'warning':
        return <AlertTriangle className="h-5 w-5 text-amber-500" />;
      case 'info':
        return <Info className="h-5 w-5 text-indigo-500" />;
    }
  };

  return (
    <ToastContext.Provider value={{ toast: toastHandlers }}>
      {children}
      {createPortal(
        <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 max-w-sm w-full">
          <AnimatePresence>
            {toasts.map(t => (
              <motion.div
                key={t.id}
                initial={{ opacity: 0, y: 20, scale: 0.95 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, scale: 0.9, transition: { duration: 0.15 } }}
                className="bg-white dark:bg-zinc-900 border border-slate-200 dark:border-zinc-800 rounded-xl shadow-lg p-4 flex gap-3 items-start relative overflow-hidden"
              >
                {/* Visual Indicator Line */}
                <div className={`absolute top-0 bottom-0 left-0 w-1.5 ${
                  t.type === 'success' ? 'bg-emerald-500' :
                  t.type === 'error' ? 'bg-rose-500' :
                  t.type === 'warning' ? 'bg-amber-500' : 'bg-indigo-500'
                }`} />

                <div className="pl-1 mt-0.5">{getIcon(t.type)}</div>
                
                <div className="flex-1">
                  {t.title && (
                    <h4 className="text-sm font-semibold text-slate-900 dark:text-zinc-50 leading-none mb-1">
                      {t.title}
                    </h4>
                  )}
                  <p className="text-xs text-slate-500 dark:text-zinc-400 font-medium">
                    {t.message}
                  </p>
                </div>

                <button
                  onClick={() => removeToast(t.id)}
                  className="text-slate-400 hover:text-slate-500 dark:hover:text-zinc-300 transition-colors p-0.5 rounded"
                >
                  <X className="h-4 w-4" />
                </button>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>,
        document.body
      )}
    </ToastContext.Provider>
  );
};

export const useToast = () => {
  const context = useContext(ToastContext);
  if (!context) throw new Error('useToast must be used within a ToastProvider');
  return context;
};
export default useToast;
