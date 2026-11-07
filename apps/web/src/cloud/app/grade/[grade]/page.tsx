import { CloudRoute } from "@/components/learning/CloudRoute";
export function generateStaticParams() { return Array.from({length:12},(_,i)=>({grade:String(i+1)})); }
export default function Page() { return <CloudRoute />; }
