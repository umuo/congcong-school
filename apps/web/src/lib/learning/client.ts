import { api, APIError, type Account } from "../api/client";
import type { AnswerSubmission, LearningKind, LearningSessionView } from "../api/learning-contract";
import { createLearningProjection, type ProgressProjection } from "./projection";
import { CLOUD_PENDING_PREFIX as PREFIX } from "./lifecycle";
import { CLOUD_REPORT_PREFIX } from "./lifecycle";

export type LearningScope = Readonly<{ contextId: string; studentId: string }>;
export interface LearningClient<P> {
  readonly mode: "local" | "cloud";
  readonly scope: LearningScope;
  getProgress(): Promise<P>;
  dispose(forgetPending?: boolean): void;
}
export type StartLearning = {
  kind: LearningKind;
  client_at: string;
  book_id?: string;
  source_id?: string;
  target_unit?: number;
  number_skill?: "count" | "compare" | "apply";
  for_hearts?: boolean;
  reading_kind?: "listen" | "followup";
};
export type Revision = { revision: number; client_at: string };
export type EconomyAction = {
  kind: "league" | "daily_reward" | "quest" | "chest" | "buy_hearts" | "buy_freeze" | "makeup"
    | "purchase_cosmetic" | "equip_cosmetic" | "set_daily_goal";
  client_at: string;
  item_id?: string;
  quest_id?: string;
  chest_id?: string;
  book_id?: string;
  daily_goal?: number;
  revision?: number;
};
export type PendingOperation = Readonly<{
  key: string;
  scope: LearningScope;
  path: string;
  method: "POST" | "PUT";
  body: string;
}>;
type StorageLike = Pick<Storage, "getItem" | "setItem" | "removeItem" | "key" | "length">;
type Transport = <T>(path: string, options?: RequestInit) => Promise<T>;
const invalidCodes = new Set([
  "AUTH_REQUIRED", "PASSWORD_CHANGE_REQUIRED", "LEARNING_CONTEXT_CHANGED",
  "PARENT_REQUIRED", "STUDENT_ARCHIVED", "STUDENT_NOT_FOUND", "LEARNING_MODE_REQUIRED",
]);
export class StaleLearningContext extends Error {
  constructor() { super("学习身份已变化，请重新进入学习空间。"); }
}

