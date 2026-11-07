import type { LearningScope } from "./client";
import { CLOUD_REPORT_PREFIX } from "./lifecycle";

export type CloudQuestionReport = {
  id: string; student_id: string; created_at: string;
  question_uid: string; question_version: string; source_id: string | null;
  question_text: string; answer_given: string;
  kind: "question_wrong" | "answer_should_count" | "audio_issue";
};
export const reportKey = (scope: LearningScope) => `${CLOUD_REPORT_PREFIX}${scope.contextId}:${scope.studentId}`;
export function cloudReports(scope: LearningScope): CloudQuestionReport[] {
  try {
    const data = JSON.parse(window.sessionStorage.getItem(reportKey(scope)) ?? "[]");
    return Array.isArray(data) ? data.filter((row) => row?.student_id === scope.studentId).slice(-200) : [];
  } catch { return []; }
}
export function addCloudReport(scope: LearningScope, value: Omit<CloudQuestionReport, "id" | "created_at" | "student_id">) {
  const record: CloudQuestionReport = { ...value, question_text: value.question_text.slice(0, 1600), answer_given: value.answer_given.slice(0, 10000), id: crypto.randomUUID(), created_at: new Date().toISOString(), student_id: scope.studentId };
  window.sessionStorage.setItem(reportKey(scope), JSON.stringify([...cloudReports(scope), record].slice(-200)));
}
