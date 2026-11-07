import { learnerProfiles } from "../learnerProfiles";
import { useProgressStore } from "../../store/progress";
import type { LearningClient } from "./client";

type LocalProgress = ReturnType<typeof useProgressStore.getState>;
/** 仅 local 目标导入此适配器；沿用 v13 档案和既有领域规则。 */
export function createLocalLearningClient(): LearningClient<LocalProgress> & {
  run<T>(operation: (store: LocalProgress) => T): T;
} {
  const studentId = learnerProfiles().activeId;
  let active = true;
  const check = () => { if (!active) throw new Error("本地学习档案已关闭"); };
  return {
    mode: "local",
    scope: Object.freeze({ contextId: `local:${studentId}`, studentId }),
    async getProgress() { check(); return useProgressStore.getState(); },
    run(operation) { check(); return operation(useProgressStore.getState()); },
    dispose() { active = false; },
  };
}
