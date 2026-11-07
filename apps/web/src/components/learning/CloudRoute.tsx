"use client";
import { useEffect, useState } from "react";
import { AccountGuard } from "@/components/account/AccountShell";
import { CloudLearningWorkspace } from "./CloudLearningWorkspace";
import { CloudEconomy } from "./CloudEconomy";
import type { Source } from "./CloudSessionRunner";
import Link from "next/link";
export function CloudRoute({ source, book, kind, tools = false, panel, query }: { source?: Source; book?: string; kind?: "lesson" | "story" | "reading"; tools?: boolean; panel?: "league" | "shop"; query?: "jump" | "number_review" | "review" }) {
  const [resolved, setResolved] = useState<Source | undefined>(source);
  const [ready, setReady] = useState(!query);
  const [error, setError] = useState("");
  useEffect(() => {
    if (!query) return;
    const params = new URLSearchParams(window.location.search);
    if (query === "jump") {
      const bookId = params.get("book"), unit = Number(params.get("unit"));
      if (bookId && Number.isSafeInteger(unit) && unit >= 2) setResolved({ kind: "jump", book_id: bookId, target_unit: unit });
      else setError("请选择教材及有效的跳级目标单元。");
    } else if (query === "number_review") {
      const skill = params.get("skill") ?? "count";
      if (skill === "count" || skill === "compare" || skill === "apply") setResolved({ kind: "number_review", number_skill: skill });
      else setError("请选择有效的数感检验类型。");
    } else setResolved({ kind: "review", for_hearts: params.get("from") === "hearts", ...(params.get("book") ? { book_id: params.get("book")! } : {}) });
    setReady(true);
  }, [query]);
  return <AccountGuard destination="/learn">{() => <main className="account-card forest-main">{!ready ? <p role="status">正在读取学习入口…</p> : error ? <><p role="alert">{error}</p><Link href="/learn/">返回学习首页</Link></> : tools ? <section className="forest-mission"><h1>{panel === "shop" ? "森林装扮商店" : "森林排行榜"}</h1><CloudEconomy panel={panel ?? "league"} /></section> : <CloudLearningWorkspace initialSource={resolved} initialBook={book} initialKind={kind} />}</main>}</AccountGuard>;
}
