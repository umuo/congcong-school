"use client";
import { AccountGuard } from "@/components/account/AccountShell";
import { CloudLearningWorkspace } from "./CloudLearningWorkspace";
export function CloudLessonEntry({ book, lesson }: { book: string; lesson: string }) {
  return <AccountGuard destination="/learn">{() => <CloudLearningWorkspace initialSource={{ kind: lesson.endsWith("-exam") ? "challenge" : "lesson", book_id: book, source_id: lesson }} />}</AccountGuard>;
}
