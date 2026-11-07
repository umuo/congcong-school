export type CurriculumSubject = { subject_code: string; book_id: string | null; enabled?: boolean };
export const CHILD_SUBJECTS = [
  { code: "chinese", label: "语文" },
  { code: "math", label: "数学" },
  { code: "english", label: "英语" },
  { code: "science", label: "科学" },
] as const;

/** The child chooses a subject; its textbook is the parent's authorized selection. */
export function subjectChoices(curriculum: readonly CurriculumSubject[]) {
  return CHILD_SUBJECTS.map(subject => ({ ...subject,
    bookId: curriculum.find(row => row.subject_code === subject.code && row.enabled !== false)?.book_id || null,
  }));
}

export function availableSubjectBook(curriculum: readonly CurriculumSubject[], current: string, requested = "") {
  const choices = subjectChoices(curriculum);
  return [current, requested].find(book => book && choices.some(subject => subject.bookId === book))
    || choices.find(subject => subject.bookId)?.bookId || "";
}
