import { describe, expect, it } from "vitest";
import vectors from "../../spec/grading-vectors.json";
import { gradeAnswer, GRADING_RULE_VERSION } from "../grade";
import type { Question } from "../types";

describe("versioned TS/Python grading vectors", () => {
  it("pins the rule version", () =>
    expect(GRADING_RULE_VERSION).toBe(vectors.version));
  for (const vector of vectors.cases) {
    it(vector.id, () => {
      const question = {
        type: vector.type,
        answer: vector.answer,
        options: vector.options ?? [],
      } as Question;
      expect(gradeAnswer(question, vector.input as string)).toBe(
        vector.expected,
      );
    });
  }
});
