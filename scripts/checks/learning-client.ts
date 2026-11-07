import assert from "node:assert/strict";
import { test } from "node:test";
import { CloudLearningClient, StaleLearningContext } from "../../apps/web/src/lib/learning/client";
import { APIError, type Account } from "../../apps/web/src/lib/api/client";
import { createLearningProjection, type ProgressProjection } from "../../apps/web/src/lib/learning/projection";
import { invalidateLearning, onLearningInvalidated } from "../../apps/web/src/lib/learning/lifecycle";

import { addCloudReport, cloudReports, reportKey } from "../../apps/web/src/lib/learning/reports";

const first = { context_id: "context-a", student_id: "student-a", mode: "child", must_change_password: false } as Account;
const second = { ...first, context_id: "context-b", student_id: "student-b" };
const path = `/students/${first.student_id}/economy/actions`;
const body = { kind: "daily_reward", client_at: "2026-11-01T10:00:00Z" };
function storage() {
  const data = new Map<string, string>();
  return { data, get length() { return data.size; }, key: (i: number) => [...data.keys()][i] ?? null,
    getItem: (key: string) => data.get(key) ?? null, setItem: (key: string, value: string) => { data.set(key, value); },
    removeItem: (key: string) => { data.delete(key); } };
}
function progress(student_id = first.student_id!, revision = 1, gems = 0): ProgressProjection {
  return { student_id, revision, rule_version: "test", state: { xp: 0, hearts: 5, gems, completedLessons: {} }, quests: [] };
}
type Transport = NonNullable<ConstructorParameters<typeof CloudLearningClient>[1]>;
const transport = (fn: (path: string, options?: RequestInit) => Promise<unknown>) => fn as Transport;

test("delayed transport ignoring abort cannot publish after switching students", async () => {
  let resolve!: (value: unknown) => void;
  let signal: AbortSignal | null | undefined;
  const old = new CloudLearningClient(first, transport(async (_, options) => {
    signal = options?.signal;
    return new Promise((r) => { resolve = r; });
  }));
  const request = old.getProgress();
  old.dispose();
  const next = new CloudLearningClient(second, transport(async () => progress(second.student_id!)));
  await next.getProgress();
  resolve(progress(first.student_id!, 99, 999));
  await assert.rejects(request, StaleLearningContext);
  assert.equal(signal?.aborted, true);
  assert.equal(old.projection.getSnapshot().progress, null);
  assert.equal(next.projection.getSnapshot().progress?.state.gems, 0);
});

test("lost response survives refresh and retries identical bytes/key without optimistic reward", async () => {
  const saved = storage();
  const requests: { body: BodyInit | null | undefined; key: string | null; context: string | null }[] = [];
  let fail = true;
  const send = transport(async (route, options) => {
    if (route === "/auth/session") return first;
    const headers = new Headers(options?.headers);
    requests.push({ body: options?.body, key: headers.get("Idempotency-Key"), context: headers.get("X-CSF-Learning-Context") });
    if (fail) throw new Error("response lost after commit");
    return { result: {}, progress: progress(first.student_id!, 2, 10) };
  });
  const client = new CloudLearningClient(first, send, saved);
  const key = client.prepare(path, body);
  assert.equal(client.blocksQuestion(key), true);
  await assert.rejects(client.retry(key), /response lost/);
  assert.equal(client.projection.getSnapshot().progress, null);
  assert.deepEqual(client.projection.getSnapshot().pending, [key]);
  client.dispose(false);
  const reloaded = new CloudLearningClient(first, send, saved);
  assert.deepEqual(reloaded.projection.getSnapshot().pending, [key]);
  fail = false;
  await Promise.all([reloaded.retry(key), reloaded.retry(key)]);
  assert.equal(requests.length, 2); // 同一个键并发点击只发送一次。
  assert.deepEqual(requests[0], requests[1]);
  assert.equal(requests[0].context, first.context_id);
  assert.equal(reloaded.projection.getSnapshot().progress?.state.gems, 10);
  assert.deepEqual(reloaded.projection.getSnapshot().pending, []);
  assert.equal(saved.length, 0);
});

