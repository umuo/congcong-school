"use client";
import { useEffect, useState, type ReactNode } from "react";

/** 专用 cloud 域名仍是首选；迁移原域名时只清理本项目旧缓存。 */
export function CloudCacheBoundary({ children }: { children: ReactNode }) {
  const [ready, setReady] = useState(false);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    let mounted = true;
    void (async () => {
      try {
        if ("serviceWorker" in navigator) {
          for (const registration of await navigator.serviceWorker.getRegistrations()) {
            const script = registration.active?.scriptURL ?? registration.waiting?.scriptURL ?? registration.installing?.scriptURL;
            if (script && new URL(script).origin === window.location.origin && new URL(script).pathname === "/sw.js") await registration.unregister();
          }
        }
        if ("caches" in window) {
          for (const key of await caches.keys()) if (key.startsWith("ctsf-")) await caches.delete(key);
        }
        if (mounted) setReady(true);
      } catch { if (mounted) setFailed(true); }
    })();
    return () => { mounted = false; };
  }, []);
  if (failed) return <main className="account-card"><h1>需要清理旧版离线缓存</h1><p>请关闭本站其他标签页，并清除本站的缓存后重新打开。设备上的本地学习备份请先保留。</p><button onClick={() => window.location.reload()}>重试</button></main>;
  return ready ? children : <main className="account-card"><p role="status">正在准备云端学习环境…</p></main>;
}
