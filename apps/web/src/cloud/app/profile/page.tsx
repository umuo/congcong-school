"use client";
import { AccountGuard } from "@/components/account/AccountShell";
import { CloudCottage } from "@/components/learning/CloudCottage";
export default function Page() { return <AccountGuard destination="/learn">{account => <CloudCottage account={account}/>}</AccountGuard>; }
