"use client";
import {
  useCallback,
  createContext,
  useContext,
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
import "../learning/forest.css";
import "../avatars/avatars.css";
import "./account.css";
import { bindPreferences } from "@/lib/learning/preferences";
import { stopTTS } from "@/lib/tts";
import { clickFeedback } from "@/lib/learning/interaction-feedback";
import { primeAudioOnFirstGesture, stopEffects } from "@/lib/sfx";
import { ChildShell } from "../learning/ChildShell";
import { AvatarEditor } from "@/components/avatars/AvatarEditor";
import { invalidateLearning } from "@/lib/learning/lifecycle";
import { LearningProvider } from "@/components/learning/LearningProvider";

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

export type ToastTone = "info" | "success" | "error";

export function FloatingToast({
  message,
  tone = "info",
  duration = 4000,
  onDismiss,
  children,
}: {
  message: string;
  tone?: ToastTone;
  duration?: number;
  onDismiss?: () => void;
  children?: ReactNode;
}) {
  const [visible, setVisible] = useState(Boolean(message));
  useEffect(() => {
    setVisible(Boolean(message));
    if (!message || !duration) return;
    const timer = window.setTimeout(() => {
      setVisible(false);
      onDismiss?.();
    }, duration);
    return () => window.clearTimeout(timer);
  }, [message, duration, onDismiss]);

  if (!message || !visible) return null;
  return (
    <aside
      className={`account-floating-toast is-${tone}`}
      aria-label="操作提示"
    >
      <div
        role={tone === "error" ? "alert" : "status"}
        aria-live="polite"
        aria-atomic="true"
        className="account-floating-toast-text"
      >
        {message}
      </div>
      {children ? <div className="account-floating-toast-actions">{children}</div> : null}
      <button
        type="button"
        className="account-toast-close"
        aria-label="关闭提示"
        onClick={() => {
          setVisible(false);
          onDismiss?.();
        }}
      >
        ×
      </button>
    </aside>
  );
}

export function InfoPopover({
  label = "说明",
  title,
  children,
  defaultOpen = false,
}: {
  label?: string;
  title?: string;
  children: ReactNode;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  const containerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!open || typeof document === "undefined") return;
    const handleKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    const handlePointer = (event: MouseEvent) => {
      if (
        containerRef.current &&
        event.target instanceof Node &&
        !containerRef.current.contains(event.target)
      ) {
        setOpen(false);
      }
    };
    document.addEventListener("keydown", handleKey);
    document.addEventListener("mousedown", handlePointer);
    return () => {
      document.removeEventListener("keydown", handleKey);
      document.removeEventListener("mousedown", handlePointer);
    };
  }, [open]);

  return (
    <div className="account-info-popover" ref={containerRef}>
      <button
        type="button"
        className={`account-info-trigger${open ? " is-open" : ""}`}
        aria-expanded={open}
        aria-haspopup="dialog"
        onClick={() => setOpen((prev) => !prev)}
      >
        <span className="account-info-icon" aria-hidden="true">
          ?
        </span>
        <span>{label}</span>
      </button>
      {open ? (
        <div
          className="account-popover-card"
          role="dialog"
          aria-label={title || label}
        >
          <div className="account-popover-head">
            <strong>{title || label}</strong>
            <button
              type="button"
              className="account-popover-close"
              aria-label="关闭说明"
              onClick={() => setOpen(false)}
            >
              ×
            </button>
          </div>
          <div className="account-popover-body">{children}</div>
        </div>
      ) : null}
    </div>
  );
}

