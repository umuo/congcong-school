"use client";
import { useCallback, useEffect, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import {
  api,
  post,
  announceSessionChange,
  type Account,
} from "@/lib/api/client";
import { Field, Message } from "./AccountShell";
import { StudentForm, type Student } from "./StudentForm";
import { CurriculumForm } from "./CurriculumForm";

const avatars: Record<string, string> = {
  panda: "🐼",
  fox: "🦊",
  rabbit: "🐰",
  bear: "🐻",
};
export function ParentDashboard({ account }: { account: Account }) {
  const router = useRouter();
  const [students, setStudents] = useState<Student[]>([]),
    [selected, setSelected] = useState("");
  const [tab, setTab] = useState("home"),
    [editing, setEditing] = useState(false),
    [creating, setCreating] = useState(false),
    [archiving, setArchiving] = useState(false);
  const [archived, setArchived] = useState(false),
    [version, setVersion] = useState(0),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const student = students.find((s) => s.id === selected);
  useEffect(() => {
    const controller = new AbortController();
    void api<Student[]>(`/students?include_archived=${archived}`, {
      signal: controller.signal,
    })
      .then(setStudents)
      .catch((e) => {
        if (!controller.signal.aborted) setError(e.message);
      });
    return () => controller.abort();
  }, [archived, version]);
  const refresh = useCallback(() => setVersion((v) => v + 1), []);
  function pick(id: string) {
    setSelected(id);
    setEditing(false);
    setCreating(false);
    setArchiving(false);
    setError("");
    setTab("overview");
  }
  async function enter() {
    if (!student) return;
    setBusy(true);
    setError("");
    try {
      await post("/mode/child", { student_id: student.id });
      announceSessionChange();
      router.replace("/learn");
    } catch (e) {
      setError(e instanceof Error ? e.message : "进入失败");
    } finally {
      setBusy(false);
    }
  }
  async function archive() {
    if (!student) return;
    setBusy(true);
    setError("");
    try {
      await api(`/students/${student.id}/archive`, {
        method: "POST",
        headers: { "If-Match": String(student.revision) },
      });
      setSelected("");
      setArchiving(false);
      setTab("home");
      refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "归档失败");
    } finally {
      setBusy(false);
    }
  }
  async function saveNickname(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    const nickname = new FormData(event.currentTarget).get("nickname");
    try {
      await api("/me", { method: "PATCH", body: JSON.stringify({ nickname }) });
      setError("昵称已保存，重新打开页面可查看最新资料。");
    } catch (e) {
      setError(e instanceof Error ? e.message : "保存失败");
    } finally {
      setBusy(false);
    }
  }
  return (
    <main>
      <h1>{account.family?.name ?? "家庭首页"}</h1>
      <p>照顾每个孩子的节奏，从自己的档案和教材开始。</p>
      <nav className="account-tabs" aria-label="家庭导航">
        <button
          className="secondary"
          aria-pressed={tab === "home"}
          onClick={() => {
            setTab("home");
            setCreating(false);
          }}
        >
          家庭首页
        </button>
        <button
          className="secondary"
          aria-pressed={tab === "settings"}
          onClick={() => setTab("settings")}
        >
          家庭设置
        </button>
      </nav>
      <Message text={error} />
      {tab === "settings" ? (
        <section className="account-card">
          <h2>家庭设置</h2>
          <p>
            家庭：{account.family?.name} · 时区：{account.family?.timezone}
          </p>
          <p className="account-hint">
            登录账号：{account.user?.login_name}
            。登录账号的开通、停用和密码重置请联系管理员。
          </p>
          <form onSubmit={saveNickname}>
            <Field label="家长昵称">
              <input
                name="nickname"
                defaultValue={account.user?.nickname}
                required
                maxLength={80}
              />
            </Field>
            <button disabled={busy}>保存昵称</button>
          </form>
        </section>
      ) : (
        <>
          <section className="account-card">
            <div className="account-toolbar">
              <h2>孩子档案</h2>
              <button
                onClick={() => {
                  setCreating(true);
                  setEditing(false);
                  setTab("home");
                }}
              >
                添加孩子档案
              </button>
            </div>
            <label className="account-actions">
              <input
                type="checkbox"
                checked={archived}
                onChange={(e) => {
                  setArchived(e.target.checked);
                  setSelected("");
                  setTab("home");
                }}
              />
              显示已归档档案
            </label>
            <div className="account-list">
              {students.map((s) => (
                <article className="account-row" key={s.id}>
                  <div>
                    <strong>
                      {avatars[s.avatar]} {s.nickname}
                    </strong>
                    <small>
                      {s.grade} 年级 · 每日目标 {s.daily_goal_minutes} 分钟
                      {s.archived_at ? " · 已归档" : ""}
                    </small>
                  </div>
                  <button className="secondary" onClick={() => pick(s.id)}>
                    {s.id === selected ? "当前孩子" : "查看档案"}
                  </button>
                </article>
              ))}
              {!students.length ? (
                <p>还没有孩子档案，可以先添加一个。</p>
              ) : null}
            </div>
          </section>
          {creating ? (
            <StudentForm
              onCancel={() => setCreating(false)}
              onSave={(s) => {
                setCreating(false);
                refresh();
                pick(s.id);
              }}
            />
          ) : null}
          {student ? (
            <>
              <nav className="account-tabs" aria-label="孩子档案导航">
                <button
                  className="secondary"
                  aria-pressed={tab === "overview"}
                  onClick={() => {
                    setTab("overview");
                    setEditing(false);
                  }}
                >
                  学习总览
                </button>
                <button
                  className="secondary"
                  aria-pressed={tab === "curriculum"}
                  onClick={() => {
                    setTab("curriculum");
                    setEditing(false);
                  }}
                >
                  教材配置
                </button>
                <button
                  className="secondary"
                  aria-pressed={editing}
                  disabled={!!student.archived_at}
                  onClick={() => setEditing(true)}
                >
                  编辑档案
                </button>
              </nav>
              {editing ? (
                <StudentForm
                  key={student.id + ":" + student.revision}
                  student={student}
                  onCancel={() => setEditing(false)}
                  onSave={() => {
                    setEditing(false);
                    refresh();
                  }}
                />
              ) : tab === "curriculum" ? (
                <CurriculumForm
                  key={student.id}
                  student={student}
                  onSave={refresh}
                />
              ) : (
                <section className="account-card">
                  <h2>
                    {avatars[student.avatar]} {student.nickname}的学习总览
                  </h2>
                  <p>
                    当前 {student.grade} 年级 · 每日目标{" "}
                    {student.daily_goal_minutes} 分钟
                  </p>
                  <p className="account-hint">
                    云端学习记录与课程入口正在接入，进度、最近学习和用时将在记录服务接入后显示。现有本地成绩尚未导入。
                  </p>
                  <div className="account-actions">
                    <button
                      disabled={busy || !!student.archived_at}
                      onClick={enter}
                    >
                      进入孩子模式
                    </button>
                    <button
                      className="secondary"
                      onClick={() => setTab("curriculum")}
                    >
                      配置教材
                    </button>
                    <button
                      className="secondary"
                      disabled={!!student.archived_at}
                      onClick={() => setArchiving(true)}
                    >
                      归档档案
                    </button>
                  </div>
                  {archiving ? (
                    <div className="account-message">
                      <p>
                        归档 {student.nickname}{" "}
                        后将停止其学习访问，资料与历史保留。
                      </p>
                      <div className="account-actions">
                        <button
                          className="danger"
                          disabled={busy}
                          onClick={archive}
                        >
                          确认归档
                        </button>
                        <button
                          className="secondary"
                          onClick={() => setArchiving(false)}
                        >
                          取消
                        </button>
                      </div>
                    </div>
                  ) : null}
                </section>
              )}
            </>
          ) : null}
        </>
      )}
    </main>
  );
}
