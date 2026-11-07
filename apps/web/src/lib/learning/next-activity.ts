export type CourseItem = { kind: "lesson" | "challenge" | "story" | "reading"; source_id: string; title: string; unit_number: number | null; question_count: number };
export type ActiveActivity = { id: string; kind: string; book_id: string | null; source_id: string | null; created_at: string };
/** Pure presentation selection: never creates sessions or changes progress. */
export function nextActivity(book: string, items: CourseItem[], completed: Record<string, unknown>, active: ActiveActivity[]) {
  const resume = active.find(activity => activity.book_id === book);
  if (resume) return { type: "resume" as const, id: resume.id, item: items.find(item => item.source_id === resume.source_id && item.kind === resume.kind) };
  const item = items.find(item => item.kind === "lesson" && !completed[item.source_id]);
  if (item) return { type: "lesson" as const, item };
  return { type: "review" as const };
}

/** Name non-course sessions without changing which existing session is resumed. */
export function activityTitle(kind: string | undefined) {
  return ({lesson:"上次的课程",challenge:"单元挑战",story:"故事阅读",reading:"听读练习",review:"复习练习",jump:"跳级挑战",number_review:"数感练习"} as Record<string,string>)[kind ?? ""] ?? "上次的练习";
}