export function ModalDialog({
  open,
  title,
  subtitle,
  onClose,
  size = "md",
  children,
}: {
  open: boolean;
  title: string;
  subtitle?: string;
  onClose: () => void;
  size?: "sm" | "md" | "lg";
  children: ReactNode;
}) {
  useEffect(() => {
    if (!open || typeof document === "undefined") return;
    const handleKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [open, onClose]);

  if (!open) return null;
  return (
    <div
      className="account-modal-backdrop"
      onClick={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div
        className={`account-modal-card is-${size}`}
        role="dialog"
        aria-modal="true"
        aria-label={title}
      >
        <header className="account-modal-head">
          <div>
            <h2>{title}</h2>
            {subtitle ? (
              <p className="account-modal-subtitle">{subtitle}</p>
            ) : null}
          </div>
          <button
            type="button"
            className="account-modal-close"
            aria-label="关闭弹窗"
            onClick={onClose}
          >
            ×
          </button>
        </header>
        <div className="account-modal-body">{children}</div>
      </div>
    </div>
  );
}
export function AccountFrame({ children }: { children: ReactNode }) {
  const frameId = useId();
  useEffect(() => primeAudioOnFirstGesture(), []);
  return (
    <div className="account-root" data-account-frame={frameId} onClick={event => {
      if (event.target instanceof Element) clickFeedback(event.nativeEvent,event.target,document.visibilityState === "hidden");
    }}>
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

const VerifiedAccountContext = createContext<Account | null>(null);
type AccountGuardProps = { destination: string; children: (account: Account) => ReactNode };

/** A page inside the persistent shell consumes its already-verified identity. */
export function AccountGuard(props: AccountGuardProps) {
  const inherited = useContext(VerifiedAccountContext);
  return inherited ? <InheritedAccountGuard {...props} account={inherited} /> : <AccountSessionGuard {...props} />;
}

function InheritedAccountGuard({ account, destination, children }: AccountGuardProps & { account: Account }) {
  const router = useRouter();
  useEffect(() => {
    if (account.destination !== destination) router.replace(account.destination);
  }, [account.destination, destination, router]);
  return account.destination === destination ? children(account) : <p role="status">正在前往你的账号页面…</p>;
}

function AccountSessionGuard({
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
  const context = useRef<string | null>(null);
  const load = useCallback(async () => {
    request.current?.abort();
    const controller = new AbortController();
    request.current = controller;
    try {
      const value = await api<Account>("/auth/session", {
        signal: controller.signal,
      });
      if (controller.signal.aborted) return;
      if (context.current && context.current !== value.context_id) invalidateLearning();
      context.current = value.context_id;
      if (value.destination !== destination) {
        setAccount(null);
        router.replace(value.destination);
      } else {
        setAccount(value);
        setError("");
      }
    } catch (e) {
      if (controller.signal.aborted) return;
      // 网络/5xx 只阻断展示并卸载实例；同身份待提交字节仍需原键恢复。
      // 已确认失效的身份才撤销队列，不能把离线误当作退出。
      if (e instanceof APIError && e.status < 500) invalidateLearning();
      setAccount(null);
      setError(e instanceof Error ? e.message : "请重新登录");
      if (e instanceof APIError && e.status === 401) router.replace("/login");
    }
  }, [destination, router]);
  useEffect(() => {
    void load();
    const channel = new BroadcastChannel("csf-session");
    const refresh = () => {
      invalidateLearning();
      setAccount(null);
      void load();
    };
    const reauth = () => {
      invalidateLearning();
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
  useEffect(() => {
    stopTTS(); stopEffects();
    let storage: Storage | undefined;
    try { storage = window.localStorage; } catch { /* in-memory preferences */ }
    const subject = account?.mode === "child" ? `student:${account.student_id}` : account?.user?.id ? `user:${account.user.id}` : "anonymous";
    bindPreferences(subject, storage);
    return () => { stopTTS(); stopEffects(); };
  }, [account?.mode, account?.student_id, account?.user?.id]);
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
    invalidateLearning();
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
      ) : account && account.destination === destination ? (
        <VerifiedAccountContext.Provider value={account}>
          {account.mode !== "child" ? <div className="account-toolbar">
            <AvatarEditor key={account.context_id} account={account} label="我的头像" />
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
          </div> : null}
          <div
            key={`${account.context_id}:${account.role}:${account.user?.id}:${account.family?.id}:${account.student_id}`}
          >
            {account.mode === "child" ? (
              <LearningProvider account={account}><ChildShell account={account} onLogout={logout}>{children(account)}</ChildShell></LearningProvider>
            ) : children(account)}
          </div>
        </VerifiedAccountContext.Provider>
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
