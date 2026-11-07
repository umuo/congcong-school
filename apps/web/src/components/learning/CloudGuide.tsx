"use client";
import { useEffect, useState } from "react";
import { AccountGuard } from "@/components/account/AccountShell";
import { useLearningClient } from "./LearningProvider";
import { MathText } from "@/components/MathText";
import { TTSButton } from "@/components/TTSButton";

type Item = { source_id: string; unit_number: number; kind: string };
type Knowledge = { point: string; core_concept: string; key_formula: string; common_mistakes: string[]; tips: string; audio?: Record<string, string | string[]> };
function Guide({ book, unit }: { book: string; unit: number }) {
  const client = useLearningClient();
  const [items, setItems] = useState<{id: string; knowledge: Knowledge}[]>([]);
  const [error, setError] = useState("");
  useEffect(() => {
    let mounted = true;
    void (async () => {
      try {
        const catalog = await client.getBookContent<Item[]>(book);
        const selected = catalog.filter((item) => item.kind === "lesson" && item.unit_number === unit);
        const rows = await Promise.all(selected.map(async (item) => {
          const value = await client.getContent<{metadata: {knowledge?: Knowledge}}>(book, "lesson", item.source_id);
          return { id: item.source_id, knowledge: value.metadata.knowledge };
        }));
        if (mounted) setItems(rows.filter((row): row is {id: string; knowledge: Knowledge} => !!row.knowledge));
      } catch (e) { if (mounted) setError(e instanceof Error ? e.message : "讲解加载失败"); }
    })();
    return () => { mounted = false; };
  }, [book, unit, client]);
  return <main className="account-card"><a href="/learn/">返回学习首页</a><h1>第 {unit} 单元学习手册</h1>{error ? <p role="alert">{error}</p> : null}
    {items.map((item) => <article className="account-card" key={item.id}><h2>{item.knowledge.point}</h2>{(["core_concept", "key_formula", "common_mistakes", "tips"] as const).map((field) => {
      const text = item.knowledge[field];
      const audio = item.knowledge.audio?.[field];
      return <div key={field}><MathText text={Array.isArray(text) ? text.join("\n") : text ?? ""} />{(Array.isArray(audio) ? audio : [audio]).filter(Boolean).map((src, i) => <TTSButton key={i} src={`/api/v1/content/books/${encodeURIComponent(book)}/lesson/${encodeURIComponent(item.id)}/media?path=${encodeURIComponent(src!)}`} />)}</div>;
    })}</article>)}
    {!items.length && !error ? <p>正在读取讲解，或本单元尚无讲解。</p> : null}
  </main>;
}
export function CloudGuide({ book, unit }: { book: string; unit: number }) {
  return <AccountGuard destination="/learn">{() => <Guide book={book} unit={unit} />}</AccountGuard>;
}
