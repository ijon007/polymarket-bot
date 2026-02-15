"use client";

import { useEffect } from "react";
import { cn } from "@/lib/utils";

const TOAST_DURATION = 2500;

interface ToastProps {
  message: string | null;
  onDismiss: () => void;
  className?: string;
}

export function Toast({ message, onDismiss, className }: ToastProps) {
  useEffect(() => {
    if (!message) return;
    const t = setTimeout(onDismiss, TOAST_DURATION);
    return () => clearTimeout(t);
  }, [message, onDismiss]);

  if (!message) return null;

  return (
    <div
      role="status"
      aria-live="polite"
      className={cn(
        "fixed bottom-4 right-4 z-50 rounded border border-border/60 bg-card px-3 py-2 text-xs font-medium shadow-lg animate-in fade-in slide-in-from-bottom-2 duration-200",
        className
      )}
    >
      {message}
    </div>
  );
}
