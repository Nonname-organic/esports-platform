"use client";

import { cn } from "@/lib/utils";
import type { MatchDetail, PlayerStat } from "@/types/match";

interface TeamStatsTabProps {
  match: MatchDetail;
}

interface TeamAggregate {
  kills: number;
  deaths: number;
  assists: number;
  score: number;
  first_bloods: number;
  players: number;
}

function aggregateTeam(stats: PlayerStat[]): TeamAggregate {
  return stats.reduce((acc, p) => ({
    kills: acc.kills + p.kills,
    deaths: acc.deaths + p.deaths,
    assists: acc.assists + p.assists,
    score: acc.score + p.score,
    first_bloods: acc.first_bloods + p.first_bloods,
    players: acc.players + 1,
  }), { kills: 0, deaths: 0, assists: 0, score: 0, first_bloods: 0, players: 0 });
}

function StatBar({ label, t1: t1v, t2: t2v, unit = "" }: {
  label: string; t1: number; t2: number; unit?: string;
}) {
  const total = t1v + t2v || 1;
  const t1Pct = (t1v / total) * 100;
  const t1Win = t1v >= t2v;

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-xs">
        <span className={cn("font-bold", t1Win ? "text-white" : "text-slate-400")}>{t1v}{unit}</span>
        <span className="text-slate-500">{label}</span>
        <span className={cn("font-bold", !t1Win ? "text-white" : "text-slate-400")}>{t2v}{unit}</span>
      </div>
      <div className="flex h-2 overflow-hidden rounded-full">
        <div className="bg-brand-500" style={{ width: `${t1Pct}%` }} />
        <div className="bg-red-500/70 flex-1" />
      </div>
    </div>
  );
}

export function TeamStatsTab({ match }: TeamStatsTabProps) {
  const allStats = match.games.flatMap((g) => g.player_stats);
  const t1All = allStats.filter((p) => p.team_id === match.team1?.id);
  const t2All = allStats.filter((p) => p.team_id === match.team2?.id);

  const t1 = aggregateTeam(t1All);
  const t2 = aggregateTeam(t2All);

  const t1Games = match.games.filter((g) => g.winner_id === match.team1?.id).length;
  const t2Games = match.games.filter((g) => g.winner_id === match.team2?.id).length;

  return (
    <div className="space-y-5 pt-4">
      {/* チーム比較 */}
      <div className="rounded-xl border border-white/10 bg-slate-900 p-5">
        <div className="mb-5 grid grid-cols-[1fr_auto_1fr] items-center gap-4 text-center">
          <div>
            <p className="text-sm font-bold text-white">{match.team1?.name}</p>
            <p className="text-xs text-slate-500">[{match.team1?.tag}]</p>
          </div>
          <div>
            <p className="text-3xl font-black text-white">{t1Games} : {t2Games}</p>
            <p className="text-xs text-slate-500">マップ</p>
          </div>
          <div>
            <p className="text-sm font-bold text-white">{match.team2?.name}</p>
            <p className="text-xs text-slate-500">[{match.team2?.tag}]</p>
          </div>
        </div>

        <div className="space-y-4">
          <StatBar label="Total Kills" t1={t1.kills} t2={t2.kills} />
          <StatBar label="Deaths" t1={t1.deaths} t2={t2.deaths} />
          <StatBar label="Assists" t1={t1.assists} t2={t2.assists} />
          <StatBar label="First Bloods" t1={t1.first_bloods} t2={t2.first_bloods} />
          <StatBar label="Total Score" t1={t1.score} t2={t2.score} />
        </div>
      </div>

      {/* マップ別結果 */}
      <div className="rounded-xl border border-white/10 bg-slate-900 p-5">
        <h3 className="mb-4 text-sm font-bold text-white">マップ別結果</h3>
        <div className="space-y-2">
          {match.games.map((game) => {
            const t1Win = game.winner_id === match.team1?.id;
            const t2Win = game.winner_id === match.team2?.id;
            const dur = game.duration_seconds
              ? `${Math.floor(game.duration_seconds / 60)}:${String(game.duration_seconds % 60).padStart(2, "0")}`
              : "—";

            return (
              <div key={game.id} className="flex items-center justify-between rounded-lg bg-white/3 px-4 py-3">
                <span className={cn("text-sm font-semibold", t1Win ? "text-green-400" : "text-slate-400")}>
                  {game.team1_score}
                </span>
                <div className="text-center">
                  <p className="text-sm font-bold text-white">{game.map_name ?? `Map ${game.game_number}`}</p>
                  <p className="text-xs text-slate-500">{dur}</p>
                </div>
                <span className={cn("text-sm font-semibold", t2Win ? "text-green-400" : "text-slate-400")}>
                  {game.team2_score}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
