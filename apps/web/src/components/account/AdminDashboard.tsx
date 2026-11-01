"use client";
import { useEffect, useState, type FormEvent } from "react";
import { api, post } from "@/lib/api/client";
import { Field, Message } from "./AccountShell";
import { PasswordFields } from "./PasswordFields";
import { LoginNameField } from "./LoginNameField";

type ManagedUser = {
  id: string;
  login_name: string;
  nickname: string;
  family_id: string;
  student_id: string | null;
  is_active: boolean;
  must_change_password: boolean;
};
type Family = { id: string; name: string };
type Profile = { id: string; nickname: string; archived: boolean };

export function AdminDashboard() {
  const [kind, setKind] = useState<"parents" | "students">("parents");
  const [users, setUsers] = useState<ManagedUser[]>([]);
  const [families, setFamilies] = useState<Family[]>([]);
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [family, setFamily] = useState("");
  const [student, setStudent] = useState("");
  const [newFamily, setNewFamily] = useState(true);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [version, setVersion] = useState(0);
  const [action, setAction] = useState<{
    user: ManagedUser;
    type: "disable" | "reset-password";
  } | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    setUsers([]);
    void Promise.all([
      api<ManagedUser[]>(`/admin/${kind}`, { signal: controller.signal }),
      api<Family[]>("/admin/families", { signal: controller.signal }),
    ])
      .then(([u, f]) => {
        setUsers(u);
        setFamilies(f);
      })
      .catch((e) => {
        if (!controller.signal.aborted) setError(e.message);
      });
    return () => controller.abort();
  }, [kind, version]);
  useEffect(() => {
    const controller = new AbortController();
    setProfiles([]);
    setStudent("");
    if (family && kind === "students")
      void api<Profile[]>(
        `/admin/student-profiles?family_id=${encodeURIComponent(family)}`,
        { signal: controller.signal },
      )
        .then(setProfiles)
        .catch((e) => {
          if (!controller.signal.aborted) setError(e.message);
        });
    return () => controller.abort();
  }, [family, kind]);
  function switchKind(value: "parents" | "students") {
    setError("");
    setKind(value);
    setAction(null);
    setFamily("");
    setNewFamily(value === "parents");
  }
  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    const form = event.currentTarget,
      data = new FormData(form);
    if (data.get("password") !== data.get("confirmation")) {
      setError("两次输入的密码不一致");
      setBusy(false);
      return;
    }
    const payload: Record<string, unknown> = {
      login_name: data.get("login_name"),
      password: data.get("password"),
      nickname: data.get("nickname"),
    };
    if (kind === "parents") {
      if (newFamily) payload.family_name = data.get("family_name");
      else payload.family_id = family;
    } else {
      payload.family_id = family;
      if (student) payload.student_id = student;
      else
        payload.profile = {
          nickname: data.get("nickname"),
          grade: Number(data.get("grade")),
        };
    }
    try {
      await post(`/admin/${kind}`, payload);
      form.reset();
      setVersion((v) => v + 1);
      setError("账号已创建。请将初始密码交给本人，可直接登录使用。");
    } catch (e) {
      setError(e instanceof Error ? e.message : "创建失败");
    } finally {
      setBusy(false);
    }
  }
  async function confirm(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!action) return;
    setBusy(true);
    setError("");
    const form = event.currentTarget,
      password = new FormData(form).get("password");
    if (
      action.type === "reset-password" &&
      password !== new FormData(form).get("confirmation")
    ) {
      setError("两次输入的密码不一致");
      setBusy(false);
      return;
    }
    try {
      await post(
        `/admin/users/${action.user.id}/${action.type}`,
        action.type === "reset-password" ? { password } : undefined,
      );
      form.reset();
      setAction(null);
      setVersion((v) => v + 1);
    } catch (e) {
      setError(e instanceof Error ? e.message : "操作失败");
    } finally {
      setBusy(false);
    }
  }
  return (
    <main>
      <h1>账号管理</h1>
      <p>为家庭开通账号，孩子的学习记录始终保存在各自档案中。</p>
      <nav aria-label="账号类型" className="account-tabs">
        <button
          aria-pressed={kind === "parents"}
          className="secondary"
          onClick={() => switchKind("parents")}
        >
          家长账号
        </button>
        <button
          aria-pressed={kind === "students"}
          className="secondary"
          onClick={() => switchKind("students")}
        >
          学生账号
        </button>
      </nav>
      <Message text={error} />
      <div className="account-grid">
        <section className="account-card">
          <h2>创建{kind === "parents" ? "家长" : "学生"}账号</h2>
          <form key={kind} onSubmit={create}>
            <LoginNameField />
            <Field label="昵称">
              <input name="nickname" maxLength={80} required />
            </Field>
            <PasswordFields />
            {kind === "parents" ? (
              <Field label="家庭归属">
                <select
                  value={newFamily ? "new" : "existing"}
                  onChange={(e) => setNewFamily(e.target.value === "new")}
                >
                  <option value="new">创建新家庭</option>
                  <option value="existing">关联已有家庭</option>
                </select>
              </Field>
            ) : null}
            {kind === "parents" && newFamily ? (
              <Field label="新家庭名称">
                <input name="family_name" maxLength={80} required />
              </Field>
            ) : (
              <Field label="所属家庭">
                <select
                  value={family}
                  onChange={(e) => setFamily(e.target.value)}
                  required
                >
                  <option value="">请选择家庭</option>
                  {families.map((f) => (
                    <option key={f.id} value={f.id}>
                      {f.name}
                    </option>
                  ))}
                </select>
              </Field>
            )}
            {kind === "students" ? (
              <>
                <Field label="学生档案">
                  <select
                    value={student}
                    onChange={(e) => setStudent(e.target.value)}
                  >
                    <option value="">新建学生档案</option>
                    {profiles
                      .filter((p) => !p.archived)
                      .map((p) => (
                        <option key={p.id} value={p.id}>
                          {p.nickname}
                        </option>
                      ))}
                  </select>
                </Field>
                {!student ? (
                  <Field label="年级">
                    <select name="grade" defaultValue="1">
                      {Array.from({ length: 12 }, (_, i) => (
                        <option value={i + 1} key={i}>
                          {i + 1} 年级
                        </option>
                      ))}
                    </select>
                  </Field>
                ) : (
                  <p className="account-hint">
                    关联已有档案会保留原教材及学习记录。
                  </p>
                )}
              </>
            ) : null}
            <button disabled={busy}>创建账号</button>
          </form>
        </section>
        <section className="account-card">
          <h2>{kind === "parents" ? "家长" : "学生"}账号列表</h2>
          <div className="account-list">
            {users.length ? (
              users.map((u) => (
                <article key={u.id} className="account-row">
                  <div>
                    <strong>{u.nickname}</strong>
                    <small>{u.login_name}</small>
                    <small>
                      {families.find((f) => f.id === u.family_id)?.name} ·{" "}
                      {!u.is_active
                        ? "已停用"
                        : u.must_change_password
                          ? "待修改初始密码"
                          : "使用中"}
                    </small>
                  </div>
                  <div className="account-actions">
                    <button
                      className="secondary"
                      disabled={busy || !u.is_active}
                      onClick={() =>
                        setAction({ user: u, type: "reset-password" })
                      }
                    >
                      重置密码
                    </button>
                    <button
                      className="secondary"
                      disabled={busy || !u.is_active}
                      onClick={() => setAction({ user: u, type: "disable" })}
                    >
                      停用
                    </button>
                  </div>
                </article>
              ))
            ) : (
              <p>暂无账号，可在左侧创建。</p>
            )}
          </div>
        </section>
      </div>
      {action ? (
        <section
          className="account-card"
          aria-labelledby="account-confirm-title"
        >
          <h2 id="account-confirm-title">
            {action.type === "disable" ? "确认停用" : "重置密码"}：
            {action.user.nickname}
          </h2>
          <p>
            {action.type === "disable"
              ? "停用后此账号的所有设备都会退出，学习记录保留。"
              : "重置后所有设备都会退出，本人可直接使用新密码登录。"}
          </p>
          <form key={`${action.user.id}:${action.type}`} onSubmit={confirm}>
            {action.type === "reset-password" ? (
              <PasswordFields
                label="新密码（至少 12 个字符）"
                confirmationLabel="确认新密码"
              />
            ) : null}
            <div className="account-actions">
              <button
                className={action.type === "disable" ? "danger" : ""}
                disabled={busy}
              >
                确认{action.type === "disable" ? "停用" : "重置"}
              </button>
              <button
                type="button"
                className="secondary"
                onClick={() => setAction(null)}
              >
                取消
              </button>
            </div>
          </form>
        </section>
      ) : null}
    </main>
  );
}
