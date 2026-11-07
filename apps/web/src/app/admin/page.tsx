"use client";
import { AccountGuard } from "@/components/account/AccountShell";
import { AdminDashboard } from "@/components/account/AdminDashboard";
export default function AdminPage() {
  return (
    <AccountGuard destination="/admin">{(account) => <AdminDashboard account={account} />}</AccountGuard>
  );
}
