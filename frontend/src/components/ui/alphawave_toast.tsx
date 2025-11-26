/**
 * Toast Notification Component
 * 
 * QA NOTES:
 * - Simple toast for error/success messages
 * - Auto-dismisses after timeout
 * - Supports different variants (error, success, warning)
 * - Uses React context for app-wide access
 */

'use client';

import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';

// Toast types
type ToastVariant = 'success' | 'error' | 'warning' | 'info';

interface Toast {
  id: string;
  message: string;
  variant: ToastVariant;
  duration?: number;
}

interface ToastContextType {
  toasts: Toast[];
  showToast: (message: string, variant?: ToastVariant, duration?: number) => void;
  dismissToast: (id: string) => void;
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

// Variant styles
const variantStyles: Record<ToastVariant, string> = {
  success: 'bg-emerald-600 text-white',
  error: 'bg-rose-600 text-white',
  warning: 'bg-amber-500 text-white',
  info: 'bg-blue-600 text-white',
};

const variantIcons: Record<ToastVariant, string> = {
  success: '✓',
  error: '✕',
  warning: '⚠',
  info: 'ℹ',
};

/**
 * Toast Provider - Wrap your app with this
 */
export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const showToast = useCallback((
    message: string, 
    variant: ToastVariant = 'info',
    duration: number = 5000
  ) => {
    const id = crypto.randomUUID();
    setToasts((prev) => [...prev, { id, message, variant, duration }]);
  }, []);

  const dismissToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  return (
    <ToastContext.Provider value={{ toasts, showToast, dismissToast }}>
      {children}
      <ToastContainer toasts={toasts} onDismiss={dismissToast} />
    </ToastContext.Provider>
  );
}

/**
 * Hook to use toast notifications
 */
export function useToast() {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return context;
}

/**
 * Toast Container - Renders all active toasts
 */
function ToastContainer({ 
  toasts, 
  onDismiss 
}: { 
  toasts: Toast[];
  onDismiss: (id: string) => void;
}) {
  if (toasts.length === 0) return null;

  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 max-w-sm">
      {toasts.map((toast) => (
        <ToastItem key={toast.id} toast={toast} onDismiss={onDismiss} />
      ))}
    </div>
  );
}

/**
 * Individual Toast Item
 */
function ToastItem({ 
  toast, 
  onDismiss 
}: { 
  toast: Toast;
  onDismiss: (id: string) => void;
}) {
  const { id, message, variant, duration = 5000 } = toast;

  // Auto-dismiss after duration
  useEffect(() => {
    if (duration > 0) {
      const timer = setTimeout(() => {
        onDismiss(id);
      }, duration);
      return () => clearTimeout(timer);
    }
  }, [id, duration, onDismiss]);

  return (
    <div 
      className={`
        ${variantStyles[variant]}
        px-4 py-3 rounded-lg shadow-lg
        flex items-center gap-3
        animate-in slide-in-from-right-full duration-300
        cursor-pointer hover:opacity-90 transition-opacity
      `}
      onClick={() => onDismiss(id)}
      role="alert"
    >
      <span className="text-lg font-bold">{variantIcons[variant]}</span>
      <span className="text-sm font-medium flex-1">{message}</span>
      <button 
        className="text-white/80 hover:text-white ml-2"
        onClick={(e) => {
          e.stopPropagation();
          onDismiss(id);
        }}
        aria-label="Dismiss"
      >
        ✕
      </button>
    </div>
  );
}

/**
 * Convenience functions for direct toast calls
 */
export const toast = {
  success: (message: string, _duration?: number) => {
    console.log('Toast success:', message);
  },
  error: (message: string, _duration?: number) => {
    console.log('Toast error:', message);
  },
  warning: (message: string, _duration?: number) => {
    console.log('Toast warning:', message);
  },
  info: (message: string, _duration?: number) => {
    console.log('Toast info:', message);
  },
};

