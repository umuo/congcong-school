"use client";
import { useEffect, useRef, useState } from "react";
import { listenToPassage, followPassage, recordingForSession } from "@/lib/readingSession";
import { suppressEffects } from "@/lib/sfx";
import { playTTSResult, stopTTS } from "@/lib/tts";
import { useRecorder } from "@/lib/useRecorder";
import { TTSButton } from "@/components/TTSButton";
import { sessionMedia } from "@/lib/learning/media";

export function CloudReading({ sessionId, kind, sentences, pageImages = [], locked, onComplete }: {
  sessionId: string; kind: "listen" | "followup"; sentences: { text: string; audio?: string }[];
  pageImages?: string[]; locked: boolean; onComplete: () => Promise<void>;
}) {
  const recorder = useRecorder();
  const stopRecording = recorder.stop;
  const [playing, setPlaying] = useState(false);
  useEffect(() => { if (playing) return suppressEffects(); }, [playing]);
  const [index, setIndex] = useState<number | null>(null);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState("");
  const [recordings, setRecordings] = useState<Record<number, string>>({});
  const urls = useRef<string[]>([]);
  const generation = useRef(0);
  const gate = useRef(false);
  useEffect(() => () => {
    generation.current++; stopTTS(); void stopRecording().then((url) => { if (url) URL.revokeObjectURL(url); });
    for (const url of urls.current) URL.revokeObjectURL(url);
    urls.current = [];
  }, [sessionId, stopRecording]);
  async function begin() {
    if (gate.current) return;
    gate.current = true;
    const run = ++generation.current;
    for (const url of urls.current) URL.revokeObjectURL(url);
    urls.current = []; setRecordings({});
    setPlaying(true); setReady(false); setError("");
    const recording = recordingForSession(recorder, () => generation.current === run);
    const io = {
      play: playTTSResult, cancelled: () => generation.current !== run,
      onSentence: setIndex, wait: (ms: number) => new Promise<void>((resolve) => window.setTimeout(resolve, ms)),
      startRecording: recording.start, stopRecording: recording.stop,
      onRecording: (i: number, url: string) => {
        urls.current.push(url);
        setRecordings((previous) => ({ ...previous, [i]: url }));
      },
    };
    try {
      const source = sentences.map((sentence) => ({ ...sentence, audio: sessionMedia(sessionId, sentence.audio) }));
      const result = kind === "followup" ? await followPassage(source, io) : await listenToPassage(source, io);
      if (generation.current !== run) return;
      setReady(result === "completed");
      if (result !== "completed" && result !== "cancelled") setError(result === "recording-unavailable" ? "录音没有完成，请检查麦克风权限后重试。本次未记录完成。" : "声音未能完整播放，请检查声音及资源后重试。本次未记录完成。");
    } finally {
      gate.current = false;
      if (generation.current === run) { setPlaying(false); setIndex(null); }
    }
  }
  return <section>
    <p>{kind === "followup" ? "逐句播放原音后，轮到你录音。录音只在当前页面保存，不上传，刷新后清除。" : "完整听完每一句，再确认同步阅读完成。"}</p>
    {error || recorder.error ? <p role="alert">{error || recorder.error}</p> : null}
    {pageImages.length ? <details><summary>课本原页</summary>{pageImages.map((src) => <img key={src} src={sessionMedia(sessionId, src)} alt="课本原页" style={{ maxWidth: "100%" }} />)}</details> : null}
    <ol>{sentences.map((sentence, i) => <li key={i} style={{ padding: 12, background: index === i ? "#dff3fe" : undefined }}>
      {sentence.text}<TTSButton src={sessionMedia(sessionId, sentence.audio)} disabled={playing} />
      {recordings[i] ? <button className="secondary" disabled={playing || locked} onClick={() => void playTTSResult(recordings[i])}>听我的录音</button> : null}
    </li>)}</ol>
    <div className="account-actions">
      <button className={ready ? "secondary" : undefined} disabled={playing || locked || !sentences.length} onClick={() => void begin()}>{kind === "followup" ? "开始逐句跟读" : "开始全文听读"}</button>
      {playing ? <button className="secondary" onClick={() => { generation.current++; stopTTS(); void recorder.stop().then((url) => { if (url) URL.revokeObjectURL(url); }); setPlaying(false); setIndex(null); }}>停止</button> : null}
      <button disabled={!ready || playing || locked} onClick={() => void onComplete()}>确认阅读完成并同步</button>
    </div>
  </section>;
}
