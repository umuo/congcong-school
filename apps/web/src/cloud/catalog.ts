import "server-only";
import { readFile } from "node:fs/promises";
import path from "node:path";

/** 仅在服务端生成 URL；不读取题目或把完整 Lesson 放进页面 props。 */
export async function cloudLessonParams() {
  const root = process.env.CSF_SOURCE_WEB_ROOT;
  if (!root) throw new Error("请通过项目的隔离构建命令启动云端站点");
  const index = JSON.parse(
    await readFile(path.join(root, "public/data/index.json"), "utf8"),
  );
  const params: { book: string; lesson: string }[] = [];
  for (const book of index.books) {
    const outline = JSON.parse(
      await readFile(
        path.join(root, "public/data/books", book.id, "outline.json"),
        "utf8",
      ),
    );
    for (const lesson of outline.lessons)
      params.push({ book: book.id, lesson: lesson.id });
    for (const unit of outline.units)
      if (unit.examLessonId)
        params.push({ book: book.id, lesson: unit.examLessonId });
  }
  return params;
}
