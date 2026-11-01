import { describe, it, expect } from "vitest";
import { sampleJumpQuestions } from "../jump";
import type { Question } from "../types";
import vectors from "../../spec/jump-vectors.json";

describe("shared cloud jump sampling vectors", () => {
  for (const vector of vectors) {
    it(vector.seed, () => {
      const sources = vector.counts.map((count, i) => ({
        lessonId: `lesson-${i}`,
        questions: Array.from(
          { length: count },
          (_, j) => ({ id: j + 1 }) as Question,
        ),
      }));
      const result = sampleJumpQuestions(sources, vector.size, vector.seed);
      expect(
        result.map((item) => `${item.lessonId}:${item.question.id}`),
      ).toEqual(vector.expected);
    });
  }
});
