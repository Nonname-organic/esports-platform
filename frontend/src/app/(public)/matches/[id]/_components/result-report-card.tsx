"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Flag } from "lucide-react";
import { matchApi } from "@/features/matches/api/match-api";
import { useAuthStore } from "@/store/auth-store";
import type { MatchDetail } from "@/types/match";

const STATUS_LABEL = {
  pending: "相手チームの確認待ち",
  confirmed: "確定しました",
  disputed: "異議あり（主催者の裁定待ち）",
  superseded: "主催者が結果を確定しました",
} as const;

/**
 * 対戦チームのオーナー・キャプテンが結果を報告し、相手チームが確認・異議を出す。
 * 何ができるかはサーバーが返す can_* で決め、画面側で権限を推測しない。
 */
export function ResultReportCard({ match }: { match: MatchDetail }) {
  const authed = useAuthStore((s) => s.isAuthenticated);
  const qc = useQueryClient();
  const [winner, setWinner] = useState<string>("");
  const [reason, setReason] = useState("");
  const { data } = useQuery({
    queryKey: ["matches", match.id, "report"],
    queryFn: () => matchApi.reportState(match.id),
    select: (r) => r.data,
    enabled: authed && !!match.team1 && !!match.team2,
  });
  // 試合詳細（["matches", "detail", id]）と報告状態の両方を取り直す
  const done = () => qc.invalidateQueries({ queryKey: ["matches"] });
  const report = useMutation({ mutationFn: (w: string) => matchApi.report(match.id, w), onSuccess: done });
  const confirm = useMutation({ mutationFn: () => matchApi.confirmReport(match.id), onSuccess: done });
  const dispute = useMutation({ mutationFn: (r: string) => matchApi.disputeReport(match.id, r), onSuccess: done });

  if (!data || !match.team1 || !match.team2) return null;
  const { can_report, can_confirm, can_dispute } = data;
  if (!data.report && !can_report) return null;

  const teamName = (id: string) => (id === match.team1!.id ? match.team1!.name : match.team2!.name);
  const error = [report, confirm, dispute].find((m) => m.isError)?.error;
  const busy = report.isPending || confirm.isPending || dispute.isPending;

  return (
    <section className="mb-5 rounded-xl border border-white/10 bg-slate-900 p-4" aria-labelledby="result-report-title">
      <h2 id="result-report-title" className="mb-3 flex items-center gap-2 text-sm font-bold text-white">
        <Flag className="h-4 w-4 text-brand-400" /> 結果の報告
      </h2>

      {data.report && (
        <p className="mb-3 text-sm text-slate-300">
          {teamName(data.report.reported_by_team_id)} の報告：勝者 {teamName(data.report.winner_id)}
          <span className="ml-2 rounded bg-white/5 px-2 py-0.5 text-xs text-slate-400">
            {STATUS_LABEL[data.report.status]}
          </span>
          {data.report.dispute_reason && (
            <span className="mt-1 block text-xs text-amber-400">理由：{data.report.dispute_reason}</span>
          )}
        </p>
      )}

      {can_confirm && (
        <div className="mb-3 flex flex-wrap gap-2">
          <button type="button" disabled={busy} onClick={() => confirm.mutate()}
            className="rounded-lg bg-brand-500 px-4 py-2 text-sm font-bold text-white hover:bg-brand-600 disabled:opacity-50">
            この結果で確定する
          </button>
        </div>
      )}
      {can_dispute && (
        <form className="mb-3 flex flex-wrap gap-2" onSubmit={(e) => { e.preventDefault(); if (reason.trim()) dispute.mutate(reason.trim()); }}>
          <label htmlFor="dispute-reason" className="sr-only">異議の理由</label>
          <input id="dispute-reason" value={reason} onChange={(e) => setReason(e.target.value)} maxLength={1000}
            placeholder="異議の理由（例: スコアが違う）"
            className="min-w-0 flex-1 rounded-lg border border-white/10 bg-slate-950 px-3 py-2 text-sm text-white placeholder:text-slate-600" />
          <button type="submit" disabled={busy || !reason.trim()}
            className="rounded-lg border border-amber-500/40 px-4 py-2 text-sm text-amber-300 hover:bg-amber-500/10 disabled:opacity-50">
            異議を出す
          </button>
        </form>
      )}
      {can_report && (
        <form className="flex flex-wrap items-center gap-2" onSubmit={(e) => { e.preventDefault(); if (winner) report.mutate(winner); }}>
          <label htmlFor="report-winner" className="text-sm text-slate-400">勝者</label>
          <select id="report-winner" value={winner} onChange={(e) => setWinner(e.target.value)}
            className="rounded-lg border border-white/10 bg-slate-950 px-3 py-2 text-sm text-white">
            <option value="">選択してください</option>
            <option value={match.team1.id}>{match.team1.name}</option>
            <option value={match.team2.id}>{match.team2.name}</option>
          </select>
          <button type="submit" disabled={busy || !winner}
            className="rounded-lg bg-white/10 px-4 py-2 text-sm font-semibold text-white hover:bg-white/15 disabled:opacity-50">
            {data.report?.status === "pending" ? "報告し直す・報告する" : "結果を報告する"}
          </button>
        </form>
      )}
      {error && <p role="alert" className="mt-2 text-sm text-red-400">{error instanceof Error ? error.message : "操作に失敗しました"}</p>}
    </section>
  );
}
