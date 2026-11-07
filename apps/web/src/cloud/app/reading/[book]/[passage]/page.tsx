import { cloudReadingParams } from "@/cloud/catalog";
import { CloudRoute } from "@/components/learning/CloudRoute";
export const generateStaticParams = cloudReadingParams;
export default async function Page({params}:{params:Promise<{book:string;passage:string}>}) { const {book,passage}=await params; return <CloudRoute source={{kind:"reading",book_id:book,source_id:passage, reading_kind: "listen"}} />; }
