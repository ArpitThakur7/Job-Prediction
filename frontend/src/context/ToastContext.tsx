"use client";

import React, { createContext, useContext, useState, useCallback, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type ToastType = "success" | "error" | "info" | "warning";

interface Toast {
  id: string;
  type: ToastType;
  title: string;
  message?: string;
  duration?: number;
}

interface ToastContextValue {
  addToast: (toast: Omit<Toast, "id">) => void;
  removeToast: (id: string) => void;
}

// ---------------------------------------------------------------------------
// Context
// ---------------------------------------------------------------------------

const ToastContext = createContext<ToastContextValue | null>(null);

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used within ToastProvider");
  return ctx;
}

// ---------------------------------------------------------------------------
// Icons
// ---------------------------------------------------------------------------

const TOAST_CONFIG: Record<ToastType, { icon: string; border: string; glow: string; text: string }> = {
  success: { icon: "✅", border: "border-emerald-500/40", glow: "shadow-[0_0_20px_rgba(16,185,129,0.15)]", text: "text-emerald-400" },
  error:   { icon: "❌", border: "border-red-500/40",     glow: "shadow-[0_0_20px_rgba(239,68,68,0.15)]",  text: "text-red-400" },
  info:    { icon: "ℹ️", border: "border-cyan-500/40",    glow: "shadow-[0_0_20px_rgba(6,182,212,0.15)]",  text: "text-cyan-400" },
  warning: { icon: "⚠️", border: "border-amber-500/40",   glow: "shadow-[0_0_20px_rgba(245,158,11,0.15)]", text: "text-amber-400" },
};

// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------

export const ToastProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const timersRef = useRef<Map<string, NodeJS.Timeout>>(new Map());

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
    const timer = timersRef.current.get(id);
    if (timer) {
      clearTimeout(timer);
      timersRef.current.delete(id);
    }
  }, []);

  const addToast = useCallback((toast: Omit<Toast, "id">) => {
    const id = `toast_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`;
    const duration = toast.duration ?? (toast.type === "error" ? 6000 : 4000);
    setToasts((prev) => [...prev.slice(-4), { ...toast, id }]); // max 5 visible
    const timer = setTimeout(() => removeToast(id), duration);
    timersRef.current.set(id, timer);
  }, [removeToast]);

  return (
    <ToastContext.Provider value={{ addToast, removeToast }}>
      {children}
      {/* Toast Container — fixed bottom-right */}
      <div className="fixed bottom-6 right-6 z-[9999] flex flex-col gap-3 pointer-events-none max-w-sm w-full">
        <AnimatePresence mode="popLayout">
          {toasts.map((toast) => {
            const cfg = TOAST_CONFIG[toast.type];
            return (
              <motion.div
                key={toast.id}
                layout
                initial={{ opacity: 0, y: 30, scale: 0.95 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, x: 80, scale: 0.9 }}
                transition={{ type: "spring", stiffness: 400, damping: 30 }}
                className={`pointer-events-auto flex items-start gap-3 px-4 py-3 rounded-xl border backdrop-blur-xl ${cfg.border} ${cfg.glow}`}
                style={{ backgroundColor: "rgba(15, 23, 42, 0.92)" }}
              >
                <span className="text-base mt-0.5 shrink-0">{cfg.icon}</span>
                <div className="flex-1 min-w-0">
                  <p className={`text-xs font-bold font-mono ${cfg.text}`}>{toast.title}</p>
                  {toast.message && (
                    <p className="text-[11px] text-slate-400 mt-0.5 leading-snug">{toast.message}</p>
                  )}
                </div>
                <button
                  onClick={() => removeToast(toast.id)}
                  className="shrink-0 text-slate-500 hover:text-slate-200 transition-colors text-xs p-0.5"
                >
                  ✕
                </button>
              </motion.div>
            );
          })}
        </AnimatePresence>
      </div>
    </ToastContext.Provider>
  );
};
