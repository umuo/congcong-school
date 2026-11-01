"use client";
import { useEffect, useId, useRef, useState } from "react";
import { Field } from "./AccountShell";

/** 创建、重置和改密共用即时确认；只在浏览器内比较，不把确认字段发给 API。 */
export function PasswordFields({
  label = "密码（至少 12 个字符）",
  confirmationLabel = "确认密码",
  name = "password",
}: {
  label?: string;
  confirmationLabel?: string;
  name?: string;
}) {
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const first = useRef<HTMLInputElement>(null);
  const second = useRef<HTMLInputElement>(null);
  const hintId = useId();
  const mismatch = confirmation.length > 0 && password !== confirmation;
  function validate(value: string, repeated: string) {
    second.current?.setCustomValidity(
      repeated && repeated !== value ? "两次输入的密码不一致" : "",
    );
  }
  useEffect(() => {
    const form = first.current?.form;
    const reset = () => {
      setPassword("");
      setConfirmation("");
      second.current?.setCustomValidity("");
    };
    form?.addEventListener("reset", reset);
    return () => form?.removeEventListener("reset", reset);
  }, []);
  return (
    <>
      <Field label={label}>
        <input
          ref={first}
          name={name}
          type="password"
          autoComplete="new-password"
          minLength={12}
          maxLength={128}
          required
          value={password}
          onChange={(e) => {
            setPassword(e.target.value);
            validate(e.target.value, confirmation);
          }}
        />
      </Field>
      <Field label={confirmationLabel}>
        <input
          ref={second}
          name="confirmation"
          type="password"
          autoComplete="new-password"
          minLength={12}
          maxLength={128}
          required
          value={confirmation}
          onChange={(e) => {
            setConfirmation(e.target.value);
            validate(password, e.target.value);
          }}
          aria-invalid={mismatch || undefined}
          aria-describedby={hintId}
        />
      </Field>
      <p id={hintId} role="status" className="account-hint">
        {mismatch
          ? "两次输入的密码不一致"
          : confirmation
            ? "两次密码输入一致"
            : "请再次输入相同密码"}
      </p>
    </>
  );
}