test("time checkpoints retain retry identity without blocking question controls", async () => {
  const client = new CloudLearningClient(first, transport(async () => first));
  const key = client.prepare(`/students/${first.student_id}/events`, { kind: "time_checkpoint" });
  assert.equal(client.blocksQuestion(key), false);
  assert.deepEqual(client.projection.getSnapshot().pending, [key]);
  client.dispose();
});

test("pending request verifies Cookie identity before sending; never relabels to sibling", async () => {
  let writes = 0;
  const saved = storage();
  saved.setItem("csf-progress-v1", "original local backup");
  const client = new CloudLearningClient(first, transport(async (route) => {
    if (route === "/auth/session") return second;
    writes++;
  }), saved);
  const key = client.prepare(path, body);
  await assert.rejects(client.retry(key), StaleLearningContext);
  assert.equal(writes, 0);
  assert.equal(client.projection.getSnapshot().progress, null);
  assert.equal(saved.length, 1);
  assert.equal(saved.getItem("csf-progress-v1"), "original local backup");
  const next = new CloudLearningClient(second, transport(async () => second), saved);
  await assert.rejects(async () => next.retry(key), StaleLearningContext);
});

for (const [status, code] of [[401, "AUTH_REQUIRED"], [403, "LEARNING_MODE_REQUIRED"], [409, "STUDENT_ARCHIVED"], [409, "LEARNING_CONTEXT_CHANGED"]] as const) {
  test(`${code} clears pending and all sensitive projections`, async () => {
    const saved = storage();
    const client = new CloudLearningClient(first, transport(async (route) => {
      if (route === "/auth/session") return first;
      throw new APIError(status, code, "denied");
    }), saved);
    client.projection.progress(progress());
    const key = client.prepare(path, body);
    await assert.rejects(client.retry(key), StaleLearningContext);
    assert.equal(saved.length, 0);
    assert.deepEqual(client.projection.getSnapshot(), { progress: null, sessions: {}, pending: [], sending: [] });
  });
}

test("business conflict is surfaced and never converted into a new key or local award", async () => {
  const client = new CloudLearningClient(first, transport(async (route) => {
    if (route === "/auth/session") return first;
    throw new APIError(409, "LEARNING_REVISION_CONFLICT", "refresh");
  }));
  const key = client.prepare(path, body);
  await assert.rejects(client.retry(key), (e: APIError) => e.code === "LEARNING_REVISION_CONFLICT");
  assert.deepEqual(client.projection.getSnapshot(), { progress: null, sessions: {}, pending: [], sending: [] });
});

test("out-of-order progress reads cannot replace a newer server revision", async () => {
  const projection = createLearningProjection();
  projection.progress(progress(first.student_id!, 2, 10));
  const old = progress(first.student_id!, 1, 0);
  projection.progress(old);
  old.state.gems = 999;
  assert.equal(projection.getSnapshot().progress?.state.gems, 10);
});

test("explicit logout / shared-tab notification disposes requests and clears queue", async () => {
  const saved = storage();
  const client = new CloudLearningClient(first, transport(async () => first), saved);
  const unsubscribe = onLearningInvalidated(() => client.dispose());
  client.prepare(path, body);
  invalidateLearning();
  unsubscribe();
  assert.equal(saved.length, 0);
  await assert.rejects(client.getProgress(), StaleLearningContext);
});

