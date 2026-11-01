"use client";
import { useEffect, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import {
  AccountGuard,
  Field,
  Message,
} from "@/components/account/AccountShell";
import {
  api,
  post,
  announceSessionChange,
  type Account,
} from "@/lib/api/client";
function LearningHome({ account }: { account: Account }) {
  const router = useRouter(),
    [profile, setProfile] = useState<{
      nickname: string;
      grade: number;
    } | null>(null),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
    void api<{ nickname: string; grade: number }>("/learning/profile", {
      signal: controller.signal,
    })
      .then(setProfile)
      .catch((e) => {
        if (!controller.signal.aborted) setError(e.message);
      });
    return () => controller.abort();
  }, [account.student_id]);
  async function restore(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    const form = event.currentTarget,
      password = new FormData(form).get("password");
    form.reset();
    try {
      const next = await post<Account>("/mode/parent", { password });
      announceSessionChange();
      router.replace(next.destination);
    } catch (e) {
      setError(e instanceof Error ? e.message : "验证失败");
    } finally {
      setBusy(false);
    }
  }
  return (
    <main className="account-card">
      <h1>{profile ? `${profile.nickname}，你好！` : "你的学习空间"}</h1>
      {profile ? <p>{profile.grade} 年级 · 当前仅访问你的档案</p> : null}
      <Message text={error} />
      <p className="account-hint">
        云端课程和学习记录正在接入。目前可以登录及管理教材，学习入口将在接入完成后开放。
      </p>
      {account.role === "parent" ? (
        <details>
          <summary>返回家长端</summary>
          <p>共享此登录的标签页也处于孩子模式，返回需要家长密码。</p>
          <form onSubmit={restore}>
            <Field label="家长密码">
              <input
                type="password"
                name="password"
                autoComplete="current-password"
                required
                maxLength={128}
              />
            </Field>
            <button disabled={busy}>验证并返回</button>
          </form>
        </details>
      ) : (
        <p>需要家长帮助时，请退出后由家长账号登录。</p>
      )}
    </main>
  );
}
export default function LearnPage() {
  return (
    <AccountGuard destination="/learn">
      {(account) => <LearningHome account={account} />}
    </AccountGuard>
  );
}
