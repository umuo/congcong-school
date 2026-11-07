"use client";
import { AccountGuard } from "@/components/account/AccountShell";
import { CloudLearningWorkspace } from "@/components/learning/CloudLearningWorkspace";
export default function LearnPage() { return <AccountGuard destination="/learn">{() => <main className="account-card forest-main"><CloudLearningWorkspace/></main>}</AccountGuard>; }
