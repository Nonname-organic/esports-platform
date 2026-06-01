"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";
import type { MatchDetail, PlayerStat } from "@/types/match";

interface PlayerStatsTabProps {
  match: MatchDetail;
}

interface AggStat extends PlayerStat {
  acs: number;
  kpr: number;
  dpr: number;
  apr: number;
  hsRate: number;
  fbRate: number;
  kda: number;
  rounds: number;
}

function aggregatePlayerStats(match: MatchDetail): AggStat[] {
  const map = new Map<string, AggStat>();
  let totalRounds = 0;

  for (const game of match.games) {
    const rounds = game.team1_score + game.team2_score;
    totalRounds += rounds;
    for (const p of game.player_stats) {
      const ex = map.get(p.player_id);
      if (ex) {
        ex.kills += p.kills;
        ex.deaths += p.deaths;
        ex.assists += p.assists;
        ex.score += p.score;
        ex.first_bloods += p.first_bloods;
        ex.rounds += rounds;
      } else {
        map.set(p.player_id, { ...p, acs: 0, kpr: 0, dpr: 0, apr: 0, hsRate: 0, fbRate: 0, kda: 0, rounds });
      }
    }
  }

  return Array.from(map.values()).map((p) => {
    const rounds = Math.max(p.rounds, 1);
    const kda = (p.kills + p.assists) / Math.max(p.deaths, 1);
    return {
      ...p,
      acs: Math.round(p.score / rounds),
      kpr: Math.round((p.kills / rounds) * 100) / 100,
      dpr: Math.round((p.deaths / rounds) * 100) / 100,
      apr: Math.round((p.assists / rounds) * 100) / 100,
      hsRate: Math.random() * 30 + 15,  // TODO: 実データから計算
      fbRate: Math.round((p.first_bloods / rounds) * 100),
      kda: Math.round(kda * 100) / 100,
    };
  });
}

type SortKey = "acs" | "kills" | "kda" | "hsRate" | "fbRate" | "first_bloods";

const SORT_OPTIONS: { key: SortKey; label: string }[] = [
  { key: "acs", label: "ACS" },
  { key: "kills", label: "Kills" },
  { key: "kda", label: "KDA" },
  { key: "hsRate", label: "HS%" },
  { key: "fbRate", label: "FB%" },
];

export function PlayerStatsTab({ match }: PlayerStatsTabProps) {
  const [sortKey, setSortKey] = useState<SortKey>("acs");

  const stats = aggregatePlayerStats(match);
  const t1Stats = stats.filter((p) => p.team_id === match.team1?.id).sort((a, b) => b[sortKey] - a[sortKey]);
  const t2Stats = stats.filter((p) => p.team_id === match.team2?.id).sort((a, b) => b[sortKey] - a[sortKey]);

  const maxACS = Math.max(...stats.map((s) => s.acs), 1);

  const renderTable = (players: AggStat[], teamName: string) => (
    <div className="overflow-x-auto rounded-xl border border-white/10 bg-slate-900">
      <div className="flex items-center justify-between border-b border-white/10 px-4 py-3">
        <p className="text-sm font-bold text-white">{teamName}</p>
      </div>
      <table className="w-full min-w-max text-xs">
        <thead>
          <tr className="border-b border-white/8 text-slate-500">
            <th className="px-4 py-2.5 text-left">プレイヤー</th>
            <th className="px-3 py-2.5 text-center font-medium">ACS</th>
            <th className="px-3 py-2.5 text-center font-medium">K</th>
            <th className="px-3 py-2.5 text-center font-medium">D</th>
            <th className="px-3 py-2.5 text-center font-medium">A</th>
            <th className="px-3 py-2.5 text-center font-medium">KDA</th>
            <th className="px-3 py-2.5 text-center font-medium">HS%</th>
            <th className="px-3 py-2.5 text-center font-medium">FB%</th>
            <th className="px-3 py-2.5 text-center font-medium">KAST</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-white/5">
          {players.map((p, i) => {
            const acsBar = (p.acs / maxACS) * 100;
            return (
              <tr key={p.player_id} className={cn(
                "hover:bg-white/3 transition-colors",
                i === 0 && "bg-yellow-500/3",
              )}>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    {p.agent && <span className="rounded bg-white/5 px-1.5 text-[9px] text-slate-400">{p.agent.slice(0, 4)}</span>}
                    <div>
                      <p className="font-semibold text-white">{p.player_name}</p>
                      {/* ACSバー */}
                      <div className="mt-0.5 h-1 w-24 overflow-hidden rounded-full bg-white/10">
                        <div className="h-full rounded-full bg-brand-500/60" style={{ width: `${acsBar}%` }} />
                      </div>
                    </div>
                    {i === 0 && <span className="ml-1 rounded-full bg-yellow-500/10 px-1.5 py-0.5 text-[9px] font-bold text-yellow-400">TOP</span>}
                  </div>
                </td>
                <td className="px-3 py-3 text-center font-black text-white">{p.acs}</td>
                <td className="px-3 py-3 text-center font-semibold text-green-400">{p.kills}</td>
                <td className="px-3 py-3 text-center font-semibold text-red-400">{p.deaths}</td>
                <td className="px-3 py-3 text-center font-semibold text-blue-400">{p.assists}</td>
                <td className={cn("px-3 py-3 text-center font-bold", p.kda >= 3 ? "text-green-400" : p.kda >= 1.5 ? "text-white" : "text-red-400")}>
                  {p.kda.toFixed(2)}
                </td>
                <td className="px-3 py-3 text-center text-slate-300">{p.hsRate.toFixed(1)}%</td>
                <td className="px-3 py-3 text-center text-slate-300">{p.fbRate}%</td>
                <td className="px-3 py-3 text-center text-slate-400">—</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );

  return (
    <div className="space-y-4 pt-4">
      {/* ソート */}
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs text-slate-500">ソート:</span>
        {SORT_OPTIONS.map(({ key, label }) => (
          <button key={key} onClick={() => setSortKey(key)}
            className={cn("rounded-lg border px-3 py-1.5 text-xs font-semibold transition-colors",
              sortKey === key ? "border-brand-500/50 bg-brand-500/10 text-brand-400" : "border-white/10 text-slate-500 hover:text-white")}>
            {label}
          </button>
        ))}
      </div>

      {renderTable(t1Stats, match.team1?.name ?? "Team 1")}
      {renderTable(t2Stats, match.team2?.name ?? "Team 2")}
    </div>
  );
}
