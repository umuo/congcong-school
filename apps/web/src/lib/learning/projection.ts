import type { LearningSessionView } from "../api/learning-contract";

export type ProgressProjection = {
  student_id: string;
  revision: number;
  rule_version: string;
  state: {
    xp: number;
    gems: number;
    hearts: number;
    completedLessons: Record<string, unknown>;
    [key: string]: unknown;
  };
  quests: Record<string, unknown>[];
};

/** 云端只缓存服务端投影。界面草稿、音效等状态不参与成绩合并。 */
export function createLearningProjection() {
  let value: {
    progress: ProgressProjection | null;
    sessions: Record<string, LearningSessionView>;
    pending: string[];
    sending: string[];
  } = { progress: null, sessions: {}, pending: [], sending: [] };
  const listeners = new Set<() => void>();
  const publish = (next: typeof value) => {
    value = next;
    for (const listener of listeners) listener();
  };
  return {
    getSnapshot: () => value,
    subscribe(listener: () => void) {
      listeners.add(listener);
      return () => { listeners.delete(listener); };
    },
    progress(next: ProgressProjection) {
      if (!value.progress || next.revision >= value.progress.revision)
        publish({ ...value, progress: structuredClone(next) });
    },
    session(next: LearningSessionView) {
      if (!value.sessions[next.id] || next.revision >= value.sessions[next.id].revision)
        publish({ ...value, sessions: { ...value.sessions, [next.id]: structuredClone(next) } });
    },
    pending(keys: string[], sending: string[] = []) { publish({ ...value, pending: [...keys], sending: [...sending] }); },
    clear() { publish({ progress: null, sessions: {}, pending: [], sending: [] }); },
  };
}
