"use client";
import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import {
  AccountGuard,
  Field,
  Message,
} from "@/components/account/AccountShell";
import { PasswordFields } from "@/components/account/PasswordFields";
import { post, announceSessionChange, type Account } from "@/lib/api/client";

function PasswordForm() {
  const router = useRouter();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    const form = event.currentTarget,
      data = new FormData(form);
    if (data.get("new_password") !== data.get("confirmation")) {
      setError("两次新密码不一致");
      return;
    }
    setBusy(true);
    try {
      const account = await post<Account>("/auth/change-password", {
        password: data.get("password"),
        new_password: data.get("new_password"),
      });
      form.reset();
      announceSessionChange();
      router.replace(account.destination);
    } catch (e) {
      setError(e instanceof Error ? e.message : "修改失败");
    } finally {
      setBusy(false);
    }
  }
  return (
    <main className="account-card account-auth">
      <h1>设置你的新密码</h1>
      <p>管理员首次登录请先修改初始密码。</p>
      <form onSubmit={submit}>
        <Field label="初始密码">
          <input
            name="password"
            type="password"
            autoComplete="current-password"
            required
            maxLength={128}
          />
        </Field>
        <PasswordFields
          name="new_password"
          label="新密码（12–128 个字符）"
          confirmationLabel="确认新密码"
        />
        <Message text={error} />
        <button disabled={busy}>保存新密码</button>
      </form>
    </main>
  );
}
export default function ChangePasswordPage() {
  return (
    <AccountGuard destination="/change-password">
      {() => <PasswordForm />}
    </AccountGuard>
  );
}
