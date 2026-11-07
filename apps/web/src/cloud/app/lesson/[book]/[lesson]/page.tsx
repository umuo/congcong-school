import { cloudLessonParams } from "@/cloud/catalog";
import { CloudLessonEntry } from "@/components/learning/CloudLessonEntry";
export const generateStaticParams = cloudLessonParams;
export default async function CloudLessonPage({ params }: { params: Promise<{ book: string; lesson: string }> }) {
  const { book, lesson } = await params;
  return <CloudLessonEntry book={book} lesson={lesson} />;
}
