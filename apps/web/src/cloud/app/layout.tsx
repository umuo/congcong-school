import type { Metadata } from "next";
import "@/app/globals.css";

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
      <body className="min-h-screen bg-bg">{children}</body>
    </html>
  );
}
