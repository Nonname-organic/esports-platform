"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Play, CheckCircle, XCircle, AlertTriangle, Shield, Flag } from "lucide-react";
import { matchApi } from "@/features/matches/api/match-api";
import { rosterApi } from "@/features/rosters/api/roster-api";
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
  // RC4: スターターが出場人数に満たないまま開始する理由（D14）・開始を経ない不戦勝（Q04）
  const [startReason, setStartReason] = useState("");
  const [showForfeit, setShowForfeit] = useState(false);
  const [forfeitWinner, setForfeitWinner] = useState("");
  const [forfeitReason, setForfeitReason] = useState("");
  const qc = useQueryClient();
  const reopen = useMutation({
    mutationFn: (reason?: string) => matchApi.reopen(match.id, reason),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["matches"] }),
  });
  const forfeit = useMutation({
    mutationFn: () => rosterApi.forfeitWithoutStart(match.id, forfeitWinner, forfeitReason.trim()),
    onSuccess: () => {
      setShowForfeit(false);
      qc.invalidateQueries({ queryKey: ["matches"] });
    },
  });

  const handleComplete = async () => {
    if (!winnerId) return;
    await registerResult.mutateAsync({ winner_id: winnerId, was_forfeit: isForfeit });
    setShowComplete(false);
  };

  if (match.status === "completed" || match.status === "cancelled") {
    return (
      <div className="flex flex-wrap items-center gap-2 rounded-xl border border-white/10 bg-slate-900 px-4 py-3">
        <CheckCircle className="h-4 w-4 text-slate-500" />
        <span className="text-sm text-slate-500">
          {match.status === "completed" ? "試合は終了しています" : "試合は中止されました"}
        </span>
        {match.status === "completed" && (
          <button
            type="button"
            disabled={reopen.isPending}
            onClick={() => {
              if (window.confirm("確定した結果を取り消して試合を戻しますか？（次の試合が始まっていると戻せません）")) {
                // 完了・中止した大会の訂正は管理者だけが理由つきで行う。それ以外は空でよい
                const reason = window.prompt("理由（大会の完了の後の訂正では必須）") ?? "";
                reopen.mutate(reason.trim() || undefined);
              }
            }}
            className="ml-auto rounded-lg border border-white/10 px-3 py-1.5 text-xs text-slate-300 hover:text-white disabled:opacity-50"
          >
            {reopen.isPending ? "処理中..." : "結果を取り消して再開"}
          </button>
        )}
        {reopen.isError && (
          <p role="alert" className="w-full text-xs text-red-400">
            {reopen.error instanceof Error ? reopen.error.message : "再開に失敗しました"}
          </p>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2 rounded-xl border border-white/10 bg-slate-900 px-4 py-3">
        <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
          ステータス操作
        </span>

        {/* 試合開始（出場登録をここで固定する） */}
        {match.status === "scheduled" && (
          <>
            <input
              value={startReason}
              onChange={(e) => setStartReason(e.target.value)}
              placeholder="人数が足りないまま開始する理由（必要なときだけ）"
              aria-label="開始の理由"
              className="min-w-0 flex-1 rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 text-xs text-white outline-none focus:border-brand-500"
            />
            <button
              onClick={() => startMatch.mutate(startReason.trim() || undefined)}
              disabled={startMatch.isPending}
              className="flex items-center gap-2 rounded-lg bg-green-500/10 px-3 py-1.5 text-sm font-semibold text-green-400 hover:bg-green-500/20 transition-colors disabled:opacity-50"
            >
              <Play className="h-4 w-4" />
              試合開始
            </button>
            <button
              type="button"
              onClick={() => setShowForfeit(!showForfeit)}
              className="flex items-center gap-2 rounded-lg border border-white/10 px-3 py-1.5 text-sm text-slate-300 hover:text-white"
            >
              <Flag className="h-4 w-4" />
              開始せずに不戦勝
            </button>
          </>
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

      {startMatch.isError && (
        <p role="alert" className="text-xs text-red-400">
          {startMatch.error instanceof Error ? startMatch.error.message : "開始できませんでした"}
        </p>
      )}

      {/* 開始を経ない不戦勝（出場登録を固定しない。マップ・成績は記録しない） */}
      {showForfeit && match.status === "scheduled" && (
        <div className="space-y-3 rounded-xl border border-orange-500/30 bg-slate-900 p-4">
          <p className="text-xs text-slate-400">
            スターターのいないチームがある・相手が来ないなど、試合をせずに決着するときに使います。結果を取り消すと予定に戻ります
          </p>
          <div className="grid grid-cols-2 gap-2">
            {[match.team1, match.team2].map((team) => (
              <button
                key={team?.id}
                type="button"
                onClick={() => setForfeitWinner(team?.id ?? "")}
                className={cn(
                  "rounded-lg border p-2 text-left text-sm",
                  forfeitWinner === team?.id ? "border-brand-500 bg-brand-500/10 text-brand-400" : "border-white/10 text-slate-400",
                )}
              >
                勝者: {team?.name ?? "TBD"}
              </button>
            ))}
          </div>
          <input
            value={forfeitReason}
            onChange={(e) => setForfeitReason(e.target.value)}
            placeholder="理由（必須）"
            aria-label="不戦勝の理由"
            className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white outline-none focus:border-brand-500"
          />
          <button
            type="button"
            disabled={!forfeitWinner || !forfeitReason.trim() || forfeit.isPending}
            onClick={() => forfeit.mutate()}
            className="rounded-lg bg-orange-500 px-4 py-2 text-sm font-bold text-white hover:bg-orange-600 disabled:opacity-40"
          >
            {forfeit.isPending ? "処理中..." : "不戦勝として確定"}
          </button>
          {forfeit.isError && (
            <p role="alert" className="text-xs text-red-400">
              {forfeit.error instanceof Error ? forfeit.error.message : "確定できませんでした"}
            </p>
          )}
        </div>
      )}

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
