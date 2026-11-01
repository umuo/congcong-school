"use client";
import { AccountGuard } from "@/components/account/AccountShell";
import { ParentDashboard } from "@/components/account/ParentDashboard";
export default function ParentPage() {
  return (
    <AccountGuard destination="/parent">
      {(account) => <ParentDashboard account={account} />}
    </AccountGuard>
  );
}
