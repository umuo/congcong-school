"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api/client";
import { LegacySummary } from "../learning/LegacySummary";
import { FloatingToast, InfoPopover } from "./AccountShell";
import { StudentDiagnosticsPanel } from "./StudentDiagnosticsPanel";

type Summary = {
  student_id: string;
  timezone: string;
  declared_time_ms: number;
  week: { starts_on: string; declared_time_ms: number };
  state: { xp: number; completedLessons: Record<string, unknown> };
  daily: Record<
    string,
    {
      attempts: number;
      lesson_completions: number;
      reading_completions: number;
      story_completions: number;
      declared_time_ms: number;
    }
  >;
};

export function StudentOverview({
  studentId,
  includeDiagnostics = false,
}: {
  studentId: string;
  includeDiagnostics?: boolean;
}) {
  const [data, setData] = useState<Summary | null>(null);
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    setData(null);
    setError("");
    void api<Summary>(`/students/${studentId}/summary`, {
      signal: controller.signal,
    })
      .then((value) => {
        if (!controller.signal.aborted && value.student_id === studentId) {
          setData(value);
        }
      })
      .catch((e: Error) => {
        if (!controller.signal.aborted) setError(e.message);
      });
    return () => controller.abort();
  }, [studentId, retry]);

  if (error) {
    return (
      <section aria-label="已记录的学习情况">
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
            刷新总览
          </button>
        </FloatingToast>
      </section>
    );
  }

  if (!data) return <p role="status">正在读取学习记录…</p>;

  const days = Object.entries(data.daily).sort(([a], [b]) =>
    b.localeCompare(a)
  );
  const completedCount = Object.keys(data.state.completedLessons).length;
  const weekMinutes = Math.round(data.week.declared_time_ms / 60000);
  const totalMinutes = Math.round(data.declared_time_ms / 60000);

  return (
    <section aria-label="已记录的学习情况">
      <div className="account-section-head">
        <div className="account-section-title-group">
          <h3>学习概况指标</h3>
          <InfoPopover label="统计说明" title="学习时间与统计口径说明">
            <p>
              按家庭时区（<strong>{data.timezone}</strong>）归并每日记录，重叠学习时段已自动去重。
            </p>
            <p>
              申报用时仅反映学习会话活跃时长，不代表实际专注度；旧本地成绩在下方历史摘要中单独保留，不计入云端逐题诊断。
            </p>
          </InfoPopover>
        </div>
      </div>

      <div className="account-stats-4">
        <div>
          <strong>已完成 {completedCount} 课</strong>
          <small>云端累计完成课程</small>
        </div>
        <div>
          <strong>{data.state.xp} XP</strong>
          <small>累计学习经验值</small>
        </div>
        <div>
          <strong>本周申报用时 {weekMinutes} 分钟</strong>
          <small>本周自 {data.week.starts_on} 起</small>
        </div>
        <div>
          <strong>累计 {totalMinutes} 分钟</strong>
          <small>历史累计申报时长</small>
        </div>
      </div>

      <h3>最近 7 日学习记录</h3>
      <LegacySummary studentId={studentId} />
      {!days.length ? (
        <p>尚无云端学习记录。</p>
      ) : (
        <div className="account-list">
          {days.slice(0, 7).map(([day, entry]) => (
            <div key={day} className="account-row">
              <div>
                <strong>{day}</strong>
                <small>
                  {entry.attempts} 次作答 · {entry.lesson_completions} 次课程 ·{" "}
                  {entry.reading_completions + entry.story_completions} 次阅读故事
                </small>
              </div>
              <span className="parent-family-badge">
                {Math.round(entry.declared_time_ms / 60000)} 分钟
              </span>
            </div>
          ))}
        </div>
      )}
      {includeDiagnostics ? (
        <StudentDiagnosticsPanel studentId={studentId} />
      ) : null}
    </section>
  );
}
