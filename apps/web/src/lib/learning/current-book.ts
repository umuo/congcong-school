"use client";
import { useCallback, useSyncExternalStore } from "react";
import { onLearningInvalidated } from "./lifecycle";
const books = new Map<string, string>();
const listeners = new Set<() => void>();
onLearningInvalidated(() => { books.clear(); for (const listener of listeners) listener(); });
/** Navigation choice only: memory scoped to the student, never a progress authority. */
export function useCurrentBook(student: string) {
  const read = useCallback(() => books.get(student) ?? "", [student]);
  const value = useSyncExternalStore(listener => { listeners.add(listener); return () => { listeners.delete(listener); }; }, read, () => "");
  const choose = useCallback((book: string) => { if (book === books.get(student)) return; books.set(student,book); for (const listener of listeners) listener(); }, [student]);
  return [value, choose] as const;
}
