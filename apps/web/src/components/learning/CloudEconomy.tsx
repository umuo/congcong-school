"use client";
import { useCallback, useEffect, useRef, useState, useSyncExternalStore } from "react";
import { useLearningClient } from "./LearningProvider";
import type { EconomyAction } from "@/lib/learning/client";
import { useAudioPreferences, setAudioPreferences } from "@/lib/learning/preferences";
import { stopTTS } from "@/lib/tts";
import { preferencesPersisted } from "@/lib/learning/preferences";
import { QUEST_POOL } from "@cstf/core/quests";
import { ALL_ACHIEVEMENTS } from "@cstf/core/achievements";
import { leagueTier } from "@cstf/core/league";
import { DAILY_GOAL_OPTIONS, HEART_REFILL_COST, FREEZE_COST, STREAK_MAKEUP_COST } from "@cstf/core/economy";
import { LeagueStandings, type LeagueRow } from "@/components/avatars/LeagueStandings";
import { AVATAR_UPDATED } from "@/lib/avatars/client";
import Link from "next/link";

import { CosmeticPreview, cosmeticGroups, cosmeticGroup } from "./CosmeticPreview";
import { FloatingNotice } from "./FloatingNotice";
import { isEquippedCosmetic } from "@/lib/learning/equipped-cosmetic";

