"use client";
import { useCallback, useEffect, useRef, useState, useSyncExternalStore } from "react";
import { useLearningClient, LearningSyncStatus } from "./LearningProvider";
import type { StartLearning } from "@/lib/learning/client";
import type { LearningSessionView } from "@/lib/api/learning-contract";
import type { Question } from "@/types";
import { QuestionRenderer } from "@/components/question/QuestionRenderer";
import { MathText } from "@/components/MathText";
import { TTSButton } from "@/components/TTSButton";
import { APIError } from "@/lib/api/client";
import { playSfx } from "@/lib/sfx";
import { CloudReading } from "./CloudReading";
import { StoryEvidencePanel } from "@/components/StoryEvidencePanel";
import { playTTS, stopTTS } from "@/lib/tts";
import { sessionMedia } from "@/lib/learning/media";
import { addCloudReport, type CloudQuestionReport } from "@/lib/learning/reports";
import { getCosmeticById, type LessonBackdrop } from "@/lib/cosmetics";

import { answerDraftKey, readAnswerDraft, writeAnswerDraft, type AnswerDraft } from "@/lib/learning/answer-draft";

export type Source = Omit<StartLearning, "client_at">;
type Metadata = {
  title?: string;
  knowledge?: { point?: string; core_concept?: string; key_formula?: string; common_mistakes?: string[]; tips?: string; audio?: Record<string, string | string[]> };
  sentences?: { text: string; audio?: string }[];
  image?: string;
  pageImages?: string[];
};
type Settlement = { session_id: string; xp_gained: number; gems_gained: number; correct: number; total: number; accuracy: number; chest?: { gems: number; tier: string }; hearts_gained?: number; first_perfect?: boolean };

