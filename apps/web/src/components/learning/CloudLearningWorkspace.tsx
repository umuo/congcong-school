"use client";
import { useCallback, useEffect, useRef, useState, useSyncExternalStore } from "react";
import { CheckCircle2, ChevronRight, Circle, Compass } from "lucide-react";
import { useLearningClient } from "./LearningProvider";
import { CloudSessionRunner, type Source } from "./CloudSessionRunner";
import { ForestGuide } from "./ForestGuide";
import { bookLabel, unitLabel, orderBookItems } from "@/lib/learning/book-labels";
import { useCurrentBook } from "@/lib/learning/current-book";
import { nextActivity, activityTitle, type ActiveActivity, type CourseItem } from "@/lib/learning/next-activity";
import { openActivity } from "@/lib/learning/open-activity";
import Link from "next/link";
import { SubjectSwitcher } from "./SubjectSwitcher";
import { availableSubjectBook, type CurriculumSubject } from "@/lib/learning/subjects";

type Item = CourseItem;
export function CloudLearningWorkspace({ initialSource, initialBook, initialKind = "lesson" }: { initialSource?: Source; initialBook?: string; initialKind?: Item["kind"] }) {
  const client = useLearningClient();
  const [selection, setSelection] = useState<{ source?: Source; id?: string } | null>(initialSource ? { source: initialSource } : null);
  const [books, setBooks] = useState<CurriculumSubject[]>([]);
  const [curriculumReady, setCurriculumReady] = useState(false);
  const [chosenBook, chooseBook] = useCurrentBook(client.scope.studentId);
  const [book, setBook] = useState(initialBook ?? chosenBook);
  const [contentBook, setContentBook] = useState("");
  const [items, setItems] = useState<Item[]>([]);
  const [active, setActive] = useState<ActiveActivity[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [opening, setOpening] = useState(false);
  const entryGate = useRef(false);
  const lifetime = useRef(true);
  useEffect(() => { lifetime.current = true; return () => { lifetime.current = false; }; }, []);
  const [revision, setRevision] = useState(0);
  const [kind, setKind] = useState<Item["kind"]>(initialKind);
  const snapshot = useSyncExternalStore(client.projection.subscribe, client.projection.getSnapshot, client.projection.getSnapshot);
  const progress = snapshot.progress;
  const unsaved = snapshot.pending.filter(key => !snapshot.sending.includes(key));
  const blocked = snapshot.pending.some(key => client.blocksQuestion(key));
  const locked = opening || blocked;
  const explore = initialKind === "story" || initialKind === "reading";
  const retry = useCallback(() => { setError(""); setRevision(n => n + 1); }, []);
  useEffect(() => {
    const id = new URLSearchParams(window.location.search).get("session");
    if (id) setSelection({ id });
    let mounted = true; setCurriculumReady(false);
    void Promise.all([client.getCurriculum<{ subjects: typeof books }>(), client.getProgress()]).then(([value]) => {
      if (mounted) { setBooks(value.subjects); const requested = initialBook || new URLSearchParams(window.location.search).get("book") || chosenBook; setBook(current => availableSubjectBook(value.subjects,current,requested)); setCurriculumReady(true); setLoading(false); }
    }).catch(e => { if (mounted) { setError(e.message); setLoading(false); } });
    return () => { mounted = false; };
  }, [client, initialBook, revision]);
  useEffect(() => {
    setItems([]); setActive([]);
    if (!book) return;
    let mounted = true; setLoading(true); setError("");
    void Promise.all([client.getBookContent<Item[]>(book), Promise.all([client.getActiveSessions({ book_id: book }), client.getActiveSessions({ book_id: book, for_hearts: true })])]).then(([content, sessionGroups]) => {
      if (mounted) { setItems(orderBookItems(book,content)); setActive(sessionGroups.flat().sort((a,b) => b.created_at.localeCompare(a.created_at))); setContentBook(book); setLoading(false); }
    }).catch(e => { if (mounted) { setError(e.message); setLoading(false); } });
    return () => { mounted = false; };
  }, [book, client, revision]);
  useEffect(() => { if (curriculumReady) chooseBook(book); }, [book,chooseBook,curriculumReady]);
  const waiting = loading || Boolean(book && contentBook !== book && !error);
  if (selection) return <CloudSessionRunner key={selection.id ?? JSON.stringify(selection.source)} source={selection.source} resumeId={selection.id} exitLabel={explore ? "返回探索" : "返回学习首页"} onExit={() => {
    const viewedBook = selection.id ? snapshot.sessions[selection.id]?.book_id : selection.source?.book_id;
    if (viewedBook) setBook(viewedBook);
    setSelection(null); const returnBook=viewedBook || book; window.history.replaceState(null, "", `${explore ? "/explore/" : "/learn/"}${returnBook ? `?book=${encodeURIComponent(returnBook)}` : ""}`); retry();
  }} />;
  const next = nextActivity(book, items, progress?.state.completedLessons ?? {}, active);
  async function open(source: Source) {
    if (entryGate.current || blocked) return;
    entryGate.current = true; setOpening(true); setError("");
    try {
      const session = await openActivity(client, source);
      if (lifetime.current) setSelection({ id: session.id });
    } catch (e) { if (lifetime.current) setError(e instanceof Error ? e.message : "课程还没准备好，请再试一次。"); }
    finally { entryGate.current = false; if (lifetime.current) setOpening(false); }
  }
  const enter = (item: Item, followup = false) => void open({ kind: item.kind, book_id: book, source_id: item.source_id, ...(item.kind === "reading" ? { reading_kind: followup ? "followup" as const : "listen" as const } : {}) });
  function continueLearning() {
    if (next.type === "resume") setSelection({ id: next.id });
    else if (next.type === "lesson") enter(next.item);
    else void open({ kind: "review", book_id: book });
  }
  const visibleItems = !waiting && contentBook === book ? items : [];
  const selectedItems = visibleItems.filter(item => item.kind === kind);
  const units = [...new Set(selectedItems.map(item => item.unit_number))];
  const lessonItems = visibleItems.filter(item => item.kind === "lesson");
  const nextIndex = next.type === "review" ? 0 : lessonItems.findIndex(item => item.source_id === next.item?.source_id);
  const previews = lessonItems.slice(Math.max(0,nextIndex-1),Math.max(0,nextIndex-1)+3);
  const label = bookLabel(book,books.find(b=>b.book_id===book)?.subject_code);
  const shortLabel = label.split("（")[0];
  const edition = label.match(/（(.+)）/)?.[1];
  const routeRow = (item:Item,index:number,preview=false) => {
    const completed = Boolean(progress?.state.completedLessons[item.source_id]);
    const current = next.type !== "review" && next.item?.source_id === item.source_id;
    const read = Boolean(((progress?.state.completedReadings ?? {}) as Record<string,string>)[`reading:${item.kind === "story" ? "story" : "listen"}:${item.source_id}`]);
    return <li key={item.source_id} data-current={current} className={preview ? "forest-preview-row" : undefined}><span aria-hidden>{completed || read ? <CheckCircle2 size={21}/> : <Circle size={21}/>}</span>{preview ? <img src={["/forest/route-ducks.webp","/forest/lesson-friends.webp","/forest/route-apples.webp"][index%3]} alt="" width="210" height="126" loading="lazy"/> : null}<div className="forest-course-copy"><strong>{item.title}</strong><small>{current ? (next.type === "resume" ? (completed ? "正在温习 · 已完成" : "正在学习") : "下一站") : completed ? "已完成" : read ? "已读" : "可以学习"}{preview ? "" : ` · ${item.kind === "reading" ? "听读与跟读" : `${item.question_count} 题`}`}</small></div><button className="secondary" disabled={locked || waiting || !book} onClick={()=>enter(item)} aria-label={`${item.kind === "reading" ? "听读" : "学习"}：${item.title}`}>{preview ? <ChevronRight size={18} aria-hidden/> : item.kind === "reading" ? "听读" : "学习"}</button>{item.kind === "reading" ? <button className="secondary" disabled={locked || waiting || !book} onClick={()=>enter(item,true)}>跟读</button> : null}</li>;
  };
  const primary = next.type === "resume" ? "继续学习" : next.type === "lesson" ? "开始学习" : "温习学过的本领";
  return <section>
    <SubjectSwitcher subjects={books} book={book} ready={curriculumReady} disabled={opening} onSelect={nextBook => {
      setBook(nextBook); chooseBook(nextBook);
      window.history.replaceState(null,"",`${window.location.pathname}?book=${encodeURIComponent(nextBook)}`);
    }}/>
    <div className="forest-welcome"><div><h1><span>{explore ? "去发现，" : "今天，"}</span><br/>{explore ? "更多有趣的世界" : "一起学点新本领"}</h1><p>跟着熊猫伙伴，每天进步一点点。</p></div><ForestGuide /></div>
    <div className="forest-home-grid">
      <section className="forest-mission" aria-label={explore ? "探索入口" : "今日学习任务"}>
        <div className="forest-book-heading"><img className="forest-book-cover" src="/forest/forest-book.webp" alt="" width="192" height="258"/><h2>{book ? shortLabel : "你的学习旅程"}</h2></div>
        {waiting ? <p role="status">正在找下一站…</p> : error ? <><p role="alert">这次没能准备好课程。{error}</p><button onClick={retry}>再试一次</button></> : !book ? <p>请家长先帮你配置学科，再回来一起学习吧。</p> : blocked && !opening ? <><p role="status">上一段进度还没保存好，先接着它继续吧。</p><button disabled={!unsaved.length} onClick={async () => { try { await client.retry(unsaved[0]); retry(); } catch(e) { setError(e instanceof Error ? e.message : "还没有保存，请重试"); } }}>{unsaved.length ? "重新保存" : "正在保存进度…"}</button></> : explore ? <><h3>{selectedItems.length ? "故事、听读和你的声音" : kind === "story" ? "这里暂时没有故事" : "这里暂时没有听读材料"}</h3>{selectedItems.length ? <><img src="/forest/lesson-friends.webp" alt="" width="2172" height="724" /><p>选择下方材料，读一读、听一听。</p></> : <><p>先去课程里学点新本领吧。</p><Link className="forest-empty-action" href={`/learn/?book=${encodeURIComponent(book)}`}>返回课程学习 <ChevronRight size={17} aria-hidden/></Link></>}</> : <>
          <small>{edition ? `${edition} · ` : ""}{next.type !== "review" && next.item?.unit_number ? `${unitLabel(book,next.item.unit_number).split(" · ")[0]} · ` : ""}{next.type === "resume" ? "接着上次的进度" : "按自己的节奏，勇敢试一试"}</small>
          <h3>{next.type === "review" ? "把学过的本领记得更牢" : next.item?.title ?? activityTitle(next.type === "resume" ? active.find(activity=>activity.id===next.id)?.kind : undefined)}</h3>
          <img src="/forest/lesson-friends.webp" alt="" width="2172" height="724" />
          <button className="forest-primary" disabled={opening} onClick={continueLearning}>{opening ? "正在准备课程…" : primary} <ChevronRight size={20} aria-hidden style={{display:"inline"}} /></button>
        </>}
      </section>
      <section aria-label={explore ? "探索材料" : "单元路线"}>
        <div className="forest-section-title"><h2>{explore ? <><Compass size={22} style={{display:"inline"}} aria-hidden /> 探索世界</> : "我的竹林路线"}</h2><a href={explore ? "#forest-subjects" : "#forest-all-units"}>{explore ? "切换学科" : "查看单元"}</a></div>
        {!explore && !waiting && !error ? <ol className="forest-route forest-preview">{previews.map((item,index)=>routeRow(item,index,true))}</ol> : null}
        <details id="forest-all-units" open={explore ? true : undefined}><summary>{explore ? "阅读材料" : "全部课程与单元"}</summary>
        <nav className="account-tabs" aria-label="学习方式">{(explore ? [["story", "故事"], ["reading", "听读与跟读"]] as const : [["lesson", "课程"], ["challenge", "单元挑战"]] as const).map(([key, text]) => <button key={key} className="secondary" aria-pressed={kind === key} onClick={() => setKind(key)}>{text}</button>)}</nav>
        {!explore && !waiting && !error && book && !selectedItems.length ? <section className="forest-empty-materials"><Compass size={34} aria-hidden/><h3>{explore ? (kind === "story" ? "这里暂时没有故事" : "这里暂时没有听读材料") : "这里暂时没有这类练习"}</h3><p>{explore ? "先去课程里学点新本领吧。" : "可以试试其他练习方式。"}</p>{explore ? <Link className="forest-empty-action" href={`/learn/?book=${encodeURIComponent(book)}`}>返回课程学习 <ChevronRight size={17} aria-hidden/></Link> : null}</section> : null}
        {units.map(unit => <section key={String(unit)}><h3 className="forest-unit">{unitLabel(book,unit)}</h3><ol className="forest-route">{selectedItems.filter(item => item.unit_number === unit).map((item,index)=>routeRow(item,index))}</ol></section>)}
        </details>
      </section>
    </div>
    {!explore ? <details className="forest-tools" id="forest-tools"><summary>更多练习</summary>
      <div className="account-actions"><button className="secondary" disabled={locked || waiting || !book} onClick={() => void open({ kind: "review", book_id: book })}>错题复习</button><button className="secondary" disabled={locked || waiting || !book} onClick={() => void open({ kind: "review", ...(book ? { book_id: book } : {}), for_hearts: true })}>回心补练</button><Link href="/explore/">故事与听读</Link></div>
      {book ? <label>跳级目标单元<select aria-label="跳级目标单元" value="" disabled={locked || waiting} onChange={e => { if(e.target.value) void open({ kind: "jump", book_id: book, target_unit: Number(e.target.value) }); }}><option value="">选择目标单元</option>{[...new Set(visibleItems.map(item => item.unit_number))].filter((n): n is number => n !== null && n >=2 && n < 100).sort((a,b)=>a-b).map(n => <option key={n} value={n}>{unitLabel(book,n)}</option>)}</select></label> : null}
      <div className="account-actions">{(["count","compare","apply"] as const).map((skill,index)=><button className="secondary" key={skill} disabled={locked || waiting || !book} onClick={()=>void open({kind:"number_review",number_skill:skill})}>{["数一数","比一比","用一用"][index]} · 隔天检验</button>)}</div>
    </details> : null}
    {!blocked && unsaved.length ? <aside className="forest-save-status"><p>还有一小段进度没保存，不影响继续练习。</p><button className="secondary" onClick={() => void client.retry(unsaved[0]).catch(e => setError(e.message))}>重新保存</button></aside> : null}
  </section>;
}
