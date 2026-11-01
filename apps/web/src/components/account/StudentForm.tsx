"use client";
import { useState, type FormEvent } from "react";
import { api } from "@/lib/api/client";
import { Field, Message } from "./AccountShell";

export interface Student {
  id: string;
  nickname: string;
  avatar: string;
  birth_month: string | null;
  province: string | null;
  city: string | null;
  school: string | null;
  school_stage: string;
  grade: number;
  school_year: string | null;
  semester: string;
  daily_goal_minutes: number;
  parent_notes: string | null;
  archived_at: string | null;
  revision: number;
}
export function StudentForm({
  student,
  onSave,
  onCancel,
}: {
  student?: Student;
  onSave: (s: Student) => void;
  onCancel: () => void;
}) {
  const [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    const data = new FormData(event.currentTarget),
      body: Record<string, unknown> = {};
    for (const [key, value] of data.entries())
      body[key] = value === "" ? null : value;
    body.grade = Number(data.get("grade"));
    body.daily_goal_minutes = Number(data.get("daily_goal_minutes"));
    try {
      const value = await api<Student>(
        student ? `/students/${student.id}` : "/students",
        {
          method: student ? "PATCH" : "POST",
          body: JSON.stringify(body),
          headers: student ? { "If-Match": String(student.revision) } : {},
        },
      );
      onSave(value);
    } catch (e) {
      setError(e instanceof Error ? e.message : "保存失败");
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="account-card">
      <h2>{student ? `编辑${student.nickname}的档案` : "添加孩子档案"}</h2>
      <p className="account-hint">
        出生年月、学校和备注均为选填。开通独立登录账号请联系管理员。
      </p>
      <form onSubmit={submit}>
        <div className="account-grid">
          <Field label="昵称">
            <input
              name="nickname"
              defaultValue={student?.nickname}
              required
              maxLength={80}
            />
          </Field>
          <Field label="头像">
            <select name="avatar" defaultValue={student?.avatar ?? "panda"}>
              <option value="panda">🐼 熊猫</option>
              <option value="fox">🦊 狐狸</option>
              <option value="rabbit">🐰 兔子</option>
              <option value="bear">🐻 小熊</option>
            </select>
          </Field>
          <Field label="出生年月（选填）">
            <input
              name="birth_month"
              type="month"
              defaultValue={student?.birth_month ?? ""}
            />
          </Field>
          <Field label="学段">
            <select
              name="school_stage"
              defaultValue={student?.school_stage ?? "primary"}
            >
              <option value="primary">小学</option>
              <option value="junior">初中</option>
              <option value="senior">高中</option>
            </select>
          </Field>
          <Field label="年级">
            <select name="grade" defaultValue={student?.grade ?? 1}>
              {Array.from({ length: 12 }, (_, i) => (
                <option value={i + 1} key={i}>
                  {i + 1} 年级
                </option>
              ))}
            </select>
          </Field>
          <Field label="学期">
            <select name="semester" defaultValue={student?.semester ?? "up"}>
              <option value="up">上学期</option>
              <option value="down">下学期</option>
            </select>
          </Field>
          <Field label="学年（例如 2026-2027，选填）">
            <input
              name="school_year"
              defaultValue={student?.school_year ?? ""}
              pattern="[0-9]{4}-[0-9]{4}"
              placeholder="2026-2027"
            />
          </Field>
          <Field label="每日学习目标（分钟）">
            <input
              name="daily_goal_minutes"
              type="number"
              min={1}
              max={240}
              defaultValue={student?.daily_goal_minutes ?? 20}
              required
            />
          </Field>
          <Field label="省份（选填）">
            <input
              name="province"
              maxLength={80}
              defaultValue={student?.province ?? ""}
            />
          </Field>
          <Field label="城市（选填）">
            <input
              name="city"
              maxLength={80}
              defaultValue={student?.city ?? ""}
            />
          </Field>
          <Field label="学校（选填）">
            <input
              name="school"
              maxLength={120}
              defaultValue={student?.school ?? ""}
            />
          </Field>
        </div>
        <Field label="家长备注（选填，仅管理端可见）">
          <textarea
            name="parent_notes"
            maxLength={2000}
            defaultValue={student?.parent_notes ?? ""}
          />
        </Field>
        <Message text={error} />
        <div className="account-actions">
          <button disabled={busy}>保存档案</button>
          <button type="button" className="secondary" onClick={onCancel}>
            取消
          </button>
        </div>
      </form>
    </section>
  );
}
