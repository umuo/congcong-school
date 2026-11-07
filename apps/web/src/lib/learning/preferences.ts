"use client";
import { useSyncExternalStore } from "react";
import { isMuted, setEffectsMuted } from "../sfx";

export type AudioPreferences = { muted: boolean; autoNarrate: boolean; reducedMotion?: boolean };
const defaults: AudioPreferences = { muted: false, autoNarrate: true, reducedMotion: false };
let value: AudioPreferences = defaults;
let scope: string | null = null;
let storage: Pick<Storage, "getItem" | "setItem"> | undefined;
let persistent = true;
const memory = new Map<string, AudioPreferences>();
export function bindPreferences(subject: string, deviceStorage?: Pick<Storage, "getItem" | "setItem">) {
  scope = subject; storage = deviceStorage; persistent = Boolean(storage);
  let next = memory.get(subject) ?? (isMuted() ? { ...defaults, muted: true, autoNarrate: false } : defaults);
  try {
    const raw = storage?.getItem(`csf-preferences-v1:${subject}`);
    if (raw) {
      const saved = JSON.parse(raw);
      if (typeof saved.muted === "boolean" && typeof saved.autoNarrate === "boolean") next = { muted: saved.muted, autoNarrate: saved.autoNarrate, reducedMotion: saved.reducedMotion === true };
    }
  } catch { persistent = false; }
  value = { ...next }; setEffectsMuted(value.muted);
  for (const listener of listeners) listener();
}
export function preferencesPersisted() { return persistent; }
export function getAudioPreferences() { return value; }
let mascotSkin = "skin_default";
const listeners = new Set<() => void>();
export function setAudioPreferences(next: AudioPreferences) {
  if (next.muted === value.muted && next.autoNarrate === value.autoNarrate && next.reducedMotion === value.reducedMotion) return;
  value = { muted: next.muted, autoNarrate: next.autoNarrate, reducedMotion: Boolean(next.reducedMotion) };
  if (scope) {
    memory.set(scope, value);
    try { storage?.setItem(`csf-preferences-v1:${scope}`, JSON.stringify(value)); } catch { persistent = false; }
    setEffectsMuted(value.muted);
  }
  for (const listener of listeners) listener();
}
export function useAudioPreferences() {
  return useSyncExternalStore((listener) => {
    listeners.add(listener);
    return () => { listeners.delete(listener); };
  }, () => value, () => value);
}
export function setMascotSkin(next: string) {
  if (next === mascotSkin) return;
  mascotSkin = next;
  for (const listener of listeners) listener();
}
export function useMascotSkin() {
  return useSyncExternalStore((listener) => {
    listeners.add(listener);
    return () => { listeners.delete(listener); };
  }, () => mascotSkin, () => mascotSkin);
}
