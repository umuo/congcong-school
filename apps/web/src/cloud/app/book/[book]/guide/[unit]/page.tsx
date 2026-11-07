import { cloudGuideParams } from "@/cloud/catalog";
import { CloudGuide } from "@/components/learning/CloudGuide";
export const generateStaticParams = cloudGuideParams;
export default async function Page({params}:{params:Promise<{book:string;unit:string}>}) {
  const {book,unit}=await params;
  return <CloudGuide book={book} unit={Number(unit)} />;
}
