/** 从现有 core 导出有限的数感日期变体，供 Python 私有题库导入；不写 public。 */
import { createHash } from "node:crypto";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import {
  NUMBER_SKILLS,
  NUMBER_LESSONS,
  NUMBER_SENSE_VERSION,
  numberReviewQuestions,
} from "../../packages/core/src/numberSense";

const root = fileURLToPath(new URL("../../", import.meta.url));
const target = path.join(root, "apps/api/private-content/number-review.json");
const source = "packages/core/src/numberSense.ts";
const sourceHash = createHash("sha256")
  .update(await readFile(path.join(root, source)))
  .digest("hex");
const banks = NUMBER_SKILLS.flatMap((skill) => [
  {
    skill,
    variant: "even",
    questions: numberReviewQuestions(skill, "2026-01-02"),
  },
  {
    skill,
    variant: "odd",
    questions: numberReviewQuestions(skill, "2026-01-01"),
  },
]);
await mkdir(path.dirname(target), { recursive: true });
await writeFile(
  target,
  JSON.stringify(
    {
      generator_version: NUMBER_SENSE_VERSION,
      source,
      source_hash: sourceHash,
      lessons: NUMBER_LESSONS,
      banks,
    },
    null,
    2,
  ) + "\n",
);
console.log(`Exported ${banks.length} private number-review banks.`);
