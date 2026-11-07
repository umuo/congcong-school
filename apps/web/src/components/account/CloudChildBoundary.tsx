"use client";
import type { ReactNode } from "react";
import { usePathname } from "next/navigation";
import { AccountGuard } from "./AccountShell";

// Login and management keep their own guards. Only the child destinations share
// one mounted guard/client; no identity is cached outside that verified lifetime.
const childPath = /^\/(?:learn|explore|league|profile|shop|book|lesson|grade|jump|number-sense|review|stories|reading)(?:\/|$)/;

export function CloudChildBoundary({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  return childPath.test(pathname) ? <AccountGuard destination="/learn">{() => children}</AccountGuard> : children;
}
