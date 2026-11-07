"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api/client";
import { Mascot } from "@/components/Mascot";
import { getCosmeticById } from "@/lib/cosmetics";
type Summary = { preview_id: string; summary: { completedLessons: Record<string, {stars: number; accuracy: number; book_id: string}>; completedReadings: Record<string, string>; legacyCosmetics: Record<string, boolean>; equipped: Record<string, string> } };
export function LegacySummary({ studentId }: { studentId: string }) {
  const [items, setItems] = useState<Summary[]>([]);
  const [error, setError] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    void api<Summary[]>(`/students/${studentId}/legacy`, { signal: controller.signal }).then((value) => { if (!controller.signal.aborted) setItems(value); }).catch((e) => { if (!controller.signal.aborted) setError(e.message); });
    return () => controller.abort();
  }, [studentId]);
  if (error) return <p role="status">{error}</p>;
  if (!items.length) return null;
  return <details><summary>查看本地历史摘要（非逐次作答证据）</summary>{items.map((item) => <section key={item.preview_id}>
    <p>导入批次 {item.preview_id.slice(0, 8)} · 旧装扮权益 {Object.keys(item.summary.legacyCosmetics).length} 项，仅作历史展示。</p>
    <p>原装扮：{Object.values(item.summary.equipped).join(" · ") || "未记录"}</p>
    <Mascot size={110} animate={false} skinOverride={item.summary.equipped.mascotSkin} />
    <p>{Object.keys(item.summary.legacyCosmetics).map((id) => getCosmeticById(id)?.name ?? id).join("、")}</p>
    <ul>{Object.entries(item.summary.completedLessons).map(([id, grade]) => <li key={id}>{grade.book_id} / {id}：{"⭐".repeat(grade.stars)} · {Math.round(grade.accuracy * 100)}%</li>)}</ul>
    <p>旧阅读记录 {Object.keys(item.summary.completedReadings ?? {}).length} 项</p>
    <ul>{Object.entries(item.summary.completedReadings ?? {}).map(([id, date]) => <li key={id}>{id} · {date}</li>)}</ul>
  </section>)}</details>;
}
