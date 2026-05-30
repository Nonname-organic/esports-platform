"use client";

import { useState } from "react";
import { Play, CheckCircle, XCircle, AlertTriangle, Shield } from "lucide-react";
import { cn } from "@/lib/utils";
import type { MatchDetail } from "@/types/match";
import type { useMatchAdmin } from "@/features/matches/hooks/use-match-admin";

interface StatusControlsProps {
  match: MatchDetail;
  startMatch: ReturnType<typeof useMatchAdmin>["startMatch"];
  registerResult: ReturnType<typeof useMatchAdmin>["registerResult"];
}

export function StatusControls({ match, startMatch, registerResult }: StatusControlsProps) {
  const [showComplete, setShowComplete] = useState(false);
  const [winnerId, setWinnerId] = useState<string>("");
  const [isForfeit, setIsForfeit] = useState(false);

  const handleComplete = async () => {
    if (!winnerId) return;
    await registerResult.mutateAsync({ winner_id: winnerId, was_forfeit: isForfeit });
    setShowComplete(false);
  };

  if (match.status === "completed" || match.status === "cancelled") {
    return (
      <div className="flex items-center gap-2 rounded-xl border border-white/10 bg-slate-900 px-4 py-3">
        <CheckCircle className="h-4 w-4 text-slate-500" />
        <span className="text-sm text-slate-500">
          {match.status === "completed" ? "試合は終了しています" : "試合は中止されました"}
        </span>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2 rounded-xl border border-white/10 bg-slate-900 px-4 py-3">
        <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
          ステータス操作
        </span>

        {/* 試合開始 */}
        {match.status === "scheduled" && (
          <button
            onClick={() => startMatch.mutate()}
            disabled={startMatch.isPending}
            className="flex items-center gap-2 rounded-lg bg-green-500/10 px-3 py-1.5 text-sm font-semibold text-green-400 hover:bg-green-500/20 transition-colors disabled:opacity-50"
          >
            <Play className="h-4 w-4" />
            試合開始
          </button>
        )}

        {/* 試合終了 */}
        {match.status === "ongoing" && !showComplete && (
          <button
            onClick={() => setShowComplete(true)}
            className="flex items-center gap-2 rounded-lg bg-brand-500/10 px-3 py-1.5 text-sm font-semibold text-brand-400 hover:bg-brand-500/20 transition-colors"
          >
            <CheckCircle className="h-4 w-4" />
            試合終了
          </button>
        )}
      </div>

      {/* 試合終了確認パネル */}
      {showComplete && match.status === "ongoing" && (
        <div className="rounded-xl border border-brand-500/30 bg-slate-900 p-4 space-y-4">
          <div className="flex items-center gap-2 text-sm font-semibold text-white">
            <AlertTriangle className="h-4 w-4 text-yellow-400" />
            勝者を選択して試合を終了
          </div>

          <div className="grid grid-cols-2 gap-2">
            {[match.team1, match.team2].map((team) => (
              <button
                key={team?.id}
                onClick={() => setWinnerId(team?.id ?? "")}
                className={cn(
                  "flex items-center gap-2 rounded-lg border p-3 text-left transition-colors",
                  winnerId === team?.id
                    ? "border-brand-500 bg-brand-500/10 text-brand-400"
                    : "border-white/10 text-slate-400 hover:border-white/20 hover:text-white",
                )}
              >
                <div className="h-8 w-8 flex-shrink-0 overflow-hidden rounded-lg border border-white/10 bg-slate-800 flex items-center justify-center">
                  {team?.logo_url ? (
                    <img src={team.logo_url} alt="" className="h-full w-full object-contain" />
                  ) : (
                    <Shield className="h-4 w-4 text-slate-600" />
                  )}
                </div>
                <div>
                  <p className="text-sm font-bold">{team?.name ?? "TBD"}</p>
                  <p className="text-xs opacity-60">{team?.tag}</p>
                </div>
              </button>
            ))}
          </div>

          {/* 没収試合 */}
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={isForfeit}
              onChange={(e) => setIsForfeit(e.target.checked)}
              className="h-4 w-4 rounded border-white/20 bg-slate-800 accent-brand-500"
            />
            <span className="text-sm text-slate-400">没収試合（Forfeit）</span>
          </label>

          <div className="flex items-center gap-2">
            <button
              onClick={handleComplete}
              disabled={!winnerId || registerResult.isPending}
              className="flex items-center gap-2 rounded-lg bg-brand-500 px-4 py-2 text-sm font-bold text-white hover:bg-brand-600 transition-colors disabled:opacity-40"
            >
              <CheckCircle className="h-4 w-4" />
              {registerResult.isPending ? "処理中..." : "試合終了を確定"}
            </button>
            <button
              onClick={() => { setShowComplete(false); setWinnerId(""); }}
              className="rounded-lg border border-white/10 px-4 py-2 text-sm text-slate-400 hover:text-white transition-colors"
            >
              キャンセル
            </button>
          </div>

          {registerResult.isError && (
            <p className="text-xs text-red-400">
              <XCircle className="inline h-3.5 w-3.5 mr-1" />
              エラーが発生しました。再試行してください。
            </p>
          )}
        </div>
      )}
    </div>
  );
}
