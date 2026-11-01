import { cloudLessonParams } from "@/cloud/catalog";
import { CloudEntry } from "@/cloud/CloudEntry";
export const generateStaticParams = cloudLessonParams;
export default function CloudLessonPage() {
  return <CloudEntry />;
}
