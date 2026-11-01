"use client";
import { useEffect, useId, useRef, useState } from "react";
import { api } from "@/lib/api/client";
import { Field } from "./AccountShell";

type Check = {
  kind: "empty" | "checking" | "available" | "taken" | "invalid" | "error";
  message: string;
};

export function LoginNameField() {
  const [value, setValue] = useState("");
  const [retry, setRetry] = useState(0);
  const generation = useRef(0);
  const [check, setCheck] = useState<Check>({ kind: "empty", message: "" });
  const input = useRef<HTMLInputElement>(null),
    hintId = useId();
  useEffect(() => {
    const controller = new AbortController(),
      normalized = value.trim();
    const currentGeneration = generation.current;
    if (!normalized) {
      setCheck({ kind: "empty", message: "" });
      input.current?.setCustomValidity("");
      return;
    }
    if (normalized.length < 3 || !/^[\p{L}\p{N}._@+-]+$/u.test(normalized)) {
      const message = "账号至少 3 个字符，只能包含字母、数字和 . _ @ + -";
      setCheck({ kind: "invalid", message });
      input.current?.setCustomValidity(message);
      return;
    }
    setCheck({ kind: "checking", message: "正在检查账号是否重复…" });
    input.current?.setCustomValidity("请等待账号检查完成");
    const timer = window.setTimeout(async () => {
      try {
        const result = await api<{ available: boolean }>(
          `/admin/login-availability?login_name=${encodeURIComponent(normalized)}`,
          { signal: controller.signal },
        );
        if (
          controller.signal.aborted ||
          currentGeneration !== generation.current
        )
          return;
        const message = result.available
          ? "该账号可以使用"
          : "该账号已存在，请换一个账号";
        setCheck({ kind: result.available ? "available" : "taken", message });
        input.current?.setCustomValidity(result.available ? "" : message);
      } catch (e) {
        if (
          controller.signal.aborted ||
          currentGeneration !== generation.current
        )
          return;
        const message = e instanceof Error ? e.message : "无法检查账号，请重试";
        setCheck({ kind: "error", message });
        input.current?.setCustomValidity(message);
      }
    }, 400);
    return () => {
      controller.abort();
      window.clearTimeout(timer);
    };
  }, [value, retry]);
  useEffect(() => {
    const form = input.current?.form;
    const reset = () => {
      generation.current += 1;
      setValue("");
      setCheck({ kind: "empty", message: "" });
      input.current?.setCustomValidity("");
    };
    form?.addEventListener("reset", reset);
    return () => form?.removeEventListener("reset", reset);
  }, []);
  return (
    <>
      <Field label="登录账号">
        <input
          ref={input}
          name="login_name"
          autoComplete="off"
          autoCapitalize="none"
          spellCheck={false}
          minLength={3}
          maxLength={320}
          required
          value={value}
          onChange={(e) => {
            generation.current += 1;
            setValue(e.target.value);
            input.current?.setCustomValidity(
              e.target.value ? "请等待账号检查完成" : "",
            );
          }}
          aria-describedby={hintId}
          aria-invalid={
            ["taken", "invalid", "error"].includes(check.kind) || undefined
          }
        />
      </Field>
      <p id={hintId} role="status" className="account-hint">
        {check.message}
      </p>
      {check.kind === "error" ? (
        <button
          type="button"
          className="secondary"
          onClick={() => setRetry((n) => n + 1)}
        >
          重新检查账号
        </button>
      ) : null}
    </>
  );
}
