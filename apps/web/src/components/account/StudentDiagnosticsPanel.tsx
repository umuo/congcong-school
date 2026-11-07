"use client";
import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api/client";
import { FloatingToast, InfoPopover, ModalDialog } from "./AccountShell";

export type MasteryStatus =
  | "mastered"
  | "developing"
  | "needs_review"
  | "insufficient_evidence"
  | "unassessed";

export type RelatedKnowledgePoint = {
  kp_id: string;
  book_id: string;
  lesson_id: string | null;
  code: string;
  title: string;
  relation_kind: string;
  direction: string;
  note?: string | null;
  status?: MasteryStatus | null;
  status_label?: string | null;
  first_attempt_count?: number;
};

export type KnowledgePointMasteryItem = {
  id: string;
  subject_code: string;
  book_id: string;
  unit_number: number;
  unit_title: string;
  lesson_id: string | null;
  scope_kind: string;
  code: string;
  title: string;
  description: string | null;
  sort_order: number;
  status: MasteryStatus;
  status_label: string;
  diagnostic_rule_version: string;
  reason_code: string;
  reason_text: string;
  total_questions_available: number;
  distinct_questions_attempted: number;
  distinct_sessions: number;
  distinct_days: number;
  total_attempts: number;
  first_attempt_count: number;
  first_correct_count: number;
  unassisted_first_correct_count: number;
  hint_assisted_count: number;
  retry_attempt_count: number;
  retry_correct_count: number;
  first_attempt_accuracy: number | null;
  unassisted_first_accuracy: number | null;
  overall_accuracy: number | null;
  last_attempted_at: string | null;
  related_has_evidence: boolean;
  related_points: RelatedKnowledgePoint[];
};

export type DiagnosticBookOption = {
  book_id: string;
  title: string;
  subject_code: string;
  subject_name: string;
  grade: number;
  semester: string;
  edition: string;
  is_current_curriculum: boolean;
  attempt_count: number;
};

export type StudentDiagnosticsResponse = {
  student_id: string;
  timezone: string;
  diagnostic_rule_version: string;
  mapping_version: string;
  selected_subject_code: string | null;
  selected_book_id: string | null;
  selected_book_title: string | null;
  available_books: DiagnosticBookOption[];
  summary: {
    total_knowledge_points: number;
    assessed_count: number;
    mastered_count: number;
    developing_count: number;
    needs_review_count: number;
    insufficient_evidence_count: number;
    unassessed_count: number;
    total_attempts: number;
    legacy_imports_count: number;
    legacy_exclusion_note: string;
  };
  priority_review: KnowledgePointMasteryItem[];
  units: {
    unit_number: number;
    unit_title: string;
    total_count: number;
    mastered_count: number;
    developing_count: number;
    needs_review_count: number;
    insufficient_evidence_count: number;
    unassessed_count: number;
    knowledge_points: KnowledgePointMasteryItem[];
  }[];
};

export type AttemptEvidenceView = {
  attempt_id: string;
  session_id: string;
  question_uid: string;
  question_version: string;
  book_id: string;
  source_id: string;
  correct: boolean;
  first_attempt: boolean;
  hint_level: number;
  declared_duration_ms: number;
  received_at: string;
  mapping_source: string;
};

export type KnowledgePointEvidenceDetailResponse = {
  student_id: string;
  timezone: string;
  diagnostic_rule_version: string;
  mapping_version: string;
  knowledge_point: KnowledgePointMasteryItem;
  recent_attempts: AttemptEvidenceView[];
};

const SUBJECT_NAMES: Record<string, string> = {
  math: "数学",
  chinese: "语文",
  english: "英语",
  science: "科学",
};

const SCOPE_LABELS: Record<string, string> = {
  lesson: "课时核心",
  unit_challenge: "单元挑战",
  story_skill: "阅读故事",
  number_skill: "数感训练",
};

function formatDate(iso: string | null): string {
  if (!iso) return "尚未作答";
  return iso.slice(0, 10);
}

function formatDateTime(iso: string): string {
  return iso.replace("T", " ").slice(0, 16);
}

