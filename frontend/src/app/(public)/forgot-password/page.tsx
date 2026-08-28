"use client";

import { useState } from "react";
import Link from "next/link";
import { KeyRound, Loader2, MailCheck } from "lucide-react";
import { apiClient } from "@/lib/api-client";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setIsLoading(true);
    try {
      await apiClient.post("/api/v1/auth/forgot-password", { email });
      setSent(true);
    } catch {
      setError("送信に失敗しました。時間をおいて再度お試しください");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="flex min-h-[70vh] items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="mb-6 text-center">
          <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-2xl bg-brand-500/10">
            <KeyRound className="h-6 w-6 text-brand-400" />
          </div>
          <h1 className="text-xl font-black text-white">パスワードをお忘れですか？</h1>
          <p className="mt-1 text-sm text-slate-400">
            登録済みのメールアドレスに再設定用のリンクを送ります
          </p>
        </div>

        {sent ? (
          <div className="rounded-2xl border border-green-500/20 bg-green-500/5 p-6 text-center">
            <MailCheck className="mx-auto mb-2 h-8 w-8 text-green-400" />
            <p className="text-sm font-semibold text-white">送信を受け付けました</p>
            <p className="mt-1 text-xs leading-relaxed text-slate-400">
              登録済みのアドレスであれば数分以内にメールが届きます。
              リンクの有効期限は30分です。
            </p>
            <Link
              href="/login"
              className="mt-4 inline-block text-sm text-brand-400 hover:text-brand-300"
            >
              ログインに戻る
            </Link>
          </div>
        ) : (
          <form
            onSubmit={handleSubmit}
            className="space-y-4 rounded-2xl border border-white/10 bg-slate-900 p-6"
          >
            {error && (
              <p className="rounded-lg border border-red-500/20 bg-red-500/10 px-3 py-2 text-xs text-red-400">
                {error}
              </p>
            )}
            <div>
              <label className="mb-1.5 block text-sm font-medium text-slate-400">
                メールアドレス
              </label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white placeholder-slate-600 outline-none transition-colors focus:border-brand-500"
              />
            </div>
            <button
              type="submit"
              disabled={isLoading}
              className="flex w-full items-center justify-center gap-2 rounded-xl bg-brand-600 py-3 text-sm font-bold text-white transition-colors hover:bg-brand-500 disabled:opacity-50"
            >
              {isLoading && <Loader2 className="h-4 w-4 animate-spin" />}
              再設定メールを送る
            </button>
            <p className="text-center text-xs text-slate-500">
              <Link href="/login" className="text-brand-400 hover:text-brand-300">
                ログインに戻る
              </Link>
            </p>
          </form>
        )}
      </div>
    </div>
  );
}
