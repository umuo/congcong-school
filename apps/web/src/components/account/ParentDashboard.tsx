"use client";
import { useCallback, useEffect, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import {
  api,
  post,
  announceSessionChange,
  type Account,
} from "@/lib/api/client";
import {
  Field,
  FloatingToast,
  InfoPopover,
  ModalDialog,
  type ToastTone,
} from "./AccountShell";
import { StudentForm, type Student } from "./StudentForm";
import { CurriculumForm } from "./CurriculumForm";
import { StudentOverview } from "./StudentOverview";
import { StudentDiagnosticsPanel } from "./StudentDiagnosticsPanel";
import { PortabilityPanel } from "./PortabilityPanel";
import { Avatar } from "@/components/avatars/Avatar";
import { AVATAR_UPDATED } from "@/lib/avatars/client";

export type ParentModuleTab =
  | "overview"
  | "diagnostics"
  | "curriculum"
  | "manage";

export function ParentDashboard({ account }: { account: Account }) {
  const router = useRouter();
  const [students, setStudents] = useState<Student[]>([]);
  const [selected, setSelected] = useState("");
  const [loading, setLoading] = useState(true);
  const [loadFailed, setLoadFailed] = useState(false);
  const [tab, setTab] = useState<ParentModuleTab>("overview");
  const [creating, setCreating] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [archiving, setArchiving] = useState(false);
  const [archived, setArchived] = useState(false);
  const [version, setVersion] = useState(0);
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState<{ text: string; tone: ToastTone }>({
    text: "",
    tone: "info",
  });

  const student =
    students.find((s) => s.id === selected) ?? students[0] ?? undefined;

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setLoadFailed(false);
    void api<Student[]>(`/students?include_archived=${archived}`, {
      signal: controller.signal,
    })
      .then((value) => {
        if (controller.signal.aborted) return;
        setStudents(value);
        setSelected((prev) =>
          prev && value.some((s) => s.id === prev)
            ? prev
            : (value[0]?.id ?? ""),
        );
      })
      .catch((e: Error) => {
        if (!controller.signal.aborted) {
          setToast({ text: e.message, tone: "error" });
          setLoadFailed(true);
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [archived, version]);

  const refresh = useCallback(() => setVersion((v) => v + 1), []);

  useEffect(() => {
    window.addEventListener(AVATAR_UPDATED, refresh);
    return () => window.removeEventListener(AVATAR_UPDATED, refresh);
  }, [refresh]);

  function pick(id: string) {
    setSelected(id);
    setCreating(false);
    setArchiving(false);
  }

  async function enter() {
    if (!student) return;
    setBusy(true);
    setToast({ text: "", tone: "info" });
    try {
      await post("/mode/child", { student_id: student.id });
      announceSessionChange();
      router.replace("/learn");
    } catch (e) {
      setToast({
        text: e instanceof Error ? e.message : "进入失败",
        tone: "error",
      });
    } finally {
      setBusy(false);
    }
  }

  async function archive() {
    if (!student) return;
    setBusy(true);
    setToast({ text: "", tone: "info" });
    try {
      await api(`/students/${student.id}/archive`, {
        method: "POST",
        headers: { "If-Match": String(student.revision) },
      });
      setToast({
        text: `已归档 ${student.nickname} 的档案。`,
        tone: "success",
      });
      setSelected("");
      setArchiving(false);
      refresh();
    } catch (e) {
      setToast({
        text: e instanceof Error ? e.message : "归档失败",
        tone: "error",
      });
    } finally {
      setBusy(false);
    }
  }

  async function saveNickname(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setToast({ text: "", tone: "info" });
    const nickname = new FormData(event.currentTarget).get("nickname");
    try {
      await api("/me", { method: "PATCH", body: JSON.stringify({ nickname }) });
      setToast({
        text: "昵称已保存，重新打开页面可查看最新资料。",
        tone: "success",
      });
    } catch (e) {
      setToast({
        text: e instanceof Error ? e.message : "保存失败",
        tone: "error",
      });
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="parent-workspace">
      <FloatingToast
        message={toast.text}
        tone={toast.tone}
        onDismiss={() => setToast({ text: "", tone: "info" })}
      />

      <header className="parent-workspace-header">
        <div className="parent-workspace-title">
          <h1>{account.family?.name ?? "家庭工作台"}</h1>
          <span className="parent-family-badge">
            时区 {account.family?.timezone ?? "Asia/Shanghai"}
          </span>
          <InfoPopover label="工作台说明" title="家长工作台使用指南">
            <p>
              顶部可一键切换孩子档案或进入孩子学习模式；下方按「学习概况、知识点诊断、教材配置、档案与数据」四大分类组织。
            </p>
            <p>
              当前家长账号：<strong>{account.user?.login_name}</strong>
              。登录账号的开通、停用和密码重置请联系管理员。
            </p>
          </InfoPopover>
        </div>
        <div className="account-actions">
          <button
            type="button"
            className="secondary"
            onClick={() => setSettingsOpen(true)}
          >
            家庭设置
          </button>
          <button
            type="button"
            onClick={() => {
              setCreating(true);
            }}
          >
            添加孩子档案
          </button>
        </div>
      </header>

      <section className="parent-child-bar" aria-label="孩子档案切换栏">
        <div className="parent-child-bar-top">
          <div className="parent-child-bar-title">
            <h2>孩子档案</h2>
            <span className="parent-family-badge">
              {students.length} 位孩子
            </span>
          </div>
          <label className="account-toggle-label">
            <input
              type="checkbox"
              checked={archived}
              onChange={(e) => {
                setArchived(e.target.checked);
                setSelected("");
              }}
            />
            显示已归档档案
          </label>
        </div>

        {loading ? <p role="status">正在读取孩子档案…</p> : null}

        {students.length > 0 ? (
          <div className="parent-child-strip" role="group" aria-label="选择孩子">
            {students.map((s) => {
              const isCurrent = s.id === student?.id;
              return (
                <button
                  key={s.id}
                  type="button"
                  className="parent-child-pill"
                  aria-pressed={isCurrent}
                  onClick={() => pick(s.id)}
                >
                  <Avatar id={s.avatar} size={44} />
                  <span className="parent-child-pill-meta">
                    <strong>
                      <span>{s.nickname}</span>
                      {isCurrent ? (
                        <span className="parent-child-current-tag">当前</span>
                      ) : null}
                      {s.archived_at ? (
                        <span className="diag-scope-tag">已归档</span>
                      ) : null}
                    </strong>
                    <small>
                      {s.grade} 年级 · 每日目标 {s.daily_goal_minutes} 分钟
                    </small>
                  </span>
                </button>
              );
            })}
          </div>
        ) : null}

        {!loading && !loadFailed && !students.length ? (
          <div className="account-row">
            <div>
              <strong>还没有孩子档案</strong>
              <small>点击右上角“添加孩子档案”为孩子建立专属学习空间</small>
            </div>
            <button type="button" onClick={() => setCreating(true)}>
              立即添加孩子
            </button>
          </div>
        ) : null}

        {loadFailed ? (
          <div className="account-actions">
            <button type="button" className="secondary" onClick={refresh}>
              重试读取档案
            </button>
          </div>
        ) : null}

        {student ? (
          <div className="parent-active-student-bar">
            <div className="parent-active-student-info">
              <Avatar id={student.avatar} size={52} />
              <div>
                <strong>{student.nickname}的工作台</strong>
                <small style={{ display: "block" }}>
                  当前 {student.grade} 年级（
                  {student.semester === "down" ? "下学期" : "上学期"}）· 每日目标{" "}
                  {student.daily_goal_minutes} 分钟
                  {student.archived_at ? " · 已归档" : ""}
                </small>
              </div>
            </div>

            <div className="account-actions">
              <nav
                className="account-segmented-tabs"
                aria-label="孩子档案导航"
              >
                <button
                  type="button"
                  aria-pressed={tab === "overview"}
                  onClick={() => setTab("overview")}
                >
                  学习概况
                </button>
                <button
                  type="button"
                  aria-pressed={tab === "diagnostics"}
                  onClick={() => setTab("diagnostics")}
                >
                  知识点诊断
                </button>
                <button
                  type="button"
                  aria-pressed={tab === "curriculum"}
                  onClick={() => setTab("curriculum")}
                >
                  教材配置
                </button>
                <button
                  type="button"
                  aria-pressed={tab === "manage"}
                  onClick={() => setTab("manage")}
                >
                  档案与数据
                </button>
              </nav>

              <button
                type="button"
                disabled={busy || !!student.archived_at}
                onClick={enter}
              >
                进入孩子模式
              </button>
            </div>
          </div>
        ) : null}
      </section>

      {student ? (
        <div key={student.id}>
          {tab === "overview" ? (
            <section className="account-card" aria-label="学习概况模块">
              <StudentOverview studentId={student.id} />
              <div className="account-actions" style={{ marginTop: 20 }}>
                <button
                  type="button"
                  className="secondary"
                  onClick={() => setTab("diagnostics")}
                >
                  查看知识点诊断
                </button>
                <button
                  type="button"
                  className="secondary"
                  onClick={() => setTab("curriculum")}
                >
                  配置教材
                </button>
              </div>
            </section>
          ) : null}

          {tab === "diagnostics" ? (
            <section className="account-card" aria-label="知识点诊断模块">
              <StudentDiagnosticsPanel studentId={student.id} />
            </section>
          ) : null}

          {tab === "curriculum" ? (
            <CurriculumForm student={student} onSave={refresh} />
          ) : null}

          {tab === "manage" ? (
            <div className="account-list">
              <StudentForm
                key={`${student.id}:${student.revision}`}
                student={student}
                onSave={() => refresh()}
              />
              <section className="account-card" aria-label="数据与归档管理">
                <PortabilityPanel
                  key={`data:${student.id}`}
                  account={account}
                  student={student}
                  embedded
                  onDeleted={() => {
                    setSelected("");
                    refresh();
                  }}
                  onImported={refresh}
                />
                <div className="parent-danger-zone">
                  <div>
                    <strong>归档 {student.nickname} 的档案</strong>
                    <small>
                      归档后停止该孩子的学习访问与独立账号登录，历史课程与作答记录完整保留
                    </small>
                  </div>
                  <button
                    type="button"
                    className="danger-outline"
                    disabled={busy || !!student.archived_at}
                    onClick={() => setArchiving(true)}
                  >
                    {student.archived_at ? "已归档" : "归档档案"}
                  </button>
                </div>
              </section>
            </div>
          ) : null}
        </div>
      ) : null}

      <ModalDialog
        open={creating}
        title="添加孩子档案"
        subtitle="为家庭建立独立隔离的孩子学习档案"
        onClose={() => setCreating(false)}
        size="lg"
      >
        <StudentForm
          embedded
          onCancel={() => setCreating(false)}
          onSave={(s) => {
            setCreating(false);
            refresh();
            setSelected(s.id);
            setTab("overview");
            setToast({
              text: `已添加 ${s.nickname} 的学习档案。`,
              tone: "success",
            });
          }}
        />
      </ModalDialog>

      <ModalDialog
        open={settingsOpen}
        title="家庭设置"
        subtitle={`家庭：${account.family?.name ?? "未命名"} · 时区：${account.family?.timezone ?? "Asia/Shanghai"}`}
        onClose={() => setSettingsOpen(false)}
        size="md"
      >
        <div className="account-section-head">
          <div className="account-section-title-group">
            <h3>家长资料与全家庭数据</h3>
            <InfoPopover label="账号说明" title="家庭账号与权限说明">
              <p>
                当前登录账号：<strong>{account.user?.login_name}</strong>
              </p>
              <p>登录账号的开通、停用和密码重置请联系系统管理员。</p>
            </InfoPopover>
          </div>
        </div>
        <form onSubmit={saveNickname}>
          <Field label="家长昵称">
            <input
              name="nickname"
              defaultValue={account.user?.nickname}
              required
              maxLength={80}
            />
          </Field>
          <div className="account-actions">
            <button disabled={busy}>保存昵称</button>
          </div>
        </form>
        <div style={{ marginTop: 12, paddingTop: 16, borderTop: "1px solid #e4eee7" }}>
          <PortabilityPanel
            account={account}
            embedded
            onDeleted={refresh}
            onImported={refresh}
          />
        </div>
      </ModalDialog>

      <ModalDialog
        open={archiving && Boolean(student)}
        title={student ? `确认归档 ${student.nickname}` : "确认归档档案"}
        subtitle="归档操作不会删除历史学习数据"
        onClose={() => setArchiving(false)}
        size="sm"
      >
        {student ? (
          <div>
            <p>
              归档 <strong>{student.nickname}</strong>{" "}
              后将停止其学习访问与独立学生账号登录，原有学习记录、教材历史与作答证据均完整保留。
            </p>
            <div className="account-actions" style={{ marginTop: 16 }}>
              <button
                type="button"
                className="danger"
                disabled={busy}
                onClick={archive}
              >
                确认归档
              </button>
              <button
                type="button"
                className="secondary"
                onClick={() => setArchiving(false)}
              >
                取消
              </button>
            </div>
          </div>
        ) : null}
      </ModalDialog>
    </main>
  );
}