test("new login for the same student removes previous login queue; restricted storage stays usable", async () => {
  const saved = storage();
  new CloudLearningClient(first, transport(async () => first), saved).prepare(path, body);
  const next = new CloudLearningClient({ ...first, context_id: "new-login" }, transport(async () => first), saved);
  assert.equal(saved.length, 0);
  assert.deepEqual(next.projection.getSnapshot().pending, []);
  const restricted = { get length() { throw new Error("denied"); }, key() { throw new Error("denied"); },
    getItem() { throw new Error("denied"); }, setItem() { throw new Error("denied"); }, removeItem() { throw new Error("denied"); } };
  const memory = new CloudLearningClient(first, transport(async () => { throw new Error("offline"); }), restricted);
  const key = memory.prepare(path, body);
  await assert.rejects(memory.retry(key), /offline/);
  assert.deepEqual(memory.projection.getSnapshot().pending, [key]);
});


test("local question reports isolate siblings and logins, reject mismatched ownership, and clear on logout", () => {
  const saved = storage();
  const original = Object.getOwnPropertyDescriptor(globalThis, "window");
  Object.defineProperty(globalThis, "window", { configurable: true, value: { sessionStorage: saved } });
  try {
    const owner = { contextId: "family-login", studentId: "child-a" };
    const sibling = { ...owner, studentId: "child-b" };
    const nextLogin = { ...owner, contextId: "next-login" };
    addCloudReport(owner, { question_uid: "q1", question_version: "v1", source_id: "lesson1", question_text: "test", answer_given: "answer", kind: "audio_issue" });
    assert.equal(cloudReports(owner).length, 1);
    assert.deepEqual(cloudReports(sibling), []);
    assert.deepEqual(cloudReports(nextLogin), []);
    saved.setItem(reportKey(sibling), saved.getItem(reportKey(owner))!);
    assert.deepEqual(cloudReports(sibling), []);
    saved.setItem("unrelated", "keep");
    invalidateLearning();
    assert.deepEqual(cloudReports(owner), []);
    assert.equal(saved.getItem("unrelated"), "keep");
  } finally {
    if (original) Object.defineProperty(globalThis, "window", original);
    else Reflect.deleteProperty(globalThis, "window");
  }
});

test("sending and retryable progress stay distinct across success and lost response", async () => {
  let release!: () => void;
  let arrived!: () => void;
  const arrival = new Promise<void>(resolve => { arrived = resolve; });
  const wait = new Promise<void>(resolve => { release = resolve; });
  const client = new CloudLearningClient(first, transport(async route => {
    if (route === '/auth/session') return first;
    arrived(); await wait;
    return {result:{applied:true},progress:progress()};
  }));
  const key=client.prepare(path,body), request=client.retry(key);
  await arrival;
  assert.deepEqual(client.projection.getSnapshot().pending,[key]);
  assert.deepEqual(client.projection.getSnapshot().sending,[key]);
  assert.equal(client.retry(key),request);
  release(); await request;
  assert.deepEqual(client.projection.getSnapshot().pending,[]);
  assert.deepEqual(client.projection.getSnapshot().sending,[]);
  const offline=new CloudLearningClient(first,transport(async route=>{
    if(route==='/auth/session')return first;
    throw Error('connection lost after possible commit');
  }));
  const saved=offline.prepare(path,body); await assert.rejects(offline.retry(saved));
  assert.deepEqual(offline.projection.getSnapshot().pending,[saved]);
  assert.deepEqual(offline.projection.getSnapshot().sending,[]);
});

test("one explicit entry opens a course, while an existing activity keeps its original ID", async () => {
  const {openActivity}=await import('../../apps/web/src/lib/learning/open-activity');
  let existing=false, writes=0;
  const confirmed={id:'original-session',student_id:first.student_id,revision:1};
  const client=new CloudLearningClient(first,transport(async (route,options)=>{
    if(route==='/auth/session')return first;
    if(route.includes('learning-sessions?'))return existing?[{id:confirmed.id}]:[];
    if(options?.method==='POST'){writes++;return confirmed;}
    return confirmed;
  }));
  const source={kind:'lesson' as const,book_id:'g1up',source_id:'test-course'};
  assert.equal((await openActivity(client,source)).id,confirmed.id); assert.equal(writes,1);
  existing=true;
  assert.equal((await openActivity(client,source)).id,confirmed.id); assert.equal(writes,1);
  client.dispose(false);
});

