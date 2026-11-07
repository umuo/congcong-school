"use client";
import { createContext, useContext, useEffect, useState, useSyncExternalStore, type ReactNode, type CSSProperties } from "react";
import type { Account } from "@/lib/api/client";
import { CloudLearningClient } from "@/lib/learning/client";
import { onLearningInvalidated } from "@/lib/learning/lifecycle";
import { setMascotSkin } from "@/lib/learning/preferences";
import { getCosmeticById, type UiTheme } from "@/lib/cosmetics";
import { themeAccentColors } from "@/lib/themeColors";

import { FloatingNotice } from "./FloatingNotice";

const Context = createContext<CloudLearningClient | null>(null);
export function LearningProvider({ account, children }: { account: Account; children: ReactNode }) {
  const [client, setClient] = useState<CloudLearningClient | null>(null);
  const { context_id, student_id, mode, must_change_password } = account;
  useEffect(() => {
    let storage: Storage | undefined;
    try { storage = window.sessionStorage; } catch { /* 内存模式仍可使用。 */ }
    const current = new CloudLearningClient({ context_id, student_id, mode, must_change_password }, undefined, storage);
    const appearance = () => {
      const skin = current.projection.getSnapshot().progress?.state.equippedMascotSkin;
      setMascotSkin(typeof skin === "string" ? skin : "skin_default");
    };
    appearance();
    const stopAppearance = current.projection.subscribe(appearance);
    setClient(current);
    // Navigation can interrupt the final time receipt. Reuse its original bytes/key;
    // answer/start/reward writes still require the visible recovery action.
    void current.retryTimeCheckpoints();
    const unsubscribe = onLearningInvalidated(() => {
      current.dispose();
      setClient(null);
    });
    return () => {
      unsubscribe();
      stopAppearance();
      setMascotSkin("skin_default");
      // 刷新/导航保留同一身份的待提交字节；显式失效通知会清理。
      current.dispose(false);
    };
  }, [context_id, student_id, mode, must_change_password]);
  if (!client) return <p role="status">正在确认学习身份…</p>;
  return <Context.Provider value={client}><CloudAppearance client={client}>{children}</CloudAppearance></Context.Provider>;
}
function CloudAppearance({ client, children }: { client: CloudLearningClient; children: ReactNode }) {
  const progress = useSyncExternalStore(client.projection.subscribe, client.projection.getSnapshot, client.projection.getSnapshot).progress;
  const item = getCosmeticById(String(progress?.state.equippedTheme ?? "theme_default")) as UiTheme | undefined;
  const data = item?.type === "ui_theme" ? item.data : undefined;
  const style = data && item?.id !== "theme_default" ? {
    ...themeAccentColors(data.primary, data.primaryDark, data.accent, Boolean(data.isDark)),
    "--theme-primary": data.primary, "--theme-primary-dark": data.primaryDark,
    "--theme-accent": data.accent, "--theme-bg": data.bg,
    "--app-bg-soft": data.bg, "--app-bg": data.bg, "--app-card": data.cardBg ?? "#ffffff",
    "--app-border": data.borderSoft ?? "#dce6d8", "--app-ink": data.ink ?? "#243728",
    "--app-ink-light": data.inkLight ?? "#57715c", "--app-ink-softer": data.inkSofter ?? "#57715c",
  } as CSSProperties : undefined;
  return <div style={style} className={data?.isDark ? "night theme-dark" : undefined}>{children}</div>;
}
export function useLearningClient() {
  const client = useContext(Context);
  if (!client) throw new Error("学习组件必须位于 LearningProvider 内");
  return client;
}
export function LearningSyncStatus() {
  const client = useLearningClient();
  const snapshot = useSyncExternalStore(client.projection.subscribe, client.projection.getSnapshot, client.projection.getSnapshot);
  const waiting = snapshot.pending.filter(key => !snapshot.sending.includes(key));
  return <FloatingNotice duration={0} message={waiting.length ? `还有 ${waiting.length} 项进度没保存成功，点“重新保存”试试。` : snapshot.sending.length ? "正在保存进度…" : ""} />;
}
