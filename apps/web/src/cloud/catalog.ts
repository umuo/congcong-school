import "server-only";
import { readFile } from "node:fs/promises";
import path from "node:path";

async function catalog() {
  const root = process.env.CSF_SOURCE_WEB_ROOT;
  if (!root) throw new Error("请通过隔离构建入口启动");
  const index = JSON.parse(await readFile(path.join(root, "public/data/index.json"), "utf8"));
  return { root, index };
}
export async function cloudBookParams() {
  const { index } = await catalog();
  return index.books.map((book: { id: string }) => ({ book: book.id }));
}
export async function cloudStoryParams() {
  const { root, index } = await catalog();
  const rows: { book: string; story: string }[] = [];
  for (const book of index.books) {
    if (!book.hasStories) continue;
    const data = JSON.parse(await readFile(path.join(root, "public/data/books", book.id, "stories.json"), "utf8"));
    for (const story of data.stories) rows.push({ book: book.id, story: story.id });
  }
  return rows;
}
export async function cloudReadingParams() {
  const { root, index } = await catalog();
  const rows: { book: string; passage: string }[] = [];
  for (const book of index.books) {
    if (!book.hasPassages) continue;
    const data = JSON.parse(await readFile(path.join(root, "public/data/books", book.id, "passages.json"), "utf8"));
    for (const passage of data.passages) rows.push({ book: book.id, passage: passage.id });
  }
  return rows;
}
export async function cloudGuideParams() {
  const { root, index } = await catalog();
  const rows: { book: string; unit: string }[] = [];
  for (const book of index.books) {
    const outline = JSON.parse(await readFile(path.join(root, "public/data/books", book.id, "outline.json"), "utf8"));
    for (const unit of outline.units) rows.push({ book: book.id, unit: String(unit.unit_number) });
  }
  return rows;
}

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