test("navigation recovers only original time receipts, never answers or rewards", async () => {
  const saved=storage();
  const before=new CloudLearningClient(first,transport(async()=>first),saved);
  const eventPath=`/students/${first.student_id}/events`;
  const eventBody={kind:'time_checkpoint',session_id:'original-session',activity_id:'original-activity',sequence:1,client_at:'2026-11-03T10:00:00Z',started_at:'2026-11-03T09:59:55Z',ended_at:'2026-11-03T10:00:00Z'};
  const receipt=before.prepare(eventPath,eventBody);
  const reward=before.prepare(path,body);
  before.dispose(false);
  const sent:{path:string;key:string|null;body:BodyInit|null|undefined}[]=[];
  const after=new CloudLearningClient(first,transport(async(route,options)=>{
    if(route==='/auth/session')return first;
    sent.push({path:route,key:new Headers(options?.headers).get('Idempotency-Key'),body:options?.body});return {accepted:true};
  }),saved);
  await after.retryTimeCheckpoints();
  assert.deepEqual(sent,[{path:eventPath,key:receipt,body:JSON.stringify(eventBody)}]);
  assert.deepEqual(after.projection.getSnapshot().pending,[reward]);
  assert.deepEqual(after.projection.getSnapshot().sending,[]);
  after.dispose(false);
});

test("public catalogue cache deduplicates, expires, isolates identities and never caches learner state", async () => {
  const calls:string[]=[];let release!:(v:unknown)=>void;
  const client=new CloudLearningClient(first,transport(async route=>{
    calls.push(route);
    if(route==='/learning/shop')return new Promise(resolve=>{release=resolve;});
    if(route.endsWith('/progress'))return progress();
    return [{title:'目录',version:'v1'}];
  }));
  const a=client.getShop<{items:string[]}>(),b=client.getShop<{items:string[]}>();
  assert.equal(calls.length,1);release({items:['hat']});
  const [one,two]=await Promise.all([a,b]);one.items.push('mutated');assert.deepEqual(two.items,['hat']);
  assert.deepEqual((await client.getShop<{items:string[]}>()).items,['hat']);assert.equal(calls.length,1);
  await client.getBookContent('g1up');await client.getBookContent('g1up');assert.equal(calls.filter(x=>x==='/content/books/g1up').length,1);
  const originalNow=Date.now;try {const now=Date.now();Date.now=()=>now+31000;await client.getBookContent('g1up');}finally{Date.now=originalNow;}
  assert.equal(calls.filter(x=>x==='/content/books/g1up').length,2);
  await client.getProgress();await client.getProgress();assert.equal(calls.filter(x=>x.endsWith('/progress')).length,2);
  const cached=client.getBookContent('g1up');client.dispose();await assert.rejects(cached,StaleLearningContext);
  const other=new CloudLearningClient(second,transport(async route=>{calls.push(route);return {items:['other']};}));
  assert.deepEqual(await other.getShop(),{items:['other']});other.dispose();
});

test("catalogue read failures and invalidated in-flight requests never populate the cache", async()=>{
 let count=0;const client=new CloudLearningClient(first,transport(async()=>{count++;if(count===1)throw Error('offline');return [];}));
 await assert.rejects(client.getBookContent('g1up'),/offline/);await client.getBookContent('g1up');assert.equal(count,2);client.dispose();
 let reply!:(v:unknown)=>void;const old=new CloudLearningClient(first,transport(async()=>new Promise(resolve=>{reply=resolve;})));
 const waiting=old.getBookContent('g1up');old.dispose();reply([]);await assert.rejects(waiting,StaleLearningContext);
});
