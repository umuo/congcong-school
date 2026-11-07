"use client";
import { useEffect, useRef, useState } from 'react';
import { avatarPreset, drawAvatar } from '@/lib/avatars/draw';
export function Avatar({ id, size=44, label }: { id?: string | null; size?: number; label?: string }) {
  const ref = useRef<HTMLCanvasElement>(null);
  const [drawn, setDrawn] = useState(false);
  const preset = avatarPreset(id);
  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    let media: MediaQueryList | undefined;
    const draw = () => {
      try {
        const dpr = Math.max(1, window.devicePixelRatio || 1);
        canvas.width = Math.round(size*dpr); canvas.height = Math.round(size*dpr);
        const ctx = canvas.getContext('2d');
        if (!ctx) { setDrawn(false); return; }
        ctx.setTransform(canvas.width/100,0,0,canvas.height/100,0,0);
        drawAvatar(ctx,preset.id); setDrawn(true);
        media?.removeEventListener('change', draw);
        media = window.matchMedia(`(resolution: ${dpr}dppx)`);
        media.addEventListener('change',draw,{once:true});
      } catch { setDrawn(false); }
    };
    draw();
    return () => media?.removeEventListener('change',draw);
  }, [preset.id,size]);
  return <span className="preset-avatar" role="img" aria-label={label ?? `${drawn ? preset.name : "熊猫"}头像`} style={{width:size,height:size}} data-avatar-id={preset.id}>
    <span className="preset-avatar-fallback" aria-hidden>{drawn ? '' : '熊猫'}</span>
    <canvas ref={ref} aria-hidden="true" style={{width:size,height:size,opacity:drawn?1:0}} />
  </span>;
}