export function CloudSessionRunner({ source, resumeId, onExit, exitLabel = "返回学习首页" }: { source?: Source; resumeId?: string; onExit: () => void; exitLabel?: string }) {
  const client = useLearningClient();
  const [sessionId, setSessionId] = useState(resumeId ?? "");
  const [metadata, setMetadata] = useState<Metadata[]>([]);
  const [contentState, setContentState] = useState<"loading" | "ready" | "error">("loading");
  const [contentRevision, reloadContent] = useState(0);
  const [answer, setAnswer] = useState("");
  const [visualDraft, setVisualDraft] = useState<number[]>([]);
  const [evidence, setEvidence] = useState<number[]>([]);
  const inputDraft = useRef<AnswerDraft>({ answer: "", visual: [], evidence: [] });
  const draftStorage = () => { try { return window.sessionStorage; } catch { return undefined; } };
  const [result, setResult] = useState<Settlement | null>(null);
  const [error, setError] = useState("");
  const [reportNotice, setReportNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const gate = useRef(false);
  const questionStartedAt = useRef(Date.now());
  const flushTime = useRef<() => void>(() => {});
  const alive = useRef(true);
  useEffect(() => () => stopTTS(), []);
  const snapshot = useSyncExternalStore(client.projection.subscribe, client.projection.getSnapshot, client.projection.getSnapshot);
  const session = snapshot.sessions[sessionId];
  const sourceKey = JSON.stringify(source);
  const attach = useCallback((next: LearningSessionView) => {
    if (!alive.current) return;
    setSessionId(next.id);
    window.history.replaceState(null, "", `/learn/?session=${encodeURIComponent(next.id)}`);
  }, []);
  useEffect(() => {
    alive.current = true;
    void (async () => {
      try {
        if (resumeId) attach(await client.getSession(resumeId));
        else if (source) {
          const active = await client.getActiveSessions(source);
          if (active[0]) attach(await client.getSession(active[0].id));
        }
      } catch (e) { if (alive.current) setError(e instanceof Error ? e.message : "无法恢复学习"); }
      finally { if (alive.current) setLoading(false); }
    })();
    return () => { alive.current = false; };
  }, [client, resumeId, sourceKey, attach]);
  useEffect(() => {
    if (!sessionId) return;
    let mounted = true;
    setContentState("loading"); setMetadata([]);
    void client.getSessionContent<Metadata[]>(sessionId).then((value) => { if (mounted) { setMetadata(value); setContentState("ready"); } })
      .catch((e) => { if (mounted) { setError(e.message); setContentState("error"); } });
    return () => { mounted = false; };
  }, [client, sessionId, contentRevision]);
  useEffect(() => {
    if (!session) return;
    if (session.settlement) setResult(session.settlement as Settlement);
    const key = answerDraftKey(client.scope, sessionId);
    const restored = session.feedback ? null : readAnswerDraft(draftStorage(), key, `${session.question?.uid}:${session.question?.version}`, session.revision);
    const draft = restored ?? { answer: session.feedback?.submitted_answer ?? session.checkpoint.draft.answer ?? "", visual: session.checkpoint.draft.visual_draft ?? [], evidence: session.checkpoint.draft.evidence_sentence_indices ?? [] };
    inputDraft.current = draft;
    setAnswer(draft.answer); setVisualDraft(draft.visual); setEvidence(draft.evidence);
    if (session.feedback) { try { draftStorage()?.removeItem(key); } catch {} }
  }, [session?.revision, sessionId]);
  // 前台时间分段申报；服务端去重并按区间并集汇总，不能代表实际专注度。
  useEffect(() => {
    if (!sessionId || result) return;
    const activity = crypto.randomUUID();
    let started = Date.now(), sequence = 0, visible = document.visibilityState === "visible";
    const flush = () => {
      const ended = Date.now();
      if (visible && ended - started >= 1000 && ended - started <= 1800000) {
        try {
        const key = client.prepare(`/students/${client.scope.studentId}/events`, {
          kind: "time_checkpoint", session_id: sessionId, activity_id: activity,
          sequence: ++sequence, client_at: new Date(ended).toISOString(),
          started_at: new Date(started).toISOString(), ended_at: new Date(ended).toISOString(),
        });
        void client.retry(key).catch(() => {}); // 留在未同步列表，原键重试。
        } catch { /* 上下文已撤销时不能创建新操作。 */ }
      }
      started = ended;
    };
    flushTime.current = flush;
    const timer = window.setInterval(flush, 20000);
    const visibility = () => { flush(); visible = document.visibilityState === "visible"; };
    document.addEventListener("visibilitychange", visibility);
    window.addEventListener("pagehide", flush);
    return () => { flush(); flushTime.current = () => {}; window.clearInterval(timer); document.removeEventListener("visibilitychange", visibility); window.removeEventListener("pagehide", flush); };
  }, [client, sessionId, result]);
  async function run<T>(operation: () => Promise<T>) {
    if (gate.current) throw new Error("请等待当前操作确认");
    gate.current = true; setBusy(true); setError("");
    try { return await operation(); }
    catch (e) {
      if (alive.current) {
        setError(e instanceof Error ? e.message : "尚未同步，请重试");
        if (e instanceof APIError && e.code === "LEARNING_REVISION_CONFLICT" && sessionId)
          await client.getSession(sessionId);
      }
      throw e;
    } finally { gate.current = false; if (alive.current) setBusy(false); }
  }
  async function saveDraft(nextAnswer = answer, nextVisual = visualDraft, page = session?.checkpoint.draft.intro_page ?? 0) {
    if (!session || session.feedback) return false;
    try { await run(() => client.updateSession(sessionId, "checkpoint", { revision: session.revision, client_at: new Date().toISOString(), answer: nextAnswer, visual_draft: nextVisual, intro_page: page, evidence_sentence_indices: evidence })); return true; } catch { return false; }
  }
  const pending = snapshot.pending.some((key) => client.blocksQuestion(key));
  const unsaved = snapshot.pending.filter(key => !snapshot.sending.includes(key));
  const locked = busy || pending;
  const knowledge = metadata[0]?.knowledge;
  const cards = knowledge ? [
    { title: knowledge.point, text: knowledge.core_concept, audio: knowledge.audio?.core_concept },
    { title: "关键方法", text: knowledge.key_formula, audio: knowledge.audio?.key_formula },
    { title: "容易出错的地方", text: knowledge.common_mistakes?.join("\n"), audio: knowledge.audio?.common_mistakes },
    { title: "小提示", text: knowledge.tips, audio: knowledge.audio?.tips },
  ].filter((card) => card.text) : [];
  const introPage = session?.checkpoint.draft.intro_page ?? 0;
  const intro = session?.kind === "lesson" && !session.checkpoint.attempt_count && introPage < cards.length;
  const q = session?.question;
  const question: Question | null = q ? {
    ...q, difficulty: q.difficulty as Question["difficulty"],
    numberTask: q.numberTask as Question["numberTask"],
    answer: session?.feedback?.answer ?? "", explanation: session?.feedback?.explanation ?? "",
    audio: { question: sessionMedia(sessionId, q.audio?.question), options: q.audio?.options?.map((src) => sessionMedia(sessionId, src) ?? null), explanation: sessionMedia(sessionId, session?.feedback?.explanation_audio) },
  } : null;
  const total = session ? new Set([...session.checkpoint.pending, ...session.checkpoint.attempted]).size : 0;
  const storyReading = session?.kind === "story" && !session.checkpoint.attempt_count && introPage === 0;
  useEffect(() => {
    if (!session?.feedback && !intro && !storyReading) questionStartedAt.current = Date.now();
  }, [q?.uid, Boolean(session?.feedback), intro, storyReading]);
  const complete = async () => {
    flushTime.current();
    await run(async () => {
      const confirmed = await client.complete<Settlement>(sessionId, { revision: session!.revision, client_at: new Date().toISOString() });
      setResult(confirmed); await client.getProgress(); playSfx("complete");
    }).catch(() => {});
  };
  function updateDraft(patch: Partial<AnswerDraft>) {
    if (!session || session.feedback) return;
    const draft = { ...inputDraft.current, ...patch };
    inputDraft.current = draft;
    setAnswer(draft.answer); setVisualDraft(draft.visual); setEvidence(draft.evidence);
    writeAnswerDraft(draftStorage(), answerDraftKey(client.scope, sessionId), `${q?.uid}:${q?.version}`, session.revision, draft);
  }
  async function leave() {
    if (locked) return;
    const dirty = session && !session.feedback && (answer !== (session.checkpoint.draft.answer ?? "") || JSON.stringify(visualDraft) !== JSON.stringify(session.checkpoint.draft.visual_draft ?? []) || JSON.stringify(evidence) !== JSON.stringify(session.checkpoint.draft.evidence_sentence_indices ?? []));
    if (dirty && !await saveDraft()) return;
    onExit();
  }
  const backdrop = getCosmeticById(String(snapshot.progress?.state.equippedBackdrop ?? "backdrop_default")) as LessonBackdrop | undefined;
  return <section className="account-card cloud-runner" style={backdrop?.type === "lesson_backdrop" && backdrop.id !== "backdrop_default" ? { background: `linear-gradient(var(--lesson-backdrop-overlay, #ffffffbb), var(--lesson-backdrop-overlay, #ffffffbb)), ${backdrop.data.background}` } : undefined}>
    <div className="forest-runner-toolbar"><button className="secondary" disabled={locked} onClick={()=>void leave()}>{exitLabel}</button><span>{intro ? "学前小提示" : session ? "一步一步，慢慢来" : "准备出发"}</span></div>
    <h1>{session?.kind === "number_review" ? "数感隔天检验" : metadata[0]?.title ?? (session?.kind === "review" || source?.kind === "review" ? "错题复习" : session?.kind === "jump" ? "跳级挑战" : "继续学习")}</h1>
    {error ? <p role="alert" className="account-message">{error}</p> : null}
    <LearningSyncStatus />
    {unsaved.length && !busy ? <div className="account-actions">{unsaved.map((key) => <button key={key} disabled={busy} onClick={() => void run(async () => {
      const value = await client.retry<LearningSessionView | Settlement | { session: LearningSessionView }>(key);
      if ("student_id" in value && "id" in value && "question" in value) attach(value);
      else if ("session" in value) attach(value.session);
      else if ("xp_gained" in value) setResult(value);
    }).catch(() => {})}>重新保存</button>)}</div> : null}
    {loading || (session && contentState === "loading") ? <p role="status">正在准备课程，马上就好…</p> : session && contentState === "error" ? <button onClick={() => { setError(""); reloadContent(n => n + 1); }}>重新读取课程</button> : !session ? <button disabled={locked || !source} onClick={() => void run(async () => attach(await client.start({ ...source!, client_at: new Date().toISOString() }))).catch(() => {})}>{busy ? "正在准备课程…" : "开始学习"}</button> : result ? <section role="status">
      <h2>学习已同步！</h2><p>{session.kind === "reading" ? "阅读完成" : `首答正确 ${result.correct}/${result.total}`} · +{result.xp_gained} XP · +{result.gems_gained} 宝石</p>{result.first_perfect ? <p>首次完美通关！</p> : null}{result.chest ? <p>🎁 宝箱：{result.chest.tier} · {result.chest.gems} 宝石，已包含在本次结算中。</p> : null}{result.hearts_gained ? <p>恢复 {result.hearts_gained} 颗红心。</p> : null}<button onClick={onExit}>完成</button>
    </section> : session.kind === "reading" ? <CloudReading sessionId={sessionId} kind={session.checkpoint.reading_kind ?? "listen"} sentences={metadata[0]?.sentences ?? []} pageImages={metadata[0]?.pageImages} locked={locked} onComplete={complete} /> : storyReading ? <section>
      {metadata[0]?.image ? <img src={sessionMedia(sessionId, metadata[0].image)} alt="故事配图" style={{ maxWidth: "100%", maxHeight: 320 }} /> : null}
      {(metadata[0]?.sentences ?? []).map((sentence, i) => <p key={i}>{sentence.text}<TTSButton src={sessionMedia(sessionId, sentence.audio)} /></p>)}
      <button disabled={locked} onClick={() => void saveDraft("", [], 1)}>开始理解练习</button>
    </section> : intro ? <section>
      <h2>先学一招</h2><MathText text={cards[0]?.text ?? ""} />
      {(Array.isArray(cards[0]?.audio) ? cards[0].audio as string[] : [cards[0]?.audio as string]).filter(Boolean).map((src, i) => <TTSButton key={i} src={sessionMedia(sessionId, src)} />)}
      {cards.length > 1 ? <details className="forest-lesson-tips"><summary>再看看小提示</summary>{cards.slice(1).map((card,i)=><section key={i}><h3>{card.title}</h3><MathText text={card.text ?? ""}/>{(Array.isArray(card.audio) ? card.audio : [card.audio]).filter((src): src is string=>Boolean(src)).map((src,j)=><TTSButton key={j} src={sessionMedia(sessionId,src)}/>)}</section>)}</details> : null}
      <button className="forest-primary" disabled={locked} onClick={() => void saveDraft("", [], cards.length)}>{busy ? "正在准备练习…" : "开始练习"}</button>
    </section> : question ? <section>
      {session.kind === "story" && metadata[0] ? <StoryEvidencePanel story={{ title: metadata[0].title ?? "故事", sentences: metadata[0].sentences ?? [] }} selected={session.feedback?.submitted_evidence_indices ?? evidence} reference={session.feedback?.evidence_sentence_indices ?? []} checked={!!session.feedback || locked} playing={null} onSelect={(sentence) => updateDraft({evidence:evidence.includes(sentence) ? evidence.filter(n=>n!==sentence) : [...evidence,sentence]})} onPlay={(index) => void playTTS(sessionMedia(sessionId, metadata[0]?.sentences?.[index]?.audio))} /> : null}
      <p>已完成 {session.checkpoint.solved.length}/{total} 题{session.checkpoint.attempt_count > total ? " · 错题再练" : ""}</p>
      <div className="forest-question"><QuestionRenderer key={`${q!.uid}:${q!.version}`} question={question} answer={answer} phase={session.feedback ? "checked" : "answering"} isCorrect={session.feedback?.correct ?? null} locked={locked}
        inputKeyboard={q!.input_keyboard ?? undefined} visualDraft={visualDraft} onVisualDraft={visual=>updateDraft({visual})}
        onChange={answer=>updateDraft({answer})} hintLevel={session.checkpoint.hint_levels[String(session.checkpoint.pending[0])] ?? 0} hintLimit={q!.numberTask ? Number(q!.numberTask.hint_count ?? 2) : undefined}
        onHint={question.numberTask && session.kind !== "number_review" ? () => void run(async () => {
          const saved = await client.updateSession(sessionId, "checkpoint", { revision: session.revision, client_at: new Date().toISOString(), answer, visual_draft: visualDraft, intro_page: introPage, evidence_sentence_indices: evidence });
          return client.updateSession(sessionId, "hint", { revision: saved.revision, client_at: new Date().toISOString() });
        }).catch(() => {}) : undefined}
        remoteMatching={question.type === "matching" ? { pairs: session.checkpoint.matching_pairs ?? {}, checkPair: (left, right) => run(async () => {
          const key = client.prepare(`/learning-sessions/${sessionId}/matching-pairs`, { revision: session.revision, client_at: new Date().toISOString(), question_uid: q!.uid, question_version: q!.version, left, right });
          const value = await client.retry<{ correct: boolean; session: LearningSessionView }>(key);
          return value.correct;
        }) } : undefined} /></div>
      {session.feedback ? <div className={session.feedback.correct ? "bg-primary/10 rounded-2xl p-5 mt-6" : "bg-danger/10 rounded-2xl p-5 mt-6"} role="status">
        <h2>{session.feedback.correct ? "答对了！" : "再想想，稍后会再练一次"}</h2><MathText text={session.feedback.explanation} /><TTSButton src={sessionMedia(sessionId, session.feedback.explanation_audio)} />
        <details><summary>报告这道题的问题</summary><p>先把问题记下来，稍后请家长在小屋里查看。本次记录不会上传，退出前可以导出保存。</p>{([["question_wrong", "题目有误"], ["answer_should_count", "我的答案应该算对"], ["audio_issue", "音频有问题"]] as const).map(([kind, label]) => <button className="secondary" key={kind} onClick={() => {
          try {
            addCloudReport(client.scope, { question_uid: q!.uid, question_version: q!.version, source_id: session.source_id, question_text: q!.question, answer_given: session.feedback?.submitted_answer ?? answer, kind: kind as CloudQuestionReport["kind"] });
            setReportNotice("问题已保存在当前学生的本地问题记录中。");
          } catch { setError("本地记录保存失败，请检查浏览器存储权限。"); }
        }}>{label}</button>)}{reportNotice ? <p role="status">{reportNotice}</p> : null}</details>
        <button disabled={locked} onClick={() => void run(() => client.updateSession(sessionId, "advance", { revision: session.revision, client_at: new Date().toISOString() })).catch(() => {})}>继续</button>
      </div> : <div className="account-actions mt-6">
        <small className="forest-save-status">草稿留在本机，检查后同步</small>
        <button disabled={locked || !answer.trim() || (question.type === "matching" && Object.keys(session.checkpoint.matching_pairs ?? {}).length < Math.min(4, question.options.length / 2))} onClick={() => void run(async () => {
          const next = await client.updateSession(sessionId, "attempts", { revision: session.revision, client_at: new Date().toISOString(), question_uid: q!.uid, question_version: q!.version, answer, evidence_sentence_indices: evidence, declared_duration_ms: Math.min(3600000, Math.max(0, Date.now() - questionStartedAt.current)) });
          playSfx(next.feedback?.correct ? "correct" : "wrong");
        }).catch(() => {})}>检查答案</button>
      </div>}
    </section> : <button disabled={locked} onClick={() => void complete()}>确认完成并同步奖励</button>}
  </section>;
}
