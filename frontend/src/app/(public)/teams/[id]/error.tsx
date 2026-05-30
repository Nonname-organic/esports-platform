"use client";

import { useEffect } from "react";
import { AlertCircle, RefreshCw } from "lucide-react";
import Link from "next/link";

export default function TeamDetailError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => { console.error(error); }, [error]);

  return (
    <div className="mx-auto max-w-5xl px-4 py-24 text-center">
      <div className="mx-auto mb-6 flex h-20 w-20 items-center justify-center rounded-2xl bg-red-500/10">
        <AlertCircle className="h-10 w-10 text-red-400" />
      </div>
      <h2 className="text-xl font-bold text-white">チーム情報の読み込みに失敗しました</h2>
      <p className="mt-2 text-sm text-slate-400">ネットワークエラーが発生しました。</p>
      <div className="mt-6 flex items-center justify-center gap-3">
        <button
          onClick={reset}
          className="flex items-center gap-2 rounded-lg bg-brand-500/10 px-4 py-2 text-sm font-medium text-brand-400 hover:bg-brand-500/20 transition-colors"
        >
          <RefreshCw className="h-4 w-4" />
          再試行
        </button>
        <Link
          href="/tournaments"
          className="rounded-lg border border-white/10 px-4 py-2 text-sm font-medium text-slate-400 hover:text-white transition-colors"
        >
          大会一覧へ
        </Link>
      </div>
    </div>
  );
}
