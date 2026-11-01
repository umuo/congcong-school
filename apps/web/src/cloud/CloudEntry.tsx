"use client";
import { AccountGuard } from "@/components/account/AccountShell";

/** 云端页面只挂载账号入口，儿童学习客户端在后续任务中接入。 */
export function CloudEntry() {
  return <AccountGuard destination="/">{() => null}</AccountGuard>;
}
