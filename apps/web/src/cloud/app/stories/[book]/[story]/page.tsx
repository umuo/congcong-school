import { cloudStoryParams } from "@/cloud/catalog";
import { CloudRoute } from "@/components/learning/CloudRoute";
export const generateStaticParams = cloudStoryParams;
export default async function Page({params}:{params:Promise<{book:string;story:string}>}) { const {book,story}=await params; return <CloudRoute source={{kind:"story",book_id:book,source_id:story}} />; }
