"use client";
import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import {
  AccountFrame,
  Field,
  Message,
} from "@/components/account/AccountShell";
import { announceSessionChange, post, type Account } from "@/lib/api/client";

export default function LoginPage() {
  const router = useRouter();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    const form = event.currentTarget;
    const data = new FormData(form);
    try {
      const account = await post<Account>("/auth/login", {
        login: data.get("login"),
        password: data.get("password"),
      });
      form.reset();
      announceSessionChange();
      router.replace(account.destination);
    } catch (e) {
      setError(e instanceof Error ? e.message : "登录失败");
    } finally {
      setBusy(false);
    }
  }
  return (
    <AccountFrame>
      <main className="account-card account-auth">
        <h1>欢迎回到聪聪学堂</h1>
        <p>登录后，继续你的家庭学习旅程。</p>
        <form onSubmit={submit}>
          <Field label="账号">
            <input
              name="login"
              autoComplete="username"
              required
              maxLength={320}
              autoCapitalize="none"
              spellCheck={false}
            />
          </Field>
          <Field label="密码">
            <input
              name="password"
              type="password"
              autoComplete="current-password"
              required
              maxLength={128}
            />
          </Field>
          <Message text={error} />
          <button disabled={busy}>{busy ? "正在登录…" : "登录"}</button>
        </form>
        <p className="account-hint">
          账号由管理员创建。如需开通账号或重置密码，请联系管理员。
        </p>
      </main>
    </AccountFrame>
  );
}
