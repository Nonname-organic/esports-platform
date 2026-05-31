"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Trophy, Eye, EyeOff, Check, X } from "lucide-react";
import { apiClient } from "@/lib/api-client";
import { useAuthStore } from "@/store/auth-store";
import { cn } from "@/lib/utils";
import type { UserRole } from "@/store/auth-store";

// ===== バリデーション =====
const USERNAME_RE = /^[a-zA-Z0-9_-]+$/;

interface PasswordRule {
  label: string;
  test: (v: string) => boolean;
}

const PASSWORD_RULES: PasswordRule[] = [
  { label: "8文字以上", test: (v) => v.length >= 8 },
  { label: "大文字を含む", test: (v) => /[A-Z]/.test(v) },
  { label: "数字を含む", test: (v) => /[0-9]/.test(v) },
];

// ===== API 型 =====
interface RegisterResponse {
  data: {
    id: string;
    email: string;
    username: string;
    role: string;
    avatar_url: string | null;
  };
}

interface LoginResponse {
  access_token: string;
  refresh_token: string;
}

// ===== ページ =====
export default function RegisterPage() {
  const router = useRouter();
  const { setTokens, setUser } = useAuthStore();

  const [form, setForm] = useState({ username: "", email: "", password: "", confirm: "" });
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [touched, setTouched] = useState<Record<string, boolean>>({});

  const set = (key: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((f) => ({ ...f, [key]: e.target.value }));
  const blur = (key: string) => () => setTouched((t) => ({ ...t, [key]: true }));

  // バリデーション
  const usernameError =
    touched.username && form.username.length > 0 && !USERNAME_RE.test(form.username)
      ? "英数字・アンダースコア・ハイフンのみ使用できます"
      : touched.username && form.username.length < 3 && form.username.length > 0
      ? "3文字以上で入力してください"
      : null;

  const passwordRules = PASSWORD_RULES.map((r) => ({ ...r, ok: r.test(form.password) }));
  const passwordValid = passwordRules.every((r) => r.ok);
  const confirmError =
    touched.confirm && form.confirm.length > 0 && form.confirm !== form.password
      ? "パスワードが一致しません"
      : null;

  const canSubmit =
    form.username.length >= 3 &&
    USERNAME_RE.test(form.username) &&
    form.email.length > 0 &&
    passwordValid &&
    form.confirm === form.password &&
    !isLoading;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!canSubmit) return;
    setError(null);
    setIsLoading(true);

    try {
      // 1. アカウント作成
      await apiClient.post<RegisterResponse>("/api/v1/auth/register", {
        username: form.username,
        email: form.email,
        password: form.password,
      });

      // 2. 登録後に自動ログイン
      const tokenRes = await apiClient.post<LoginResponse>("/api/v1/auth/login", {
        email: form.email,
        password: form.password,
      });
      setTokens(tokenRes.access_token, tokenRes.refresh_token);

      // 3. ユーザー情報取得
      const me = await apiClient.get<{ id: string; email: string; username: string; role: string; avatar_url: string | null }>("/api/v1/auth/me");
      setUser({
        id: me.id,
        email: me.email,
        username: me.username,
        role: me.role as UserRole,
        avatar_url: me.avatar_url,
      });

      router.replace("/dashboard");
    } catch (err) {
      const msg =
        err instanceof Error ? err.message : "登録に失敗しました。しばらく待ってから再試行してください。";
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="flex min-h-[calc(100vh-3.5rem)] items-center justify-center px-4 py-12">
      <div className="w-full max-w-md">
        {/* ヘッダー */}
        <div className="mb-8 text-center">
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-brand-500/20">
            <Trophy className="h-7 w-7 text-brand-400" />
          </div>
          <h1 className="text-2xl font-black text-white">アカウント作成</h1>
          <p className="mt-1 text-sm text-slate-400">EsportsPlatform に参加する</p>
        </div>

        {/* フォーム */}
        <form onSubmit={handleSubmit} className="space-y-4 rounded-2xl border border-white/10 bg-slate-900 p-6">
          {/* サーバーエラー */}
          {error && (
            <div className="flex items-start gap-2 rounded-lg border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-400">
              <X className="mt-0.5 h-4 w-4 shrink-0" />
              {error}
            </div>
          )}

          {/* ユーザー名 */}
          <div>
            <label className="mb-1.5 block text-sm font-medium text-slate-400">
              ユーザー名 <span className="text-slate-600">（3〜50文字、英数字・_・-）</span>
            </label>
            <input
              type="text"
              value={form.username}
              onChange={set("username")}
              onBlur={blur("username")}
              required
              autoComplete="username"
              maxLength={50}
              className={cn(
                "w-full rounded-lg border bg-white/5 px-3 py-2.5 text-sm text-white placeholder-slate-600 outline-none transition-colors",
                usernameError ? "border-red-500/50 focus:border-red-500" : "border-white/10 focus:border-brand-500",
              )}
              placeholder="player_one"
            />
            {usernameError && (
              <p className="mt-1.5 flex items-center gap-1 text-xs text-red-400">
                <X className="h-3 w-3" />
                {usernameError}
              </p>
            )}
          </div>

          {/* メールアドレス */}
          <div>
            <label className="mb-1.5 block text-sm font-medium text-slate-400">
              メールアドレス
            </label>
            <input
              type="email"
              value={form.email}
              onChange={set("email")}
              onBlur={blur("email")}
              required
              autoComplete="email"
              className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2.5 text-sm text-white placeholder-slate-600 outline-none transition-colors focus:border-brand-500"
              placeholder="you@example.com"
            />
          </div>

          {/* パスワード */}
          <div>
            <label className="mb-1.5 block text-sm font-medium text-slate-400">
              パスワード
            </label>
            <div className="relative">
              <input
                type={showPassword ? "text" : "password"}
                value={form.password}
                onChange={set("password")}
                onBlur={blur("password")}
                required
                autoComplete="new-password"
                className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2.5 pr-10 text-sm text-white placeholder-slate-600 outline-none transition-colors focus:border-brand-500"
                placeholder="••••••••"
              />
              <button
                type="button"
                onClick={() => setShowPassword((v) => !v)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
                tabIndex={-1}
              >
                {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>

            {/* パスワード強度インジケーター */}
            {form.password.length > 0 && (
              <div className="mt-2 space-y-1">
                {passwordRules.map((rule) => (
                  <p
                    key={rule.label}
                    className={cn(
                      "flex items-center gap-1.5 text-xs transition-colors",
                      rule.ok ? "text-green-400" : "text-slate-500",
                    )}
                  >
                    {rule.ok ? <Check className="h-3 w-3" /> : <X className="h-3 w-3" />}
                    {rule.label}
                  </p>
                ))}
              </div>
            )}
          </div>

          {/* パスワード確認 */}
          <div>
            <label className="mb-1.5 block text-sm font-medium text-slate-400">
              パスワード（確認）
            </label>
            <div className="relative">
              <input
                type={showConfirm ? "text" : "password"}
                value={form.confirm}
                onChange={set("confirm")}
                onBlur={blur("confirm")}
                required
                autoComplete="new-password"
                className={cn(
                  "w-full rounded-lg border bg-white/5 px-3 py-2.5 pr-10 text-sm text-white placeholder-slate-600 outline-none transition-colors",
                  confirmError ? "border-red-500/50 focus:border-red-500" : "border-white/10 focus:border-brand-500",
                  !confirmError && form.confirm.length > 0 && form.confirm === form.password && "border-green-500/50",
                )}
                placeholder="••••••••"
              />
              <button
                type="button"
                onClick={() => setShowConfirm((v) => !v)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
                tabIndex={-1}
              >
                {showConfirm ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
            {confirmError && (
              <p className="mt-1.5 flex items-center gap-1 text-xs text-red-400">
                <X className="h-3 w-3" />
                {confirmError}
              </p>
            )}
            {!confirmError && form.confirm.length > 0 && form.confirm === form.password && (
              <p className="mt-1.5 flex items-center gap-1 text-xs text-green-400">
                <Check className="h-3 w-3" />
                パスワードが一致しています
              </p>
            )}
          </div>

          {/* 登録ボタン */}
          <button
            type="submit"
            disabled={!canSubmit}
            className="w-full rounded-xl bg-brand-500 py-3 text-sm font-semibold text-white transition-colors hover:bg-brand-600 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {isLoading ? (
              <span className="flex items-center justify-center gap-2">
                <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                登録中...
              </span>
            ) : (
              "アカウントを作成する"
            )}
          </button>

          {/* 規約テキスト */}
          <p className="text-center text-xs text-slate-600">
            登録することで、利用規約およびプライバシーポリシーに同意したものとみなされます。
          </p>
        </form>

        <p className="mt-4 text-center text-sm text-slate-500">
          すでにアカウントをお持ちの方は{" "}
          <Link href="/login" className="text-brand-400 hover:text-brand-300">
            ログイン
          </Link>
        </p>
      </div>
    </div>
  );
}
