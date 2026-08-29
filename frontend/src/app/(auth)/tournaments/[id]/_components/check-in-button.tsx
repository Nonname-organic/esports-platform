"use client";

import { useEffect, useState } from "react";
import { Check, Clock, Loader2, LogIn } from "lucide-react";
import { apiClient, ApiError } from "@/lib/api-client";
import { useAuthStore } from "@/store/auth-store";

interface CheckInWindow {
  state: "open" | "before" | "after";
  start_at: string | null;
  end_at: string | null;
}

interface CheckInState {
  registered: boolean;
  approved?: boolean;
  checked_in?: boolean;
  window?: CheckInWindow;
}

/** "8/30 13:00 〜 13:05" 形式。終了が同日なら時刻のみに省略する */
function fmtWindow(start: string | null, end: string | null): string {
  const fmt = (iso: string, timeOnly: boolean) => {
    const d = new Date(iso);
    const time = `${d.getHours()}:${String(d.getMinutes()).padStart(2, "0")}`;
    return timeOnly ? time : `${d.getMonth() + 1}/${d.getDate()} ${time}`;
  };
  if (start && end) {
    const sameDay = new Date(start).toDateString() === new Date(end).toDateString();
    return `${fmt(start, false)} 〜 ${fmt(end, sameDay)}`;
  }
  if (start) return `${fmt(start, false)} から`;
  if (end) return `${fmt(end, false)} まで`;
  return "";
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

  // 未ログイン・未登録は非表示（公開ページなのでログインを強制しない）。
  // 承認前（抽選の当落が出る前）も表示しない — チェックインは当選チームの操作
  if (!_hasHydrated || !isAuthenticated) return null;
  if (!state || !state.registered || state.approved !== true) return null;

  const win = state.window;
  const windowLabel = win ? fmtWindow(win.start_at, win.end_at) : "";

  // チェックイン済みは時間帯に関係なく完了表示を維持する
  if (state.checked_in) {
    return (
      <div className="rounded-xl border border-white/10 bg-slate-900 p-5">
        <div className="flex items-center gap-2">
          <Check className="h-5 w-5 text-green-400" />
          <span className="text-sm font-semibold text-green-400">チェックイン済み</span>
        </div>
      </div>
    );
  }

  // 受付前: ボタンは出さず、いつ可能になるかだけ案内する
  if (win?.state === "before") {
    return (
      <div className="rounded-xl border border-white/10 bg-slate-900 p-5">
        <h3 className="mb-1 flex items-center gap-2 font-bold text-white">
          <Clock className="h-4 w-4 text-slate-400" />
          チェックイン
        </h3>
        <p className="text-xs text-slate-400">
          チェックイン可能時間:{" "}
          <span className="font-semibold text-white">{windowLabel}</span>
        </p>
        <p className="mt-1 text-[11px] text-slate-500">
          時間になるとここにチェックインボタンが表示されます
        </p>
      </div>
    );
  }

  // 受付終了: 未チェックインのチームには終了した旨を表示する
  if (win?.state === "after") {
    return (
      <div className="rounded-xl border border-red-500/20 bg-slate-900 p-5">
        <h3 className="mb-1 flex items-center gap-2 font-bold text-white">
          <Clock className="h-4 w-4 text-red-400" />
          チェックイン受付終了
        </h3>
        <p className="text-xs text-slate-400">
          受付時間（{windowLabel}）を過ぎました。参加希望の場合は主催者に連絡してください
        </p>
      </div>
    );
  }

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
    <div className="rounded-xl border border-brand-500/30 bg-slate-900 p-5">
      <h3 className="mb-1 flex items-center gap-2 font-bold text-white">
        <LogIn className="h-4 w-4 text-brand-400" />
        チェックイン受付中
      </h3>
      {windowLabel ? (
        <p className="mb-3 text-xs text-slate-400">
          受付時間: <span className="font-semibold text-white">{windowLabel}</span>
        </p>
      ) : (
        <p className="mb-3 text-xs text-slate-400">
          この大会への参加にはチェックインが必要です
        </p>
      )}
      <button
        onClick={handleCheckIn}
        disabled={loading}
        className="flex w-full items-center justify-center gap-1.5 rounded-lg bg-brand-500 px-4 py-2.5 text-sm font-bold text-white hover:bg-brand-600 disabled:opacity-50 transition-colors"
      >
        {loading && <Loader2 className="h-4 w-4 animate-spin" />}
        チェックインする
      </button>
      {error && <p className="mt-2 text-xs text-red-400">{error}</p>}
    </div>
  );
}