type League = { started: boolean; unlocked: boolean; tier: string; rows: LeagueRow[] };
export function CloudEconomy({ panel = "cottage" }: { panel?: "cottage" | "league" | "shop" }) {
  const client = useLearningClient();
  const snapshot = useSyncExternalStore(client.projection.subscribe, client.projection.getSnapshot, client.projection.getSnapshot);
  const progress = snapshot.progress;
  const [items, setItems] = useState<{id: string; name: string; cost: number}[]>([]);
  const [league, setLeague] = useState<League | null>(null);
  const [cottagePanel, setCottagePanel] = useState("wardrobe");
  const [message, setMessage] = useState("");
  const [busyItem, setBusyItem] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const gate = useRef(false);
  const audio = useAudioPreferences();
  useEffect(() => {
    let mounted = true;
    void client.getProgress().catch(e => { if(mounted) setMessage(e.message); });
    if(panel !== "league") void client.getShop<{items: typeof items}>().then((value) => { if (mounted) setItems(value.items); }).catch((e) => { if (mounted) setMessage(e.message); });
    return () => { mounted = false; };
  }, [client, panel]);
  const leagueVisible = useRef(false);
  const leagueLifetime = useRef({ active: false, generation: 0 });
  const loadLeague = useCallback(async () => {
    const life = leagueLifetime.current;
    const generation = ++life.generation;
    try {
      const value = await client.getLeague<League>();
      if (life.active && generation === life.generation) setLeague(value);
    } catch (e) {
      if (life.active && generation === life.generation) setMessage(e instanceof Error ? e.message : "读取联赛失败");
    }
  }, [client]);
  useEffect(() => {
    const life = { active: true, generation: 0 };
    leagueLifetime.current = life;
    leagueVisible.current = panel === "league";
    if (leagueVisible.current) void loadLeague();
    const refresh = () => { if (leagueVisible.current) void loadLeague(); };
    window.addEventListener(AVATAR_UPDATED, refresh);
    return () => { life.active = false; window.removeEventListener(AVATAR_UPDATED, refresh); };
  }, [loadLeague, panel]);
  async function action(input: Omit<EconomyAction, "client_at">) {
    if (gate.current) return;
    gate.current = true; setBusyItem(input.item_id ?? null); setBusy(true); setMessage("");
    try {
      const value = await client.economy({ ...input, client_at: new Date().toISOString() });
      setMessage(value.result.applied ? (input.item_id ? "装扮已穿上" : "操作已同步") : "当前没有可领取的新奖励");
      if (input.kind === "league") await loadLeague();
    } catch (e) { setMessage(e instanceof Error ? e.message : "操作尚未同步"); }
    finally { gate.current = false; setBusy(false); setBusyItem(null); }
  }
  const locked = busy || snapshot.pending.length > 0;
  const owned = (progress?.state.ownedCosmetics ?? {}) as Record<string, boolean>;
  const waiting = snapshot.pending.filter(key=>!snapshot.sending.includes(key));
  return <section>
    <FloatingNotice message={message || (busy ? "正在同步…" : waiting.length ? "进度还没保存成功，请重试" : "")} duration={busy || waiting.length ? 0 : 3200}>
    {waiting.map((key) => <button key={key} disabled={busy} onClick={async () => {
      setBusy(true);
      try { await client.retry(key); await client.getProgress(); setMessage("已同步。"); }
      catch (e) { setMessage(e instanceof Error ? e.message : "仍未同步"); }
      finally { setBusy(false); }
    }}>重新保存</button>)}
    </FloatingNotice>
    {panel === "cottage" ? <nav className="forest-cottage-tabs" aria-label="小屋内容">{[["wardrobe","我的装扮"],["quests","任务奖励"],["settings","学习设置"]].map(([id,label])=><button key={id} className="secondary" aria-pressed={cottagePanel===id} onClick={()=>setCottagePanel(id)}>{label}</button>)}</nav> : null}
    {panel === "cottage" && cottagePanel === "settings" ? <section className="forest-cottage-panel"><h2>声音与动态</h2><div className="forest-preferences">
    <label>播放轻音效<input type="checkbox" checked={!audio.muted} onChange={e => setAudioPreferences({...audio,muted:!e.target.checked})} /></label>
    <label>自动朗读<input type="checkbox" checked={audio.autoNarrate} onChange={e => {stopTTS();setAudioPreferences({...audio,autoNarrate:e.target.checked});}} /></label>
    <label>减少动态<input type="checkbox" checked={Boolean(audio.reducedMotion)} onChange={e => setAudioPreferences({...audio,reducedMotion:e.target.checked})} /></label>
    </div><p className="account-hint">{preferencesPersisted() ? "已记住这台设备的声音设置。" : "本次设置已生效。"}</p>
    <fieldset className="forest-goal-options"><legend>每天的小目标</legend>{[...new Set([...DAILY_GOAL_OPTIONS, Number(progress?.state.dailyGoal ?? DAILY_GOAL_OPTIONS[0])])].map(n=><button key={n} className="secondary" aria-pressed={Number(progress?.state.dailyGoal ?? DAILY_GOAL_OPTIONS[0])===n} disabled={locked || !progress} onClick={()=>void action({kind:"set_daily_goal",daily_goal:n,revision:progress!.revision})}>{n} XP</button>)}</fieldset>
    </section> : null}
    {panel === "cottage" && cottagePanel === "quests" ? <>
    <section className="forest-cottage-panel"><h2>每日任务与成就</h2>

      {progress?.quests.map((quest) => <p key={String(quest.id)}>{String(quest.label ?? quest.title ?? QUEST_POOL.find(item=>item.id===quest.id)?.title ?? "每日任务")} · {String(quest.progress)}/{String(quest.target)} <button disabled={locked || Boolean(quest.claimed) || Number(quest.progress) < Number(quest.target)} onClick={() => void action({ kind: "quest", quest_id: String(quest.id) })}>{quest.claimed ? "已领取" : `领取 ${quest.reward} 宝石`}</button></p>)}
      <p>已解锁成就：{ALL_ACHIEVEMENTS.filter(item=>Boolean((progress?.state.unlockedAchievements as Record<string,unknown> | undefined)?.[item.id])).map(item=>item.name).join("、") || "继续学习来解锁"}。</p>
    </section>
<details className="forest-supplies"><summary>需要补给时再打开</summary><div className="account-actions">
      <button disabled={locked} onClick={() => void action({ kind: "daily_reward" })}>领取每日奖励</button>
      <button className="secondary" disabled={locked} onClick={() => void action({ kind: "buy_hearts" })}>{HEART_REFILL_COST} 宝石补满红心</button>
      <button className="secondary" disabled={locked} onClick={() => void action({ kind: "buy_freeze" })}>{FREEZE_COST} 宝石买护盾</button>
      <button className="secondary" disabled={locked} onClick={() => void action({ kind: "makeup" })}>{STREAK_MAKEUP_COST} 宝石补昨天连胜</button>
    </div></details>
    </> : null}
    {panel === "shop" || (panel === "cottage" && cottagePanel === "wardrobe") ? <section className="forest-cottage-panel"><h2>{panel === "shop" ? "装扮商店" : "我的装扮"}</h2><div className="forest-wardrobe">{cosmeticGroups.map(group => { const choices=items.filter(item=>(panel === "shop" || owned[item.id]) && cosmeticGroup(item.id)===group.id); return choices.length ? <section key={group.id} aria-label={group.label} className="forest-cosmetic-group"><h3>{group.label}</h3><div className="forest-cosmetic-grid">{choices.map((item) => { const equipped = isEquippedCosmetic(item.id, progress?.state); return <article className="account-row forest-cosmetic-card" key={item.id}>
      <CosmeticPreview id={item.id}/>
      <div><strong>{item.name}</strong><small>{owned[item.id] ? "已拥有" : `${item.cost} 宝石`}</small></div>
      <button className="forest-equip-button" aria-pressed={equipped} aria-busy={busyItem === item.id} disabled={locked || !progress || equipped} onClick={() => void action({ kind: owned[item.id] ? "equip_cosmetic" : "purchase_cosmetic", item_id: item.id })}>{busyItem === item.id ? "穿上中…" : equipped ? "已穿上" : owned[item.id] ? "穿上" : "购买并穿上"}</button>
    </article>; })}</div></section> : null; })}</div>{panel === "cottage" ? <Link href="/shop/">去装扮商店看看</Link> : <Link href="/profile/">返回小屋</Link>}</section> : null}
    {panel === "league" ? <section className="forest-league-board"><span className="forest-league-label">模拟榜 · 练习伙伴</span>
      {league ? <><p>{leagueTier(league.tier).name} · {league.unlocked ? "已解锁" : "完成 10 节课后解锁"}</p><LeagueStandings rows={league.rows}/></> : null}
      <details><summary>周奖励</summary><button disabled={locked} onClick={() => void action({ kind: "league" })}>领取上周奖励</button></details>
    </section> : null}
  </section>;
}
