import { UI_THEMES } from "../../packages/core/src/cosmetics";
import assert from "node:assert/strict";
import React, { StrictMode } from "react";
import TestRenderer, { act } from "react-test-renderer";
import { LearningProvider, useLearningClient } from "../../apps/web/src/components/learning/LearningProvider";
import { invalidateLearning } from "../../apps/web/src/lib/learning/lifecycle";
import type { CloudLearningClient } from "../../apps/web/src/lib/learning/client";
import type { Account } from "../../apps/web/src/lib/api/client";

async function main() {
  const data = new Map<string, string>();
  const storage = { get length() { return data.size; }, key: (index: number) => [...data.keys()][index] ?? null,
    getItem: (key: string) => data.get(key) ?? null,
    setItem: (key: string, value: string) => { data.set(key, value); },
    removeItem: (key: string) => { data.delete(key); } };
  let localReads = 0;
  Object.assign(globalThis, { IS_REACT_ACT_ENVIRONMENT: true, window: {
    sessionStorage: storage,
    get localStorage() { localReads++; throw new Error("cloud must not initialize local profiles"); },
  } });
  let current!: CloudLearningClient;
  function Probe() { current = useLearningClient(); return <span>{current.scope.studentId}</span>; }
  const first = { context_id: "first", student_id: "student-a", mode: "child", must_change_password: false } as Account;
  const second = { ...first, context_id: "second", student_id: "student-b" };
  const tree = (account: Account) => <StrictMode><LearningProvider key={account.context_id} account={account}><Probe /></LearningProvider></StrictMode>;
  let renderer!: TestRenderer.ReactTestRenderer;
  await act(async () => { renderer = TestRenderer.create(tree(first)); });
  const old = current;
  old.prepare("/students/student-a/economy/actions", { kind: "daily_reward" });
  assert.equal(data.size, 1);
  await act(async () => { renderer.update(tree(second)); });
  assert.equal(current.scope.studentId, "student-b");
  assert.notEqual(current, old);
  assert.equal(data.size, 0);
  await assert.rejects(old.getProgress(), /身份已变化/);
  for (const theme of UI_THEMES) {
    await act(async () => { current.projection.progress({student_id:"student-b",revision:1,rule_version:"test",state:{xp:0,gems:0,hearts:5,completedLessons:{},equippedTheme:theme.id},quests:[]}); });
    const surface=renderer.root.findByType("div");
    assert.equal(Boolean(surface.props.className?.split(" ").includes("theme-dark")),Boolean(theme.data.isDark));
    if(theme.id!=="theme_default") {
      assert.equal(surface.props.style["--theme-primary"],theme.data.primary);
      assert.equal(surface.props.style["--app-card"],theme.data.cardBg ?? "#ffffff");
    }
  }
  current.prepare("/students/student-b/economy/actions", { kind: "daily_reward" });
  await act(async () => { invalidateLearning(); });
  assert.equal(data.size, 0);
  assert.equal(current.projection.getSnapshot().progress, null);
  assert.match(JSON.stringify(renderer.toJSON()), /正在确认学习身份/);
  await act(async () => { renderer.unmount(); });
  // 组件已经卸载时的登录变化也必须清理保留队列。
  data.set("csf-cloud-pending-v1:unmounted", "old answer");
  data.set("local-backup", "preserve");
  invalidateLearning();
  assert.deepEqual([...data], [["local-backup", "preserve"]]);
  assert.equal(localReads, 0);
  console.log("PASS LearningProvider: StrictMode, student remount, retired client, invalidation, unmounted queue cleanup, no local profile initialization; all 10 equipped-theme variables and dark surface hooks.");
}
void main().catch((error) => { console.error(error); process.exitCode = 1; });
