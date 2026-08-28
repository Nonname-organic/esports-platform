"use client";

import Link from "next/link";
import { Medal, Users, ExternalLink } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { useRankings, usePlayerRankings } from "@/features/analytics/hooks/use-analytics";
import { rankingApi } from "@/features/rankings/api/ranking-api";
import { useAnalyticsFilterStore } from "@/store/analytics-filter-store";
import { cn } from "@/lib/utils";
import type { RankingEntry, PlayerRankingEntry } from "@/types/analytics";

function Skeleton() {
  return (
    <div className="space-y-2">
      {Array.from({ length: 5 }).map((_, i) => (
        <div key={i} className="h-12 animate-pulse rounded-lg bg-white/5" />
      ))}
    </div>
  );
}

const MEDAL = ["🥇", "🥈", "🥉"];

function RankCell({ rank }: { rank: number }) {
  if (rank <= 3) return <span className="text-base">{MEDAL[rank - 1]}</span>;
  return <span className="font-mono text-sm text-slate-500">{rank}</span>;
}

// ── チームランキング ───────────────────────────────────────────────────────────
function TeamRankingTable({ data }: { data: RankingEntry[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-white/8 text-xs text-slate-500">
            <th className="pb-2.5 text-center w-8">#</th>
            <th className="pb-2.5 text-left">チーム</th>
            <th className="pb-2.5 text-center w-10">勝</th>
            <th className="pb-2.5 text-center w-10">敗</th>
            <th className="pb-2.5 w-28">勝率</th>
            <th className="pb-2.5 text-right w-12">Pt</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-white/5">
          {data.map((entry) => {
            const wr = Math.round(entry.win_rate * 100);
            return (
              <tr
                key={entry.team_id}
                className={cn(
                  "hover:bg-white/3 transition-colors",
                  entry.rank_position === 1 && "bg-yellow-500/3",
                )}
              >
                <td className="py-2.5 text-center">
                  <RankCell rank={entry.rank_position} />
                </td>
                <td className="py-2.5">
                  <div className="flex items-center gap-2">
                    <div className="h-7 w-7 flex-shrink-0 overflow-hidden rounded-lg border border-white/10 bg-slate-800 flex items-center justify-center">
                      {entry.team_logo_url ? (
                        <img src={entry.team_logo_url} alt="" className="h-full w-full object-contain" />
                      ) : (
                        <span className="text-[9px] font-bold text-slate-500">{entry.team_tag.slice(0, 2)}</span>
                      )}
                    </div>
                    <div>
                      <p className="font-semibold text-white leading-tight">{entry.team_name}</p>
                      <p className="text-[10px] text-slate-600">{entry.team_tag}</p>
                    </div>
                  </div>
                </td>
                <td className="py-2.5 text-center font-semibold text-green-400">{entry.wins}</td>
                <td className="py-2.5 text-center font-semibold text-red-400">{entry.losses}</td>
                <td className="py-2.5">
                  <div className="flex items-center gap-1.5">
                    <div className="flex-1 h-1.5 overflow-hidden rounded-full bg-white/10">
                      <div
                        className={cn(
                          "h-full rounded-full",
                          wr >= 60 ? "bg-green-500" : wr >= 40 ? "bg-yellow-500" : "bg-red-500",
                        )}
                        style={{ width: `${wr}%` }}
                      />
                    </div>
                    <span className="w-8 text-right text-xs text-slate-400">{wr}%</span>
                  </div>
                </td>
                <td className="py-2.5 text-right font-bold text-white">{entry.points}</td>
              </tr>
            );
          })}
          {data.length === 0 && (
            <tr>
              <td colSpan={6} className="py-8 text-center text-sm text-slate-500">
                ランキングデータがありません
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

// ── プレイヤーランキング ───────────────────────────────────────────────────────
function PlayerRankingTable({ data }: { data: PlayerRankingEntry[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-white/8 text-xs text-slate-500">
            <th className="pb-2.5 text-center w-8">#</th>
            <th className="pb-2.5 text-left">プレイヤー</th>
            <th className="pb-2.5 text-center w-12">KDA</th>
            <th className="pb-2.5 text-center w-12">K/D</th>
            <th className="pb-2.5 text-center w-10">勝率</th>
            <th className="pb-2.5 w-8" />
          </tr>
        </thead>
        <tbody className="divide-y divide-white/5">
          {data.map((entry) => (
            <tr key={entry.player_id} className="hover:bg-white/3 transition-colors">
              <td className="py-2.5 text-center">
                <RankCell rank={entry.rank} />
              </td>
              <td className="py-2.5">
                <div className="flex items-center gap-2">
                  <div className="h-7 w-7 flex-shrink-0 overflow-hidden rounded-full border border-white/10 bg-slate-800 flex items-center justify-center">
                    {entry.avatar_url ? (
                      <img src={entry.avatar_url} alt="" className="h-full w-full object-cover" />
                    ) : (
                      <span className="text-[9px] font-bold text-slate-500">
                        {entry.player_name.charAt(0)}
                      </span>
                    )}
                  </div>
                  <div>
                    <p className="font-semibold text-white leading-tight">
                      {entry.in_game_name ?? entry.player_name}
                    </p>
                    <p className="text-[10px] text-slate-600">{entry.team_name ?? "—"}</p>
                  </div>
                </div>
              </td>
              <td className="py-2.5 text-center">
                <span className={cn("font-bold tabular-nums", entry.avg_kda >= 3 ? "text-green-400" : entry.avg_kda >= 1.5 ? "text-white" : "text-red-400")}>
                  {entry.avg_kda.toFixed(2)}
                </span>
              </td>
              <td className="py-2.5 text-center text-xs tabular-nums text-slate-400">
                {entry.avg_kills.toFixed(1)}/{entry.avg_deaths.toFixed(1)}
              </td>
              <td className="py-2.5 text-center text-xs text-slate-400">
                {(entry.win_rate * 100).toFixed(0)}%
              </td>
              <td className="py-2.5">
                <Link
                  href={`/players/${entry.player_id}`}
                  className="text-slate-600 hover:text-white transition-colors"
                >
                  <ExternalLink className="h-3.5 w-3.5" />
                </Link>
              </td>
            </tr>
          ))}
          {data.length === 0 && (
            <tr>
              <td colSpan={7} className="py-8 text-center text-sm text-slate-500">
                プレイヤーデータがありません
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

// ── セクション ────────────────────────────────────────────────────────────────
export function RankingsSection() {
  const { game, tournamentId } = useAnalyticsFilterStore();

  const { data: teamRankings, isLoading: isLoadingTeams } = useRankings(tournamentId);

  // 大会未選択（全大会）のときは大会別ランキングが引けないため、
  // 全大会の成績を合算した総合ランキングの上位20チームを表示する
  const { data: globalTeams, isLoading: isLoadingGlobal } = useQuery({
    queryKey: ["analytics", "global-team-rankings", game],
    queryFn: () => rankingApi.global({ game, limit: 20 }),
    select: (res) =>
      res.data.map<RankingEntry>((e) => ({
        rank_position: e.rank,
        team_id: e.team_id,
        team_name: e.team_name,
        team_tag: e.team_tag,
        team_logo_url: e.team_logo_url,
        points: e.rp,
        wins: e.wins,
        losses: e.losses,
        game_wins: 0,
        game_losses: 0,
        win_rate: e.win_rate,
      })),
    enabled: !tournamentId,
    staleTime: 60 * 1000,
  });

  const teamRows = tournamentId ? (teamRankings ?? []) : (globalTeams ?? []);
  const teamsLoading = tournamentId ? isLoadingTeams : isLoadingGlobal;
  const { data: playerRankings, isLoading: isLoadingPlayers } = usePlayerRankings({
    game,
    tournamentId: tournamentId || undefined,
    limit: 20,
  });

  return (
    <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
      {/* チームランキング */}
      <section className="rounded-xl border border-white/10 bg-slate-900">
        <div className="flex items-center gap-2 border-b border-white/10 px-5 py-4">
          <div className="rounded-lg bg-yellow-500/10 p-1.5">
            <Medal className="h-4 w-4 text-yellow-400" />
          </div>
          <h2 className="text-sm font-bold text-white">チームランキング</h2>
          <span className="ml-auto text-[10px] text-slate-600">
            {tournamentId ? "大会内の順位" : "全大会合算 · 上位20"}
          </span>
        </div>
        <div className="px-5 py-4">
          {teamsLoading ? <Skeleton /> : <TeamRankingTable data={teamRows} />}
        </div>
      </section>

      {/* プレイヤーランキング */}
      <section className="rounded-xl border border-white/10 bg-slate-900">
        <div className="flex items-center gap-2 border-b border-white/10 px-5 py-4">
          <div className="rounded-lg bg-green-500/10 p-1.5">
            <Users className="h-4 w-4 text-green-400" />
          </div>
          <h2 className="text-sm font-bold text-white">プレイヤーランキング</h2>
          <span className="ml-auto text-[10px] text-slate-600">KDA順</span>
        </div>
        <div className="px-5 py-4">
          {isLoadingPlayers ? <Skeleton /> : <PlayerRankingTable data={playerRankings ?? []} />}
        </div>
      </section>
    </div>
  );
}
