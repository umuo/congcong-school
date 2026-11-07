"use client";
import { useEffect, useState, type ReactNode } from "react";

/** Feedback overlays the page; adding/removing it never moves task controls. */
export function FloatingNotice({ message, duration = 3200, children }: { message: string; duration?: number; children?: ReactNode }) {
  const [visible, setVisible] = useState(Boolean(message));
  useEffect(() => {
    setVisible(Boolean(message));
    if (!message || !duration) return;
    const timer = window.setTimeout(() => setVisible(false), duration);
    return () => window.clearTimeout(timer);
  }, [message, duration]);
  if (!message || !visible) return null;
  return <aside className="forest-floating-notice" aria-label="操作提示"><div role="status" aria-live="polite" aria-atomic="true">{message}</div>{children}{duration > 0 ? <button type="button" className="secondary forest-notice-close" aria-label="关闭提示" onClick={() => setVisible(false)}>×</button> : null}</aside>;
}
