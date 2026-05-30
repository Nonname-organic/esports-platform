"use client";

import { BarChart2, Users, Map, Trophy } from "lucide-react";
import { useRankings, useMapStats } from "@/features/analytics/hooks/use-analytics";
import { cn } from "@/lib/utils";
import type { TournamentDetail } from "@/types/tournament";

interface AnalyticsTabProps {
  tournament: TournamentDetail;
}

export function AnalyticsTab({ tournament }: AnalyticsTabProps) {
  const { data: rankings, isLoading: rankingsLoading } = useRankings(tournament.id);
  const { data: mapStats, isLoading: mapsLoading } = useMapStats(tournament.game);

  const topTeams = rankings?.slice(0, 5) ?? [];
  const topMaps = mapStats?.slice(0, 5) ?? [];

  return (
    <div className="space-y-6 pt-6">
      {/* サマリーカード */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {[
          {
            label: "参加チーム数",
            value: tournament.registered_teams,
            icon: Users,
            color: "text-brand-400",
            bg: "bg-brand-500/10",
          },
          {
            label: "最大チーム数",
            value: tournament.max_teams,
            icon: Trophy,
            color: "text-yellow-400",
            bg: "bg-yellow-500/10",
          },
        ].map(({ label, value, icon: Icon, color, bg }) => (
          <div key={label} className="rounded-xl border border-white/10 bg-slate-900 p-4">
            <div className={cn("mb-2 inline-flex rounded-lg p-2", bg)}>
              <Icon className={cn("h-4 w-4", color)} />
            </div>
            <p className="text-2xl font-black text-white">{value}</p>
            <p className="text-xs text-slate-500">{label}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* トップチーム */}
        <section className="rounded-xl border border-white/10 bg-slate-900 p-5">
          <h3 className="mb-4 flex items-center gap-2 font-bold text-white">
            <Users className="h-4 w-4 text-brand-400" />
            チームランキング
          </h3>
          {rankingsLoading ? (
            <div className="space-y-2">
              {Array.from({ length: 5 }).map((_, i) => (
                <div key={i} className="h-10 animate-pulse rounded-lg bg-white/5" />
              ))}
            </div>
          ) : topTeams.length === 0 ? (
            <p className="py-8 text-center text-sm text-slate-500">データなし</p>
          ) : (
            <ol className="space-y-2">
              {topTeams.map((team, idx) => {
                const winRate = (team.win_rate * 100).toFixed(0);
                const maxPoints = Math.max(...topTeams.map((t) => t.points), 1);
                const barWidth = (team.points / maxPoints) * 100;

                return (
                  <li key={team.team_id} className="flex items-center gap-3">
                    <span className="w-5 text-center text-sm font-bold text-slate-500">{idx + 1}</span>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between gap-2">
                        <p className="truncate text-sm font-semibold text-white">{team.team_name}</p>
                        <div className="flex-shrink-0 text-right">
                          <span className="text-xs text-slate-500">{winRate}%</span>
                          <span className="ml-2 text-sm font-bold text-brand-400">{team.points}pt</span>
                        </div>
                      </div>
                      <div className="mt-1 h-1 rounded-full bg-white/10">
                        <div
                          className="h-full rounded-full bg-brand-500/60"
                          style={{ width: `${barWidth}%` }}
                        />
                      </div>
                    </div>
                  </li>
                );
              })}
            </ol>
          )}
        </section>

        {/* マップ統計 */}
        <section className="rounded-xl border border-white/10 bg-slate-900 p-5">
          <h3 className="mb-4 flex items-center gap-2 font-bold text-white">
            <Map className="h-4 w-4 text-brand-400" />
            {tournament.game} マップ勝率
          </h3>
          {mapsLoading ? (
            <div className="space-y-2">
              {Array.from({ length: 5 }).map((_, i) => (
                <div key={i} className="h-10 animate-pulse rounded-lg bg-white/5" />
              ))}
            </div>
          ) : topMaps.length === 0 ? (
            <p className="py-8 text-center text-sm text-slate-500">データなし</p>
          ) : (
            <ol className="space-y-3">
              {topMaps.map((map) => {
                const atkRate = map.total_rounds > 0
                  ? ((map.attacker_wins / map.total_rounds) * 100).toFixed(0)
                  : "50";

                return (
                  <li key={map.map_id}>
                    <div className="flex items-center justify-between gap-2 text-sm">
                      <span className="font-semibold text-white">{map.map_name}</span>
                      <span className="text-xs text-slate-500">{map.total_rounds} ラウンド</span>
                    </div>
                    <div className="mt-1 flex h-2 overflow-hidden rounded-full bg-white/10">
                      <div
                        className="bg-blue-500/60"
                        style={{ width: `${atkRate}%` }}
                        title={`ATK ${atkRate}%`}
                      />
                      <div
                        className="bg-orange-500/60"
                        style={{ width: `${100 - Number(atkRate)}%` }}
                        title={`DEF ${100 - Number(atkRate)}%`}
                      />
                    </div>
                    <div className="mt-0.5 flex justify-between text-xs text-slate-600">
                      <span>ATK {atkRate}%</span>
                      <span>DEF {100 - Number(atkRate)}%</span>
                    </div>
                  </li>
                );
              })}
            </ol>
          )}
        </section>
      </div>

      <div className="rounded-xl border border-brand-500/20 bg-brand-500/5 p-4">
        <div className="flex items-start gap-3">
          <BarChart2 className="mt-0.5 h-4 w-4 flex-shrink-0 text-brand-400" />
          <p className="text-sm text-slate-400">
            詳細な分析データは
            <a href="/dashboard/analytics" className="ml-1 text-brand-400 hover:text-brand-300 underline">
              アナリティクスダッシュボード
            </a>
            でご確認いただけます。
          </p>
        </div>
      </div>
    </div>
  );
}
