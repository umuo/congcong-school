import assert from "node:assert/strict";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import type { Question } from "../../packages/core/src/types";

async function main() {
  Object.defineProperty(globalThis, "localStorage", {
    value: { getItem: () => null, setItem: () => {}, removeItem: () => {} },
    configurable: true,
  });
  const { TTSButton } = await import("../../apps/web/src/components/TTSButton");
  const { QuestionRenderer } = await import(
    "../../apps/web/src/components/question/QuestionRenderer"
  );
  const { numberSenseQuestions } = await import(
    "../../packages/core/src/numberSense"
  );
  const sample = (
    type: Question["type"],
    extra: Partial<Question> = {},
  ): Question => ({
    id: 1,
    type,
    question: "试一试",
    options: [],
    answer: "2",
    explanation: "看看方法",
    score: 5,
    difficulty: 1,
    knowledge_point: "例题",
    audio: { question: "/voice.mp3" },
    ...extra,
  });
  const questions = [
    sample("choice", { options: ["2", "3", "4"], answer: "2" }),
    sample("true_false", { answer: "对" }),
    sample("calculation"),
    sample("fill_blank_text", { answer: "山" }),
    sample("word_order", { options: ["I", "am", "Sam"], answer: "I am Sam" }),
    sample("matching", { options: ["one", "two", "three", "four", "1", "2", "3", "4"], answer: "A-1,B-2,C-3,D-4" }),
    ...numberSenseQuestions("compare"),
  ];
  for (const question of questions) {
    for (const phase of ["answering", "checked"] as const) {
      const html = renderToStaticMarkup(
        <QuestionRenderer
          question={question}
          answer=""
          phase={phase}
          isCorrect={phase === "checked" ? false : null}
          onChange={() => {}}
        />,
      );
      assert.equal(
        (html.match(/<h2>/g) ?? []).length,
        1,
        `${question.type}: one shared question heading, including visual questions`,
      );
      assert(html.includes(question.question));
      assert(
        !html.includes('role="button" tabindex'),
        "audio actions must be native keyboard-operable buttons",
      );
    }
    const saving = renderToStaticMarkup(<QuestionRenderer question={question} answer="" phase="answering" isCorrect={null} onChange={() => {}} locked />);
    for (const button of saving.matchAll(/<button\b[^>]*>/g)) {
      assert.match(button[0], /disabled=""/, `${question.type}: waiting controls must look disabled, rather than silently ignore the child's click`);
    }
  }
  // Saving locks editing, but must never imply grading a partial answer.
  for (const question of questions.filter(q => ["calculation", "fill_blank_text", "word_order"].includes(q.type))) {
    const box = (phase: "answering" | "checked", locked: boolean, isCorrect: boolean | null) => {
      const html = renderToStaticMarkup(<QuestionRenderer question={question} answer={question.type === "fill_blank_text" ? "y" : "1"} phase={phase} isCorrect={isCorrect} onChange={() => {}} locked inputKeyboard={{candidates:["y","o","u","r"],language:"letters",max_length:10}} />);
      const match = html.match(/<div[^>]*class="([^"]*min-h-\[(?:68|64)px\][^"]*)"/);
      assert.ok(match, `${question.type}: answer display exists`);
      return match[1];
    };
    for (const locked of [false,true]) {
      for (const result of [null,false,true]) {
        assert.doesNotMatch(box("answering",locked,result), /border-(?:danger|primary)|bg-(?:danger|primary)\//, `${question.type}: typing/saving a partial answer stays neutral`);
      }
      assert.doesNotMatch(box("checked",locked,null), /border-(?:danger|primary)|bg-(?:danger|primary)\//, `${question.type}: an unknown result stays neutral`);
      assert.match(box("checked",locked,true), /border-primary/);
      assert.match(box("checked",locked,false), /border-danger/);
    }
  }
  const audio = renderToStaticMarkup(
    <TTSButton src="/voice.mp3" label="听题目" disabled />,
  );
  assert.match(audio, /<button[^>]*type="button"/);
  assert.match(audio, /disabled=""/);
  assert.match(audio, /aria-label="听题目"/);
  assert.equal(
    renderToStaticMarkup(<TTSButton />),
    "",
    "missing audio does not leave a fake control",
  );
  const locked = renderToStaticMarkup(
    <QuestionRenderer
      question={questions[0]}
      answer=""
      phase="answering"
      isCorrect={null}
      onChange={() => {}}
      locked
    />,
  );
  assert.equal((locked.match(/class="[^"]*option-card/g) ?? []).length, 3);
  assert.equal(
    (locked.match(/disabled=""/g) ?? []).length,
    4,
    "all three options and the audio action are disabled under a modal",
  );
  console.log(
    "PASS: 24 question states have one prompt, native audio semantics, locked actions and no missing-audio controls.",
  );
}
main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
