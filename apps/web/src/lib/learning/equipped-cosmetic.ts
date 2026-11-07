import { getCosmeticById } from "@cstf/core/cosmetics";
const slots = {
  mascot_skin: ["equippedMascotSkin", "skin_default"],
  ui_theme: ["equippedTheme", "theme_default"],
  lesson_backdrop: ["equippedBackdrop", "backdrop_default"],
} as const;
export function isEquippedCosmetic(id: string, state: Record<string, unknown> | undefined) {
  const type = getCosmeticById(id)?.type;
  if (!type || !state) return false;
  const [slot, fallback] = slots[type];
  return (state[slot] ?? fallback) === id;
}
