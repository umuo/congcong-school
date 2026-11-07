/** Same-tab recovery only. No per-keystroke network writes or cross-identity reuse. */
export type AnswerDraft = { answer: string; visual: number[]; evidence: number[] };
type DraftStore = Pick<Storage, "getItem" | "setItem" | "removeItem">;
export const answerDraftKey = (scope: { contextId: string; studentId: string }, session: string) =>
  `csf-answer-draft:v1:${scope.contextId}:${scope.studentId}:${session}`;
export function readAnswerDraft(storage: DraftStore | undefined, key: string, question: string, revision: number): AnswerDraft | null {
  try {
    const value = JSON.parse(storage?.getItem(key) ?? "null");
    if (!value || value.question !== question || value.revision !== revision || Date.now() - value.at > 86400000) return null;
    if (typeof value.answer !== "string" || !Array.isArray(value.visual) || !value.visual.every(Number.isFinite) || !Array.isArray(value.evidence) || !value.evidence.every(Number.isInteger)) return null;
    return { answer: value.answer, visual: value.visual, evidence: value.evidence };
  } catch { return null; }
}
export function writeAnswerDraft(storage: DraftStore | undefined, key: string, question: string, revision: number, draft: AnswerDraft) {
  try { storage?.setItem(key, JSON.stringify({ ...draft, question, revision, at: Date.now() })); } catch { /* Input stays usable when storage is unavailable. */ }
}
