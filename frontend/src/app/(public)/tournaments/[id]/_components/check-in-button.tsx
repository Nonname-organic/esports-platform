"use client";

import { useEffect, useState } from "react";
import { Check, Loader2, LogIn } from "lucide-react";
import { apiClient, ApiError } from "@/lib/api-client";
import { useAuthStore } from "@/store/auth-store";

interface CheckInState {
  registered: boolean;
  approved?: boolean;
  checked_in?: boolean;
}

export function CheckInButton({ tournamentId }: { tournamentId: string }) {
  const { isAuthenticated, _hasHydrated } = useAuthStore();
  const [state, setState] = useState<CheckInState | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!_hasHydrated || !isAuthenticated) return;
    apiClient
      .get<{ data: CheckInState }>(`/api/v1/tournaments/${tournamentId}/check-in/me`)
      .then((r) => setState(r.data))
      .catch(() => setState(null));
  }, [_hasHydrated, isAuthenticated, tournamentId]);

  // 未ログイン or 未登録チームは非表示（公開ページなのでログイン強制しない）
  if (!_hasHydrated) return null;
  if (!isAuthenticated) return null;
  if (!state || !state.registered) return null;

  const handleCheckIn = async () => {
    setLoading(true);
    setError(null);
    try {
      await apiClient.post(`/api/v1/tournaments/${tournamentId}/check-in`);
      setState((s) => (s ? { ...s, checked_in: true } : s));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "チェックインに失敗しました");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mb-6 flex items-center gap-3 rounded-xl border border-white/10 bg-slate-900 px-4 py-3">
      {state.checked_in ? (
        <>
          <Check className="h-5 w-5 text-green-400" />
          <span className="text-sm font-semibold text-green-400">チェックイン済み</span>
        </>
      ) : (
        <>
          <LogIn className="h-5 w-5 text-brand-400" />
          <span className="text-sm text-slate-300">この大会へのチェックインが必要です</span>
          <button
            onClick={handleCheckIn}
            disabled={loading || state.approved === false}
            className="ml-auto flex items-center gap-1.5 rounded-lg bg-brand-500 px-4 py-2 text-sm font-bold text-white hover:bg-brand-600 disabled:opacity-50"
          >
            {loading && <Loader2 className="h-4 w-4 animate-spin" />}
            {state.approved === false ? "登録承認待ち" : "チェックイン"}
          </button>
        </>
      )}
      {error && <span className="text-xs text-red-400">{error}</span>}
    </div>
  );
}
