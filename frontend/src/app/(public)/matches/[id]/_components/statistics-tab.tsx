import { useState } from "react";
import { BarChart2 } from "lucide-react";
import { cn } from "@/lib/utils";
import type { MatchDetail, PlayerStat } from "@/types/match";

interface StatisticsTabProps {
  match: MatchDetail;
}

interface AggregatedStat {
  player_id: string;
  player_name: string;
  team_id: string;
  kills: number;
  deaths: number;
  assists: number;
  score: number;
  first_bloods: number;
  games: number;
  agent: string | null;
}

function aggregateStats(match: MatchDetail): AggregatedStat[] {
  const map = new Map<string, AggregatedStat>();
  for (const game of match.games) {
    for (const p of game.player_stats) {
      const existing = map.get(p.player_id);
      if (existing) {
        existing.kills += p.kills;
        existing.deaths += p.deaths;
        existing.assists += p.assists;
        existing.score += p.score;
        existing.first_bloods += p.first_bloods;
        existing.games += 1;
      } else {
        map.set(p.player_id, {
          player_id: p.player_id,
          player_name: p.player_name,
          team_id: p.team_id,
          kills: p.kills,
          deaths: p.deaths,
          assists: p.assists,
          score: p.score,
          first_bloods: p.first_bloods,
          games: 1,
          agent: p.agent,
        });
      }
    }
  }
  return Array.from(map.values());
}

type SortKey = "kda" | "kills" | "deaths" | "assists" | "score" | "first_bloods";

export function StatisticsTab({ match }: StatisticsTabProps) {
  const [sortKey, setSortKey] = useState<SortKey>("kda");

  const allStats = aggregateStats(match);
  if (allStats.length === 0) {
    return (
      <div className="flex h-48 items-center justify-center pt-4">
        <p className="text-sm text-slate-500">統計データがまだありません</p>
      </div>
    );
  }

  const t1Stats = allStats.filter((p) => p.team_id === match.team1?.id);
  const t2Stats = allStats.filter((p) => p.team_id === match.team2?.id);

  const sortFn = (a: AggregatedStat, b: AggregatedStat): number => {
    if (sortKey === "kda") {
      return ((b.kills + b.assists) / Math.max(b.deaths, 1)) - ((a.kills + a.assists) / Math.max(a.deaths, 1));
    }
    return (b[sortKey] as number) - (a[sortKey] as number);
  };

  const SORT_OPTIONS: { key: SortKey; label: string }[] = [
    { key: "kda", label: "KDA" },
    { key: "kills", label: "Kill" },
    { key: "deaths", label: "Death" },
    { key: "assists", label: "Assist" },
    { key: "score", label: "スコア" },
    { key: "first_bloods", label: "FB" },
  ];

  return (
    <div className="space-y-5 pt-4">
      {/* ソート切替 */}
      <div className="flex flex-wrap items-center gap-1.5">
        <span className="text-xs text-slate-500">ソート:</span>
        {SORT_OPTIONS.map(({ key, label }) => (
          <button
            key={key}
            onClick={() => setSortKey(key)}
            className={cn(
              "rounded-lg border px-3 py-1.5 text-xs font-semibold transition-colors",
              sortKey === key
                ? "border-brand-500/50 bg-brand-500/10 text-brand-400"
                : "border-white/10 text-slate-500 hover:text-white",
            )}
          >
            {label}
          </button>
        ))}
      </div>

      {/* 両チームのスタッツ */}
      <div className="grid gap-5 md:grid-cols-2">
        <StatsTable
          players={[...t1Stats].sort(sortFn)}
          teamName={match.team1?.name ?? "Team 1"}
          sortKey={sortKey}
        />
        <StatsTable
          players={[...t2Stats].sort(sortFn)}
          teamName={match.team2?.name ?? "Team 2"}
          sortKey={sortKey}
        />
      </div>
    </div>
  );
}

function StatsTable({
  players, teamName, sortKey,
}: { players: AggregatedStat[]; teamName: string; sortKey: SortKey; }) {
  return (
    <div className="rounded-xl border border-white/10 bg-slate-900">
      <div className="border-b border-white/10 px-4 py-3">
        <h3 className="text-sm font-bold text-white">{teamName}</h3>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-white/8 text-slate-500">
              <th className="px-4 py-2.5 text-left font-medium">プレイヤー</th>
              <th className={cn("px-2 py-2.5 text-center font-medium", sortKey === "kills" && "text-green-400")}>K</th>
              <th className={cn("px-2 py-2.5 text-center font-medium", sortKey === "deaths" && "text-red-400")}>D</th>
              <th className={cn("px-2 py-2.5 text-center font-medium", sortKey === "assists" && "text-blue-400")}>A</th>
              <th className={cn("px-2 py-2.5 text-center font-medium", sortKey === "kda" && "text-brand-400")}>KDA</th>
              <th className={cn("px-2 py-2.5 text-center font-medium", sortKey === "score" && "text-yellow-400")}>Score</th>
              <th className={cn("px-2 py-2.5 text-center font-medium", sortKey === "first_bloods" && "text-purple-400")}>FB</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5">
            {players.map((p, i) => {
              const kda = ((p.kills + p.assists) / Math.max(p.deaths, 1)).toFixed(2);
              const avgScore = Math.round(p.score / p.games);
              return (
                <tr key={p.player_id} className={cn("hover:bg-white/3 transition-colors", i === 0 && "bg-yellow-500/3")}>
                  <td className="px-4 py-2.5">
                    <div className="flex items-center gap-1.5">
                      {p.agent && <span className="rounded bg-white/5 px-1 text-[9px] text-slate-500">{p.agent.slice(0, 4)}</span>}
                      <span className="truncate font-medium text-slate-200 max-w-[80px]">{p.player_name}</span>
                    </div>
                  </td>
                  <td className="px-2 py-2.5 text-center font-semibold text-green-400">{p.kills}</td>
                  <td className="px-2 py-2.5 text-center font-semibold text-red-400">{p.deaths}</td>
                  <td className="px-2 py-2.5 text-center font-semibold text-blue-400">{p.assists}</td>
                  <td className={cn("px-2 py-2.5 text-center font-black", Number(kda) >= 3 ? "text-green-400" : Number(kda) >= 1.5 ? "text-white" : "text-red-400")}>
                    {kda}
                  </td>
                  <td className="px-2 py-2.5 text-center text-slate-300">{avgScore}</td>
                  <td className="px-2 py-2.5 text-center text-purple-400">{p.first_bloods}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
