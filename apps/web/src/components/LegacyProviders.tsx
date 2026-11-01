"use client";
import type { ReactNode } from "react";
import { ThemeProvider } from "./ThemeProvider";
import { ToastProvider } from "./Toast";
import { DailyRewardWatcher } from "./DailyRewardWatcher";
import { AchievementWatcher } from "./AchievementWatcher";
import { LeagueWatcher } from "./LeagueWatcher";
import { IntroAudioUnlock } from "./IntroAudioUnlock";
import { BottomNav } from "./BottomNav";

export default function LegacyProviders({ children }: { children: ReactNode }) {
  return (
    <ThemeProvider>
      <ToastProvider>
        <DailyRewardWatcher />
        <AchievementWatcher />
        <LeagueWatcher />
        <IntroAudioUnlock />
        {children}
        <BottomNav />
      </ToastProvider>
    </ThemeProvider>
  );
}
