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

function getRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  // Zustand storeから読む（persisted state）
  try {
    const stored = localStorage.getItem("esports-auth");
    if (stored) {
      const parsed = JSON.parse(stored);
      return parsed?.state?.refreshToken ?? null;
    }
  } catch { /* ignore */ }
  return null;
}

let isRefreshing = false;
let refreshQueue: Array<(token: string) => void> = [];

async function tryRefreshToken(): Promise<string | null> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) return null;

  try {
    const res = await fetch(`${API_BASE}/api/v1/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (!res.ok) return null;
    const data = await res.json();
    const newToken = data.access_token;
    if (newToken) {
      localStorage.setItem("access_token", newToken);
      // Zustand storeも更新
      try {
        const stored = localStorage.getItem("esports-auth");
        if (stored) {
          const parsed = JSON.parse(stored);
          parsed.state.accessToken = newToken;
          parsed.state.refreshToken = data.refresh_token ?? refreshToken;
          localStorage.setItem("esports-auth", JSON.stringify(parsed));
        }
      } catch { /* ignore */ }
      return newToken;
    }
  } catch { /* ignore */ }
  return null;
}

async function request<T>(
  path: string,
  options: RequestInit = {},
  retry = true,
): Promise<T> {
  const token = getAccessToken();
  const headers: HeadersInit = {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
  };

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });

  // 401 → トークンリフレッシュを試みる
  if (res.status === 401 && retry) {
    if (isRefreshing) {
      // 他のリフレッシュを待つ
      return new Promise((resolve, reject) => {
        refreshQueue.push((newToken) => {
          request<T>(path, { ...options, headers: { ...headers, Authorization: `Bearer ${newToken}` } }, false)
            .then(resolve)
            .catch(reject);
        });
      });
    }

    isRefreshing = true;
    const newToken = await tryRefreshToken();
    isRefreshing = false;

    if (newToken) {
      refreshQueue.forEach((cb) => cb(newToken));
      refreshQueue = [];
      return request<T>(path, options, false);
    } else {
      // リフレッシュ失敗 → ログアウト
      localStorage.removeItem("access_token");
      if (typeof window !== "undefined") {
        window.location.href = `/login?next=${encodeURIComponent(window.location.pathname)}`;
      }
    }
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({ title: "エラーが発生しました", type: "unknown" }));
    throw new ApiError(res.status, err.type ?? "unknown", err.title ?? err.detail ?? "エラー");
  }

  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

/** FormData（ファイルアップロード）用 - Content-Typeを自動設定させる */
async function uploadRequest<T>(path: string, formData: FormData, retry = true): Promise<T> {
  const token = getAccessToken();
  const headers: HeadersInit = token ? { Authorization: `Bearer ${token}` } : {};

  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    body: formData,
    headers,
  });

  if (res.status === 401 && retry) {
    const newToken = await tryRefreshToken();
    if (newToken) return uploadRequest<T>(path, formData, false);
    localStorage.removeItem("access_token");
    if (typeof window !== "undefined") {
      window.location.href = `/login?next=${encodeURIComponent(window.location.pathname)}`;
    }
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({ title: "アップロードに失敗しました", type: "unknown" }));
    throw new ApiError(res.status, err.type ?? "unknown", err.detail ?? err.title ?? "エラー");
  }

  return res.json() as Promise<T>;
}

export const apiClient = {
  get: <T>(path: string, init?: RequestInit) =>
    request<T>(path, { method: "GET", ...init }),

  upload: <T>(path: string, formData: FormData) =>
    uploadRequest<T>(path, formData),

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
