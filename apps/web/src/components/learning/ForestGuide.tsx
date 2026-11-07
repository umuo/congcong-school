"use client";
import { useEffect, useState } from "react";
import { Mascot } from "@/components/Mascot";
import { useMascotSkin } from "@/lib/learning/preferences";

/** Illustrated home guide; all other earned outfits retain their original renderer. */
export function ForestGuide() {
  const skin = useMascotSkin();
  const [failed, setFailed] = useState(false);
  useEffect(() => setFailed(false), [skin]);
  const illustration = skin === "skin_default" ? "default" : skin === "skin_graduate" ? "graduate" : null;
  return <div className="forest-guide">{illustration && !failed
    ? <img src={`/forest/forest-guide-${illustration}.webp`} alt="聪聪，向你挥手" width={148} height={172} onError={() => setFailed(true)} />
    : <Mascot size={148} mood="wave" />}</div>;
}
