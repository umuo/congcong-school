export interface Account {
  context_id: string;
  role: "admin" | "parent" | "student";
  mode: "admin" | "parent" | "child";
  user: {
    id: string;
    login_name: string;
    email: string | null;
    nickname: string;
    role: string;
  } | null;
  family: { id: string; name: string; timezone: string; role: string } | null;
  student_id: string | null;
  must_change_password: boolean;
  destination: string;
}

export class APIError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
  ) {
    super(message);
  }
}

export async function api<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const headers = new Headers(options.headers);
  if (options.body) headers.set("Content-Type", "application/json");
  if (options.method && !["GET", "HEAD"].includes(options.method)) {
    const csrf = document.cookie
      .split("; ")
      .find((v) => v.startsWith("csf_csrf="))
      ?.slice(9);
    if (csrf) headers.set("X-CSF-CSRF", decodeURIComponent(csrf));
  }
  let response: Response;
  try {
    response = await fetch(`/api/v1${path}`, {
      ...options,
      headers,
      credentials: "same-origin",
      cache: "no-store",
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError")
      throw error;
    throw new Error("暂时无法连接服务，请检查网络后重试。");
  }
  if (!response.ok) {
    const body = await response
      .json()
      .catch(() => ({ code: "HTTP_ERROR", message: "请求未成功，请稍后重试" }));
    const error = new APIError(response.status, body.code, body.message);
    if (
      path !== "/auth/session" &&
      [
        "AUTH_REQUIRED",
        "PASSWORD_CHANGE_REQUIRED",
        "LEARNING_CONTEXT_CHANGED",
      ].includes(error.code)
    )
      window.dispatchEvent(new Event("csf-session-invalid"));
    if (error.code === "PARENT_REAUTH_REQUIRED")
      window.dispatchEvent(new Event("csf-reauth-required"));
    if (error.code === "REVISION_CONFLICT")
      error.message =
        "资料已在其他页面修改。请刷新后重新编辑，你的修改尚未保存。";
    throw error;
  }
  return response.status === 204 ? (undefined as T) : response.json();
}

export const post = <T>(path: string, body?: unknown) =>
  api<T>(path, {
    method: "POST",
    body: body ? JSON.stringify(body) : undefined,
  });
export function announceSessionChange() {
  const channel = new BroadcastChannel("csf-session");
  channel.postMessage("changed");
  channel.close();
}
