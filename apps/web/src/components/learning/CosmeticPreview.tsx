"use client";
import { Mascot } from "@/components/Mascot";
import { getCosmeticById, UI_THEMES, LESSON_BACKDROPS } from "@cstf/core/cosmetics";
import { Shirt } from "lucide-react";
export const cosmeticGroups = [
  { id: "mascot_skin", label: "熊猫装扮" },
  { id: "ui_theme", label: "界面主题" },
  { id: "lesson_backdrop", label: "答题背景" },
  { id: "other", label: "其他装扮" },
] as const;
export const cosmeticGroup = (id: string) => getCosmeticById(id)?.type ?? "other";
export function CosmeticPreview({ id }: { id: string }) {
  const type = cosmeticGroup(id);
  const theme = UI_THEMES.find(item=>item.id===id);
  const illustration = id === "skin_default" ? "default" : id === "skin_graduate" ? "graduate" : null;
  const backdrop = LESSON_BACKDROPS.find(item=>item.id===id);
  return <div className="forest-cosmetic-preview" aria-hidden="true">
    {type === "mascot_skin" ? (illustration ? <img src={`/forest/forest-guide-${illustration}.webp`} width={64} height={76} alt="" loading="lazy"/> : <Mascot size={72} animate={false} skinOverride={id}/>) : theme ? <div className="forest-theme-preview" style={{background:theme.data.bg}}><span style={{background:theme.data.primary}}/><span style={{background:theme.data.accent}}/><span style={{background:theme.data.primaryDark}}/></div> : backdrop ? <div className="forest-backdrop-preview" style={{background:backdrop.data.background}}><span/><span/><span/></div> : <Shirt size={42}/>}
  </div>;
}
