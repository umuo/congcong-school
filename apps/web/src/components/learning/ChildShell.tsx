"use client";
import { createContext, useContext, useEffect, useState, useSyncExternalStore, type ReactNode } from "react";
import { MotionConfig } from "framer-motion";
import Link from "next/link";
import { useCurrentBook } from "@/lib/learning/current-book";
import { usePathname } from "next/navigation";
import { BookOpen, Compass, Trophy, House, Star, Gem, Volume2, VolumeX } from "lucide-react";
import type { Account } from "@/lib/api/client";
import { AvatarEditor } from "@/components/avatars/AvatarEditor";
import { useLearningClient } from "./LearningProvider";
import { useAudioPreferences, setAudioPreferences } from "@/lib/learning/preferences";

const ChildLogout = createContext<() => void>(() => {});
export const useChildLogout = () => useContext(ChildLogout);

export function ChildShell({ account, children, onLogout }: { account: Account; children: ReactNode; onLogout: () => void }) {
  const client = useLearningClient();
  const path = usePathname();
  const [book] = useCurrentBook(client.scope.studentId);
  const [nickname, setNickname] = useState("小伙伴");
  const progress = useSyncExternalStore(client.projection.subscribe, client.projection.getSnapshot, client.projection.getSnapshot).progress;
  const audio = useAudioPreferences();
  useEffect(() => { let active = true; void client.getProfile().then(p => { if (active) setNickname(p.nickname); }).catch(() => {}); return () => { active = false; }; }, [client]);
  const tabs = [["/learn/", "学习", BookOpen], ["/explore/", "探索", Compass], ["/league/", "排行", Trophy], ["/profile/", "小屋", House]] as const;
  return <MotionConfig reducedMotion={audio.reducedMotion ? "always" : "user"}><div className="forest-child" data-reduced-motion={audio.reducedMotion}>
    <header className="account-toolbar">
      <AvatarEditor account={account} label={`${nickname}的头像`} />
      <div className="forest-stats" aria-label="学习进度"><span><Star size={16} aria-hidden />{progress?.state.xp ?? "—"} XP</span><span><Gem size={16} aria-hidden />{progress?.state.gems ?? "—"}</span></div>
      <button className="secondary" aria-label={audio.muted ? "打开音效" : "关闭音效"} aria-pressed={!audio.muted} onClick={() => setAudioPreferences({ ...audio, muted: !audio.muted })}>{audio.muted ? <VolumeX size={20} /> : <Volume2 size={20} />}</button>
    </header>
    <ChildLogout.Provider value={onLogout}>{children}</ChildLogout.Provider>
    <nav className="forest-bottom-nav" aria-label="儿童导航">{tabs.map(([href, label, Icon]) => <Link key={href} href={book && (href === "/learn/" || href === "/explore/") ? `${href}?book=${encodeURIComponent(book)}` : href} aria-current={path.startsWith(href.slice(0,-1)) || (href === "/explore/" && /\/(stories|reading)\//.test(path)) || (href === "/profile/" && path.startsWith("/shop")) ? "page" : undefined}><Icon size={24} aria-hidden /><span>{label}</span></Link>)}</nav>
  </div></MotionConfig>;
}
