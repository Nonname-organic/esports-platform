"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Users } from "lucide-react";
import { rosterApi } from "@/features/rosters/api/roster-api";
import { useLineups } from "@/features/rosters/hooks/use-rosters";
import { useAuthStore } from "@/store/auth-store";
import type { MatchDetail } from "@/types/match";

/**
 * 試合の出場登録（RC4・D18: 試合を見られる人に公開）。出場登録・成績に載ったのに出場して
 * いない本人は、ここから異議を出せる（C5）。出せるかどうかはサーバーが判定する。
 */
export function MatchLineup({ match }: { match: MatchDetail }) {
  const authed = useAuthStore((s) => s.isAuthenticated);
  const { data: lineup } = useLineups(match.id);
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState("");
  const dispute = useMutation({
    mutationFn: () => rosterApi.createDispute(match.id, reason.trim()),
    onSuccess: () => { setOpen(false); setReason(""); },
  });

  if (!lineup || lineup.entries.length === 0) return null;
  const teams = [match.team1, match.team2].filter(Boolean) as { id: string; name: string }[];

  return (
    <section className="mb-6 rounded-xl border border-white/10 bg-slate-900 p-4">
      <h2 className="mb-2 flex items-center gap-2 text-sm font-bold text-white">
        <Users className="h-4 w-4 text-brand-400" /> 出場登録
      </h2>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {teams.map((t) => (
          <div key={t.id} className="text-xs text-slate-400">
            <p className="mb-0.5 font-semibold text-white">{t.name}</p>
            {(["starter", "bench"] as const).map((slot) => (
              <p key={slot}>
                <span className="text-slate-500">{slot === "starter" ? "スターター" : "控え"}: </span>
                {lineup.entries.filter((e) => e.team_id === t.id && e.slot === slot)
                  .map((e) => e.in_game_name ?? "選手").join("、") || "—"}
              </p>
            ))}
          </div>
        ))}
      </div>

      {authed && lineup.locked_at && (
        <div className="mt-3 border-t border-white/10 pt-3 text-xs">
          {dispute.isSuccess ? (
            <p role="status" className="text-green-400">異議を受け付けました。運営が確認して結果をお知らせします</p>
          ) : !open ? (
            <button type="button" onClick={() => setOpen(true)} className="text-slate-500 underline hover:text-slate-300">
              出場していないのに載っている場合（本人のみ）
            </button>
          ) : (
            <div className="space-y-2">
              <textarea
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                rows={2}
                aria-label="異議の理由"
                placeholder="出場していない理由・事情"
                className="w-full resize-none rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-xs text-white outline-none focus:border-brand-500"
              />
              <button
                type="button"
                disabled={!reason.trim() || dispute.isPending}
                onClick={() => dispute.mutate()}
                className="rounded-lg bg-brand-500 px-3 py-1.5 font-semibold text-white disabled:opacity-40"
              >
                異議を出す
              </button>
              {dispute.isError && (
                <p role="alert" className="text-red-400">
                  {dispute.error instanceof Error ? dispute.error.message : "異議を出せませんでした"}
                </p>
              )}
            </div>
          )}
        </div>
      )}
    </section>
  );
}