/** 每个实例固定一个登录及学生；不存在将旧请求重新绑定到新学生的操作。 */
export class CloudLearningClient implements LearningClient<ProgressProjection> {
  readonly mode = "cloud";
  readonly scope: LearningScope;
  readonly projection = createLearningProjection();
  private active = true;
  private controllers = new Set<AbortController>();
  private pending = new Map<string, PendingOperation>();
  private inflight = new Map<string, Promise<unknown>>();
  private storageKey: string;
  private catalogueCache = new Map<string, { expires: number; value: unknown }>();
  private catalogueReads = new Map<string, Promise<unknown>>();
  /** Only public catalogue metadata: never auth, curriculum, progress, questions or results. */
  private async catalogue<T>(path: string, ttl: number): Promise<T> {
    this.assertActive();
    const hit = this.catalogueCache.get(path);
    if (hit && hit.expires > Date.now()) return Promise.resolve().then(() => { this.assertActive(); return structuredClone(hit.value) as T; });
    const inflight = this.catalogueReads.get(path);
    if (inflight) return inflight.then(value => { this.assertActive(); return structuredClone(value) as T; });
    const request = this.request<T>(path).then(value => {
      this.assertActive();
      this.catalogueCache.delete(path);
      this.catalogueCache.set(path, { expires: Date.now() + ttl, value: structuredClone(value) });
      while (this.catalogueCache.size > 12) this.catalogueCache.delete(this.catalogueCache.keys().next().value!);
      return value;
    }).finally(() => this.catalogueReads.delete(path));
    this.catalogueReads.set(path,request);
    return request.then(value => { this.assertActive(); return structuredClone(value); });
  }
  constructor(account: Pick<Account, "context_id" | "student_id" | "mode" | "must_change_password">, private transport: Transport = api, private storage?: StorageLike) {
    if (account.mode !== "child" || !account.student_id || account.must_change_password)
      throw new StaleLearningContext();
    this.scope = Object.freeze({ contextId: account.context_id, studentId: account.student_id });
    this.storageKey = PREFIX + this.scope.contextId + ":" + this.scope.studentId;
    try {
      // 只清理云端待提交数据；不删除原 local 档案和备份。
      for (let i = (storage?.length ?? 0) - 1; i >= 0; i--) {
        const key = storage!.key(i);
        if (key?.startsWith(PREFIX) && key !== this.storageKey) storage!.removeItem(key);
        if (key?.startsWith(CLOUD_REPORT_PREFIX) && key !== `${CLOUD_REPORT_PREFIX}${this.scope.contextId}:${this.scope.studentId}`) storage!.removeItem(key);
      }
      const saved: unknown = JSON.parse(storage?.getItem(this.storageKey) ?? "[]");
      if (Array.isArray(saved)) for (const operation of saved) {
        if (this.validOperation(operation)) this.pending.set(operation.key, Object.freeze(operation));
      }
    } catch { /* 受限存储下仍保留当前页面的内存队列。 */ }
    this.publishPending();
  }
  private validOperation(operation: PendingOperation) {
    return operation && operation.scope?.contextId === this.scope.contextId
      && operation.scope?.studentId === this.scope.studentId
      && typeof operation.key === "string" && /^[a-f0-9-]{36}$/i.test(operation.key)
      && ["POST", "PUT"].includes(operation.method) && typeof operation.body === "string"
      && (operation.path === `/students/${this.scope.studentId}/learning-sessions`
        || operation.path === `/students/${this.scope.studentId}/events`
        || operation.path === `/students/${this.scope.studentId}/economy/actions`
        || /^\/learning-sessions\/[a-f0-9-]{36}\/(attempts|advance|checkpoint|complete|hint|matching-pairs)$/i.test(operation.path));
  }
  private assertActive() { if (!this.active) throw new StaleLearningContext(); }
  private publishPending() {
    this.projection.pending([...this.pending.keys()], [...this.inflight.keys()]);
    try {
      if (this.pending.size) this.storage?.setItem(this.storageKey, JSON.stringify([...this.pending.values()]));
      else this.storage?.removeItem(this.storageKey);
    } catch { /* 内存队列仍可重试，不能把存储失败当作服务端确认。 */ }
  }
  private async request<T>(path: string, options: RequestInit = {}): Promise<T> {
    this.assertActive();
    const controller = new AbortController();
    this.controllers.add(controller);
    const headers = new Headers(options.headers);
    headers.set("X-CSF-Learning-Context", this.scope.contextId);
    try {
      const result = await this.transport<T>(path, { ...options, headers, signal: controller.signal });
      this.assertActive(); // 即使 transport 忽略 abort，旧响应也不得发布。
      return result;
    } catch (error) {
      if (error instanceof APIError && (error.status === 401 || invalidCodes.has(error.code)))
        this.dispose();
      this.assertActive();
      throw error;
    } finally { this.controllers.delete(controller); }
  }
  async getProgress() {
    const result = await this.request<ProgressProjection>(`/students/${this.scope.studentId}/progress`);
    if (result.student_id !== this.scope.studentId) { this.dispose(); throw new StaleLearningContext(); }
    this.projection.progress(result);
    return result;
  }
  async getProfile() {
    const result = await this.request<{ id: string; nickname: string; grade: number }>("/learning/profile");
    if (result.id !== this.scope.studentId) { this.dispose(); throw new StaleLearningContext(); }
    return result;
  }
  getSummary<T>() { return this.request<T>(`/students/${this.scope.studentId}/summary`); }
  getShop<T>() { return this.catalogue<T>("/learning/shop", 300000); }
  getLeague<T>() { return this.request<T>(`/students/${this.scope.studentId}/league`); }
  getCurriculum<T>() { return this.request<T>("/learning/curriculum"); }
  getBookContent<T>(book: string) { return this.catalogue<T>(`/content/books/${encodeURIComponent(book)}`, 30000); }
  getContent<T>(book: string, kind: string, source: string) { return this.request<T>(`/content/books/${encodeURIComponent(book)}/${encodeURIComponent(kind)}/${encodeURIComponent(source)}`); }
  getSessionContent<T>(id: string) { return this.request<T>(`/learning-sessions/${encodeURIComponent(id)}/content`); }
  getActiveSessions(source: Partial<Omit<StartLearning, "client_at">>) {
    const query = new URLSearchParams();
    if (source.kind) query.set("kind", source.kind);
    if (source.book_id) query.set("book_id", source.book_id);
    if (source.source_id) query.set("source_id", source.source_id);
    if (source.target_unit) query.set("target_unit", String(source.target_unit));
    if (source.number_skill) query.set("number_skill", source.number_skill);
    if (source.reading_kind) query.set("reading_kind", source.reading_kind);
    if (source.for_hearts) query.set("for_hearts", "true");
    return this.request<import("./next-activity").ActiveActivity[]>(`/students/${this.scope.studentId}/learning-sessions?${query}`);
  }
  getMistakes<T>() { return this.request<T>(`/students/${this.scope.studentId}/mistakes`); }
  getChanges<T>(after = 0) {
    if (!Number.isSafeInteger(after) || after < 0) throw new Error("无效的变化游标");
    return this.request<T>(`/students/${this.scope.studentId}/changes?after=${after}`);
  }
  async getSession(id: string) {
    const result = await this.request<LearningSessionView>(`/learning-sessions/${encodeURIComponent(id)}`);
    this.acceptSession(result);
    return result;
  }
  private acceptSession(result: LearningSessionView) {
    if (result.student_id !== this.scope.studentId) { this.dispose(); throw new StaleLearningContext(); }
    this.projection.session(result);
  }
  /** 先固定请求字节和幂等键，再发送；调用方可保存 key 并展示未同步状态。 */
  prepare(path: string, body: unknown, method: "POST" | "PUT" = "POST") {
    this.assertActive();
    const operation = Object.freeze({ key: crypto.randomUUID(), scope: this.scope, path, method, body: JSON.stringify(body) });
    if (!this.validOperation(operation)) throw new Error("不支持的学习写入路径");
    this.pending.set(operation.key, operation);
    this.publishPending();
    return operation.key;
  }
  /** 用时事件不改变题目 revision，可与当前题目的操作并存。 */
  blocksQuestion(key: string) {
    return this.pending.get(key)?.path !== `/students/${this.scope.studentId}/events`;
  }
  /** Resume only existing foreground-time receipts; never create a learning action. */
  retryTimeCheckpoints() {
    return Promise.allSettled([...this.pending.keys()].filter(key => !this.blocksQuestion(key)).map(key => this.retry(key)));
  }
  retry<T>(key: string): Promise<T> {
    this.assertActive();
    if (this.inflight.has(key)) return this.inflight.get(key) as Promise<T>;
    const task = this.send<T>(key).finally(() => {
      this.inflight.delete(key);
      if (this.active) this.publishPending();
    });
    this.inflight.set(key, task);
    this.publishPending();
    return task;
  }
  private async send<T>(key: string): Promise<T> {
    const operation = this.pending.get(key);
    if (!operation || !this.validOperation(operation)) throw new StaleLearningContext();
    // 刷新恢复的队列和原键重试也必须先确认当前 Cookie 的身份。
    const account = await this.request<Account>("/auth/session");
    if (account.context_id !== this.scope.contextId || account.student_id !== this.scope.studentId
      || account.mode !== "child" || account.must_change_password) {
      this.dispose();
      throw new StaleLearningContext();
    }
    try {
      const result = await this.request<T>(operation.path, {
        method: operation.method, body: operation.body, headers: { "Idempotency-Key": key },
      });
      if (/\/learning-sessions(?:\/[^/]+\/(attempts|advance|checkpoint|hint))?$/.test(operation.path))
        this.acceptSession(result as LearningSessionView);
      if (operation.path.endsWith("/matching-pairs"))
        this.acceptSession((result as { session: LearningSessionView }).session);
      if (operation.path.endsWith("/economy/actions")) {
        const progress = (result as { progress: ProgressProjection }).progress;
        if (progress.student_id !== this.scope.studentId) { this.dispose(); throw new StaleLearningContext(); }
        this.projection.progress(progress);
      }
      // 仅服务端成功确认才删除；没有任何本地判分或奖励写入。
      this.pending.delete(key);
      this.publishPending();
      return result;
    } catch (error) {
      // 明确的业务拒绝不自动重试；5xx/网络异常可能已经提交，保留原字节。
      if (this.active && error instanceof APIError && error.status < 500) {
        this.pending.delete(key);
        this.publishPending();
      }
      throw error;
    }
  }
  async start(body: StartLearning) {
    const result = await this.retry<LearningSessionView>(this.prepare(`/students/${this.scope.studentId}/learning-sessions`, body));
    this.acceptSession(result);
    return result;
  }
  async updateSession(id: string, action: "attempts" | "advance" | "checkpoint" | "hint", body: AnswerSubmission | Revision | (Revision & { answer?: string; intro_page?: number; visual_draft?: number[]; evidence_sentence_indices?: number[] })) {
    const key = this.prepare(`/learning-sessions/${encodeURIComponent(id)}/${action}`, body, action === "checkpoint" ? "PUT" : "POST");
    const result = await this.retry<LearningSessionView>(key);
    this.acceptSession(result);
    return result;
  }
  async economy(body: EconomyAction) {
    const result = await this.retry<{ result: Record<string, unknown>; progress: ProgressProjection }>(
      this.prepare(`/students/${this.scope.studentId}/economy/actions`, body));
    if (result.progress.student_id !== this.scope.studentId) { this.dispose(); throw new StaleLearningContext(); }
    this.projection.progress(result.progress);
    return result;
  }
  complete<T>(id: string, body: Revision & { abandon?: boolean }) {
    return this.retry<T>(this.prepare(`/learning-sessions/${encodeURIComponent(id)}/complete`, body));
  }
  timeCheckpoint<T>(body: {
    kind: "time_checkpoint"; session_id: string; activity_id: string; sequence: number;
    client_at: string; started_at: string; ended_at: string;
  }) {
    return this.retry<T>(this.prepare(`/students/${this.scope.studentId}/events`, body));
  }
  dispose(forgetPending = true) {
    this.active = false;
    this.catalogueCache.clear(); this.catalogueReads.clear();
    for (const controller of this.controllers) controller.abort();
    this.controllers.clear();
    if (forgetPending) { this.pending.clear(); this.publishPending(); }
    this.projection.clear();
  }
}
