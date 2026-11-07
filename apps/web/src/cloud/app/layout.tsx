import type { Metadata } from "next";
import "@/app/globals.css";
import { CloudCacheBoundary } from "@/components/learning/CloudCacheBoundary";
import { CloudChildBoundary } from "@/components/account/CloudChildBoundary";

export const metadata: Metadata = {
  title: "聪聪学堂",
  description: "家庭成长与学习",
  manifest: "/manifest.webmanifest",
};

export default function CloudLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN">
      <body className="min-h-screen bg-bg"><CloudCacheBoundary><CloudChildBoundary>{children}</CloudChildBoundary></CloudCacheBoundary></body>
    </html>
  );
}
