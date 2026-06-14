"use client";

import { Medal, ListOrdered } from "lucide-react";
import { useRankings } from "@/features/analytics/hooks/use-analytics";
import { cn } from "@/lib/utils";

interface StandingsTabProps {
  tournamentId: string;
}

const MEDAL_COLORS = ["text-yellow-400", "text-slate-300", "text-amber-600"];

export function StandingsTab({ tournamentId }: StandingsTabProps) {
  const { data: rankings, isLoading, isError } = useRankings(tournamentId);

  if (isLoading) {
    return (
      <div className="space-y-2 pt-6">
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} className="h-14 animate-pulse rounded-xl bg-white/5" />
        ))}
      </div>
    );
  }

  if (isError) {
    return (
      <div className="py-16 text-center text-slate-400 pt-6">
        順位表の読み込みに失敗しました
      </div>
    );
  }

  if (!rankings || rankings.length === 0) {
    return (
      <div className="flex flex-col items-center py-24 text-center pt-6">
        <ListOrdered className="mb-4 h-12 w-12 text-slate-700" />
        <p className="font-semibold text-white">順位表はまだありません</p>
        <p className="mt-1 text-sm text-slate-400">大会終了後に順位が確定します</p>
      </div>
    );
  }

  return (
    <div className="pt-6">
      <div className="overflow-hidden rounded-xl border border-white/10">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-white/10 bg-white/5">
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500 w-12">
                順位
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">
                チーム
              </th>
              <th className="px-4 py-3 text-center text-xs font-semibold uppercase tracking-wider text-slate-500 w-16">
                勝
              </th>
              <th className="px-4 py-3 text-center text-xs font-semibold uppercase tracking-wider text-slate-500 w-16">
                負
              </th>
              <th className="px-4 py-3 text-center text-xs font-semibold uppercase tracking-wider text-slate-500 w-20">
                勝率
              </th>
              <th className="px-4 py-3 text-center text-xs font-semibold uppercase tracking-wider text-slate-500 w-20">
                ポイント
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5 bg-slate-900">
            {rankings.map((entry, idx) => {
              const rank = idx + 1;
              const hasMedal = rank <= 3;
              const winRate = (entry.win_rate * 100).toFixed(1);

              return (
                <tr
                  key={entry.team_id}
                  className={cn(
                    "transition-colors hover:bg-white/5",
                    rank === 1 && "bg-yellow-500/5",
                  )}
                >
                  {/* 順位 */}
                  <td className="px-4 py-3.5 text-center">
                    {hasMedal ? (
                      <Medal className={cn("mx-auto h-5 w-5", MEDAL_COLORS[rank - 1])} />
                    ) : (
                      <span className="font-mono text-slate-500">{rank}</span>
                    )}
                  </td>

                  {/* チーム */}
                  <td className="px-4 py-3.5">
                    <div className="flex items-center gap-3">
                      {entry.team_logo_url ? (
                        <img
                          src={entry.team_logo_url}
                          alt={entry.team_name}
                          className="h-7 w-7 rounded-md object-contain"
                        />
                      ) : (
                        <div className="flex h-7 w-7 items-center justify-center rounded-md bg-white/10">
                          <span className="text-[10px] font-bold text-slate-500">
                            {entry.team_name.slice(0, 2)}
                          </span>
                        </div>
                      )}
                      <div>
                        <p className={cn("font-semibold", hasMedal ? "text-white" : "text-slate-300")}>
                          {entry.team_name}
                        </p>
                        {entry.team_tag && (
                          <p className="text-xs text-slate-600">{entry.team_tag}</p>
                        )}
                      </div>
                    </div>
                  </td>

                  {/* 勝 */}
                  <td className="px-4 py-3.5 text-center font-semibold text-green-400">
                    {entry.wins}
                  </td>

                  {/* 負 */}
                  <td className="px-4 py-3.5 text-center font-semibold text-red-400">
                    {entry.losses}
                  </td>

                  {/* 勝率 */}
                  <td className="px-4 py-3.5 text-center text-slate-300">
                    {winRate}%
                  </td>

                  {/* ポイント */}
                  <td className="px-4 py-3.5 text-center font-bold text-brand-400">
                    {entry.points}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
