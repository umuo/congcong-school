"use client";
import {
  useCallback,
  useEffect,
  useRef,
  useState,
  useId,
  cloneElement,
  isValidElement,
  type ReactElement,
  type FormEvent,
  type ReactNode,
} from "react";
import { useRouter } from "next/navigation";
import {
  api,
  post,
  announceSessionChange,
  APIError,
  type Account,
} from "@/lib/api/client";
import "./account.css";

export function Field({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  const id = useId();
  return (
    <div className="account-field">
      <label htmlFor={id} id={`${id}-label`}>
        {label}
      </label>
      {isValidElement(children)
        ? cloneElement(
            children as ReactElement<{
              id?: string;
              "aria-labelledby"?: string;
            }>,
            { id, "aria-labelledby": `${id}-label` },
          )
        : children}
    </div>
  );
}
export function Message({ text }: { text: string }) {
  return text ? (
    <p className="account-message" role="status">
      {text}
    </p>
  ) : null;
}
export function AccountFrame({ children }: { children: ReactNode }) {
  return (
    <div className="account-root">
      <header className="account-brand">
        <span aria-hidden>🌱</span>
        <span>
          聪聪学堂<small>家庭成长与学习</small>
        </span>
      </header>
      {children}
      <footer>让每个孩子，按照自己的节奏成长。</footer>
    </div>
  );
}

export function AccountGuard({
  destination,
  children,
}: {
  destination: string;
  children: (account: Account) => ReactNode;
}) {
  const router = useRouter();
  const [account, setAccount] = useState<Account | null>(null);
  const [error, setError] = useState("");
  const [verify, setVerify] = useState(false);
  const [busy, setBusy] = useState(false);
  const request = useRef<AbortController | null>(null);
  const load = useCallback(async () => {
    request.current?.abort();
    const controller = new AbortController();
    request.current = controller;
    try {
      const value = await api<Account>("/auth/session", {
        signal: controller.signal,
      });
      if (value.destination !== destination) {
        setAccount(null);
        router.replace(value.destination);
      } else {
        setAccount(value);
        setError("");
      }
    } catch (e) {
      if (controller.signal.aborted) return;
      setAccount(null);
      setError(e instanceof Error ? e.message : "请重新登录");
      if (e instanceof APIError && e.status === 401) router.replace("/login");
    }
  }, [destination, router]);
  useEffect(() => {
    void load();
    const channel = new BroadcastChannel("csf-session");
    const refresh = () => {
      setAccount(null);
      void load();
    };
    const reauth = () => {
      setAccount(null);
      setVerify(true);
    };
    channel.onmessage = refresh;
    window.addEventListener("csf-session-invalid", refresh);
    window.addEventListener("csf-reauth-required", reauth);
    const focus = () => {
      if (document.visibilityState === "visible") void load();
    };
    window.addEventListener("focus", focus);
    document.addEventListener("visibilitychange", focus);
    const interval = window.setInterval(() => void load(), 30000);
    return () => {
      request.current?.abort();
      channel.close();
      window.clearInterval(interval);
      window.removeEventListener("focus", focus);
      document.removeEventListener("visibilitychange", focus);
      window.removeEventListener("csf-session-invalid", refresh);
      window.removeEventListener("csf-reauth-required", reauth);
    };
  }, [load]);
  async function verifyPassword(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    const password = String(new FormData(event.currentTarget).get("password"));
    event.currentTarget.reset();
    try {
      await post("/auth/reauth", { password });
      setVerify(false);
      announceSessionChange();
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "验证失败");
    } finally {
      setBusy(false);
    }
  }
  async function logout() {
    try {
      await post("/auth/logout");
    } catch (e) {
      setError(e instanceof Error ? e.message : "退出失败，请重试");
      return;
    }
    setAccount(null);
    announceSessionChange();
    router.replace("/login");
  }
  return (
    <AccountFrame>
      {verify ? (
        <main className="account-card account-auth">
          <h1>再次验证身份</h1>
          <p>为保护家庭资料，请重新输入账号密码。</p>
          <form onSubmit={verifyPassword}>
            <Field label="账号密码">
              <input
                name="password"
                type="password"
                autoComplete="current-password"
                required
                maxLength={128}
              />
            </Field>
            <Message text={error} />
            <button disabled={busy}>验证并继续</button>
          </form>
          <a href="/login/">切换账号</a>
        </main>
      ) : account ? (
        <>
          <div className="account-toolbar">
            <span>
              {account.user?.nickname ?? "孩子学习模式"} ·{" "}
              {account.mode === "admin"
                ? "管理员"
                : account.mode === "parent"
                  ? "家长"
                  : "学习"}
            </span>
            <button className="secondary" onClick={logout}>
              退出登录
            </button>
          </div>
          <div
            key={`${account.context_id}:${account.role}:${account.user?.id}:${account.family?.id}:${account.student_id}`}
          >
            {children(account)}
          </div>
        </>
      ) : (
        <main className="account-card account-auth">
          <h1>{error ? "请重新连接" : "正在确认登录状态…"}</h1>
          <Message text={error} />
          {error ? (
            <>
              <button onClick={() => void load()}>重试</button>
              <a href="/login/">前往登录</a>
            </>
          ) : null}
        </main>
      )}
    </AccountFrame>
  );
}