export function StudentDiagnosticsPanel({ studentId }: { studentId: string }) {
  const [data, setData] = useState<StudentDiagnosticsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [subjectFilter, setSubjectFilter] = useState<string>("");
  const [bookFilter, setBookFilter] = useState<string>("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [retry, setRetry] = useState(0);

  const [selectedKpId, setSelectedKpId] = useState<string | null>(null);
  const [detail, setDetail] = useState<KnowledgePointEvidenceDetailResponse | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState("");
  const reqSeqRef = useRef(0);
  const detailSeqRef = useRef(0);

  useEffect(() => {
    setSubjectFilter("");
    setBookFilter("");
    setStatusFilter("all");
    setSelectedKpId(null);
    setDetail(null);
    setDetailError("");
  }, [studentId]);

  useEffect(() => {
    const controller = new AbortController();
    const seq = ++reqSeqRef.current;
    setLoading(true);
    setError("");

    const params = new URLSearchParams();
    if (bookFilter) {
      params.set("book_id", bookFilter);
    } else if (subjectFilter) {
      params.set("subject", subjectFilter);
    }
    const qs = params.toString();
    const path = `/students/${studentId}/diagnostics${qs ? `?${qs}` : ""}`;

    void api<StudentDiagnosticsResponse>(path, { signal: controller.signal })
      .then((res) => {
        if (
          controller.signal.aborted ||
          seq !== reqSeqRef.current ||
          res.student_id !== studentId
        ) {
          return;
        }
        setData(res);
        setLoading(false);
      })
      .catch((err: Error) => {
        if (!controller.signal.aborted && seq === reqSeqRef.current) {
          setError(err.message || "无法读取知识点诊断");
          setLoading(false);
        }
      });

    return () => controller.abort();
  }, [studentId, subjectFilter, bookFilter, retry]);

  useEffect(() => {
    if (!selectedKpId) {
      setDetail(null);
      setDetailError("");
      setDetailLoading(false);
      return;
    }
    const controller = new AbortController();
    const seq = ++detailSeqRef.current;
    setDetailLoading(true);
    setDetailError("");

    void api<KnowledgePointEvidenceDetailResponse>(
      `/students/${studentId}/diagnostics/knowledge-points/${encodeURIComponent(selectedKpId)}`,
      { signal: controller.signal }
    )
      .then((res) => {
        if (
          controller.signal.aborted ||
          seq !== detailSeqRef.current ||
          res.student_id !== studentId ||
          res.knowledge_point.id !== selectedKpId
        ) {
          return;
        }
        setDetail(res);
        setDetailLoading(false);
      })
      .catch((err: Error) => {
        if (!controller.signal.aborted && seq === detailSeqRef.current) {
          setDetailError(err.message || "无法读取知识点作答证据");
          setDetailLoading(false);
        }
      });

    return () => controller.abort();
  }, [studentId, selectedKpId]);

  const handleSubjectSelect = (subj: string) => {
    setSelectedKpId(null);
    setSubjectFilter(subj);
    setBookFilter("");
  };

  const handleBookSelect = (bookId: string) => {
    setSelectedKpId(null);
    setBookFilter(bookId);
    const matched = data?.available_books.find((b) => b.book_id === bookId);
    if (matched) {
      setSubjectFilter(matched.subject_code);
    }
  };

  if (error) {
    return (
      <section className="diag-panel" aria-label="知识点掌握诊断">
        <FloatingToast
          message={error}
          tone="error"
          duration={0}
          onDismiss={() => setError("")}
        >
          <button
            type="button"
            className="secondary"
            onClick={() => setRetry((v) => v + 1)}
          >
            重试诊断加载
          </button>
        </FloatingToast>
      </section>
    );
  }

  if (loading && !data) {
    return (
      <section className="diag-panel" aria-label="知识点掌握诊断">
        <p role="status">正在分析知识点掌握情况…</p>
      </section>
    );
  }

  if (!data) return null;

  const activeSubject = subjectFilter || data.selected_subject_code || "math";
  const activeBookId = bookFilter || data.selected_book_id || "";

  const subjectsAvailable = Array.from(
    new Set(data.available_books.map((b) => b.subject_code))
  );
  const subjectTabs =
    subjectsAvailable.length > 0
      ? subjectsAvailable
      : ["math", "chinese", "english", "science"];

  const booksForSubject = data.available_books.filter(
    (b) => b.subject_code === activeSubject
  );
  const bookOptions =
    booksForSubject.length > 0 ? booksForSubject : data.available_books;

  const { summary } = data;

  return (
    <section
      className="diag-panel"
      aria-label="知识点掌握诊断"
      data-testid="student-diagnostics-panel"
    >
      {loading ? (
        <FloatingToast message="正在切换教材诊断数据…" tone="info" duration={1800} />
      ) : null}

      <div className="diag-header">
        <div className="account-section-title-group">
          <h3>知识点掌握诊断</h3>
          <span className="parent-family-badge">
            {data.selected_book_title || data.selected_book_id || "未选择"}
          </span>
          <InfoPopover label="诊断说明" title="知识点诊断与证据边界说明">
            <p>
              当前教材：<strong>{data.selected_book_title || data.selected_book_id || "未选择"}</strong> · 诊断规则{" "}
              <code>{data.diagnostic_rule_version}</code>（题库映射{" "}
              <code>{data.mapping_version}</code>）
            </p>
            <p data-testid="diag-boundary-note">
              {summary.legacy_exclusion_note}
              {summary.legacy_imports_count > 0
                ? `（当前已单独保留 ${summary.legacy_imports_count} 份旧本地档案摘要）`
                : ""}
            </p>
            <p>
              掌握度仅依据云端逐次题目作答（区分首答正确、提示辅助与同场错题回炉），不掺杂经验值、宝石或打卡记录。
            </p>
          </InfoPopover>
        </div>
        <div className="diag-controls">
          <div className="diag-subject-tabs" role="group" aria-label="学科筛选">
            {subjectTabs.map((subj) => (
              <button
                key={subj}
                type="button"
                className={activeSubject === subj ? "" : "secondary"}
                aria-pressed={activeSubject === subj}
                onClick={() => handleSubjectSelect(subj)}
              >
                {SUBJECT_NAMES[subj] || subj}
              </button>
            ))}
          </div>
          {bookOptions.length > 0 && (
            <label className="diag-book-select">
              <span>教材版本</span>
              <select
                aria-label="诊断教材"
                value={activeBookId}
                onChange={(e) => handleBookSelect(e.target.value)}
              >
                {bookOptions.map((b) => (
                  <option key={b.book_id} value={b.book_id}>
                    {b.title}
                    {b.is_current_curriculum ? "（当前在学）" : ""}
                    {b.attempt_count > 0 ? ` · ${b.attempt_count}次作答` : ""}
                  </option>
                ))}
              </select>
            </label>
          )}
        </div>
      </div>

      <div className="diag-summary-grid" role="region" aria-label="掌握度统计">
        <button
          type="button"
          className={`diag-stat-card diag-stat-all ${statusFilter === "all" ? "diag-stat-active" : ""}`}
          aria-pressed={statusFilter === "all"}
          onClick={() => setStatusFilter("all")}
        >
          <span className="diag-stat-label">全部知识点</span>
          <strong>{summary.total_knowledge_points}</strong>
          <small>已评估 {summary.assessed_count} 项</small>
        </button>
        <button
          type="button"
          className={`diag-stat-card diag-stat-mastered ${statusFilter === "mastered" ? "diag-stat-active" : ""}`}
          aria-pressed={statusFilter === "mastered"}
          onClick={() => setStatusFilter("mastered")}
        >
          <span className="diag-stat-label">已掌握</span>
          <strong>{summary.mastered_count}</strong>
          <small>多题或跨日稳定正确</small>
        </button>
        <button
          type="button"
          className={`diag-stat-card diag-stat-developing ${statusFilter === "developing" ? "diag-stat-active" : ""}`}
          aria-pressed={statusFilter === "developing"}
          onClick={() => setStatusFilter("developing")}
        >
          <span className="diag-stat-label">巩固中</span>
          <strong>{summary.developing_count}</strong>
          <small>首答良好待隔天巩固</small>
        </button>
        <button
          type="button"
          className={`diag-stat-card diag-stat-needs_review ${statusFilter === "needs_review" ? "diag-stat-active" : ""}`}
          aria-pressed={statusFilter === "needs_review"}
          onClick={() => setStatusFilter("needs_review")}
        >
          <span className="diag-stat-label">需复习</span>
          <strong>{summary.needs_review_count}</strong>
          <small>首答出错或近期波动</small>
        </button>
        <button
          type="button"
          className={`diag-stat-card diag-stat-insufficient_evidence ${statusFilter === "insufficient_evidence" ? "diag-stat-active" : ""}`}
          aria-pressed={statusFilter === "insufficient_evidence"}
          onClick={() => setStatusFilter("insufficient_evidence")}
        >
          <span className="diag-stat-label">证据不足</span>
          <strong>{summary.insufficient_evidence_count}</strong>
          <small>单题或依赖提示</small>
        </button>
        <button
          type="button"
          className={`diag-stat-card diag-stat-unassessed ${statusFilter === "unassessed" ? "diag-stat-active" : ""}`}
          aria-pressed={statusFilter === "unassessed"}
          onClick={() => setStatusFilter("unassessed")}
        >
          <span className="diag-stat-label">未评估</span>
          <strong>{summary.unassessed_count}</strong>
          <small>尚无云端作答</small>
        </button>
      </div>

      {data.priority_review.length > 0 && (
        <div
          className="diag-priority-box"
          role="region"
          aria-label="建议优先复习与巩固"
        >
          <h4>建议优先关注（{data.priority_review.length} 项）</h4>
          <div className="diag-kp-list">
            {data.priority_review.slice(0, 6).map((kp) => (
              <div key={kp.id} className="diag-kp-row diag-kp-priority">
                <div className="diag-kp-main">
                  <div className="diag-kp-title-line">
                    <span className={`diag-badge diag-badge-${kp.status}`}>
                      {kp.status_label}
                    </span>
                    <span className="diag-scope-tag">
                      {SCOPE_LABELS[kp.scope_kind] || kp.scope_kind}
                    </span>
                    <strong>{kp.title}</strong>
                  </div>
                  <p className="diag-kp-reason">{kp.reason_text}</p>
                  <small>
                    {kp.unit_title} · 无提示首答{" "}
                    {kp.unassisted_first_correct_count}/{kp.first_attempt_count}{" "}
                    · 覆盖 {kp.distinct_questions_attempted}/
                    {kp.total_questions_available} 题 · {kp.distinct_days} 天 ·
                    最近作答 {formatDate(kp.last_attempted_at)}
                  </small>
                </div>
                <div className="account-actions">
                  <button
                    type="button"
                    className="secondary"
                    aria-expanded={selectedKpId === kp.id}
                    onClick={() =>
                      setSelectedKpId((prev) => (prev === kp.id ? null : kp.id))
                    }
                  >
                    {selectedKpId === kp.id ? "收起证据" : "查看证据"}
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <ModalDialog
        open={Boolean(selectedKpId)}
        title="知识点证据明细"
        subtitle={
          detail?.knowledge_point
            ? `${detail.knowledge_point.unit_title} · ${detail.knowledge_point.code}`
            : undefined
        }
        onClose={() => setSelectedKpId(null)}
        size="lg"
      >
        <div role="region" aria-label="知识点作答证据详情">
          {detailLoading && <p role="status">正在读取知识点作答证据…</p>}
          {detailError && (
            <FloatingToast
              message={detailError}
              tone="error"
              onDismiss={() => setDetailError("")}
            />
          )}
          {detail && detail.knowledge_point.id === selectedKpId && (
            <div className="diag-evidence-body">
              <div className="diag-kp-title-line">
                <span
                  className={`diag-badge diag-badge-${detail.knowledge_point.status}`}
                >
                  {detail.knowledge_point.status_label}
                </span>
                <strong>{detail.knowledge_point.title}</strong>
                <small>({detail.knowledge_point.code})</small>
              </div>
              {detail.knowledge_point.description && (
                <p>{detail.knowledge_point.description}</p>
              )}
              <p className="diag-kp-reason">
                诊断结论：{detail.knowledge_point.reason_text}
              </p>
              <div className="account-stats-4">
                <div>
                  <strong>{detail.knowledge_point.total_attempts} 次</strong>
                  <small>
                    累计作答（首答 {detail.knowledge_point.first_attempt_count} 次）
                  </small>
                </div>
                <div>
                  <strong>
                    {detail.knowledge_point.unassisted_first_correct_count} 次
                  </strong>
                  <small>无提示首答正确</small>
                </div>
                <div>
                  <strong>{detail.knowledge_point.hint_assisted_count} 次</strong>
                  <small>使用提示辅助</small>
                </div>
                <div>
                  <strong>
                    {detail.knowledge_point.retry_correct_count}/
                    {detail.knowledge_point.retry_attempt_count} 次
                  </strong>
                  <small>同场回炉订正</small>
                </div>
              </div>
              {detail.knowledge_point.related_points.length > 0 && (
                <div className="diag-related-box">
                  <strong>关联课程/跨版知识点：</strong>
                  <ul>
                    {detail.knowledge_point.related_points.map((rel) => (
                      <li key={`${rel.kp_id}-${rel.relation_kind}-${rel.direction}`}>
                        {rel.title}（{rel.book_id} ·{" "}
                        {rel.relation_kind === "restores_lesson"
                          ? "同书专项拆课关联"
                          : "跨版同名知识点"}
                        {rel.status_label ? ` · ${rel.status_label}` : ""}）
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              <h5>最近作答记录</h5>
              {detail.recent_attempts.length === 0 ? (
                <p>该知识点尚无云端题目作答记录。</p>
              ) : (
                <ul className="diag-attempt-list">
                  {detail.recent_attempts.map((att) => (
                    <li key={att.attempt_id}>
                      <span>{formatDateTime(att.received_at)}</span> ·{" "}
                      <strong>{att.correct ? "答对" : "答错"}</strong> ·{" "}
                      <span>{att.first_attempt ? "首答" : "同场回炉重做"}</span>
                      {att.hint_level > 0
                        ? ` · 使用提示(L${att.hint_level})`
                        : " · 无提示"}{" "}
                      ·{" "}
                      <small>
                        用时 {Math.max(1, Math.round(att.declared_duration_ms / 1000))}{" "}
                        秒 · 来源 {att.source_id}
                      </small>
                    </li>
                  ))}
                </ul>
              )}
              <div className="account-actions" style={{ marginTop: 16 }}>
                <button
                  type="button"
                  className="secondary"
                  onClick={() => setSelectedKpId(null)}
                >
                  关闭明细
                </button>
              </div>
            </div>
          )}
        </div>
      </ModalDialog>

      <div className="diag-units-list">
        {data.units.map((unit) => {
          const filteredKps =
            statusFilter === "all"
              ? unit.knowledge_points
              : unit.knowledge_points.filter((kp) => kp.status === statusFilter);
          if (filteredKps.length === 0) return null;
          return (
            <details
              key={unit.unit_number}
              className="diag-unit-card"
              open={
                unit.needs_review_count > 0 ||
                unit.developing_count > 0 ||
                unit.mastered_count > 0 ||
                unit.unit_number === 1
              }
            >
              <summary className="diag-unit-summary">
                <span>
                  第 {unit.unit_number} 单元 · {unit.unit_title}
                </span>
                <small>
                  共 {unit.total_count} 项 · 已掌握 {unit.mastered_count} · 巩固中{" "}
                  {unit.developing_count} · 需复习 {unit.needs_review_count}
                </small>
              </summary>
              <div className="diag-kp-list">
                {filteredKps.map((kp) => (
                  <div key={kp.id} className="diag-kp-row">
                    <div className="diag-kp-main">
                      <div className="diag-kp-title-line">
                        <span className={`diag-badge diag-badge-${kp.status}`}>
                          {kp.status_label}
                        </span>
                        <span className="diag-scope-tag">
                          {SCOPE_LABELS[kp.scope_kind] || kp.scope_kind}
                        </span>
                        <strong>{kp.title}</strong>
                      </div>
                      <p className="diag-kp-reason">{kp.reason_text}</p>
                      <small>
                        无提示首答 {kp.unassisted_first_correct_count}/
                        {kp.first_attempt_count} · 题量覆盖{" "}
                        {kp.distinct_questions_attempted}/
                        {kp.total_questions_available} 题 · {kp.distinct_days}{" "}
                        个学习日
                        {kp.related_points.length > 0
                          ? ` · 含 ${kp.related_points.length} 项跨课/跨版关联`
                          : ""}
                      </small>
                    </div>
                    <div className="account-actions">
                      <button
                        type="button"
                        className="secondary"
                        aria-expanded={selectedKpId === kp.id}
                        onClick={() =>
                          setSelectedKpId((prev) =>
                            prev === kp.id ? null : kp.id
                          )
                        }
                      >
                        {selectedKpId === kp.id ? "收起证据" : "查看证据"}
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </details>
          );
        })}
      </div>
    </section>
  );
}
