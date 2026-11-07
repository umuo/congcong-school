import { cloudBookParams } from "@/cloud/catalog";
import { CloudRoute } from "@/components/learning/CloudRoute";
export const generateStaticParams = cloudBookParams;
export default async function Page({params}:{params:Promise<{book:string}>}) { const {book}=await params; return <CloudRoute book={book} kind="lesson" />; }
