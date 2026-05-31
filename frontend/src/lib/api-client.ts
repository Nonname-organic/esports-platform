// ブラウザは相対URL（CloudFront/Nginx経由）
// SSRはINTERNAL_API_URL（Docker内部）またはフォールバック
const API_BASE =
  typeof window !== "undefined"
    ? ""
    : (process.env.INTERNAL_API_URL ?? "http://api:8000");

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly type: string,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("access_token");
}

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const token = getAccessToken();
  const headers: HeadersInit = {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
  };

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ title: "エラーが発生しました", type: "unknown" }));
    throw new ApiError(res.status, err.type ?? "unknown", err.title ?? err.detail ?? "エラー");
  }

  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const apiClient = {
  get: <T>(path: string, init?: RequestInit) =>
    request<T>(path, { method: "GET", ...init }),

  post: <T>(path: string, body?: unknown, init?: RequestInit) =>
    request<T>(path, {
      method: "POST",
      body: body != null ? JSON.stringify(body) : undefined,
      ...init,
    }),

  patch: <T>(path: string, body?: unknown, init?: RequestInit) =>
    request<T>(path, {
      method: "PATCH",
      body: body != null ? JSON.stringify(body) : undefined,
      ...init,
    }),

  delete: <T>(path: string, init?: RequestInit) =>
    request<T>(path, { method: "DELETE", ...init }),
};

/** Server Component 用（Docker内部ネットワークで直接APIを呼ぶ） */
export async function serverFetch<T>(
  path: string,
  token: string | undefined,
  init?: RequestInit,
): Promise<T> {
  // サーバーサイドは常にDocker内部URLを使用（NEXT_PUBLIC_*はビルド時に空になるため使えない）
  const serverBase = process.env.INTERNAL_API_URL ?? "http://api:8000";
  const headers: HeadersInit = {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
  const res = await fetch(`${serverBase}${path}`, {
    ...init,
    headers,
    cache: init?.cache ?? "no-store",
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ title: "Error", type: "unknown" }));
    throw new ApiError(res.status, err.type, err.title ?? err.detail);
  }
  return res.json() as Promise<T>;
}
