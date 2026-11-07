"use client";

/**
 * useRecorder — 轻量麦克风录音 hook。
 *
 * - 用原生 MediaRecorder，不接 ASR、不上传
 * - 每次 stop() 返回一个 blob URL，交给组件去 new Audio(url) 回放
 * - 刷新页面即丢（不落磁盘），因此不涉及隐私持久化
 *
 * 用法：
 *   const rec = useRecorder();
 *   await rec.start();
 *   const url = await rec.stop(); // blob URL
 */
import { suppressEffects } from "./sfx";
import { useCallback, useEffect, useRef, useState } from "react";

export type RecorderState = "idle" | "requesting" | "recording" | "error";

export function useRecorder() {
  const [state, setState] = useState<RecorderState>("idle");
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { if (state === "requesting" || state === "recording") return suppressEffects(); }, [state]);
  const mediaRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const generationRef = useRef(0);
  const mountedRef = useRef(true);
  const stopResolverRef = useRef<((url: string | null) => void) | null>(null);
  const stopPromiseRef = useRef<Promise<string | null> | null>(null);

  const cleanup = useCallback(() => {
    generationRef.current++;
    const mr = mediaRef.current;
    mediaRef.current = null;
    if (mr) {
      mr.ondataavailable = null;
      mr.onstop = null;
      try { if (mr.state !== "inactive") mr.stop(); }
      catch { /* 即使设备已失效，也必须继续释放 tracks 并结束等待。 */ }
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(t => t.stop());
      streamRef.current = null;
    }
    chunksRef.current = [];
    const resolver = stopResolverRef.current;
    stopResolverRef.current = null;
    stopPromiseRef.current = null;
    resolver?.(null);
  }, []);

  useEffect(() => {
    mountedRef.current = true;
    return () => { mountedRef.current = false; cleanup(); };
  }, [cleanup]);

  const start = useCallback(async () => {
    if (!mountedRef.current) return false;
    setError(null);
    if (mediaRef.current) return mediaRef.current.state === "recording";
    const generation = ++generationRef.current;
    if (typeof navigator === "undefined" || !navigator.mediaDevices?.getUserMedia) {
      setState("error");
      setError("当前浏览器不支持录音");
      return false;
    }
    setState("requesting");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      if (generation !== generationRef.current) {
        stream.getTracks().forEach(track => track.stop());
        return false;
      }
      streamRef.current = stream;
      const mr = new MediaRecorder(stream);
      chunksRef.current = [];
      mr.ondataavailable = e => {
        if (generation === generationRef.current && e.data && e.data.size > 0)
          chunksRef.current.push(e.data);
      };
      mr.onstop = () => {
        if (generation !== generationRef.current) return;
        const resolver = stopResolverRef.current;
        stopResolverRef.current = null;
        const blob = new Blob(chunksRef.current, {
          type: mr.mimeType || "audio/webm",
        });
        const url = resolver && mountedRef.current && blob.size > 0 ? URL.createObjectURL(blob) : null;
        cleanup();
        if (mountedRef.current) setState("idle");
        resolver?.(url);
      };
      mr.start();
      mediaRef.current = mr;
      setState("recording");
      return true;
    } catch (e) {
      // A cancelled permission prompt may reject after a new recording has started.
      if (generation !== generationRef.current) return false;
      setState("error");
      setError(e instanceof Error ? e.message : String(e));
      cleanup();
      return false;
    }
  }, [cleanup]);

  const stop = useCallback((): Promise<string | null> => {
    if (stopPromiseRef.current) return stopPromiseRef.current;
    const mr = mediaRef.current;
    if (!mr || mr.state === "inactive") {
      cleanup();
      if (mountedRef.current) setState("idle");
      return Promise.resolve(null);
    }
    const pending = new Promise<string | null>(resolve => { stopResolverRef.current = resolve; });
    stopPromiseRef.current = pending;
    try { mr.stop(); }
    catch {
      cleanup();
      if (mountedRef.current) { setState("error"); setError("录音停止失败，请重试"); }
    }
    return pending;
  }, [cleanup]);

  return { state, error, start, stop };
}
