"use client";
import { usePathname } from "next/navigation";
import dynamic from "next/dynamic";
import type { ReactNode } from "react";
import { IS_LOCAL_MODE } from "@/lib/appMode";
import { AccountGuard } from "./account/AccountShell";
const LegacyProviders = dynamic(() => import("./LegacyProviders"));

export function RootProviders({ children }: { children: ReactNode }) {
  const path = usePathname() ?? "/";
  if (/^\/(login|change-password|admin|parent|learn)(\/|$)/.test(path))
    return <>{children}</>;
  if (!IS_LOCAL_MODE) {
    // 原首页、课程、商店等旧 URL 也必须先验证；云端接入完成前不挂载本地学习树。
    // 会话有效时按角色转至入口，无会话转登录，网络故障时保持阻断并提供重试。
    return <AccountGuard destination="/">{() => null}</AccountGuard>;
  }
  return <LegacyProviders>{children}</LegacyProviders>;
}
