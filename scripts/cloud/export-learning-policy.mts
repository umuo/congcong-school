/** 从现有 core 导出服务端数值及目录；不包含任何题目或答案。 */
import { createHash } from "node:crypto";
import { readFile, writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import path from "node:path";
import * as economy from "../../packages/core/src/economy";
import {
  ALL_COSMETICS,
  DEFAULT_EQUIPPED,
} from "../../packages/core/src/cosmetics";
import { ALL_ACHIEVEMENTS } from "../../packages/core/src/achievements";
import { QUEST_POOL } from "../../packages/core/src/quests";
import {
  NUMBER_LESSONS,
  NUMBER_SENSE_VERSION,
} from "../../packages/core/src/numberSense";
const root = fileURLToPath(new URL("../../", import.meta.url));
const metric: Record<string, string> = {
  "first-lesson": "lessons",
  "ten-lessons": "lessons",
  "fifty-lessons": "lessons",
  "xp-100": "xp",
  "xp-1000": "xp",
  "xp-5000": "xp",
  "streak-3": "streak",
  "streak-7": "streak",
  "streak-30": "streak",
  "streak-100": "streak",
  "perfect-1": "perfect",
  "perfect-10": "perfect",
  "perfect-50": "perfect",
  "first-cosmetic": "cosmetics",
  "gem-collector": "lifetimeGems",
  "first-review": "reviews",
};
const files = [
  "economy",
  "cosmetics",
  "achievements",
  "quests",
  "numberSense",
].map((name) => `packages/core/src/${name}.ts`);
const source_hashes = Object.fromEntries(
  await Promise.all(
    files.map(async (file) => [
      file,
      createHash("sha256")
        .update(await readFile(path.join(root, file)))
        .digest("hex"),
    ]),
  ),
);
const policy = {
  version: "cstf-economy-1",
  source_hashes,
  constants: Object.fromEntries(
    Object.entries(economy).filter(([, value]) => typeof value !== "function"),
  ),
  cosmetics: ALL_COSMETICS,
  equipped: DEFAULT_EQUIPPED,
  achievements: ALL_ACHIEVEMENTS.map(({ getProgress, ...value }) => {
    if (!metric[value.id])
      throw new Error(`Missing achievement metric: ${value.id}`);
    return { ...value, metric: metric[value.id] };
  }),
  quests: QUEST_POOL,
  number_lessons: NUMBER_LESSONS,
  number_version: NUMBER_SENSE_VERSION,
};
await writeFile(
  path.join(root, "apps/api/app/learning/policy.json"),
  JSON.stringify(policy, null, 2) + "\n",
);
console.log(
  `Exported ${policy.cosmetics.length} cosmetics, ${policy.achievements.length} achievements and ${policy.quests.length} quest definitions`,
);
